"""
Automation API Routes — Endpoints JSON para integração com sistemas externos.

Permite:
  - Disparar auditorias via HTTP (Make, Zapier, scripts, agendadores)
  - Publicar conteúdo em plataformas via API
  - Deploy automático de sites para Netlify
  - Consultar status do pipeline pós-audit

Todos os endpoints retornam JSON (não HTML).
Autenticação via API key no header X-CouncilIA-Key (configurável em .env).
"""
import os
import logging
import zipfile
import io
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Header, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger("councilia.api")

router = APIRouter(prefix="/api", tags=["automation"])

# API key simples — definir COUNCILIA_API_KEY no .env para proteger os endpoints.
# Se não definida, os endpoints ficam abertos (aceitável em localhost).
_API_KEY = os.environ.get("COUNCILIA_API_KEY", "")


def _check_auth(x_councilia_key: str = "") -> None:
    if _API_KEY and x_councilia_key != _API_KEY:
        raise HTTPException(status_code=401, detail="API key inválida ou ausente.")


# ── SCHEMAS ────────────────────────────────────────────────────────────────

class AuditRequest(BaseModel):
    entity_name: str
    country: str = "Brasil"
    industry: str = ""
    auto_content: bool = True  # se False, desabilita o pipeline pós-audit


class PublishRequest(BaseModel):
    platforms: list[str] | None = None  # None = todas as plataformas com API free
    asset_types: list[str] | None = None  # None = todos em cache
    dry_run: bool = False  # True = formata mas não publica de fato


class DeployRequest(BaseModel):
    site_id: str | None = None  # ID do site no Netlify (usa NETLIFY_SITE_ID se None)


# ── AUDIT ──────────────────────────────────────────────────────────────────

@router.post("/audit")
async def trigger_audit(
    body: AuditRequest,
    background_tasks: BackgroundTasks,
    x_councilia_key: str = Header(default=""),
):
    """
    Dispara uma auditoria completa de forma assíncrona.

    Retorna imediatamente com o slug gerado.
    O resultado fica disponível em GET /api/audit/{slug}/status.

    Uso externo:
      curl -X POST http://localhost:8000/api/audit \\
           -H "Content-Type: application/json" \\
           -H "X-CouncilIA-Key: sua_chave" \\
           -d '{"entity_name": "João Silva", "country": "Brasil", "industry": "Finanças"}'
    """
    _check_auth(x_councilia_key)

    import re
    slug = re.sub(r"\s+", "_", body.entity_name.lower().strip())
    slug = re.sub(r"[^\w]", "", slug)

    background_tasks.add_task(
        _run_audit_background,
        body.entity_name,
        body.country,
        body.industry,
        body.auto_content,
        slug,
    )

    return {
        "status": "queued",
        "slug": slug,
        "entity_name": body.entity_name,
        "queued_at": datetime.now(timezone.utc).isoformat(),
        "check_status_at": f"/api/audit/{slug}/status",
        "report_at": f"http://localhost:8000/snapshots/{slug}/compare",
        "message": "Auditoria iniciada em background. Resultados disponíveis em 30-90 segundos.",
    }


def _run_audit_background(
    entity_name: str,
    country: str,
    industry: str,
    auto_content: bool,
    slug: str,
) -> None:
    """Executa audit em thread background (chamado pelo BackgroundTasks do FastAPI)."""
    from services.audit_service import run_audit
    import re

    try:
        logger.info(f"[{slug}] Audit background iniciado para '{entity_name}'")
        # Se auto_content=False, desabilita o pipeline pós-audit temporariamente
        if not auto_content:
            import services.post_audit_pipeline as _pip
            original = _pip._ASSETS_BY_THREAT.copy()
            _pip._ASSETS_BY_THREAT = {"LOW": [], "MEDIUM": [], "HIGH": [], "CRITICAL": []}

        run_audit(entity_name, country=country, industry=industry)
        logger.info(f"[{slug}] Audit background concluído.")

        if not auto_content:
            _pip._ASSETS_BY_THREAT = original
    except Exception as e:
        logger.error(f"[{slug}] Audit background falhou: {e}")


