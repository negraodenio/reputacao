import re
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from pathlib import Path
from services.audit_service import run_audit, _build_npa
from services.constants import classify_domain, domain_authority

NEWS_DOMAIN_TYPES = {"mainstream", "investigative", "blog"}
from services.snapshot_service import compare_snapshots, get_latest_snapshot, get_two_latest_snapshots, infer_threat_from_snapshot, extract_negative_domains, extract_source_concentration, format_associations_from_snapshot, list_entities, get_all_snapshots
from services.cost_tracker import get_costs, get_latest_audit_cost
from services.archetype import ARCHETYPE_LABELS, CRISIS_STATE_LABELS
from services.serp_dominance import compute_serp_score, compute_domain_clusters, compute_position_map
from services.battle_planner import build_battle_plan
from services.content_producer import produce_article, save_article, load_article, list_cached_articles
from services.site_builder import build_news_site
from services.asset_service import generate_asset, generate_campaign, ASSET_TYPES
from services.response_service import generate_response, parse_response_sections
from services.occupation_service import generate_occupation, parse_occupation_sections
from services.youtube_warfare import extract_youtube_results, compute_youtube_toxicity, compute_video_npa_boost, youtube_ads_campaign
from services.knowledge_panel import compute_knowledge_panel_score, generate_wikidata_profile, generate_schema_org, kp_setup_guide
from services.recovery_probability import compute_recovery_probability
from services.crisis_stage import classify_crisis_stage, get_stage_config, stage_drives_response
from services.news_distribution import PORTALS, select_portals, generate_release_payload, compute_news_occupation_score, distribution_battle_section
from services.monitoring_engine import check_serp, check_news, check_npa_delta, get_monitor_summary, configure_monitoring, TRIGGERS, reset_monitoring, dispatch_alert
from services.linkedin_targeting import generate_linkedin_ads_plan, linkedin_battle_section
from urllib.parse import urlparse
from collections import Counter
import markdown
from services.pdf_service import serve_pdf

SNAPSHOTS_DIR = Path(__file__).parent.parent.parent / "snapshots"

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))
templates.env.filters["markdown"] = lambda text: markdown.markdown(text or "", extensions=["tables"])

SECTION_PATTERNS = [
    ("reputation_summary",      r"\d+\.\s+\**\s*(SUM[ÁA]RIO EXECUTIVO|REPUTATION SUMMARY|EXECUTIVE SUMMARY)\**"),
    ("negative_signals",        r"\d+\.\s+\**\s*(SINAIS NEGATIVOS|NEGATIVE SIGNALS|THREAT ASSESSMENT)\**"),
    ("positive_assets",         r"\d+\.\s+\**\s*(ATIVOS POSITIVOS|POSITIVE ASSETS|SEARCH BATTLEFIELD)\**"),
    ("narrative_analysis",      r"\d+\.\s+\**\s*(AN[ÁA]LISE NARRATIVA|NARRATIVE ANALYSIS)\**"),
    ("npa_interpretation",      r"\d+\.\s+\**\s*(INTERPRETA[CÇ][AÃ]O DA PRESS[ÃA]O NARRATIVA|NARRATIVE PRESSURE ANALYTICS)\**"),
    ("discovered_associations", r"\d+\.\s+\**\s*(ASSOCIA[CÇ][ÕO]ES DESCOBERTAS|DISCOVERED ASSOCIATIONS)\**"),
    ("suggested_positioning",   r"\d+\.\s+\**\s*(POSICIONAMENTO RECOMENDADO|SUGGESTED POSITIONING|STRATEGIC RESPONSE PLAN)\**"),
]


def _parse_sections(text: str) -> dict:
    boundaries = []
    for key, pattern in SECTION_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            boundaries.append((m.start(), m.end(), key))
    boundaries.sort()

    sections = {key: "" for key, _ in SECTION_PATTERNS}
    for i, (start, end, key) in enumerate(boundaries):
        next_start = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
        body = text[end:next_start].strip()
        # Strip markdown headings (## Heading)
        body = re.sub(r"^#+\s*", "", body, flags=re.MULTILINE)
        # Strip lines that are ONLY a bold heading — e.g. "**SINAIS NEGATIVOS**"
        # Does NOT strip inline bold like "**Risco:** texto" (has content after **)
        body = re.sub(r"^\*\*[^*]+\*\*\s*$", "", body, flags=re.MULTILINE)
        # Strip horizontal rules
        body = re.sub(r"^---+\s*$", "", body, flags=re.MULTILINE)
        sections[key] = body.strip()
    return sections


def _parse_npa_struct(news: list[dict], serp: list[dict] | None = None) -> dict:
    from services.metrics import compute_npa_domains
    return compute_npa_domains(news, serp)


def _infer_threat(sections: dict, npa: dict) -> str:
    momentum = npa.get("momentum", "Stable")
    count_7d = npa.get("count_7d", 0)
    neg = sections.get("negative_signals", "").lower()

    has_legal = any(w in neg for w in [
        "processo", "fraude", "criminal", "prisão", "condenado",
        "investigação", "denúncia", "acusação", "réu", "ação judicial",
        "mandado", "busca e apreensão", "quebra de sigilo", "indiciado",
    ])
    has_crisis = any(w in neg for w in [
        "escândalo", "crise", "polêmica", "controvérsia", "escandalo",
        "danos", "prejuízo", "reputação ameaçada", "controvérsia",
    ])

    if has_legal or (momentum == "Escalating" and has_crisis):
        return "CRITICAL"
    if momentum == "Escalating" and count_7d >= 3:
        return "HIGH"
    if momentum == "Escalating" or count_7d >= 2 or has_crisis:
        return "MEDIUM"
    return "LOW"


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/snapshots", response_class=HTMLResponse)
def snapshot_center(request: Request):
    entities = list_entities()
    for e in entities:
        e["_archetype_label"] = ARCHETYPE_LABELS.get(e.get("latest_archetype", ""), e.get("latest_archetype", "—"))
        e["_crisis_label"] = CRISIS_STATE_LABELS.get(e.get("latest_crisis", ""), e.get("latest_crisis", "—"))
    return templates.TemplateResponse("snapshots.html", {
        "request": request,
        "entities": entities,
    })


@router.get("/timeline/{entity:path}", response_class=HTMLResponse)
def entity_timeline(request: Request, entity: str):
    slug = _entity_slug(entity)
    snapshots = get_all_snapshots(slug)
    if not snapshots:
        return templates.TemplateResponse("result.html", {
            "request": request,
            "entity_name": entity,
            "result": None,
            "error": f"Nenhum snapshot encontrado para '{entity}'.",
        })

    timeline = []
    prev_score = None
    for s in snapshots:
        threat = infer_threat_from_snapshot(s)
        npa = s.get("narrative_pressure", {})
        order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
        curr = order.get(threat, 0)
        direction = "worsened" if prev_score and curr > prev_score else "improved" if prev_score and curr < prev_score else "stable"
        timeline.append({
            "date":      s["date"],
            "threat":    threat,
            "momentum":  npa.get("momentum", "Stable"),
            "direction": direction,
            "neg_ratio": round(s.get("page_1_negative_ratio", 0) * 100, 0),
            "controlled": s.get("controlled_assets", 0),
        })
        prev_score = curr

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return templates.TemplateResponse("timeline.html", {
        "request":      request,
        "entity_name":  snapshots[0]["entity"],
        "entity_slug":  slug,
        "timeline":     timeline,
        "generated_at": generated_at,
    })


@router.get("/costs", response_class=HTMLResponse)
def cost_dashboard(request: Request):
    entity = request.query_params.get("entity", "")
    last_n_param = request.query_params.get("last", "200")

    try:
        last_n = int(last_n_param)
    except ValueError:
        last_n = 200

    if entity:
        data = get_costs(entity=entity, last_n=last_n)
    else:
        data = get_costs(last_n=last_n)

    return templates.TemplateResponse("costs.html", {
        "request":  request,
        "costs":    data,
        "entity":   entity,
        "entities": list_entities(),
    })


@router.post("/", response_class=HTMLResponse)
def run(
    request: Request,
    entity_name: str = Form(...),
    country: str = Form(...),
    industry: str = Form(...),
):
    try:
        audit_result = run_audit(entity_name=entity_name, country=country, industry=industry)
        audit_text = audit_result["text"]
        sections = _parse_sections(audit_text)
        all_news = audit_result.get("all_news", [])
        serp = audit_result.get("serp", [])
        npa = _parse_npa_struct(all_news, serp)
        threat = _infer_threat(sections, npa)
        slug = _entity_slug(entity_name)
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        return templates.TemplateResponse("report.html", {
            "request": request,
            "entity_name": entity_name,
            "country": country,
            "industry": industry,
            "generated_at": generated_at,
            "threat_level": threat,
            "sections": sections,
            "npa": npa,
            "slug": slug,
        })
    except Exception as e:
        return templates.TemplateResponse("result.html", {
            "request": request,
            "entity_name": entity_name,
            "result": None,
            "error": str(e),
        })


