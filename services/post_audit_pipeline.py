"""
Post-Audit Pipeline — Encadeia automaticamente as ações após cada auditoria.

Lógica por threat level:
  LOW    → nenhuma geração automática
  MEDIUM → gera artigo_linkedin + comunicado_imprensa
  HIGH   → gera todos os 6 ativos de conteúdo
  CRITICAL → gera todos os 6 ativos + aciona response strategy automática

Tudo acontece em background thread para não bloquear a resposta HTTP ao operador.
Cada geração é idempotente — se o artigo já existe em cache, pula.
"""
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("councilia.pipeline")

# Ativos gerados por nível de ameaça
_ASSETS_BY_THREAT: dict[str, list[str]] = {
    "LOW":      [],
    "MEDIUM":   ["artigo_linkedin", "comunicado_imprensa"],
    "HIGH":     ["artigo_linkedin", "comunicado_imprensa", "biografia_executiva",
                 "faq_transparencia", "perfil_institucional", "esclarecimento_juridico",
                 "roteiro_youtube"],
    "CRITICAL": ["artigo_linkedin", "comunicado_imprensa", "biografia_executiva",
                 "faq_transparencia", "perfil_institucional", "esclarecimento_juridico",
                 "roteiro_youtube"],
}

# Mapa do tipo de ativo para a chave usada no content_producer
_ASSET_TYPE_MAP = {
    "artigo_linkedin":       "artigo_linkedin",
    "comunicado_imprensa":   "comunicado_imprensa",
    "biografia_executiva":   "biografia_executiva",
    "faq_transparencia":     "faq_transparencia",
    "perfil_institucional":  "perfil_institucional",
    "esclarecimento_juridico": "esclarecimento_juridico",
}


def run_post_audit_pipeline(
    entity_name: str,
    threat_level: str,
    slug: str,
    async_mode: bool = True,
) -> None:
    """
    Dispara o pipeline pós-audit.

    Se async_mode=True (padrão), roda em thread background — não bloqueia o request HTTP.
    Se async_mode=False, roda na thread atual (útil para testes e reauditoria automática).
    """
    assets = _ASSETS_BY_THREAT.get(threat_level, [])
    if not assets:
        logger.info(f"[{slug}] Threat {threat_level} — sem geração automática.")
        return

    logger.info(f"[{slug}] Pipeline pós-audit iniciado: {threat_level} → {len(assets)} ativos")

    if async_mode:
        t = threading.Thread(
            target=_run_pipeline,
            args=(entity_name, threat_level, slug, assets),
            daemon=True,
            name=f"pipeline-{slug}",
        )
        t.start()
    else:
        _run_pipeline(entity_name, threat_level, slug, assets)