@router.get("/audit/{slug}/status")
async def audit_status(
    slug: str,
    x_councilia_key: str = Header(default=""),
):
    """Retorna o status da última auditoria para um slug."""
    _check_auth(x_councilia_key)

    from services.snapshot_service import get_latest_snapshot, get_all_snapshots
    from services.post_audit_pipeline import get_pipeline_status

    snap = get_latest_snapshot(slug)
    if not snap:
        return {"status": "not_found", "slug": slug}

    all_snaps = get_all_snapshots(slug)
    pipeline = get_pipeline_status(slug)

    return {
        "status": "ok",
        "slug": slug,
        "entity": snap.get("entity", slug),
        "latest_snapshot": snap.get("generated_at", ""),
        "threat_level": snap.get("threat_level", ""),
        "threat_archetype": snap.get("threat_archetype", ""),
        "npa_score": snap.get("npa_score"),
        "snapshot_count": len(all_snaps),
        "pipeline": pipeline,
        "links": {
            "report":      f"http://localhost:8000/battle-plan/{slug}",
            "content":     f"http://localhost:8000/content/{slug}",
            "distribution": f"http://localhost:8000/distribution/{slug}",
        },
    }


@router.post("/audit/batch")
async def batch_audit(
    entities: list[AuditRequest],
    background_tasks: BackgroundTasks,
    x_councilia_key: str = Header(default=""),
):
    """
    Dispara auditorias para múltiplas entidades de uma vez.
    Máximo de 10 entidades por chamada (para não sobrecarregar APIs externas).
    """
    _check_auth(x_councilia_key)

    if len(entities) > 10:
        raise HTTPException(status_code=400, detail="Máximo de 10 entidades por batch.")

    import re
    results = []
    for e in entities:
        slug = re.sub(r"\s+", "_", e.entity_name.lower().strip())
        slug = re.sub(r"[^\w]", "", slug)
        background_tasks.add_task(
            _run_audit_background, e.entity_name, e.country, e.industry, e.auto_content, slug
        )
        results.append({"entity_name": e.entity_name, "slug": slug, "status": "queued"})

    return {
        "status": "batch_queued",
        "count": len(results),
        "entities": results,
        "queued_at": datetime.now(timezone.utc).isoformat(),
    }


# ── PUBLISH ────────────────────────────────────────────────────────────────

@router.post("/publish/{slug}")
async def publish_content(
    slug: str,
    body: PublishRequest,
    x_councilia_key: str = Header(default=""),
):
    """
    Publica conteúdo em cache nas plataformas configuradas.

    Credenciais lidas do .env:
      MEDIUM_TOKEN, LINKEDIN_TOKEN, WP_URL/WP_USER/WP_PASS,
      EIN_API_KEY, GHOST_URL/GHOST_ADMIN_KEY

    Se dry_run=True, formata o conteúdo mas não envia nada.
    """
    _check_auth(x_councilia_key)

    from services.snapshot_service import get_latest_snapshot
    from services.content_producer import list_cached_articles
    from services.distribution_engine import (
        PLATFORM_REGISTRY, publish_all, format_for
    )

    snap = get_latest_snapshot(slug)
    if not snap:
        raise HTTPException(status_code=404, detail=f"Snapshot não encontrado para '{slug}'")

    entity = snap.get("entity", slug)
    articles = list_cached_articles(entity)
    if not articles:
        return {"status": "no_content", "message": "Nenhum artigo em cache. Rodar geração primeiro."}

    # Filtrar por asset_type se especificado
    if body.asset_types:
        articles = [a for a in articles if a.get("asset_type", "") in body.asset_types]

    # Plataformas — default: só APIs gratuitas com credencial disponível
    platforms = body.platforms or _get_available_platforms()

    if not platforms:
        return {
            "status": "no_credentials",
            "message": "Nenhuma credencial de publicação encontrada no .env. "
                       "Configurar MEDIUM_TOKEN, LINKEDIN_TOKEN, etc.",
        }

    if body.dry_run:
        # Dry run: apenas formata e retorna o payload
        preview = {}
        for a in articles:
            asset_type = a.get("asset_type", "")
            body_text = a.get("body_md", "") or a.get("article", "")
            for p in platforms:
                first_name = entity.split()[0] if entity.split() else entity
                formatted = format_for(p, first_name, body_text, a.get("seo"))
                preview[f"{asset_type}@{p}"] = {
                    "platform": p,
                    "asset_type": asset_type,
                    "title": formatted.get("title") or formatted.get("headline", ""),
                    "body_preview": (formatted.get("body", "") or "")[:200] + "...",
                }
        return {"status": "dry_run", "would_publish": len(preview), "preview": preview}

    # Publicação real — publish_all é async, rota também é async, usar await diretamente
    credentials = _load_credentials()
    results = await publish_all(entity, articles, platforms, credentials)

    return {
        "status": "published",
        "entity": entity,
        "slug": slug,
        "total_articles": results.get("total_articles"),
        "total_publishes": results.get("total_publishes"),
        "successful": results.get("successful"),
        "generated_at": results.get("generated_at"),
        "results_summary": {
            k: v.get("status", "unknown")
            for k, v in results.get("results", {}).items()
        },
    }