@router.post("/pdf", response_class=Response)
def report_pdf(
    request: Request,
    entity_name: str = Form(...),
    country: str = Form(...),
    industry: str = Form(...),
):
    try:
        from services.pdf_service import generate_audit_pdf
        audit_result = run_audit(entity_name=entity_name, country=country, industry=industry)
        audit_text = audit_result["text"]
        sections = _parse_sections(audit_text)
        all_news = audit_result.get("all_news", [])
        serp = audit_result.get("serp", [])
        npa = _parse_npa_struct(all_news, serp)
        threat = _infer_threat(sections, npa)
        slug = _entity_slug(entity_name)
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        pdf_bytes = generate_audit_pdf(entity_name, threat, generated_at, sections, npa)
        filename = f"{slug}_auditoria_{datetime.now().strftime('%Y%m%d')}.pdf"
        return serve_pdf(pdf_bytes, filename)
    except Exception as e:
        import traceback
        return templates.TemplateResponse("result.html", {
            "request": request,
            "entity_name": entity_name,
            "result": None,
            "error": f"Erro ao gerar PDF: {e}<br><pre>{traceback.format_exc()}</pre>",
        })


@router.get("/snapshots/{entity_path:path}/compare/pdf", response_class=Response)
def compare_pdf(request: Request, entity_path: str):
    try:
        slug = entity_path.strip("/").replace("/", "_")
        pair = get_two_latest_snapshots(slug)
        if not pair or pair[0] is None:
            return templates.TemplateResponse("result.html", {
                "request": request, "result": None,
                "error": "Menos de 2 snapshots encontrados para gerar comparação.",
            })
        old_snap, new_snap = pair
        old_date = old_snap.get("date", "")
        new_date = new_snap.get("date", "")
        diff = compare_snapshots(
            str(SNAPSHOTS_DIR / slug / f"{old_date}.json"),
            str(SNAPSHOTS_DIR / slug / f"{new_date}.json"),
        )
        entity_name = new_snap.get("entity", slug)
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        from services.pdf_service import generate_compare_pdf
        pdf_bytes = generate_compare_pdf(entity_name, generated_at, old_snap, new_snap, diff)
        filename = f"{slug}_comparacao_{datetime.now().strftime('%Y%m%d')}.pdf"
        return serve_pdf(pdf_bytes, filename)
    except Exception as e:
        return templates.TemplateResponse("result.html", {
            "request": request,
            "entity_name": entity_name,
            "result": None,
            "error": str(e),
        })


@router.get("/serp-img/{slug}/{date}", response_class=Response)
def serve_serp_screenshot(slug: str, date: str):
    from fastapi.responses import FileResponse
    path = SNAPSHOTS_DIR / slug / f"serp_{date}.png"
    if path.exists():
        return FileResponse(str(path), media_type="image/png")
    return Response(status_code=404)


# ── Snapshot comparison helpers ────────────────────────────────

def _entity_slug(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s]", "", slug)
    slug = re.sub(r"\s+", "_", slug)
    return slug


def _find_snapshots(slug: str) -> tuple[dict, dict] | None:
    dir_path = SNAPSHOTS_DIR / slug
    if not dir_path.exists():
        return None
    files = sorted(dir_path.glob("*.json"))
    if len(files) < 2:
        return None
    import json
    old = json.loads(files[-2].read_text(encoding="utf-8"))
    new = json.loads(files[-1].read_text(encoding="utf-8"))
    return old, new


def _recovery_score(
    neg_displacement: int,
    asset_growth: int,
    top3_delta: int,
    old_momentum: str,
    new_momentum: str,
) -> int:
    # Negative displacement (max 30)
    nd_score = max(0, min(neg_displacement * 10, 30))
    # Asset growth (max 25)
    ag_score = max(0, min(asset_growth * 8, 25))
    # Top 3 reduction (max 25)
    t3_score = max(0, min(abs(top3_delta) * 12, 25)) if top3_delta < 0 else 0
    # Momentum improvement (max 20)
    order = {"Declining": 0, "Stable": 1, "Escalating": 2}
    old_val = order.get(old_momentum, 1)
    new_val = order.get(new_momentum, 1)
    delta = new_val - old_val
    if delta >= 2:
        mm_score = 20
    elif delta == 1:
        mm_score = 12
    elif delta == 0:
        mm_score = 5
    else:
        mm_score = 0
    return min(nd_score + ag_score + t3_score + mm_score, 100)


def _strategic_status(score: int, new_npa: dict, new_neg_ratio: float, new: dict) -> tuple[str, str]:
    # Escalating Crisis: triple-condition gate
    if (
        new_npa["momentum"] == "Escalating"
        and new.get("top_3_negative_count", 0) > 0
        and new.get("page_1_negative_ratio", 0) > 0.3
    ):
        return "Escalating Crisis", "Critical"
    if score < 20 or (new_npa["momentum"] == "Escalating" and new_neg_ratio > 0.5):
        return "Critical Exposure", "Critical"
    if score < 40:
        return "Active Stabilization", "Stabilization"
    if score < 70:
        return "Narrative Recovery", "Recovery"
    if score < 85:
        return "Authority Repositioning", "Repositioning"
    return "Stable Reputation", "Stable"


def _leverage_asset(old: dict, new: dict) -> dict | None:
    old_pos = {r["domain"]: r for r in old["serp"]}
    candidates = []
    for r in new["serp"]:
        if not r.get("controlled"):
            continue
        domain = r["domain"]
        if domain in old_pos and old_pos[domain].get("controlled"):
            delta = old_pos[domain]["position"] - r["position"]
            if delta > 0:
                candidates.append((delta, domain, old_pos[domain]["position"], r["position"]))
        elif domain not in old_pos:
            candidates.append((99, domain, None, r["position"]))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    _, domain, from_pos, to_pos = candidates[0]
    return {"domain": domain, "from_pos": from_pos, "to_pos": to_pos}


def _controlled_list(snapshot: dict) -> list[dict]:
    return [r for r in snapshot["serp"] if r.get("controlled")]


def _strategic_interpretation(
    score: int,
    status: str,
    old: dict,
    new: dict,
    comparison: dict,
    leverage: dict | None,
) -> str:
    lines = []
    rm = comparison["ranking_movement"]
    lines.append(f"Period analyzed: {old['date']} to {new['date']}.")
    lines.append(f"Recovery Score: {score}/100 — {status}.")

    nd = comparison["negative_displacement"]
    if nd > 0:
        lines.append(f"Negative signals displaced by {nd} positions. Positive directional shift confirmed.")
    elif nd < 0:
        lines.append(f"Negative signals increased by {abs(nd)}. Requires immediate narrative defense.")
    else:
        lines.append("Negative signal volume unchanged.")

    ag = comparison["asset_penetration_growth"]
    if ag > 0:
        lines.append(f"Controlled asset penetration grew by {ag}. Narrative share of voice improving.")
    elif ag == 0:
        lines.append("Controlled asset penetration stable. Opportunity to increase owned SERP presence.")

    t3 = comparison["top_3_negative_delta"]
    if t3 < 0:
        lines.append(f"Top 3 negative results reduced by {abs(t3)}. Critical risk zone clearing.")
    elif t3 > 0:
        lines.append(f"Top 3 negative results increased by {t3}. Escalating search risk.")

    if rm["new_negative_entrants"]:
        domains = ", ".join(d["domain"] for d in rm["new_negative_entrants"])
        lines.append(f"New negative sources entered top 10: {domains}. Monitor closely.")

    if leverage:
        lines.append(f"Highest leverage asset: {leverage['domain']} moved from #{leverage['from_pos']} to #{leverage['to_pos']}.")

    if rm["exited"]:
        domains = ", ".join(d["domain"] for d in rm["exited"])
        lines.append(f"Domains exited top 10: {domains}.")

    old_mom = old["narrative_pressure"]["momentum"]
    new_mom = new["narrative_pressure"]["momentum"]
    if old_mom != new_mom:
        lines.append(f"Narrative momentum shifted from {old_mom} to {new_mom}.")
    else:
        lines.append(f"Narrative momentum remains {new_mom}.")

    lines.append("")
    lines.append("Next recommended action: run targeted audit to validate findings and generate strategic response plan.")

    return "\n".join(lines)


