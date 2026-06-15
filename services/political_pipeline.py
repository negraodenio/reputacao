"""
Political Pipeline — Pipeline Automatizado para Políticos.

Ciclo completo: auditar → gerar conteúdo → publicar em portais regionais.

Lógica por ciclo:
  1. Auditoria SERP + AI Overview (quem está ocupando o Google)
  2. Diagnóstico de ameaça e gaps
  3. Geração de conteúdo político (por tipo de ameaça)
  4. Publicação em portais regionais selecionados automaticamente
  5. Registro de resultados e próxima ação

Frequência sugerida:
  - LOW threat:       1x/semana
  - MEDIUM threat:    2x/semana
  - HIGH threat:      diário
  - CRITICAL threat:  a cada 4h

Chamado automaticamente pelo cron do monitoring_engine
ou acionado manualmente via POST /political/pipeline.
"""
from __future__ import annotations
import json
import logging
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("councilia.political_pipeline")

# ── Storage ────────────────────────────────────────────────────────────────────
if os.environ.get("VERCEL"):
    PIPELINE_DIR = Path("/tmp/political_pipeline")
else:
    PIPELINE_DIR = Path(__file__).parent.parent / "political_pipeline"

PIPELINE_DIR.mkdir(parents=True, exist_ok=True)

# Conteúdo gerado por nível de ameaça
_CONTENT_BY_THREAT: dict[str, list[str]] = {
    "LOW":      ["mandato_realizacoes"],
    "MEDIUM":   ["mandato_realizacoes", "perfil_eleitoral"],
    "HIGH":     ["mandato_realizacoes", "perfil_eleitoral", "posicionamento_legislativo",
                 "agenda_publica"],
    "CRITICAL": ["mandato_realizacoes", "perfil_eleitoral", "posicionamento_legislativo",
                 "agenda_publica", "contraposicao_narrativa", "release_conquista"],
}


def run_political_pipeline(
    politician_slug: str,
    async_mode:      bool = True,
    force_content:   list[str] | None = None,
) -> dict:
    """
    Executa o pipeline político completo para um político.

    Se async_mode=True, roda em thread background.
    Retorna imediatamente com status de início.

    Args:
        politician_slug: Slug do político cadastrado
        async_mode:      Se True, não bloqueia a request HTTP
        force_content:   Lista de tipos de conteúdo a gerar (sobrescreve automático)
    """
    from services.political_engine import get_politician

    entity = get_politician(politician_slug)
    if not entity:
        return {"error": f"Político '{politician_slug}' não cadastrado."}

    if async_mode:
        t = threading.Thread(
            target=_run_full_pipeline,
            args=(entity, force_content),
            daemon=True,
            name=f"political-{politician_slug}",
        )
        t.start()
        return {
            "status":  "started",
            "message": f"Pipeline político iniciado em background para {entity.name}",
            "slug":    politician_slug,
        }
    else:
        return _run_full_pipeline(entity, force_content)