def _get_available_platforms() -> list[str]:
    """Retorna plataformas com API gratuita E credencial configurada no .env."""
    available = []
    if os.environ.get("MEDIUM_TOKEN"):
        available.append("medium")
    if os.environ.get("LINKEDIN_TOKEN"):
        available.append("linkedin")
    if os.environ.get("WP_URL") and os.environ.get("WP_USER"):
        available.append("wordpress")
    if os.environ.get("EIN_API_KEY"):
        available.append("einpresswire")
    if os.environ.get("GHOST_URL") and os.environ.get("GHOST_ADMIN_KEY"):
        available.append("ghost")
    return available


def _load_credentials() -> dict:
    return {
        "medium_token":     os.environ.get("MEDIUM_TOKEN", ""),
        "linkedin_token":   os.environ.get("LINKEDIN_TOKEN", ""),
        "wp_url":           os.environ.get("WP_URL", ""),
        "wp_user":          os.environ.get("WP_USER", ""),
        "wp_pass":          os.environ.get("WP_PASS", ""),
        "ein_api_key":      os.environ.get("EIN_API_KEY", ""),
        "ghost_url":        os.environ.get("GHOST_URL", ""),
        "ghost_admin_key":  os.environ.get("GHOST_ADMIN_KEY", ""),
    }


# ── NETLIFY DEPLOY ─────────────────────────────────────────────────────────