@router.get("/compare/{entity:path}", response_class=HTMLResponse)
def compare(request: Request, entity: str):
    slug = _entity_slug(entity)
    pair = _find_snapshots(slug)
    if not pair:
        return templates.TemplateResponse("result.html", {
            "request": request,
            "entity_name": entity,
            "result": None,
            "error": f"Not enough snapshots found for '{entity}'. Run at least two audits first.",
        })

    old, new = pair
    comparison = compare_snapshots(
        str(SNAPSHOTS_DIR / slug / f"{old['date']}.json"),
        str(SNAPSHOTS_DIR / slug / f"{new['date']}.json"),
    )
    rm = comparison["ranking_movement"]
    nd = comparison["negative_displacement"]
    ag = comparison["asset_penetration_growth"]
    ns_delta = comparison["narrative_share_change_pp"]
    neg_ratio_delta = comparison["page_1_negative_ratio_delta"]
    neg_ratio_delta_str = f"{(neg_ratio_delta * 100):+.0f} pp"
    t3d = comparison["top_3_negative_delta"]

    old_npa = old["narrative_pressure"]
    new_npa = new["narrative_pressure"]

    score = _recovery_score(nd, ag, t3d, old_npa["momentum"], new_npa["momentum"])
    new_neg_ratio = new.get("page_1_negative_ratio", 0)
    status, status_class = _strategic_status(score, new_npa, new_neg_ratio, new)
    leverage = _leverage_asset(old, new)

    # Derived values for template
    old_neg_ratio_pct = round(old.get("page_1_negative_ratio", 0) * 100, 0)
    new_neg_ratio_pct = round(new.get("page_1_negative_ratio", 0) * 100, 0)
    old_ns_pct = round(old.get("controlled_assets", 0) / 10 * 100, 0)
    new_ns_pct = round(new.get("controlled_assets", 0) / 10 * 100, 0)

    order = {"Declining": 0, "Stable": 1, "Escalating": 2}
    old_val = order.get(old_npa["momentum"], 1)
    new_val = order.get(new_npa["momentum"], 1)
    momentum_improved = new_val > old_val
    momentum_worsened = new_val < old_val
    if momentum_improved:
        momentum_label = "Improved"
    elif momentum_worsened:
        momentum_label = "Worsened"
    else:
        momentum_label = "Unchanged"

    vac_order = {"HIGH": 2, "MODERATE": 1, "LOW": 0}
    old_vac = vac_order.get(old.get("authority_vacuum", "LOW"), 0)
    new_vac = vac_order.get(new.get("authority_vacuum", "LOW"), 0)
    av_improved = old_vac > new_vac
    av_worsened = old_vac < new_vac
    if av_improved:
        av_label = "Improved"
    elif av_worsened:
        av_label = "Worsened"
    else:
        av_label = old.get("authority_vacuum", "LOW")

    strategic_text = _strategic_interpretation(score, status, old, new, comparison, leverage)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Safe access for backward-compatible snapshot comparisons
    old_legal = old.get("legal_domain_count", None)
    new_legal = new.get("legal_domain_count", 0)
    old_av = old.get("authority_vacuum", None)
    new_av = new.get("authority_vacuum", "LOW")

    # Screenshot paths for before/after
    old_serp_png = f"/serp-img/{slug}/{old['date']}"
    new_serp_png = f"/serp-img/{slug}/{new['date']}"

    return templates.TemplateResponse("movement_report.html", {
        "request": request,
        "entity_name": old["entity"],
        "generated_at": generated_at,
        "recovery_score": score,
        "strategic_status": status,
        "strategic_status_class": status_class,
        "strategic_one_liner": strategic_text.split(".")[0] + "." if strategic_text else "",
        "old": old,
        "new": new,
        "old_legal_domain_count": old_legal,
        "new_legal_domain_count": new_legal,
        "old_authority_vacuum": old_av,
        "new_authority_vacuum": new_av,
        "ranking_movement": rm,
        "neg_displacement": nd,
        "asset_growth": ag,
        "ns_delta": ns_delta,
        "neg_ratio_delta_pp": neg_ratio_delta,
        "neg_ratio_delta_str": neg_ratio_delta_str,
        "top3_delta": t3d,
        "leverage_asset": leverage,
        "new_controlled_list": _controlled_list(new),
        "old_neg_ratio_pct": int(old_neg_ratio_pct),
        "new_neg_ratio_pct": int(new_neg_ratio_pct),
        "old_ns_pct": int(old_ns_pct),
        "new_ns_pct": int(new_ns_pct),
        "old_npa": old_npa,
        "new_npa": new_npa,
        "momentum_improved": momentum_improved,
        "momentum_worsened": momentum_worsened,
        "momentum_label": momentum_label,
        "authority_vacuum_improved": av_improved,
        "authority_vacuum_worsened": av_worsened,
        "authority_vacuum_label": av_label,
        "strategic_interpretation": strategic_text,
        "old_serp_png": old_serp_png,
        "new_serp_png": new_serp_png,
    })


# ── SERP Dominance Analysis ────────────────────────────────────────────────

@router.get("/dominance/{entity_path:path}", response_class=HTMLResponse)
def serp_dominance(request: Request, entity_path: str):
    slug = _entity_slug(entity_path)
    snap = get_latest_snapshot(slug)
    if not snap:
        return templates.TemplateResponse("result.html", {
            "request": request,
            "entity_name": entity_path,
            "result": None,
            "error": f"Nenhum snapshot encontrado para '{entity_path}'. Execute uma auditoria primeiro.",
        })

    enriched_serp = snap.get("serp", [])
    score = compute_serp_score(enriched_serp)
    clusters = compute_domain_clusters(enriched_serp)
    position_map = compute_position_map(enriched_serp)

    total = len(enriched_serp)
    ctrl_count = sum(1 for r in enriched_serp if r.get("controlled"))
    threat = infer_threat_from_snapshot(snap)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return templates.TemplateResponse("serp_dominance.html", {
        "request":       request,
        "entity_name":   snap["entity"],
        "entity_slug":   slug,
        "snapshot_date": snap["date"],
        "generated_at":  generated_at,
        "threat":        threat,
        "score":         score,
        "clusters":      clusters,
        "position_map":  position_map,
        "total_results": total,
        "ctrl_count":    ctrl_count,
    })


# ── SERP Battle Plan ───────────────────────────────────────────────────────

@router.get("/battle-plan/{entity_path:path}", response_class=HTMLResponse)
def serp_battle_plan(request: Request, entity_path: str):
    slug = _entity_slug(entity_path)
    snap = get_latest_snapshot(slug)
    if not snap:
        return templates.TemplateResponse("result.html", {
            "request": request,
            "entity_name": entity_path,
            "result": None,
            "error": f"Nenhum snapshot encontrado para '{entity_path}'. Execute uma auditoria primeiro.",
        })

    enriched_serp = snap.get("serp", [])
    score = compute_serp_score(enriched_serp)
    clusters = compute_domain_clusters(enriched_serp)
    threat = infer_threat_from_snapshot(snap)
    archetype = snap.get("threat_archetype", "")
    plan = build_battle_plan(enriched_serp, clusters, score, threat, archetype)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return templates.TemplateResponse("serp_battle_plan.html", {
        "request":       request,
        "entity_name":   snap["entity"],
        "entity_slug":   slug,
        "snapshot_date": snap["date"],
        "generated_at":  generated_at,
        "plan":          plan,
    })


# ── Content Production Studio ──────────────────────────────────────────────

@router.get("/content/{entity_path:path}", response_class=HTMLResponse)
def content_studio(request: Request, entity_path: str):
    slug = _entity_slug(entity_path)
    snap = get_latest_snapshot(slug)
    if not snap:
        return templates.TemplateResponse("result.html", {
            "request": request,
            "entity_name": entity_path,
            "result": None,
            "error": f"Nenhum snapshot encontrado para '{entity_path}'. Execute uma auditoria primeiro.",
        })

    enriched_serp = snap.get("serp", [])
    score = compute_serp_score(enriched_serp)
    clusters = compute_domain_clusters(enriched_serp)
    threat = infer_threat_from_snapshot(snap)
    archetype = snap.get("threat_archetype", "")
    plan = build_battle_plan(enriched_serp, clusters, score, threat, archetype)
    content_assets = plan["organic_warfare"]["content_assets"]

    # Cache awareness — quais artigos já foram gerados
    from services.content_producer import list_cached_articles
    cached_articles = list_cached_articles(snap["entity"])
    cached_types = {a.get("asset_type", "") for a in cached_articles}

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    entity = snap["entity"]

    return templates.TemplateResponse("content_studio.html", {
        "request":        request,
        "entity_name":    entity,
        "entity_slug":    slug,
        "generated_at":   generated_at,
        "content_assets": content_assets,
        "plan":           plan,
        "cached_types":   cached_types,
        "cached_articles": cached_articles,
        "has_cache":      len(cached_articles) > 0,
    })


@router.post("/content/{entity_path}", response_class=HTMLResponse)
def content_generate(request: Request, entity_path: str,
                     asset_type: str = Form(...)):
    slug = _entity_slug(entity_path)
    snap = get_latest_snapshot(slug)
    if not snap:
        return templates.TemplateResponse("result.html", {
            "request": request,
            "entity_name": entity_path,
            "result": None,
            "error": "Nenhum snapshot encontrado.",
        })

    enriched_serp = snap.get("serp", [])
    score = compute_serp_score(enriched_serp)
    clusters = compute_domain_clusters(enriched_serp)
    threat = infer_threat_from_snapshot(snap)
    archetype = snap.get("threat_archetype", "")
    plan = build_battle_plan(enriched_serp, clusters, score, threat, archetype)

    try:
        result = produce_article(asset_type, snap["entity"], battle_plan=plan)
        save_article(snap["entity"], asset_type, result)
        return templates.TemplateResponse("article_generated.html", {
            "request":      request,
            "entity_name":  snap["entity"],
            "entity_slug":  slug,
            "result":       result,
        })
    except Exception as e:
        return templates.TemplateResponse("result.html", {
            "request":     request,
            "entity_name": snap["entity"],
            "result":      None,
            "error":       str(e),
        })