def _run_pipeline(
    entity_name: str,
    threat_level: str,
    slug: str,
    assets: list[str],
) -> None:
    """Executa o pipeline na thread atual."""
    from services.content_producer import load_article, produce_article, save_article
    from services.snapshot_service import get_latest_snapshot
    from services.serp_dominance import compute_serp_score, compute_domain_clusters
    from services.battle_planner import build_battle_plan
    from services.archetype import classify_archetype

    snap = get_latest_snapshot(slug)
    if not snap:
        logger.error(f"[{slug}] Snapshot não encontrado para pipeline.")
        return

    # Carrega battle plan com os argumentos corretos extraídos do snapshot
    battle_plan = None
    try:
        serp = snap.get("serp", [])
        clusters = compute_domain_clusters(serp)
        score_data = compute_serp_score(serp)
        threat = snap.get("threat_level", threat_level)
        archetype = snap.get("threat_archetype", classify_archetype(snap))
        battle_plan = build_battle_plan(serp, clusters, score_data, threat, archetype)
    except Exception as e:
        logger.warning(f"[{slug}] Não foi possível carregar battle plan: {e}")
        battle_plan = None

    generated = []
    skipped = []
    failed = []

    for asset_type in assets:
        # Idempotência — pula se já existe em cache
        existing = load_article(entity_name, asset_type)
        if existing and existing.get("generated_at"):
            skipped.append(asset_type)
            continue

        try:
            logger.info(f"[{slug}] Gerando {asset_type}...")
            result = produce_article(
                asset_type=asset_type,
                entity_name=entity_name,
                battle_plan=battle_plan,
            )
            if result and result.get("article"):
                # CRÍTICO: salvar em cache para que o Content Studio e o Distribution Engine
                # possam encontrar o artigo gerado
                save_article(entity_name, asset_type, result)
                generated.append(asset_type)
                logger.info(f"[{slug}] {asset_type} gerado e salvo em cache.")
            else:
                failed.append(asset_type)
                logger.warning(f"[{slug}] {asset_type} gerou resultado vazio.")
        except Exception as e:
            failed.append(asset_type)
            logger.error(f"[{slug}] Erro gerando {asset_type}: {e}")

    logger.info(
        f"[{slug}] Pipeline concluído — "
        f"gerados: {generated}, pulados: {skipped}, falhos: {failed}"
    )

    # Para CRITICAL — gera response strategy automaticamente
    if threat_level == "CRITICAL":
        _auto_generate_response(entity_name, slug, snap)

    # Salva log do pipeline no snapshot directory
    _save_pipeline_log(slug, {
        "entity": entity_name,
        "threat_level": threat_level,
        "generated": generated,
        "skipped": skipped,
        "failed": failed,
        "run_at": datetime.now(timezone.utc).isoformat(),
    })


def _auto_generate_response(entity_name: str, slug: str, snap: dict) -> None:
    """Gera response strategy automaticamente para CRITICAL."""
    try:
        from services.response_service import generate_response
        archetype = snap.get("threat_archetype", "corporate")
        crisis_state = snap.get("crisis_state", "active_crisis")

        logger.info(f"[{slug}] Gerando response strategy automática (CRITICAL, {archetype})...")
        result = generate_response(
            entity=entity_name,
            threat_level="CRITICAL",
            narrative_state=crisis_state,
            archetype=archetype,
            dominant_themes=[],
            serp_context=snap,
        )
        if result:
            # Salva em cache dedicado
            cache_path = (
                Path(__file__).parent.parent / "articles_cache" / slug / "auto_response.json"
            )
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            import json
            cache_path.write_text(
                json.dumps({
                    "entity": entity_name,
                    "archetype": archetype,
                    "response": result,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                }, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.info(f"[{slug}] Response strategy automática salva.")
    except Exception as e:
        logger.error(f"[{slug}] Erro na response strategy automática: {e}")


def _save_pipeline_log(slug: str, log_entry: dict) -> None:
    """Salva log de execução do pipeline."""
    import json, os, tempfile
    log_path = (
        Path(__file__).parent.parent / "articles_cache" / slug / "pipeline_log.json"
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        existing = []
        if log_path.exists():
            try:
                existing = json.loads(log_path.read_text(encoding="utf-8"))
            except Exception:
                existing = []
        existing.append(log_entry)
        # Mantém só os últimos 30 logs
        existing = existing[-30:]

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
    except Exception as e:
        logger.warning(f"Não foi possível salvar pipeline log: {e}")


def get_pipeline_status(slug: str) -> dict:
    """Retorna o último log de pipeline para um slug."""
    import json
    log_path = (
        Path(__file__).parent.parent / "articles_cache" / slug / "pipeline_log.json"
    )
    if not log_path.exists():
        return {"status": "never_run", "slug": slug}
    try:
        logs = json.loads(log_path.read_text(encoding="utf-8"))
        return {"status": "ok", "slug": slug, "last_run": logs[-1] if logs else None, "total_runs": len(logs)}
    except Exception:
        return {"status": "error_reading_log", "slug": slug}
