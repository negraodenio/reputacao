"""
Political Routes — API do Módulo Político-Eleitoral.

Endpoints:
  GET  /political              → Dashboard de assessor
  POST /political/register     → Cadastrar político
  POST /political/audit        → Auditoria especializada
  POST /political/pipeline     → Rodar pipeline completo
  POST /political/content      → Gerar conteúdo específico
  POST /political/opponent     → Análise de oponente
  GET  /political/calendar/{slug} → Calendário eleitoral
  GET  /political/status/{slug}   → Status do pipeline
  GET  /political/queue/{slug}    → Fila de distribuição
  POST /political/mark-sent    → Marcar conteúdo como enviado
"""
import re
from datetime import date, datetime, timezone

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))


def _slug(name: str) -> str:
    s = re.sub(r"[^\w\s]", "", name.lower().strip())
    return re.sub(r"\s+", "_", s)


# ── Dashboard Principal ─────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def political_dashboard(request: Request):
    from services.political_engine import (
        list_politicians, get_electoral_window, POLITICAL_ROLES, PARTIES, STATES
    )
    from services.political_pipeline import get_pipeline_status

    politicians = list_politicians()
    window = get_electoral_window(date.today())

    # Enriquecer com status de pipeline
    for p in politicians:
        status = get_pipeline_status(p.slug)
        p._pipeline_status = status.get("last_run", {}).get("status", "never_run")
        p._last_run = status.get("last_run", {}).get("completed_at", "")
        p._threat = status.get("last_run", {}).get("threat_level", "—")

    return templates.TemplateResponse("political_dashboard.html", {
        "request":     request,
        "politicians": politicians,
        "window":      window,
        "roles":       POLITICAL_ROLES,
        "parties":     PARTIES,
        "states":      STATES,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    })


# ── Cadastro de Político ────────────────────────────────────────────────────

@router.post("/register")
def register_politician(
    request:       Request,
    name:          str = Form(...),
    role:          str = Form(...),
    party:         str = Form(...),
    state:         str = Form(...),
    city:          str = Form(""),
    target_role:   str = Form(""),
    opponent:      str = Form(""),
    keywords:      str = Form(""),
    election_year: int = Form(2026),
    original_slug: str = Form(""),
):
    from services.political_engine import PoliticalEntity, register_politician as _register, delete_politician

    entity = PoliticalEntity(
        name=name,
        slug=_slug(name),
        role=role,
        party=party,
        state=state,
        city=city,
        target_role=target_role or role,
        opponent=opponent,
        keywords=[k.strip() for k in keywords.split(",") if k.strip()],
        election_year=election_year,
    )
    
    if original_slug and original_slug != entity.slug:
        delete_politician(original_slug)

    _register(entity)

    return JSONResponse({
        "status": "registered",
        "slug":   entity.slug,
        "name":   entity.name,
        "message": f"Político '{name}' cadastrado com sucesso. Slug: {entity.slug}",
    })


# ── Auditoria Especializada ─────────────────────────────────────────────────

@router.post("/audit")
def political_audit(
    request: Request,
    slug:    str = Form(...),
):
    from services.political_engine import get_politician, political_queries, electoral_calendar
    from services.audit_service import run_audit

    entity = get_politician(slug)
    if not entity:
        return JSONResponse({"error": f"Político '{slug}' não encontrado."}, status_code=404)

    queries = political_queries(entity)
    # Usa a query principal (nome completo)
    audit_result = run_audit(
        entity_name=entity.name,
        country="Brazil",
        industry="political",
    )

    calendar = electoral_calendar(entity)

    return JSONResponse({
        "entity":          entity.name,
        "slug":            slug,
        "queries_checked": queries,
        "threat_level":    audit_result.get("text", "")[:100],
        "ai_overview":     audit_result.get("ai_overview", {}),
        "calendar":        calendar,
        "audit_text":      audit_result.get("text", "")[:1000],
    })


# ── Pipeline Completo ───────────────────────────────────────────────────────