@router.post("/content/{entity_path:path}/generate-all", response_class=HTMLResponse)
def content_generate_all(request: Request, entity_path: str):
    slug = _entity_slug(entity_path)
    snap = get_latest_snapshot(slug)
    if not snap:
        return templates.TemplateResponse("result.html", {
            "request": request,
            "entity_name": entity_path,
            "result": None,
            "error": "Nenhum snapshot encontrado.",
        })

    enriched_serp = snap.get("serp", [])
    score = compute_serp_score(enriched_serp)
    clusters = compute_domain_clusters(enriched_serp)
    threat = infer_threat_from_snapshot(snap)
    archetype = snap.get("threat_archetype", "")
    plan = build_battle_plan(enriched_serp, clusters, score, threat, archetype)

    asset_types = [
        "artigo_linkedin", "biografia_executiva", "perfil_institucional",
        "comunicado_imprensa", "esclarecimento_juridico", "faq_transparencia",
        "roteiro_youtube",
    ]

    results = []
    errors = []
    for at in asset_types:
        try:
            r = produce_article(at, snap["entity"], battle_plan=plan)
            save_article(snap["entity"], at, r)
            results.append(r)
        except Exception as e:
            errors.append(f"{at}: {str(e)[:120]}")

    return templates.TemplateResponse("article_generated.html", {
        "request":      request,
        "entity_name":  snap["entity"],
        "entity_slug":  slug,
        "result":       results[0] if len(results) == 1 else None,
        "all_results":  results,          # todos os artigos — template usa este
        "errors":       errors,
        "generated_all": True,
        "total_generated": len(results),
        "total_errors": len(errors),
    })


# ── Journalistic Site Builder ────────────────────────────────────────────────

@router.post("/content/{entity_path:path}/build-site", response_class=HTMLResponse)
def build_site(request: Request, entity_path: str):
    slug = _entity_slug(entity_path)
    snap = get_latest_snapshot(slug)
    if not snap:
        return templates.TemplateResponse("result.html", {
            "request": request,
            "entity_name": entity_path,
            "result": None,
            "error": "Nenhum snapshot encontrado.",
        })

    asset_types = [
        "artigo_linkedin", "biografia_executiva", "perfil_institucional",
        "comunicado_imprensa", "esclarecimento_juridico", "faq_transparencia",
    ]

    # Try cache first, generate missing ones
    articles = list_cached_articles(snap["entity"])
    cached_types = {a["asset_type"] for a in articles}
    missing = [at for at in asset_types if at not in cached_types]

    if missing:
        enriched_serp = snap.get("serp", [])
        score = compute_serp_score(enriched_serp)
        clusters = compute_domain_clusters(enriched_serp)
        threat = infer_threat_from_snapshot(snap)
        archetype = snap.get("threat_archetype", "")
        plan = build_battle_plan(enriched_serp, clusters, score, threat, archetype)
        for at in missing:
            try:
                r = produce_article(at, snap["entity"], battle_plan=plan)
                save_article(snap["entity"], at, r)
                articles.append(r)
            except Exception:
                pass

    site = build_news_site(snap["entity"], articles)

    # Write files to disk for deployment
    site_dir = Path(__file__).parent.parent.parent / "content_sites" / slug
    site_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for fname, content in site["files"].items():
        (site_dir / fname).write_text(content, encoding="utf-8")
        written += 1

    return templates.TemplateResponse("site_generated.html", {
        "request":      request,
        "entity_name":  snap["entity"],
        "entity_slug":  slug,
        "site":         site,
        "homepage":     site["files"].get("index.html", ""),
        "written":      written,
    })


# ── Asset Generator routes ────────────────────────────────────

ASSET_LABELS = {
    "linkedin_article": "LinkedIn Article",
    "executive_bio": "Executive Bio",
    "legal_clarification": "Legal Clarification",
    "institutional_profile": "Institutional Profile",
    "interview_talking_points": "Interview Talking Points",
    "press_release": "Press Release",
}


@router.get("/assets", response_class=HTMLResponse)
def asset_form(request: Request):
    entity_name = request.query_params.get("entity", "")
    return templates.TemplateResponse("asset_generator.html", {
        "request": request,
        "entity_name": entity_name,
    })


@router.post("/assets", response_class=HTMLResponse)
def asset_generate(
    request: Request,
    entity_name: str = Form(...),
    asset_type: str = Form(...),
    strategic_context: str = Form(""),
):
    try:
        result = generate_asset(asset_type, entity_name, strategic_context)
        return templates.TemplateResponse("asset_generator.html", {
            "request": request,
            "entity_name": entity_name,
            "asset_type": asset_type,
            "asset_type_label": ASSET_LABELS.get(asset_type, asset_type),
            "strategic_context": strategic_context,
            "generated_asset": result,
        })
    except Exception as e:
        return templates.TemplateResponse("asset_generator.html", {
            "request": request,
            "entity_name": entity_name,
            "asset_type": asset_type,
            "asset_type_label": ASSET_LABELS.get(asset_type, asset_type),
            "strategic_context": strategic_context,
            "error": str(e),
        })


# ── Campaign Generator routes ──────────────────────────────────

@router.get("/campaign", response_class=HTMLResponse)
def campaign_form(request: Request):
    entity_name = request.query_params.get("entity", "")
    return templates.TemplateResponse("campaign_generator.html", {
        "request": request,
        "entity_name": entity_name,
    })


@router.post("/campaign", response_class=HTMLResponse)
def campaign_generate(
    request: Request,
    entity: str = Form(...),
    threat_level: str = Form(...),
    narrative_state: str = Form(...),
    objective: str = Form(""),
):
    try:
        result = generate_campaign(entity, threat_level, narrative_state, objective)
        return templates.TemplateResponse("campaign_generator.html", {
            "request": request,
            "entity_name": entity,
            "threat_level": threat_level,
            "narrative_state": narrative_state,
            "objective": objective,
            "campaign": result,
        })
    except Exception as e:
        return templates.TemplateResponse("campaign_generator.html", {
            "request": request,
            "entity_name": entity,
            "threat_level": threat_level,
            "narrative_state": narrative_state,
            "objective": objective,
            "error": str(e),
        })


# ── Resposta Operacional Narrativa ─────────────────────────────────────────────

@router.get("/response", response_class=HTMLResponse)
def response_form(request: Request):
    return templates.TemplateResponse("response_form.html", {"request": request})


@router.post("/response", response_class=HTMLResponse)
def response_generate(
    request: Request,
    entity_name:             str  = Form(...),
    threat_level:            str  = Form(...),
    narrative_state:         str  = Form(...),
    dominant_themes:         str  = Form(...),
    source_concentration:    str  = Form(...),
    legal_exposure:          str  = Form(...),
    authority_vacuum:        str  = Form(...),
    discovered_associations: str  = Form(""),
    threat_archetype:        str  = Form(""),
):
    try:
        legal_exposure_bool = legal_exposure.strip().lower() == "sim"

        result = generate_response(
            entity_name             = entity_name,
            threat_level            = threat_level,
            narrative_state         = narrative_state,
            dominant_themes         = dominant_themes,
            source_concentration    = source_concentration,
            legal_exposure          = legal_exposure_bool,
            authority_vacuum        = authority_vacuum,
            discovered_associations = discovered_associations,
            threat_archetype        = threat_archetype,
        )

        sections = parse_response_sections(result["text"])
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        # Montar pares de redirecionamento para o template
        redirection_pairs = []
        for line in result["redirection_map"].splitlines():
            line = line.strip().lstrip("•").strip()
            if "→" in line:
                parts = line.split("→", 1)
                redirection_pairs.append({
                    "from": parts[0].strip(),
                    "to":   parts[1].strip(),
                })

        meta = {
            "posture":              result["posture"],
            "posture_desc":         result["posture_desc"],
            "visibility":           result["visibility"],
            "response_temperature": result["response_temperature"],
            "stakeholder_order":    result["stakeholder_order"],
            "escalation_triggers":  result["escalation_triggers"],
            "redirection_map":      result["redirection_map"],
            "redirection_pairs":    redirection_pairs,
            "asset_sequence":       result["asset_sequence"],
            "threat_archetype":     result["threat_archetype"],
            "archetype_label":      result["archetype_label"],
            "archetype_principio":  result["archetype_principio"],
        }

        return templates.TemplateResponse("response_strategy.html", {
            "request":      request,
            "entity_name":  entity_name,
            "threat_level": threat_level,
            "generated_at": generated_at,
            "sections":     sections,
            "meta":         meta,
        })

    except Exception as e:
        return templates.TemplateResponse("result.html", {
            "request":     request,
            "entity_name": entity_name,
            "result":      None,
            "error":       str(e),
        })


# ── SERP Occupation Strategy ───────────────────────────────────────────────────

@router.get("/occupation", response_class=HTMLResponse)
def occupation_form(request: Request):
    return templates.TemplateResponse("occupation_form.html", {"request": request})


@router.post("/occupation", response_class=HTMLResponse)
def occupation_generate(
    request: Request,
    entity_name:  str = Form(...),
    threat_level: str = Form(""),
):
    try:
        result = generate_occupation(
            entity_name  = entity_name,
            threat_level = threat_level.strip() or "",
        )

        sections = parse_occupation_sections(result["text"])
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        enriched_serp = []
        for r in result["serp_results"]:
            domain = urlparse(r.get("link", "")).netloc.replace("www.", "")
            enriched_serp.append({
                "position": r.get("position", "?"),
                "domain":   domain,
                "title":    r.get("title", ""),
                "type":     classify_domain(domain),
            })

        meta = {
            "authority_vacuum":     result["authority_vacuum"],
            "source_concentration": result["source_concentration"],
            "negative_domains":     result["negative_domains"],
            "serp_results":         enriched_serp,
            "asset_table":          result["asset_table"],
        }

        return templates.TemplateResponse("occupation_strategy.html", {
            "request":      request,
            "entity_name":  entity_name,
            "threat_level": result["threat_level"],
            "generated_at": generated_at,
            "sections":     sections,
            "meta":         meta,
        })

    except Exception as e:
        return templates.TemplateResponse("result.html", {
            "request":     request,
            "entity_name": entity_name,
            "result":      None,
            "error":       str(e),
        })


