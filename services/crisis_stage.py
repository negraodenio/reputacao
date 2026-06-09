"""
Crisis Stage Engine — Detects the exact phase of a reputation crisis.

Stages:
  - BREAKING: first 0-60 minutes, new negative article detected
  - ESCALATING: multiple vehicles replicating, momentum increasing
  - SATURATED: SERP fully contaminated, structural damage
  - DECAYING: search volume dropping, negative results consolidating
  - ARCHIVED: no new activity, residual indexed negativity

Each stage changes: ads, assets, visibility, tone, timing, stakeholder priority.

AVISO OPERACIONAL: classify_crisis_stage() é stateless — não rastreia
transições entre estágios. Se o snapshot estiver desatualizado (>48h),
o stage pode refletir a situação de dias atrás, não a atual.
Sempre verificar snapshot_age antes de confiar no stage para decisões críticas.
"""
from datetime import datetime, timezone
from services.metrics import snapshot_is_stale


STAGES = {
    "BREAKING": {
        "label": "BREAKING — Crise em Erupção",
        "severity": 5,
        "response_window": "0-60 minutos",
        "ads_mode": "DEFENSIVO MÁXIMO",
        "tone": "Contido, factual, sem posicionamento público",
        "visibility": "BAIXÍSSIMA — Apenas jurídico e stakeholders diretos",
        "primary_asset": "esclarecimento_juridico",
        "cadence": "A cada 15 minutos: reavaliar",
        "stakeholder_priority": "Jurídico + Sócios",
        "description": "Acabou de sair. A matéria ainda não está indexada no Google. "
                       "Janela de ouro para preparar resposta antes da indexação em 15-60 min.",
    },
    "ESCALATING": {
        "label": "ESCALADA — Contaminação em Aceleração",
        "severity": 4,
        "response_window": "1-12 horas",
        "ads_mode": "CONTAINMENT + BRAND DEFENSE",
        "tone": "Reativo, com posicionamento claro",
        "visibility": "MODERADA — Comunicado oficial + stakeholders",
        "primary_asset": "comunicado_imprensa",
        "cadence": "A cada 1-2 horas: monitorar novos veículos",
        "stakeholder_priority": "Clientes-chave + Imprensa + Jurídico",
        "description": "Múltiplos veículos replicando. SERP começando a ser "
                       "contaminada. Top Stories ativado para buscas de marca.",
    },
    "SATURATED": {
        "label": "SATURAÇÃO — SERP Contaminada",
        "severity": 3,
        "response_window": "12-48 horas",
        "ads_mode": "SEO AMPLIFICATION + OCCUPATION",
        "tone": "Ofensivo-estratégico, ocupação de posições",
        "visibility": "ALTA — Produção intensiva de conteúdo ocupacional",
        "primary_asset": "perfil_institucional",
        "cadence": "Diário: publicar conteúdo ocupacional + monitorar",
        "stakeholder_priority": "Todos os stakeholders + Mercado",
        "description": "SERP já está contaminada em múltiplas posições. "
                       "Não adianta mais só defender — precisa ocupar.",
    },
    "DECAYING": {
        "label": "DECAIMENTO — Pressão Reduzindo",
        "severity": 2,
        "response_window": "48h+",
        "ads_mode": "MAINTENANCE + REMARKETING",
        "tone": "Construtivo, de reconstrução de autoridade",
        "visibility": "MODERADA — Conteúdo de autoridade contínuo",
        "primary_asset": "biografia_executiva",
        "cadence": "Semanal: publicação + SEO + relações públicas",
        "stakeholder_priority": "Parceiros estratégicos + Mercado",
        "description": "Pico de buscas passou. Notícias novas pararam de sair. "
                       "Momento de consolidar ocupação e reconstruir autoridade.",
    },
    "ARCHIVED": {
        "label": "ARQUIVADO — Residual Indexado",
        "severity": 1,
        "response_window": "Mensal",
        "ads_mode": "VIGILÂNCIA",
        "tone": "Institucional, de manutenção",
        "visibility": "BAIXA — Conteúdo de manutenção cadencial",
        "primary_asset": "faq_transparencia",
        "cadence": "Mensal: auditoria + manutenção de assets",
        "stakeholder_priority": "Monitoramento passivo",
        "description": "Crise passou. Resultados negativos residuais ainda indexados "
                       "mas sem novo volume. Manter vigilância para evitar reativação.",
    },
}