def _run_full_pipeline(entity, force_content: list[str] | None) -> dict:
    """Executa o pipeline na thread atual."""
    from services.political_engine import (
        political_queries, electoral_calendar, get_electoral_window
    )
    from services.audit_service import run_audit
    from services.political_content_producer import (
        produce_political_content, save_political_content
    )
    from services.regional_portals import select_regional_portals

    slug = entity.slug
    log_entry = {
        "slug":        slug,
        "entity_name": entity.name,
        "started_at":  datetime.now(timezone.utc).isoformat(),
        "steps":       [],
        "errors":      [],
    }

    logger.info(f"[{slug}] Pipeline político iniciado para {entity.name}")

    # ── PASSO 1: Calendário e janela eleitoral ────────────────────────────────
    from datetime import date
    current_window = get_electoral_window(date.today())
    window_key = current_window["window"]
    log_entry["electoral_window"] = window_key
    log_entry["election_countdown"] = current_window.get("election_countdown")
    logger.info(f"[{slug}] Janela eleitoral: {current_window['label']}")

    if window_key == "silence":
        log_entry["status"] = "blocked_silence"
        log_entry["message"] = "Pipeline bloqueado — Silêncio Eleitoral ativo"
        _save_pipeline_log(slug, log_entry)
        return log_entry

    # ── PASSO 2: Auditoria SERP ────────────────────────────────────────────────
    audit_result = {}
    threat_level = "MEDIUM"
    try:
        logger.info(f"[{slug}] Auditando SERP...")
        # Usa o nome principal do político
        audit_result = run_audit(
            entity_name=entity.name,
            country="Brazil",
            industry="political",
        )
        log_entry["steps"].append({"step": "audit", "status": "ok"})

        # Inferir threat level do snapshot
        from services.snapshot_service import get_latest_snapshot, infer_threat_from_snapshot
        import re
        snap_slug = re.sub(r"\s+", "_", entity.name.lower().strip())
        snap_slug = re.sub(r"[^\w]", "", snap_slug)
        snap = get_latest_snapshot(snap_slug)
        if snap:
            threat_level = snap.get("threat_level") or infer_threat_from_snapshot(snap)
        log_entry["threat_level"] = threat_level
        logger.info(f"[{slug}] Threat level: {threat_level}")

    except Exception as e:
        log_entry["errors"].append({"step": "audit", "error": str(e)})
        log_entry["steps"].append({"step": "audit", "status": "error", "error": str(e)})
        logger.error(f"[{slug}] Erro na auditoria: {e}")

    # ── PASSO 3: Análise de AI Overview ───────────────────────────────────────
    aio_report = audit_result.get("ai_overview", {})
    if aio_report.get("has_overview"):
        logger.info(f"[{slug}] AI Overview detectado — AIO Risk: {aio_report.get('risk_label')}")
        log_entry["aio_risk"] = aio_report.get("risk_label")
        # Se ALTO RISCO no AI Overview, escalar threat
        if aio_report.get("risk_score", 0) >= 60 and threat_level == "LOW":
            threat_level = "MEDIUM"

    # ── PASSO 4: Selecionar tipos de conteúdo ─────────────────────────────────
    content_types = force_content or _CONTENT_BY_THREAT.get(threat_level, ["mandato_realizacoes"])
    logger.info(f"[{slug}] Gerando {len(content_types)} tipo(s) de conteúdo: {content_types}")

    # ── PASSO 5: Gerar conteúdo político ─────────────────────────────────────
    generated_content = []
    context = {
        "role":   entity.role,
        "party":  entity.party,
        "state":  entity.state,
        "city":   entity.city,
        "details": audit_result.get("text", "")[:500] if audit_result.get("text") else "",
    }

    for content_type in content_types:
        try:
            logger.info(f"[{slug}] Gerando {content_type}...")
            content = produce_political_content(
                entity_name=entity.name,
                content_type=content_type,
                context=context,
                electoral_window=window_key,
            )

            if content.get("error"):
                log_entry["errors"].append({"step": content_type, "error": content["error"]})
                continue

            # Salvar em disco
            saved_path = save_political_content(slug, content_type, content)
            content["saved_path"] = str(saved_path)
            generated_content.append(content)
            log_entry["steps"].append({"step": f"generate_{content_type}", "status": "ok"})
            logger.info(f"[{slug}] {content_type} gerado ({content.get('word_count', 0)} palavras)")

        except Exception as e:
            log_entry["errors"].append({"step": content_type, "error": str(e)})
            log_entry["steps"].append({"step": f"generate_{content_type}", "status": "error"})
            logger.error(f"[{slug}] Erro gerando {content_type}: {e}")

    log_entry["generated_count"] = len(generated_content)

    # ── PASSO 6: Seleção de portais regionais ────────────────────────────────
    portals = []
    try:
        portals = select_regional_portals(
            state=entity.state,
            city=entity.city,
            archetype="political",
            max_count=5,
        )
        log_entry["portals_selected"] = [p["name"] for p in portals]
        logger.info(f"[{slug}] Portais selecionados: {[p['name'] for p in portals]}")
        log_entry["steps"].append({"step": "portal_selection", "status": "ok",
                                   "count": len(portals)})
    except Exception as e:
        log_entry["errors"].append({"step": "portal_selection", "error": str(e)})

    # ── PASSO 7: Preparar payloads de distribuição ─────────────────────────────
    distribution_queue = []
    for content in generated_content:
        for portal in portals:
            distribution_queue.append({
                "entity_name":  entity.name,
                "content_type": content.get("content_type"),
                "title":        content.get("title"),
                "lead":         content.get("lead"),
                "body":         content.get("body"),
                "portal_name":  portal.get("name"),
                "portal_url":   portal.get("url"),
                "portal_method": portal.get("method"),
                "portal_instructions": portal.get("instructions"),
                "speed":        portal.get("speed"),
                "queued_at":    datetime.now(timezone.utc).isoformat(),
                "status":       "queued",
            })

    # Salvar fila de distribuição
    _save_distribution_queue(slug, distribution_queue)
    log_entry["distribution_queued"] = len(distribution_queue)
    log_entry["steps"].append({
        "step": "distribution_queue",
        "status": "ok",
        "count": len(distribution_queue),
    })

    # ── PASSO 8: Análise de oponente (só se cadastrado e HIGH+) ──────────────
    if entity.opponent and threat_level in ("HIGH", "CRITICAL"):
        try:
            logger.info(f"[{slug}] Analisando oponente: {entity.opponent}")
            from services.opponent_service import analyze_opponent
            opp_report = analyze_opponent(entity.name, entity.opponent)
            _save_opponent_report(slug, opp_report)
            log_entry["opponent_score"] = opp_report.get("comparison", {}).get("opponent_score")
            log_entry["politician_score"] = opp_report.get("comparison", {}).get("politician_score")
            log_entry["steps"].append({"step": "opponent_analysis", "status": "ok"})
        except Exception as e:
            log_entry["errors"].append({"step": "opponent_analysis", "error": str(e)})

    # ── Finalizar ─────────────────────────────────────────────────────────────
    log_entry["completed_at"] = datetime.now(timezone.utc).isoformat()
    log_entry["status"] = "completed" if not log_entry["errors"] else "completed_with_errors"

    _save_pipeline_log(slug, log_entry)

    logger.info(
        f"[{slug}] Pipeline concluído — "
        f"gerados: {len(generated_content)}, "
        f"na fila: {len(distribution_queue)}, "
        f"erros: {len(log_entry['errors'])}"
    )

    return log_entry