# ── SERP Occupation Strategy — Snapshot Inheritance ────────────────────────────

@router.get("/occupation/{entity_path:path}", response_class=HTMLResponse)
def occupation_from_snapshot(request: Request, entity_path: str):
    slug = _entity_slug(entity_path)
    snap = get_latest_snapshot(slug)
    if not snap:
        return templates.TemplateResponse("result.html", {
            "request": request,
            "entity_name": entity_path,
            "result": None,
            "error": f"Nenhum snapshot encontrado para '{entity_path}'. Execute uma auditoria primeiro.",
        })

    threat = infer_threat_from_snapshot(snap)
    archetype = snap.get("threat_archetype", "")
    if not archetype:
        from services.archetype import classify_archetype
        archetype = classify_archetype(snap)
    crisis = snap.get("crisis_state", "")
    if not crisis:
        from services.archetype import classify_crisis_state
        crisis = classify_crisis_state(snap)
    neg_domains = extract_negative_domains(snap)
    concentration, _ = extract_source_concentration(snap)

    serp_lines = []
    for r in snap.get("serp", []):
        pos  = r.get("position", "?")
        ttl  = (r.get("title", "") or "")[:80]
        dom  = r.get("domain", "")
        snip = (r.get("snippet", "") or "")[:120]
        serp_lines.append(f"#{pos} | {ttl}\n     Domínio: {dom} | Snippet: {snip}")
    serp_context = "\n".join(serp_lines)

    npa = snap.get("narrative_pressure", {})

    enriched_serp = []
    for r in snap.get("serp", []):
        enriched_serp.append({
            "position":  r.get("position", "?"),
            "domain":    r.get("domain", ""),
            "title":     r.get("title", ""),
            "sentiment": r.get("sentiment", "neutral"),
            "type":      r.get("type", classify_domain(r.get("domain", ""))),
        })

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return templates.TemplateResponse("occupation_confirm.html", {
        "request":      request,
        "entity_name":  snap["entity"],
        "entity_slug":  slug,
        "snapshot_date": snap["date"],
        "generated_at": generated_at,
        "threat_level": threat,
        "threat_archetype": archetype,
        "crisis_state": crisis,
        "negative_domains": neg_domains,
        "authority_vacuum": snap.get("authority_vacuum", "MODERATE"),
        "source_concentration": concentration,
        "serp_results": enriched_serp,
        "npa": npa,
    })


@router.post("/occupation/{entity_path:path}", response_class=HTMLResponse)
def occupation_generate_from_snapshot(
    request: Request,
    entity_path: str,
    threat_level: str = Form(""),
):
    slug = _entity_slug(entity_path)
    snap = get_latest_snapshot(slug)
    if not snap:
        return templates.TemplateResponse("result.html", {
            "request": request,
            "entity_name": entity_path,
            "result": None,
            "error": f"Nenhum snapshot encontrado para '{entity_path}'.",
        })

    threat = threat_level.strip() or infer_threat_from_snapshot(snap)
    archetype = snap.get("threat_archetype", "")
    if not archetype:
        from services.archetype import classify_archetype
        archetype = classify_archetype(snap)
    neg_domains = extract_negative_domains(snap)
    concentration, _ = extract_source_concentration(snap)
    assoc_str = format_associations_from_snapshot(snap)

    serp_lines = []
    for r in snap.get("serp", []):
        pos  = r.get("position", "?")
        ttl  = (r.get("title", "") or "")[:80]
        dom  = r.get("domain", "")
        snip = (r.get("snippet", "") or "")[:120]
        serp_lines.append(f"#{pos} | {ttl}\n     Domínio: {dom} | Snippet: {snip}")
    serp_context = "\n".join(serp_lines)

    intelligence = {
        "serp_context":              serp_context,
        "negative_domains_str":      ", ".join(neg_domains[:5]) if neg_domains else "Nenhum domínio negativo identificado.",
        "negative_domains_list":     neg_domains,
        "associations_str":          assoc_str,
        "authority_vacuum":          snap.get("authority_vacuum", "MODERATE"),
        "source_concentration":      concentration,
        "serp_results":              snap.get("serp", []),
    }

    try:
        result = generate_occupation(
            entity_name  = snap["entity"],
            threat_level = threat,
            threat_archetype = archetype,
            intelligence = intelligence,
        )

        sections = parse_occupation_sections(result["text"])
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        enriched_serp = []
        for r in result["serp_results"]:
            domain = r.get("domain", "") or urlparse(r.get("link", "")).netloc.replace("www.", "")
            enriched_serp.append({
                "position": r.get("position", "?"),
                "domain":   domain,
                "title":    r.get("title", ""),
                "sentiment": r.get("sentiment", "neutral"),
                "type":     r.get("type", classify_domain(domain)),
            })

        meta = {
            "authority_vacuum":     result["authority_vacuum"],
            "source_concentration": result["source_concentration"],
            "negative_domains":     result["negative_domains"],
            "serp_results":         enriched_serp,
            "asset_table":          result["asset_table"],
        }

        return templates.TemplateResponse("occupation_strategy.html", {
            "request":      request,
            "entity_name":  snap["entity"],
            "threat_level": result["threat_level"],
            "generated_at": generated_at,
            "sections":     sections,
            "meta":         meta,
        })

    except Exception as e:
        return templates.TemplateResponse("result.html", {
            "request":     request,
            "entity_name": snap["entity"],
            "result":      None,
            "error":       str(e),
        })


# ── YOUTUBE WARFARE ────────────────────────────────────────────────────────

@router.get("/youtube/{entity_path:path}", response_class=HTMLResponse)
def youtube_dashboard(request: Request, entity_path: str):
    slug = _entity_slug(entity_path)
    snap = get_latest_snapshot(slug)
    if not snap:
        return templates.TemplateResponse("result.html", {
            "request": request,
            "entity_name": entity_path,
            "result": None,
            "error": f"Nenhum snapshot encontrado para '{entity_path}'.",
        })

    enriched_serp = snap.get("serp", [])
    videos = extract_youtube_results(enriched_serp)
    toxicity = compute_youtube_toxicity(videos)
    npa_boost = compute_video_npa_boost(toxicity)
    ads = youtube_ads_campaign(snap.get("entity", entity_path),
                                infer_threat_from_snapshot(snap),
                                snap.get("threat_archetype", "corporate"))

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return templates.TemplateResponse("youtube_warfare.html", {
        "request": request,
        "entity_name": snap.get("entity", entity_path),
        "generated_at": generated_at,
        "videos": videos,
        "toxicity": toxicity,
        "npa_boost": npa_boost,
        "ads": ads,
    })


@router.post("/content/{entity_path}/generate-video", response_class=HTMLResponse)
def generate_video_script(request: Request, entity_path: str,
                          asset_subtype: str = Form("posicionamento_institucional"),
                          strategic_context: str = Form("")):
    slug = _entity_slug(entity_path)
    snap = get_latest_snapshot(slug)
    if not snap:
        return templates.TemplateResponse("result.html", {
            "request": request,
            "entity_name": entity_path,
            "result": None,
            "error": f"Nenhum snapshot encontrado para '{entity_path}'.",
        })

    from services.youtube_warfare import generate_video_script
    from services.content_producer import save_article as _save_article
    entity = snap.get("entity", entity_path)
    script = generate_video_script(entity, asset_subtype, strategic_context)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Salvar roteiro em cache para Distribution Engine e build-site
    video_result = {
        "asset_type":   "roteiro_youtube",
        "label":        "Roteiro YouTube",
        "entity_name":  entity,
        "article":      script,
        "body_md":      script,
        "seo": {
            "title":              f"Roteiro de Vídeo — {entity}",
            "meta_description":   f"Roteiro para produção de vídeo de {asset_subtype} para {entity}.",
            "slug":               slug,
            "tags":               ["youtube", "video", asset_subtype, slug],
            "suggested_filename": f"{slug}-roteiro-youtube.md",
        },
        "structured_data": None,
        "platform":   {},
        "amplification": {},
        "generated_at": generated_at,
    }
    try:
        _save_article(entity, "roteiro_youtube", video_result)
    except Exception:
        pass

    return templates.TemplateResponse("article_generated.html", {
        "request":      request,
        "entity_name":  entity,
        "entity_slug":  slug,
        "generated_at": generated_at,
        "result":       video_result,
    })


# ── KNOWLEDGE PANEL ENGINEERING ───────────────────────────────────────────