def classify_crisis_stage(npa: dict, serp: list[dict], threat_level: str) -> str:
    """Classify the exact crisis stage based on NPA + SERP + threat.

    Deterministic rules (first match wins):

    1. BREAKING: count_7d >= 1 AND momentum == "Escalating"
       AND no previous snapshot (new crisis)
    2. ESCALATING: momentum == "Escalating" AND count_7d >= 3
       AND neg_ratio >= 0.3
    3. SATURATED: momentum == "Escalating" AND count_7d >= 5
       AND neg_ratio >= 0.5
    4. SATURATED: neg_ratio >= 0.5 AND controlled_assets <= 2
    5. DECAYING: momentum == "Declining" AND neg_ratio >= 0.3
    6. ARCHIVED: momentum == "Declining" AND count_7d == 0
       AND neg_ratio < 0.3
    7. ARCHIVED: count_7d == 0 AND count_30d > 0 AND neg_ratio < 0.3
    8. Default: STABLE (not a crisis stage per se, but vigilance)
    """
    count_7d = npa.get("count_7d", 0)
    count_30d = npa.get("count_30d", 0)
    momentum = npa.get("momentum", "Stable")

    total = len(serp) or 1
    neg_count = sum(1 for r in serp if r.get("sentiment") == "negative")
    neg_ratio = neg_count / total
    controlled = sum(1 for r in serp if r.get("controlled"))

    # 1. BREAKING
    if count_7d >= 1 and momentum == "Escalating" and threat_level.upper() in ("CRITICAL", "HIGH"):
        return "BREAKING"

    # 2. ESCALATING
    if count_7d >= 3 and momentum == "Escalating" and neg_ratio >= 0.3:
        return "ESCALATING"

    # 3. SATURATED (by volume)
    if count_7d >= 5 and momentum == "Escalating" and neg_ratio >= 0.5:
        return "SATURATED"

    # 4. SATURATED (by ratio)
    if neg_ratio >= 0.5 and controlled <= 2:
        return "SATURATED"

    # 5. DECAYING — momentum dropping but still contaminated
    if momentum == "Declining" and neg_ratio >= 0.3:
        return "DECAYING"

    # 6. ARCHIVED — crisis passed, residual
    if momentum == "Declining" and count_7d == 0 and neg_ratio < 0.3:
        return "ARCHIVED"

    # 7. ARCHIVED — no new articles
    if count_7d == 0 and count_30d > 0 and neg_ratio < 0.3:
        return "ARCHIVED"

    # Default: stable / vigilance
    return "STABLE"


def get_stage_config(stage_key: str) -> dict:
    """Get full stage config with all strategy parameters."""
    return STAGES.get(stage_key, {
        "label": "ESTÁVEL — Vigilância",
        "severity": 0,
        "response_window": "N/A",
        "ads_mode": "VIGILÂNCIA",
        "tone": "Institucional",
        "visibility": "BAIXA",
        "primary_asset": "nenhum",
        "cadence": "Auditoria mensal",
        "stakeholder_priority": "Nenhum",
        "description": "Nenhuma crise ativa. Monitoramento de rotina.",
    })


def narrative_velocity(stage_key: str, count_7d: int, count_30d: int) -> str:
    """Narrative Velocity — how fast the narrative is moving.

    Based on stage + article velocity ratio.
    """
    ratio_7d_30d = count_7d / max(count_30d, 1)

    if stage_key in ("BREAKING", "ESCALATING"):
        return f"ACELERAÇÃO CRÍTICA — {count_7d} artigos nos últimos 7 dias"
    if stage_key == "SATURATED":
        return f"VELOCIDADE MÁXIMA — {count_7d} artigos/7d, saturação de {ratio_7d_30d:.0%}"
    if stage_key == "DECAYING":
        return f"DESACELERAÇÃO — {count_7d} artigos/7d, tendência de queda"
    if stage_key == "ARCHIVED":
        return f"VELOCIDADE ZERO — Nenhum artigo novo, narrativa estabilizada"
    return f"ESTÁVEL — {count_7d} artigos/7d, velocidade normal"


def stage_drives_response(stage_key: str, snapshot: dict | None = None) -> dict:
    """What the crisis stage changes in the response strategy.

    Returns adjusted recommendations for: ads, assets, visibility, tone, timing.
    Inclui aviso de dados desatualizados se snapshot fornecido tiver > 48h.
    """
    config = get_stage_config(stage_key)

    stale_warning = None
    if snapshot is not None and snapshot_is_stale(snapshot, max_hours=48):
        stale_warning = (
            "ATENÇÃO: snapshot com mais de 48 horas. O crisis stage pode não "
            "refletir o estado atual da SERP. Reauditar antes de tomar decisões "
            "operacionais baseadas neste estágio."
        )

    return {
        "stage": stage_key,
        "stage_label": config["label"],
        "severity": config["severity"],
        "response_window": config["response_window"],
        "ads_mode": config["ads_mode"],
        "tone": config["tone"],
        "visibility": config["visibility"],
        "primary_asset": config["primary_asset"],
        "cadence": config["cadence"],
        "stakeholder_priority": config["stakeholder_priority"],
        "description": config["description"],
        "stale_warning": stale_warning,
        "ai_context_injection": f"CRISIS STAGE: {stage_key}. "
                                f"Response window: {config['response_window']}. "
                                f"Suggested tone: {config['tone']}. "
                                f"Primary asset: {config['primary_asset']}.",
    }