# ── Storage helpers ────────────────────────────────────────────────────────────

def _save_pipeline_log(slug: str, log_entry: dict) -> None:
    log_path = PIPELINE_DIR / slug / "pipeline_log.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    existing = []
    if log_path.exists():
        try:
            existing = json.loads(log_path.read_text(encoding="utf-8"))
        except Exception:
            existing = []
    existing.append(log_entry)
    existing = existing[-50:]  # mantém últimos 50 ciclos

    text = json.dumps(existing, indent=2, ensure_ascii=False)
    fd, tmp = tempfile.mkstemp(dir=log_path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, log_path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _save_distribution_queue(slug: str, queue: list) -> None:
    q_path = PIPELINE_DIR / slug / "distribution_queue.json"
    q_path.parent.mkdir(parents=True, exist_ok=True)

    text = json.dumps(queue, indent=2, ensure_ascii=False)
    fd, tmp = tempfile.mkstemp(dir=q_path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, q_path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _save_opponent_report(slug: str, report: dict) -> None:
    r_path = PIPELINE_DIR / slug / "opponent_report.json"
    r_path.parent.mkdir(parents=True, exist_ok=True)
    r_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def get_pipeline_status(slug: str) -> dict:
    """Retorna status do último ciclo de pipeline para um político."""
    log_path = PIPELINE_DIR / slug / "pipeline_log.json"
    if not log_path.exists():
        return {"status": "never_run", "slug": slug}
    try:
        logs = json.loads(log_path.read_text(encoding="utf-8"))
        return {
            "status":      "ok",
            "slug":        slug,
            "last_run":    logs[-1] if logs else None,
            "total_runs":  len(logs),
            "recent_logs": logs[-5:],
        }
    except Exception as e:
        return {"status": "error", "slug": slug, "error": str(e)}


def get_distribution_queue(slug: str) -> list:
    """Retorna fila de distribuição de um político."""
    q_path = PIPELINE_DIR / slug / "distribution_queue.json"
    if not q_path.exists():
        return []
    try:
        return json.loads(q_path.read_text(encoding="utf-8"))
    except Exception:
        return []


def mark_distributed(slug: str, portal_name: str, content_type: str, url: str = "") -> bool:
    """Marca um item da fila como distribuído."""
    q_path = PIPELINE_DIR / slug / "distribution_queue.json"
    if not q_path.exists():
        return False
    try:
        queue = json.loads(q_path.read_text(encoding="utf-8"))
        for item in queue:
            if item.get("portal_name") == portal_name and item.get("content_type") == content_type:
                item["status"] = "distributed"
                item["distributed_at"] = datetime.now(timezone.utc).isoformat()
                item["published_url"] = url
                break
        q_path.write_text(json.dumps(queue, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except Exception:
        return False