@router.get("/knowledge-panel/{entity_path:path}", response_class=HTMLResponse)
def knowledge_panel_dashboard(request: Request, entity_path: str):
    slug = _entity_slug(entity_path)
    snap = get_latest_snapshot(slug)
    if not snap:
        return templates.TemplateResponse("result.html", {
            "request": request,
            "entity_name": entity_path,
            "result": None,
            "error": f"Nenhum snapshot encontrado para '{entity_path}'.",
        })

    entity = snap.get("entity", entity_path)
    kp = compute_knowledge_panel_score(snap)
    setup = kp_setup_guide(entity, snap)

    enriched = snap.get("serp", [])
    linkedin_url = ""
    site_url = ""
    for r in enriched:
        if "linkedin.com" in (r.get("domain", "") or ""):
            linkedin_url = r.get("link", "")
        if r.get("controlled") and r.get("type") == "institutional":
            site_url = r.get("link", "")

    wikidata_profile = generate_wikidata_profile(
        entity,
        title="",
        company="",
    )
    schema_html = generate_schema_org(entity, site_url=site_url, linkedin_url=linkedin_url)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return templates.TemplateResponse("knowledge_panel.html", {
        "request": request,
        "entity_name": entity,
        "generated_at": generated_at,
        "kp_score": kp,
        "setup_guide": setup,
        "wikidata_profile": wikidata_profile,
        "schema_html": schema_html,
    })


# ── RECOVERY PROBABILITY ──────────────────────────────────────────────────

@router.get("/recovery/{entity_path:path}", response_class=HTMLResponse)
def recovery_probability_dashboard(request: Request, entity_path: str):
    slug = _entity_slug(entity_path)
    snap = get_latest_snapshot(slug)
    if not snap:
        return templates.TemplateResponse("result.html", {
            "request": request,
            "entity_name": entity_path,
            "result": None,
            "error": f"Nenhum snapshot encontrado para '{entity_path}'.",
        })

    entity = snap.get("entity", entity_path)
    enriched = snap.get("serp", [])
    serp_score = compute_serp_score(enriched)
    npa = snap.get("narrative_pressure", {})
    youtube_tox = (snap.get("youtube_toxicity", {}) or {}).get("total", 0)

    recovery = compute_recovery_probability(
        serp=enriched,
        serp_score=serp_score["total"],
        npa=npa,
        youtube_toxicity=youtube_tox,
    )

    crisis_stage = classify_crisis_stage(npa, enriched,
                                          infer_threat_from_snapshot(snap))
    stage_config = stage_drives_response(crisis_stage, snapshot=snap)  # passa snap para detectar dados desatualizados

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return templates.TemplateResponse("recovery_probability.html", {
        "request": request,
        "entity_name": entity,
        "generated_at": generated_at,
        "recovery": recovery,
        "serp_score": serp_score,
        "crisis_stage": stage_config,
    })


# ── NEWS DISTRIBUTION ─────────────────────────────────────────────────────

@router.get("/news-distribution/{entity_path:path}", response_class=HTMLResponse)
def news_distribution_dashboard(request: Request, entity_path: str):
    slug = _entity_slug(entity_path)
    snap = get_latest_snapshot(slug)
    if not snap:
        return templates.TemplateResponse("result.html", {
            "request": request,
            "entity_name": entity_path,
            "result": None,
            "error": f"Nenhum snapshot encontrado para '{entity_path}'.",
        })

    entity = snap.get("entity", entity_path)
    archetype = snap.get("threat_archetype", "corporate")
    enriched = snap.get("serp", [])

    # Map entity industry from domains
    sectors = []
    for r in enriched:
        dtype = r.get("type", "")
        if dtype in ("mainstream", "legal", "institutional"):
            sectors.append(dtype)

    portals = select_portals(archetype, list(set(sectors)) if sectors else None)
    news_occ = compute_news_occupation_score([], [])
    battle_sec = distribution_battle_section(archetype, list(set(sectors)) if sectors else None)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return templates.TemplateResponse("news_distribution.html", {
        "request": request,
        "entity_name": entity,
        "generated_at": generated_at,
        "archetype": archetype,
        "portals": portals,
        "all_portals": PORTALS,
        "news_occupation": news_occ,
        "battle_section": battle_sec,
    })


@router.post("/news-distribution/{entity_path}/send", response_class=HTMLResponse)
def send_release(request: Request, entity_path: str,
                 portal_name: str = Form(""),
                 release_text: str = Form("")):
    slug = _entity_slug(entity_path)
    snap = get_latest_snapshot(slug)
    if not snap:
        return templates.TemplateResponse("result.html", {
            "request": request, "entity_name": entity_path,
            "result": None, "error": "Snapshot não encontrado",
        })

    entity = snap.get("entity", entity_path)
    portal = next((p for p in PORTALS if p["name"] == portal_name), PORTALS[0])
    payload = generate_release_payload(entity, release_text, portal)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return templates.TemplateResponse("release_sent.html", {
        "request": request,
        "entity_name": entity,
        "generated_at": generated_at,
        "portal": portal,
        "payload": payload,
    })


# ── MONITORING ────────────────────────────────────────────────────────────

@router.get("/monitor/{entity_path:path}", response_class=HTMLResponse)
def monitoring_dashboard(request: Request, entity_path: str):
    slug = _entity_slug(entity_path)
    snap = get_latest_snapshot(slug)
    if not snap:
        return templates.TemplateResponse("result.html", {
            "request": request,
            "entity_name": entity_path,
            "result": None,
            "error": f"Nenhum snapshot encontrado para '{entity_path}'.",
        })

    entity = snap.get("entity", entity_path)
    summary = get_monitor_summary(slug)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return templates.TemplateResponse("monitoring.html", {
        "request": request,
        "entity_name": entity,
        "generated_at": generated_at,
        "monitor": summary,
        "triggers": TRIGGERS,
    })


@router.post("/monitor/{entity_path}/check", response_class=HTMLResponse)
def run_monitor_check(request: Request, entity_path: str):
    """Compara os dois snapshots mais recentes para detectar mudanças reais.

    Não chama APIs externas — usa apenas snapshots já salvos em disco.
    Para monitoramento com dados frescos, rodar nova auditoria primeiro.
    """
    slug = _entity_slug(entity_path)
    previous, latest = get_two_latest_snapshots(slug)

    if not latest:
        return templates.TemplateResponse("result.html", {
            "request": request, "entity_name": entity_path,
            "result": None, "error": "Snapshot não encontrado",
        })

    entity = latest.get("entity", entity_path)
    summary = get_monitor_summary(slug)

    # Comparação real entre snapshots
    check_result = None
    if previous and latest:
        old_serp = previous.get("serp", [])
        new_serp = latest.get("serp", [])
        old_npa = previous.get("narrative_pressure", {})
        new_npa = latest.get("narrative_pressure", {})

        serp_alerts = check_serp(slug, old_serp, new_serp)
        npa_alerts = check_npa_delta(slug, old_npa, new_npa)
        all_new_alerts = serp_alerts + npa_alerts

        check_result = {
            "compared_from": previous.get("date", "?"),
            "compared_to": latest.get("date", "?"),
            "new_alerts_count": len(all_new_alerts),
            "new_alerts": all_new_alerts,
            "message": (
                f"{len(all_new_alerts)} alerta(s) detectado(s) comparando "
                f"{previous.get('date','?')} → {latest.get('date','?')}."
                if all_new_alerts else
                f"Nenhuma mudança significativa entre {previous.get('date','?')} e {latest.get('date','?')}."
            ),
        }
        # Recarregar summary após novos alertas serem salvos
        summary = get_monitor_summary(slug)
    else:
        check_result = {
            "message": "Apenas um snapshot disponível — sem comparação possível. Execute uma segunda auditoria para habilitar o check.",
            "new_alerts_count": 0,
            "new_alerts": [],
        }

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return templates.TemplateResponse("monitoring.html", {
        "request": request,
        "entity_name": entity,
        "generated_at": generated_at,
        "monitor": summary,
        "triggers": TRIGGERS,
        "checked": True,
        "check_result": check_result,
    })


@router.post("/monitor/{entity_path}/reset", response_class=HTMLResponse)
def reset_monitor(request: Request, entity_path: str):
    slug = _entity_slug(entity_path)
    reset_monitoring(slug)
    summary = get_monitor_summary(slug)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return templates.TemplateResponse("monitoring.html", {
        "request": request,
        "entity_name": entity_path,
        "generated_at": generated_at,
        "monitor": summary,
        "triggers": TRIGGERS,
    })


@router.post("/monitor/{entity_path}/configure", response_class=HTMLResponse)
def configure_monitor(
    request: Request,
    entity_path: str,
    email_to: str = Form(""),
    slack_webhook: str = Form(""),
    smtp_host: str = Form("smtp.gmail.com"),
    smtp_port: int = Form(587),
    smtp_user: str = Form(""),
    smtp_pass: str = Form(""),
    serp_freq_h: int = Form(6),
    news_freq_m: int = Form(120),
):
    slug = _entity_slug(entity_path)
    configure_monitoring(
        slug=slug,
        serp_freq_h=serp_freq_h,
        news_freq_m=news_freq_m,
        slack_webhook=slack_webhook,
        email_to=email_to,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_pass=smtp_pass,
    )
    snap = get_latest_snapshot(slug)
    entity = snap.get("entity", entity_path) if snap else entity_path
    summary = get_monitor_summary(slug)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Envia email de teste se configurado
    test_result = None
    if email_to and smtp_user and smtp_pass:
        from services.monitoring_engine import _send_email_alert
        cfg = summary.get("config", {})
        test_result = _send_email_alert(
            {"level": "INFO", "detail": "Configuração de alertas CouncilIA concluída.",
             "trigger": "config_test", "timestamp": generated_at, "entity": entity},
            email_to, cfg
        )

    return templates.TemplateResponse("monitoring.html", {
        "request": request,
        "entity_name": entity,
        "generated_at": generated_at,
        "monitor": summary,
        "triggers": TRIGGERS,
        "configured": True,
        "config_message": (
            f"Configuração salva. Email de teste {'enviado' if test_result and test_result.get('ok') else 'falhou: ' + (test_result or {}).get('error', '')} para {email_to}."
            if email_to and smtp_user else "Configuração salva."
        ),
    })