@router.post("/deploy/{slug}")
async def deploy_to_netlify(
    slug: str,
    body: DeployRequest,
    x_councilia_key: str = Header(default=""),
):
    """
    Deploy do site estático gerado para o Netlify via API.

    Pré-requisito:
      1. Rodar POST /content/{slug}/build-site para gerar os arquivos
      2. Configurar no .env:
           NETLIFY_TOKEN = seu_personal_access_token
           NETLIFY_SITE_ID = id_do_site  (opcional se passado no body)

    Como obter as credenciais:
      - Token: app.netlify.com → User settings → Applications → Personal access tokens
      - Site ID: app.netlify.com → seu site → Site settings → General → Site details
    """
    _check_auth(x_councilia_key)

    netlify_token = os.environ.get("NETLIFY_TOKEN", "")
    if not netlify_token:
        raise HTTPException(
            status_code=400,
            detail="NETLIFY_TOKEN não configurado. Adicionar ao .env."
        )

    site_id = body.site_id or os.environ.get("NETLIFY_SITE_ID", "")
    if not site_id:
        raise HTTPException(
            status_code=400,
            detail="Netlify Site ID não fornecido. Passar no body ou configurar NETLIFY_SITE_ID no .env."
        )

    site_dir = Path(__file__).parent.parent.parent / "content_sites" / slug
    if not site_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Site não encontrado em content_sites/{slug}. Rodar build-site primeiro."
        )

    html_files = list(site_dir.glob("*.html")) + list(site_dir.glob("*.txt"))
    if not html_files:
        raise HTTPException(status_code=404, detail="Nenhum arquivo HTML encontrado no site.")

    # Cria zip em memória com todos os arquivos do site
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in html_files:
            zf.write(f, f.name)
    zip_buffer.seek(0)

    # Deploy via Netlify API
    try:
        import httpx
        headers = {
            "Authorization": f"Bearer {netlify_token}",
            "Content-Type": "application/zip",
        }
        response = httpx.post(
            f"https://api.netlify.com/api/v1/sites/{site_id}/deploys",
            content=zip_buffer.read(),
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()
        deploy_data = response.json()

        return {
            "status": "deployed",
            "slug": slug,
            "netlify_deploy_id": deploy_data.get("id"),
            "netlify_url": deploy_data.get("deploy_ssl_url") or deploy_data.get("url"),
            "deploy_state": deploy_data.get("state"),
            "files_deployed": len(html_files),
            "deployed_at": datetime.now(timezone.utc).isoformat(),
        }

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Netlify API retornou HTTP {e.response.status_code}: {e.response.text[:300]}"
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro no deploy: {e}")


@router.get("/deploy/{slug}/status")
async def get_deploy_status(
    slug: str,
    deploy_id: str,
    x_councilia_key: str = Header(default=""),
):
    """Consulta o status de um deploy específico no Netlify."""
    _check_auth(x_councilia_key)

    netlify_token = os.environ.get("NETLIFY_TOKEN", "")
    if not netlify_token:
        raise HTTPException(status_code=400, detail="NETLIFY_TOKEN não configurado.")

    try:
        import httpx
        r = httpx.get(
            f"https://api.netlify.com/api/v1/deploys/{deploy_id}",
            headers={"Authorization": f"Bearer {netlify_token}"},
            timeout=15,
        )
        r.raise_for_status()
        d = r.json()
        return {
            "deploy_id": deploy_id,
            "state": d.get("state"),
            "url": d.get("deploy_ssl_url") or d.get("url"),
            "error_message": d.get("error_message"),
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro consultando Netlify: {e}")


# ── PIPELINE STATUS ────────────────────────────────────────────────────────

@router.get("/pipeline/{slug}")
async def pipeline_status(
    slug: str,
    x_councilia_key: str = Header(default=""),
):
    """Status do pipeline pós-audit para um slug."""
    _check_auth(x_councilia_key)
    from services.post_audit_pipeline import get_pipeline_status
    return get_pipeline_status(slug)


@router.get("/credentials/check")
async def check_credentials(
    x_councilia_key: str = Header(default=""),
):
    """
    Verifica quais credenciais de publicação estão configuradas no .env.
    Não expõe os valores — só confirma se estão presentes.
    """
    _check_auth(x_councilia_key)

    def _present(key: str) -> bool:
        v = os.environ.get(key, "")
        return bool(v and v.strip())

    return {
        "audit_apis": {
            "SERPAPI_API_KEY":    _present("SERPAPI_API_KEY"),
            "OPENROUTER_API_KEY": _present("OPENROUTER_API_KEY"),
            "FIRECRAWL_API_KEY":  _present("FIRECRAWL_API_KEY"),
            "GNEWS_API_KEY":      _present("GNEWS_API_KEY"),
        },
        "publish_apis": {
            "MEDIUM_TOKEN":       _present("MEDIUM_TOKEN"),
            "LINKEDIN_TOKEN":     _present("LINKEDIN_TOKEN"),
            "WP_URL":             _present("WP_URL"),
            "EIN_API_KEY":        _present("EIN_API_KEY"),
            "GHOST_URL":          _present("GHOST_URL"),
            "GHOST_ADMIN_KEY":    _present("GHOST_ADMIN_KEY"),
        },
        "deploy_apis": {
            "NETLIFY_TOKEN":      _present("NETLIFY_TOKEN"),
            "NETLIFY_SITE_ID":    _present("NETLIFY_SITE_ID"),
        },
        "alert_apis": {
            "COUNCILIA_SMTP_USER": _present("COUNCILIA_SMTP_USER"),
            "COUNCILIA_SMTP_PASS": _present("COUNCILIA_SMTP_PASS"),
        },
        "auth": {
            "COUNCILIA_API_KEY":   _present("COUNCILIA_API_KEY"),
        },
        "ready_to_publish": _get_available_platforms(),
    }