@router.post("/pipeline")
def run_pipeline(
    request: Request,
    slug:    str = Form(...),
    async_mode: str = Form("true"),
):
    from services.political_pipeline import run_political_pipeline

    result = run_political_pipeline(
        politician_slug=slug,
        async_mode=(async_mode.lower() == "true"),
    )
    return JSONResponse(result)


# ── Gerar Conteúdo ─────────────────────────────────────────────────────────

@router.post("/content")
def generate_content(
    request:      Request,
    slug:         str = Form(...),
    content_type: str = Form(...),
    details:      str = Form(""),
    mandate_info: str = Form(""),
):
    from services.political_engine import get_politician, get_electoral_window
    from services.political_content_producer import (
        produce_political_content, save_political_content
    )

    entity = get_politician(slug)
    if not entity:
        return JSONResponse({"error": f"Político '{slug}' não encontrado."}, status_code=404)

    window = get_electoral_window(date.today())

    content = produce_political_content(
        entity_name=entity.name,
        content_type=content_type,
        context={
            "role":         entity.role,
            "party":        entity.party,
            "state":        entity.state,
            "city":         entity.city,
            "details":      details,
            "mandate_info": mandate_info,
        },
        electoral_window=window["window"],
    )

    if not content.get("error"):
        save_political_content(slug, content_type, content)

    return JSONResponse(content)


# ── Análise de Oponente ─────────────────────────────────────────────────────

@router.post("/opponent")
def opponent_analysis(
    request:       Request,
    slug:          str = Form(...),
    opponent_name: str = Form(""),
):
    from services.political_engine import get_politician
    from services.opponent_service import analyze_opponent

    entity = get_politician(slug)
    if not entity:
        return JSONResponse({"error": f"Político '{slug}' não encontrado."}, status_code=404)

    opp = opponent_name or entity.opponent
    if not opp:
        return JSONResponse({"error": "Nome do adversário não fornecido."}, status_code=400)

    report = analyze_opponent(entity.name, opp)
    return JSONResponse(report)


# ── Calendário Eleitoral ────────────────────────────────────────────────────

@router.get("/calendar/{slug}", response_class=HTMLResponse)
def electoral_calendar_view(request: Request, slug: str):
    from services.political_engine import get_politician, electoral_calendar

    entity = get_politician(slug)
    if not entity:
        return HTMLResponse(f"<h2>Político '{slug}' não encontrado.</h2>", status_code=404)

    calendar = electoral_calendar(entity)
    return templates.TemplateResponse("political_calendar.html", {
        "request":  request,
        "entity":   entity,
        "calendar": calendar,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    })


# ── Status do Pipeline ──────────────────────────────────────────────────────

@router.get("/status/{slug}")
def pipeline_status(request: Request, slug: str):
    from services.political_pipeline import get_pipeline_status
    return JSONResponse(get_pipeline_status(slug))


# ── Fila de Distribuição ────────────────────────────────────────────────────

@router.get("/queue/{slug}", response_class=HTMLResponse)
def distribution_queue(request: Request, slug: str):
    from services.political_engine import get_politician
    from services.political_pipeline import get_distribution_queue
    from services.political_content_producer import list_political_content

    entity = get_politician(slug)
    queue  = get_distribution_queue(slug)
    content_list = list_political_content(slug)

    return templates.TemplateResponse("political_queue.html", {
        "request":      request,
        "entity":       entity,
        "slug":         slug,
        "queue":        queue,
        "content_list": content_list,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    })


# ── Marcar como Enviado ─────────────────────────────────────────────────────

@router.post("/mark-sent")
def mark_sent(
    request:      Request,
    slug:         str = Form(...),
    portal_name:  str = Form(...),
    content_type: str = Form(...),
    published_url: str = Form(""),
):
    from services.political_pipeline import mark_distributed

    ok = mark_distributed(slug, portal_name, content_type, published_url)
    return JSONResponse({
        "status": "marked" if ok else "not_found",
        "slug":   slug,
        "portal": portal_name,
    })


# ── Portais Disponíveis por Estado ─────────────────────────────────────────

@router.get("/portals/{state}")
def portals_by_state(request: Request, state: str):
    from services.regional_portals import get_state_portals_summary
    return JSONResponse(get_state_portals_summary(state.upper()))