# ── LINKEDIN ADS ──────────────────────────────────────────────────────────

@router.get("/linkedin-ads/{entity_path:path}", response_class=HTMLResponse)
def linkedin_ads_dashboard(request: Request, entity_path: str):
    slug = _entity_slug(entity_path)
    snap = get_latest_snapshot(slug)
    if not snap:
        return templates.TemplateResponse("result.html", {
            "request": request,
            "entity_name": entity_path,
            "result": None,
            "error": f"Nenhum snapshot encontrado para '{entity_path}'.",
        })

    entity = snap.get("entity", entity_path)
    archetype = snap.get("threat_archetype", "corporate")

    ads_plan = generate_linkedin_ads_plan(archetype)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return templates.TemplateResponse("linkedin_ads.html", {
        "request": request,
        "entity_name": entity,
        "generated_at": generated_at,
        "archetype": archetype,
        "ads_plan": ads_plan,
    })


# ── Distribution Engine ───────────────────────────────────────────────────

from services.distribution_engine import (
    PLATFORM_REGISTRY, get_ranked_platforms, get_platform_scorecard,
    format_for, publish_to, free_platforms, platforms_with_api,
    platforms_by_region, build_narrative_blast,
)


@router.get("/distribution/format/{slug}/{asset_type}/{platform}")
def distribution_format(request: Request, slug: str, asset_type: str, platform: str):
    from services.content_producer import list_cached_articles

    snap = get_latest_snapshot(slug)
    if not snap:
        return {"error": "Snapshot não encontrado"}
    entity = snap.get("entity", slug)

    articles = list_cached_articles(entity)
    article = next((a for a in articles if a.get("asset_type", "") == asset_type), None)
    if not article:
        return {"error": f"Artigo '{asset_type}' não encontrado em cache para '{entity}'"}

    body_md = article.get("body_md", "") or article.get("article", "")

    first_name = entity.split()[0] if entity.split() else entity
    result = format_for(platform, first_name, body_md, article.get("seo"))

    reg = PLATFORM_REGISTRY.get(platform)
    if reg:
        steps = []
        if reg.api and reg.pricing == "free":
            steps.append("Publicação automática via API")
        elif reg.api and reg.pricing in ("paid", "enterprise"):
            steps.append("Requer conta paga — payload gerado aguarda aprovação")
        else:
            steps.append("Distribuição manual")
        if reg.tier in ("S", "A"):
            steps.append("Indexação estimada: 2-24h")
        result["steps"] = steps

    return result


@router.get("/narrative-blast/{entity_path:path}", response_class=HTMLResponse)
def narrative_blast_page(
    request: Request,
    entity_path: str,
    budget: str = "standard",
    region: str = "BR",
):
    slug = entity_path.strip("/").replace("/", "_")
    snap = get_latest_snapshot(slug)
    if not snap:
        return templates.TemplateResponse("result.html", {
            "request": request,
            "entity_name": entity_path,
            "result": None,
            "error": f"Nenhum snapshot encontrado para '{entity_path}'.",
        })

    entity = snap.get("entity", entity_path)
    archetype = snap.get("threat_archetype", "corporate")
    has_company = bool(snap.get("occupation_targets") or snap.get("company"))

    blast = build_narrative_blast(
        entity=entity,
        archetype=archetype,
        budget=budget,
        region=region,
        has_company=has_company,
    )

    return templates.TemplateResponse("narrative_blast.html", {
        "request": request,
        "entity_name": entity,
        "slug": slug,
        "archetype": archetype,
        "budget": budget,
        "region": region,
        "blast": blast,
    })


@router.get("/distribution/{entity_path:path}", response_class=HTMLResponse)
def distribution_dashboard(request: Request, entity_path: str):
    slug = entity_path.strip("/").replace("/", "_")
    snap = get_latest_snapshot(slug)
    if not snap:
        return templates.TemplateResponse("result.html", {
            "request": request,
            "entity_name": entity_path,
            "result": None,
            "error": f"Nenhum snapshot encontrado para '{entity_path}'.",
        })

    entity = snap.get("entity", entity_path)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    ranked = get_ranked_platforms(0)

    # Group by tier
    tiers = {"S": [], "A": [], "B": [], "C": []}
    for p in ranked:
        t = p.get("tier", "C")
        if t in tiers:
            tiers[t].append(p)

    # Cached articles for this entity
    from services.content_producer import list_cached_articles
    articles = list_cached_articles(entity)

    return templates.TemplateResponse("distribution.html", {
        "request": request,
        "entity_name": entity,
        "slug": slug,
        "generated_at": generated_at,
        "tiers": tiers,
        "ranked": ranked,
        "articles": articles,
        "free_api_platforms": [k for k, v in PLATFORM_REGISTRY.items() if v.api and v.pricing == "free"],
    })


# ── Semantic Variation Engine ─────────────────────────────────────────────────

@router.get("/semantic-variations/{entity_path:path}", response_class=HTMLResponse)
def semantic_variations_page(request: Request, entity_path: str):
    from services.content_producer import list_cached_articles, get_variation_frames

    slug = entity_path.strip("/").replace("/", "_")
    snap = get_latest_snapshot(slug)
    if not snap:
        return templates.TemplateResponse("result.html", {
            "request": request,
            "entity_name": entity_path,
            "result": None,
            "error": f"Nenhum snapshot encontrado para '{entity_path}'.",
        })

    entity = snap.get("entity", entity_path)
    articles = list_cached_articles(entity)
    frames = get_variation_frames()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return templates.TemplateResponse("semantic_variations.html", {
        "request": request,
        "entity_name": entity,
        "slug": slug,
        "articles": articles,
        "frames": frames,
        "generated_at": generated_at,
    })


