import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from services.constants import classify_domain
from services.archetype import classify_archetype, classify_crisis_state
from services.youtube_warfare import extract_youtube_results, compute_youtube_toxicity, compute_video_npa_boost
from services.metrics import compute_news_counts, compute_momentum, compute_neg_ratio

import os
if os.environ.get("VERCEL"):
    SNAPSHOTS_DIR = Path("/tmp/snapshots")
else:
    SNAPSHOTS_DIR = Path(__file__).parent.parent / "snapshots"
INDEX_PATH = SNAPSHOTS_DIR / "entities.json"


def _atomic_write_json(path: Path, data: dict | list) -> None:
    """Escrita atômica: temp → rename. Elimina corrupção por crash durante escrita."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, ensure_ascii=False)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise

NEGATIVE_KEYWORDS = [
    "fraude", "escândalo", "escandalo", "crime",
    "prisão", "prisao", "preso", "condenado", "golpe",
    "denúncia", "denuncia", "acusação", "acusacao",
    "polêmica", "polemica", "investigação", "investigacao",
    "frauda", "lawsuit", "scandal", "fraud",
    "criminal", "indicted", "arrested", "controversy", "crisis",
]

POSITIVE_KEYWORDS = [
    "fundador", "founder", "best-seller", "bestseller", "líder", "lider",
    "award", "prêmio", "premio", "reconhecido", "reconhecimento",
    "sucesso", "success", "lançamento", "lancamento", "investidor",
    "empreendedor", "entrepreneur", "author", "autor", "CEO", "destaque",
]

SOCIAL_DOMAINS = [
    "instagram.com", "tiktok.com", "twitter.com", "x.com",
    "linkedin.com", "youtube.com", "facebook.com",
]

DOMAIN_TYPES = {}  # retained for import compatibility — use classify_domain()


def _classify_domain(domain: str) -> str:
    return classify_domain(domain)


def _classify_snippet(snippet: str) -> str:
    text = (snippet or "").lower()
    if any(k in text for k in NEGATIVE_KEYWORDS):
        return "negative"
    if any(k in text for k in POSITIVE_KEYWORDS):
        return "positive"
    return "neutral"


def _entity_slug(entity: str) -> str:
    slug = entity.lower().strip()
    slug = re.sub(r"[^\w\s]", "", slug)
    slug = re.sub(r"\s+", "_", slug)
    return slug


def _is_controlled(domain: str, entity_slug: str) -> bool:
    if any(s in domain for s in SOCIAL_DOMAINS):
        return True
    clean_slug = entity_slug.replace("_", "")
    return clean_slug in domain.replace(".", "").replace("-", "")


def save_snapshot(entity: str, serp: list[dict], news: list[dict],
                  expansion_associations: list[dict] | None = None,
                  aio_report: dict | None = None) -> Path:
    slug = _entity_slug(entity)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    enriched_serp = []
    sentiment_counts = {"negative": 0, "neutral": 0, "positive": 0}
    controlled = 0
    top_3_negative = 0
    legal_domains = 0

    for r in serp:
        domain = urlparse(r.get("link", "")).netloc.replace("www.", "")
        dtype = _classify_domain(domain)
        sentiment = _classify_snippet(r.get("snippet", ""))
        is_ctrl = _is_controlled(domain, slug)
        position = r.get("position", 99)

        sentiment_counts[sentiment] += 1
        if is_ctrl:
            controlled += 1
        if sentiment == "negative" and position <= 3:
            top_3_negative += 1
        if dtype == "legal":
            legal_domains += 1

        enriched_serp.append({
            "position":   position,
            "title":      r.get("title", ""),
            "link":       r.get("link", ""),
            "snippet":    r.get("snippet", ""),
            "domain":     domain,
            "type":       dtype,
            "sentiment":  sentiment,
            "controlled": is_ctrl,
            "is_video":   "youtube.com" in domain or "youtu.be" in r.get("link", ""),
        })

    total = len(enriched_serp) or 1
    page_1_negative_ratio = compute_neg_ratio(enriched_serp)  # fonte canônica

    ctrl_ratio = controlled / total
    if ctrl_ratio < 0.3:
        authority_vacuum = "HIGH"
    elif ctrl_ratio < 0.5:
        authority_vacuum = "MODERATE"
    else:
        authority_vacuum = "LOW"

    # NPA summary — usar compute_npa_domains como fonte canônica
    # Inclui SERP enrichment + authority-weighted ranking
    from services.metrics import compute_npa_domains
    npa = compute_npa_domains(news, enriched_serp)

    snapshot = {
        "entity":   entity,
        "date":     date_str,
        "serp":     enriched_serp,
        "domains":  [r["domain"] for r in enriched_serp],
        "sentiment_counts":        sentiment_counts,
        "controlled_assets":       controlled,
        "page_1_negative_ratio":   page_1_negative_ratio,
        "top_3_negative_count":    top_3_negative,
        "legal_domain_count":      legal_domains,
        "authority_vacuum":        authority_vacuum,
        "expansion_associations":  expansion_associations or [],
        "narrative_pressure": {
            "count_7d":              npa["count_7d"],
            "count_30d":             npa["count_30d"],
            "momentum":              npa["momentum"],
            "most_aggressive":       npa["most_aggressive"],
            "most_aggressive_count": npa["most_aggressive_count"],
            "top_domains":           npa["top_domains"],      # agora salvo no snapshot
            "concentration":         npa["concentration"],
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    snapshot["threat_archetype"] = classify_archetype(snapshot)
    snapshot["crisis_state"]     = classify_crisis_state(snapshot)

    # Inferir e persistir threat_level no snapshot para acesso direto pelos outros módulos
    snapshot["threat_level"] = infer_threat_from_snapshot(snapshot)

    # YouTube analysis
    youtube_videos = extract_youtube_results(enriched_serp)
    youtube_toxicity = compute_youtube_toxicity(youtube_videos)
    video_npa_boost = compute_video_npa_boost(youtube_toxicity)
    snapshot["youtube_toxicity"]   = youtube_toxicity
    snapshot["video_npa_boost"]    = video_npa_boost
    snapshot["youtube_videos"]     = youtube_videos

    # AI Overview — persisténcia dos scores AIO no snapshot
    if aio_report:
        snapshot["aio_has_overview"]  = aio_report.get("has_overview", False)
        snapshot["aio_risk_score"]    = aio_report.get("risk_score", 0.0)
        snapshot["aio_risk_label"]    = aio_report.get("risk_label", "SEM OVERVIEW")
        snapshot["aio_sentiment"]     = aio_report.get("sentiment", "absent")
        snapshot["aio_source_count"]  = aio_report.get("source_count", 0)
        snapshot["aio_cited_sources"] = aio_report.get("cited_sources", [])
        snapshot["aio_llm_analysis"]  = aio_report.get("llm_analysis", "")
    else:
        snapshot["aio_has_overview"]  = False
        snapshot["aio_risk_score"]    = 0.0
        snapshot["aio_risk_label"]    = "N/A"
        snapshot["aio_sentiment"]     = "absent"
        snapshot["aio_source_count"]  = 0
        snapshot["aio_cited_sources"] = []
        snapshot["aio_llm_analysis"]  = ""

    # Deep SERP — campos inicializados como None (serão preenchidos async)
    snapshot["deep_negative_index"]  = None
    snapshot["dni_label"]            = None
    snapshot["resurface_risk"]       = None
    snapshot["deep_negatives_count"] = None

    out_dir = SNAPSHOTS_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{date_str}.json"
    _atomic_write_json(out_path, snapshot)

    _update_entity_index(slug, snapshot, out_dir)
    return out_path


def compare_snapshots(old_path: str, new_path: str) -> dict:
    old = json.loads(Path(old_path).read_text(encoding="utf-8"))
    new = json.loads(Path(new_path).read_text(encoding="utf-8"))

    # Ranking movement
    old_positions  = {r["domain"]: r.get("position", 99) for r in old.get("serp", [])}
    new_positions  = {r["domain"]: r.get("position", 99) for r in new.get("serp", [])}
    old_negatives  = {r["domain"] for r in old.get("serp", []) if r.get("sentiment") == "negative"}
    new_negatives  = {r["domain"] for r in new.get("serp", []) if r.get("sentiment") == "negative"}
    all_domains    = set(old_positions) | set(new_positions)

    moved_up, moved_down, entered, exited = [], [], [], []
    new_negative_entrants = []

    for domain in all_domains:
        in_old = domain in old_positions
        in_new = domain in new_positions

        if in_old and in_new:
            delta = old_positions[domain] - new_positions[domain]
            if delta > 0:
                moved_up.append({"domain": domain, "from": old_positions[domain], "to": new_positions[domain]})
            elif delta < 0:
                moved_down.append({"domain": domain, "from": old_positions[domain], "to": new_positions[domain]})
        elif in_new:
            entered.append({"domain": domain, "position": new_positions[domain]})
            if domain in new_negatives:
                new_negative_entrants.append({"domain": domain, "position": new_positions[domain]})
        else:
            exited.append({"domain": domain, "last_position": old_positions[domain]})

    # Core metrics
    old_sc = old.get("sentiment_counts", {})
    new_sc = new.get("sentiment_counts", {})
    neg_displacement = old_sc.get("negative", 0) - new_sc.get("negative", 0)
    asset_growth = new.get("controlled_assets", 0) - old.get("controlled_assets", 0)
    old_ns = old.get("controlled_assets", 0) / 10
    new_ns = new.get("controlled_assets", 0) / 10
    narrative_share_delta = round((new_ns - old_ns) * 100, 1)
    neg_ratio_delta = round(new.get("page_1_negative_ratio", 0) - old.get("page_1_negative_ratio", 0), 3)
    top3_delta = new.get("top_3_negative_count", 0) - old.get("top_3_negative_count", 0)

    return {
        "period": {"from": old.get("date", "?"), "to": new.get("date", "?")},
        "ranking_movement": {
            "moved_up":             sorted(moved_up,   key=lambda x: x["to"]),
            "moved_down":           sorted(moved_down, key=lambda x: x["to"]),
            "entered":              sorted(entered,    key=lambda x: x["position"]),
            "exited":               exited,
            "new_negative_entrants": new_negative_entrants,
        },
        "negative_displacement":      neg_displacement,
        "asset_penetration_growth":   asset_growth,
        "narrative_share_change_pp":  narrative_share_delta,
        "page_1_negative_ratio_delta": neg_ratio_delta,
        "top_3_negative_delta":        top3_delta,
    }


# ── Occupation intelligence extraction ─────────────────────────────────────────

def get_latest_snapshot(slug: str) -> dict | None:
    """Returns the most recent snapshot for an entity slug."""
    dir_path = SNAPSHOTS_DIR / slug
    if not dir_path.exists():
        return None
    files = sorted(dir_path.glob("*.json"))
    if not files:
        return None
    return json.loads(files[-1].read_text(encoding="utf-8"))


def get_two_latest_snapshots(slug: str) -> tuple[dict | None, dict | None]:
    """Returns (previous, latest) snapshots.

    Se só existir um snapshot, retorna (None, latest).
    Usado pelo monitor /check para comparar sem chamar APIs externas.
    """
    dir_path = SNAPSHOTS_DIR / slug
    if not dir_path.exists():
        return None, None
    files = sorted(dir_path.glob("*.json"))
    if not files:
        return None, None
    latest = json.loads(files[-1].read_text(encoding="utf-8"))
    previous = json.loads(files[-2].read_text(encoding="utf-8")) if len(files) >= 2 else None
    return previous, latest


def infer_threat_from_snapshot(snapshot: dict) -> str:
    """Compute threat level from snapshot metrics without LLM text."""
    neg_ratio  = snapshot.get("page_1_negative_ratio", 0)
    top3_neg   = snapshot.get("top_3_negative_count", 0)
    legal_cnt  = snapshot.get("legal_domain_count", 0)
    momentum   = snapshot.get("narrative_pressure", {}).get("momentum", "Stable")
    count_7d   = snapshot.get("narrative_pressure", {}).get("count_7d", 0)

    if neg_ratio >= 0.5 and legal_cnt >= 2:
        return "CRITICAL"
    if momentum == "Escalating" and (top3_neg >= 1 or legal_cnt >= 1):
        return "CRITICAL"
    if neg_ratio >= 0.3 or legal_cnt >= 1:
        return "HIGH"
    if momentum == "Escalating" or count_7d >= 3:
        return "MEDIUM"
    if neg_ratio > 0:
        return "MEDIUM"
    return "LOW"


def extract_negative_domains(snapshot: dict) -> list[str]:
    """Extract unique negative domains from snapshot SERP data."""
    domains = []
    for r in snapshot.get("serp", []):
        if r.get("sentiment") == "negative":
            d = r.get("domain", "")
            if d and d not in domains:
                domains.append(d)
    return domains


def extract_source_concentration(snapshot: dict) -> tuple[str, str]:
    """Returns (concentration_label, dominant_type) from snapshot."""
    from collections import Counter
    cnt = Counter()
    types = Counter()
    for r in snapshot.get("serp", []):
        d = r.get("domain", "")
        t = r.get("type", "blog")
        if d:
            cnt[d] += 1
            types[t] += 1
    total = sum(cnt.values()) or 1
    top_domain, top_count = cnt.most_common(1)[0] if cnt else ("—", 0)
    concentration = "Concentrated" if top_count / total > 0.5 else "Distributed"
    dominant_type = types.most_common(1)[0][0] if types else "unknown"
    return concentration, dominant_type


def format_associations_from_snapshot(snapshot: dict) -> str:
    """Format expansion associations from snapshot for prompt injection."""
    assocs = snapshot.get("expansion_associations", [])
    if not assocs:
        return "Nenhuma associação crítica armazenada no snapshot."
    lines = []
    for a in assocs[:6]:
        domains_str = ", ".join(a.get("domains", [])) if a.get("domains") else "fonte desconhecida"
        lines.append(
            f"  {a.get('entity', a.get('entity_name', '?'))}\n"
            f"    Tipo: {a.get('type', 'unknown')} | Risco: {a.get('risk', '?')} | Domínios: {domains_str}"
        )
    return "\n".join(lines)


# ── Entity Index ───────────────────────────────────────────────────────────────

def _update_entity_index(slug: str, snapshot: dict, entity_dir: Path):
    """Update the global entity index after saving a snapshot."""
    index = _load_entity_index()
    threat = infer_threat_from_snapshot(snapshot)

    snapshot_files = sorted(entity_dir.glob("*.json"))
    index[slug] = {
        "slug":            slug,
        "entity":          snapshot["entity"],
        "latest_snapshot": snapshot["date"],
        "latest_threat":   threat,
        "latest_momentum": snapshot.get("narrative_pressure", {}).get("momentum", "stable").lower(),
        "latest_archetype": snapshot.get("threat_archetype", "corporate"),
        "latest_crisis":    snapshot.get("crisis_state", "stable"),
        "youtube_toxicity": (snapshot.get("youtube_toxicity", {}) or {}).get("total", 0),
        "video_count":      len(snapshot.get("youtube_videos", []) or []),
        "kp_score":         None,  # computed on demand
        "last_update":     datetime.now(timezone.utc).isoformat(),
        "snapshot_count":  len(snapshot_files),
    }

    _atomic_write_json(INDEX_PATH, index)


def _load_entity_index() -> dict:
    """Load the entity index, auto-rebuild if missing or stale."""
    if not INDEX_PATH.exists():
        return _rebuild_entity_index()
    try:
        data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return _rebuild_entity_index()
        return data
    except (json.JSONDecodeError, KeyError):
        return _rebuild_entity_index()


def _rebuild_entity_index() -> dict:
    """Scan the snapshots directory and rebuild the entity index."""
    index = {}
    if not SNAPSHOTS_DIR.exists():
        return index

    for entity_dir in SNAPSHOTS_DIR.iterdir():
        if not entity_dir.is_dir() or entity_dir.name.startswith("."):
            continue
        files = sorted(entity_dir.glob("*.json"))
        if not files:
            continue
        latest = json.loads(files[-1].read_text(encoding="utf-8"))
        slug = entity_dir.name
        entity = latest.get("entity", slug)
        momentum = latest.get("narrative_pressure", {}).get("momentum", "Stable")
        threat = infer_threat_from_snapshot(latest)

        index[slug] = {
            "slug":            slug,
            "entity":          entity,
            "latest_snapshot": latest.get("date", ""),
            "latest_threat":   threat,
            "latest_momentum": momentum.lower(),
            "latest_archetype": latest.get("threat_archetype", classify_archetype(latest)),
            "latest_crisis":    latest.get("crisis_state", classify_crisis_state(latest)),
            "last_update":     latest.get("date", ""),
            "snapshot_count":  len(files),
        }

    _atomic_write_json(INDEX_PATH, index)
    return index


def list_entities() -> list[dict]:
    """Return all entities from the index, sorted by last_update descending."""
    index = _load_entity_index()
    entities = list(index.values())
    entities.sort(key=lambda e: e.get("last_update", ""), reverse=True)
    return entities


def get_all_snapshots(slug: str) -> list[dict]:
    """Return all snapshots for an entity, oldest first."""
    dir_path = SNAPSHOTS_DIR / slug
    if not dir_path.exists():
        return []
    files = sorted(dir_path.glob("*.json"))
    snapshots = []
    for f in files:
        snap = json.loads(f.read_text(encoding="utf-8"))
        snap["threat"] = infer_threat_from_snapshot(snap)
        snapshots.append(snap)
    return snapshots


def update_snapshot_deep_serp(slug: str, deep_report: dict) -> bool:
    """
    Atualiza o snapshot mais recente com os dados do Deep SERP.

    Chamado de forma assíncrona (thread separada) após o deep audit concluir.
    Retorna True se o snapshot foi encontrado e atualizado, False caso contrário.
    """
    dir_path = SNAPSHOTS_DIR / slug
    if not dir_path.exists():
        return False

    files = sorted(dir_path.glob("*.json"))
    if not files:
        return False

    latest_path = files[-1]
    try:
        snap = json.loads(latest_path.read_text(encoding="utf-8"))

        # Atualizar campos deep SERP
        snap["deep_negative_index"]  = deep_report.get("deep_negative_index")
        snap["dni_label"]            = deep_report.get("dni_label")
        snap["resurface_risk"]       = deep_report.get("resurface_risk")
        snap["deep_negatives_count"] = deep_report.get("total_negatives", 0)
        snap["deep_suppressed_count"] = len(deep_report.get("suppressed_domains", []))
        snap["deep_serp_fetched_at"] = deep_report.get("fetched_at")

        _atomic_write_json(latest_path, snap)
        return True
    except Exception as e:
        import logging as _log
        _log.getLogger("councilia.snapshot").warning(
            f"Falha ao atualizar snapshot deep SERP para {slug}: {e}"
        )
        return False