@router.post("/semantic-variations/{slug}/generate")
async def semantic_variations_generate(
    request: Request,
    slug: str,
):
    from services.content_producer import (
        list_cached_articles, generate_semantic_variations, get_variation_frames
    )
    import json as _json

    data = await request.json()
    asset_type = data.get("asset_type", "")
    selected_frames = data.get("frames") or None

    snap = get_latest_snapshot(slug)
    if not snap:
        return {"error": "Snapshot não encontrado"}
    entity = snap.get("entity", slug)

    articles = list_cached_articles(entity)
    article = next((a for a in articles if a.get("asset_type", "") == asset_type), None)
    if not article:
        return {"error": f"Artigo '{asset_type}' não encontrado em cache"}

    base_text = article.get("body_md", "") or article.get("article", "")

    variations = generate_semantic_variations(
        entity=entity,
        base_article=base_text,
        asset_type=asset_type,
        frames=selected_frames,
    )

    return {
        "entity": entity,
        "asset_type": asset_type,
        "variations": variations,
        "total": len(variations),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Publication Assistant ─────────────────────────────────────────────────────

@router.get("/publish-assist/{entity_path:path}", response_class=HTMLResponse)
def publish_assist(request: Request, entity_path: str):
    """
    Assistente de Publicação Manual — guia o operador por cada plataforma não-automatizável.
    Mostra conteúdo formatado + link direto + instruções passo a passo.
    """
    from services.distribution_engine import (
        get_all_manual_guides, get_manual_platforms_for_entity, format_for, PLATFORM_REGISTRY
    )
    from services.content_producer import list_cached_articles

    slug = entity_path.strip("/").replace("/", "_")
    snap = get_latest_snapshot(slug)
    if not snap:
        return templates.TemplateResponse("result.html", {
            "request": request, "entity_name": entity_path,
            "result": None, "error": f"Nenhum snapshot encontrado para '{entity_path}'.",
        })

    entity = snap.get("entity", entity_path)
    archetype = snap.get("threat_archetype", "corporate")

    # Inferir região do snapshot (country salvo na auditoria)
    country = snap.get("country", "Brasil").lower()
    if any(w in country for w in ["portugal", "portuguesa", "pt"]):
        region = "PT"
    elif any(w in country for w in ["espanha", "spain", "españa", "es"]):
        region = "ES"
    elif any(w in country for w in ["eua", "usa", "estados unidos", "united states", "us"]):
        region = "US"
    else:
        region = "BR"  # padrão para Brasil e LATAM

    # Artigos em cache
    articles = list_cached_articles(entity)
    article_map = {a.get("asset_type", ""): a for a in articles}

    # Plataformas manuais prioritárias para este arquétipo
    priority_platforms = get_manual_platforms_for_entity(archetype, region)
    all_guides = get_all_manual_guides()

    # Para cada plataforma, preparar conteúdo formatado se houver artigo em cache
    platform_data = []
    for pk in priority_platforms:
        guide = all_guides.get(pk)
        if not guide:
            continue

        # Escolher o melhor artigo para esta plataforma
        formatted = None
        source_article = None
        article_type_for_platform = _best_article_for_platform(pk, article_map)
        if article_type_for_platform:
            art = article_map[article_type_for_platform]
            body = art.get("body_md", "") or art.get("article", "")
            first_name = entity.split()[0] if entity.split() else entity
            try:
                formatted = format_for(pk, first_name, body, art.get("seo"))
            except Exception:
                formatted = None
            source_article = art

        platform_data.append({
            "key": pk,
            "guide": guide,
            "formatted": formatted,
            "source_article": source_article,
            "has_content": bool(formatted and not formatted.get("error")),
            "in_registry": pk in PLATFORM_REGISTRY,
        })

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return templates.TemplateResponse("publish_assist.html", {
        "request": request,
        "entity_name": entity,
        "slug": slug,
        "archetype": archetype,
        "generated_at": generated_at,
        "platform_data": platform_data,
        "articles_cached": len(articles),
    })


def _best_article_for_platform(platform_key: str, article_map: dict) -> str | None:
    """Mapeia plataforma → melhor tipo de artigo em cache."""
    mapping = {
        "linkedin":          ["artigo_linkedin"],
        "medium":            ["artigo_linkedin", "perfil_institucional"],
        "youtube":           ["roteiro_youtube"],
        "substack":          ["artigo_linkedin", "comunicado_imprensa"],
        "hackernoon":        ["artigo_linkedin"],
        "devto":             ["artigo_linkedin"],
        "exame":             ["comunicado_imprensa", "artigo_linkedin"],
        "infomoney":         ["comunicado_imprensa"],
        "estadao_empresas":  ["comunicado_imprensa"],
        "startse":           ["artigo_linkedin"],
        "observador":        ["comunicado_imprensa"],
        "crunchbase":        ["biografia_executiva", "perfil_institucional"],
        "google_business":   ["perfil_institucional"],
        "glassdoor":         ["perfil_institucional"],
        "globenewswire":     ["comunicado_imprensa"],
        "einpresswire":      ["comunicado_imprensa"],
        "prnewswire":        ["comunicado_imprensa"],
        "einpresswire_br":   ["comunicado_imprensa"],
        "dino":              ["comunicado_imprensa"],
        "wordpress":         ["artigo_linkedin", "perfil_institucional"],
        "ghost":             ["artigo_linkedin"],
        "vimeo":             ["roteiro_youtube"],
        "github":            ["biografia_executiva"],
        "angellist":         ["biografia_executiva", "perfil_institucional"],
    }
    candidates = mapping.get(platform_key, ["artigo_linkedin", "comunicado_imprensa"])
    for c in candidates:
        if c in article_map:
            return c
    return None


# ── Quick Publish UI ──────────────────────────────────────────────────────────

@router.get("/quick-publish/{entity_path:path}", response_class=HTMLResponse)
def quick_publish_page(request: Request, entity_path: str):
    """
    Página de publicação rápida — mostra estado das credenciais, artigos em cache,
    e permite disparar publicação via API ou abrir o assistente manual.
    """
    from services.content_producer import list_cached_articles
    from services.distribution_engine import PLATFORM_REGISTRY
    import os

    slug = entity_path.strip("/").replace("/", "_")
    snap = get_latest_snapshot(slug)
    if not snap:
        return templates.TemplateResponse("result.html", {
            "request": request, "entity_name": entity_path,
            "result": None, "error": f"Nenhum snapshot para '{entity_path}'.",
        })

    entity = snap.get("entity", entity_path)
    articles = list_cached_articles(entity)

    # Estado das credenciais
    creds_status = {
        "medium":    bool(os.getenv("MEDIUM_TOKEN")),
        "linkedin":  bool(os.getenv("LINKEDIN_TOKEN")),
        "wordpress": bool(os.getenv("WP_URL") and os.getenv("WP_USER")),
        "einpresswire": bool(os.getenv("EIN_API_KEY")),
        "ghost":     bool(os.getenv("GHOST_URL") and os.getenv("GHOST_ADMIN_KEY")),
        "dino":      bool(os.getenv("DINO_API_KEY")),
        "globenewswire": bool(os.getenv("GLOBENEWSWIRE_TOKEN")),
        "prnewswire": bool(os.getenv("PRNEWSWIRE_API_KEY")),
    }
    ready_platforms = [k for k, v in creds_status.items() if v]
    has_any_creds = bool(ready_platforms)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return templates.TemplateResponse("quick_publish.html", {
        "request":        request,
        "entity_name":    entity,
        "slug":           slug,
        "generated_at":   generated_at,
        "articles":       articles,
        "creds_status":   creds_status,
        "ready_platforms": ready_platforms,
        "has_any_creds":  has_any_creds,
        "has_articles":   len(articles) > 0,
    })


@router.post("/quick-publish/{slug}/trigger", response_class=HTMLResponse)
async def quick_publish_trigger(
    request: Request,
    slug: str,
    platforms: str = Form(""),
    asset_types: str = Form(""),
    dry_run: str = Form("false"),
):
    """Dispara publicação via API para as plataformas selecionadas."""
    from services.content_producer import list_cached_articles
    from services.distribution_engine import publish_all, PLATFORM_REGISTRY
    from services.snapshot_service import get_latest_snapshot as _gs
    import os

    snap = _gs(slug)
    if not snap:
        return templates.TemplateResponse("result.html", {
            "request": request, "entity_name": slug, "result": None,
            "error": "Snapshot não encontrado.",
        })

    entity = snap.get("entity", slug)
    articles = list_cached_articles(entity)
    if not articles:
        return templates.TemplateResponse("quick_publish.html", {
            "request": request, "entity_name": entity, "slug": slug,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "articles": [], "creds_status": {}, "ready_platforms": [],
            "has_any_creds": False, "has_articles": False,
            "pub_error": "Nenhum artigo em cache. Gerar artigos primeiro.",
        })

    selected_platforms = [p.strip() for p in platforms.split(",") if p.strip()]
    selected_assets = [a.strip() for a in asset_types.split(",") if a.strip()]
    is_dry_run = dry_run.lower() == "true"

    if selected_assets:
        articles = [a for a in articles if a.get("asset_type", "") in selected_assets]

    credentials = {
        "medium_token":     os.getenv("MEDIUM_TOKEN", ""),
        "linkedin_token":   os.getenv("LINKEDIN_TOKEN", ""),
        "wp_url":           os.getenv("WP_URL", ""),
        "wp_user":          os.getenv("WP_USER", ""),
        "wp_pass":          os.getenv("WP_PASS", ""),
        "ein_api_key":      os.getenv("EIN_API_KEY", ""),
        "ghost_url":        os.getenv("GHOST_URL", ""),
        "ghost_admin_key":  os.getenv("GHOST_ADMIN_KEY", ""),
        "dino_api_key":     os.getenv("DINO_API_KEY", ""),
        "globenewswire_token": os.getenv("GLOBENEWSWIRE_TOKEN", ""),
    }

    if is_dry_run:
        from services.distribution_engine import format_for
        preview = {}
        for a in articles:
            body = a.get("body_md", "") or a.get("article", "")
            first_name = entity.split()[0] if entity.split() else entity
            for p in selected_platforms:
                fmt = format_for(p, first_name, body, a.get("seo"))
                preview[f"{a.get('asset_type')}@{p}"] = {
                    "title": fmt.get("title") or fmt.get("headline", ""),
                    "preview": (fmt.get("body", "") or "")[:200],
                    "status": "dry_run",
                }
        pub_results = {"dry_run": True, "preview": preview, "count": len(preview)}
    else:
        pub_results_raw = await publish_all(entity, articles, selected_platforms, credentials)
        pub_results = {
            "dry_run":        False,
            "total_articles": pub_results_raw.get("total_articles", 0),
            "successful":     pub_results_raw.get("successful", 0),
            "total_publishes": pub_results_raw.get("total_publishes", 0),
            "results":        pub_results_raw.get("results", {}),
        }

    # Recarregar estado para mostrar na UI atualizada
    creds_status = {
        "medium":    bool(os.getenv("MEDIUM_TOKEN")),
        "linkedin":  bool(os.getenv("LINKEDIN_TOKEN")),
        "wordpress": bool(os.getenv("WP_URL") and os.getenv("WP_USER")),
        "einpresswire": bool(os.getenv("EIN_API_KEY")),
        "ghost":     bool(os.getenv("GHOST_URL") and os.getenv("GHOST_ADMIN_KEY")),
        "dino":      bool(os.getenv("DINO_API_KEY")),
        "globenewswire": bool(os.getenv("GLOBENEWSWIRE_TOKEN")),
    }
    ready_platforms = [k for k, v in creds_status.items() if v]

    return templates.TemplateResponse("quick_publish.html", {
        "request":        request,
        "entity_name":    entity,
        "slug":           slug,
        "generated_at":   datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "articles":       list_cached_articles(entity),
        "creds_status":   creds_status,
        "ready_platforms": ready_platforms,
        "has_any_creds":  bool(ready_platforms),
        "has_articles":   len(articles) > 0,
        "pub_results":    pub_results,
    })
