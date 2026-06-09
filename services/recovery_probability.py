"""
Recovery Probability Engine — Deterministic probability of SERP recovery.

Formula integrates 9 factors:
  - tier1 dominance: authority-weighted negative presence
  - saturation: per-domain saturation score
  - legal permanence: JusBrasil/STF/CGU type domains (non-displaceable)
  - Wikipedia contamination: negative wikipedia presence
  - video toxicity: YouTube negative video score
  - controlled assets: entity-owned results
  - momentum: narrative acceleration/deceleration
  - indexed persistence: domain authority of negative results
  - domain authority: average authority of negative domains
"""
from services.constants import domain_authority


# Weight multipliers for each factor (sum = 1.0)
WEIGHTS = {
    "tier1_dominance":      0.18,
    "saturation":           0.15,
    "legal_permanence":     0.14,
    "wikipedia_contamination": 0.12,
    "video_toxicity":       0.12,
    "controlled_assets":    0.10,
    "momentum":             0.08,
    "indexed_persistence":  0.06,
    "domain_authority":     0.05,
}


LEVELS = ["VERY_HIGH", "HIGH", "MEDIUM", "LOW", "VERY_LOW"]


def compute_recovery_probability(
    serp: list[dict],
    serp_score: float,
    npa: dict,
    youtube_toxicity: float = 0,
) -> dict:
    """Compute full recovery probability with 9-factor decomposition.

    Returns:
      - probability_pct: 0-98
      - level: VERY_HIGH / HIGH / MEDIUM / LOW / VERY_LOW
      - level_label: Portuguese string
      - factors: list of each contributing factor with score
      - estimated_time: displacement time estimate
      - confidence: confidence band
      - estimated_budget: budget range
      - difficulty: overall recovery difficulty
    """
    total = len(serp) or 1
    neg_results = [r for r in serp if r.get("sentiment") == "negative"]
    neg_count = len(neg_results)
    neg_ratio = neg_count / total
    controlled = sum(1 for r in serp if r.get("controlled"))
    npa_momentum = npa.get("momentum", "Stable")

    # 1. Tier-1 dominance (0-1, higher = worse)
    neg_authorities = [domain_authority(r.get("domain", "")) for r in neg_results]
    avg_neg_auth = sum(neg_authorities) / max(len(neg_authorities), 1)
    tier1 = min(avg_neg_auth / 10, 1.0)

    # 2. Saturation (0-1)
    saturation = min(neg_count / max(total, 3), 1.0)

    # 3. Legal permanence (0-1)
    legal_results = [r for r in serp if r.get("type") == "legal" and r.get("sentiment") == "negative"]
    legal_perm = min(len(legal_results) / 3, 1.0)

    # 4. Wikipedia contamination (0-1)
    wiki_neg = [r for r in neg_results if "wikipedia.org" in (r.get("domain", "") or "")]
    wiki_contam = 1.0 if wiki_neg else 0.0

    # 5. Video toxicity (0-1), normalized from youtube_toxicity
    video_tox = min(youtube_toxicity / 100, 1.0)

    # 6. Controlled assets (0-1, higher = better → invert)
    ctrl_bonus = min(controlled / 5, 1.0)
    controlled_factor = 1.0 - ctrl_bonus  # invert: more control = lower penalty

    # 7. Momentum penalty
    mom_map = {"Escalating": 0.8, "Declining": 0.3, "Stable": 0.5}
    mom_pen = mom_map.get(npa_momentum, 0.5)

    # 8. Indexed persistence — how many high-authority negative results
    high_auth_neg = sum(1 for r in neg_results if domain_authority(r.get("domain", "")) >= 7)
    persistence = min(high_auth_neg / 5, 1.0)

    # 9. Domain authority (average of top-3 negative)
    top3_neg = sorted(neg_results, key=lambda r: r.get("position", 99))[:3]
    top3_auths = [domain_authority(r.get("domain", "")) for r in top3_neg]
    avg_top3_auth = sum(top3_auths) / max(len(top3_auths), 1)
    da_factor = min(avg_top3_auth / 10, 1.0)

    # Composite penalty (weighted sum)
    raw_penalty = (
        tier1 * WEIGHTS["tier1_dominance"] +
        saturation * WEIGHTS["saturation"] +
        legal_perm * WEIGHTS["legal_permanence"] +
        wiki_contam * WEIGHTS["wikipedia_contamination"] +
        video_tox * WEIGHTS["video_toxicity"] +
        controlled_factor * WEIGHTS["controlled_assets"] +
        mom_pen * WEIGHTS["momentum"] +
        persistence * WEIGHTS["indexed_persistence"] +
        da_factor * WEIGHTS["domain_authority"]
    )

    # Base probability: 0.98 max, 0.05 min
    probability = max(0.05, min(0.98, 0.90 - raw_penalty))

    # Boost by controlled assets (up to +0.08)
    probability = min(0.98, probability + ctrl_bonus * 0.08)

    probability_pct = round(probability * 100)

    # Level
    level = _classify_level(probability_pct)

    # Estimated time
    estimated_time = _estimate_time(probability_pct, legal_perm, wiki_contam)

    # Confidence — sem banda numérica: não temos dados históricos para calibrar.
    # Exibir só nível qualitativo para não criar falsa precisão ao cliente.
    if probability_pct >= 65:
        confidence = "ALTA"
    elif probability_pct >= 40:
        confidence = "MÉDIA"
    else:
        confidence = "BAIXA"
    band = None  # removido: ±pp era inventado, sem base em backtesting real

    # Estimated budget
    estimated_budget = _estimate_budget(probability_pct, legal_perm > 0, tier1 > 0.7)

    # Difficulty
    difficulty = _estimate_difficulty(level, legal_perm, wiki_contam)

    # Factor breakdown
    factors = [
        {"factor": "Tier-1 dominance", "weight": f"{WEIGHTS['tier1_dominance']:.0%}",
         "value": f"{tier1:.0%}", "impact": "positivo" if tier1 < 0.3 else "negativo"},
        {"factor": "Narrative saturation", "weight": f"{WEIGHTS['saturation']:.0%}",
         "value": f"{saturation:.0%}", "impact": "positivo" if saturation < 0.3 else "negativo"},
        {"factor": "Legal permanence (JusBrasil/STF)", "weight": f"{WEIGHTS['legal_permanence']:.0%}",
         "value": f"{legal_perm:.0%}", "impact": "positivo" if legal_perm < 0.3 else "negativo"},
        {"factor": "Wikipedia contamination", "weight": f"{WEIGHTS['wikipedia_contamination']:.0%}",
         "value": "Sim" if wiki_contam else "Não", "impact": "negativo" if wiki_contam else "positivo"},
        {"factor": "Video toxicity (YouTube)", "weight": f"{WEIGHTS['video_toxicity']:.0%}",
         "value": f"{video_tox:.0%}", "impact": "positivo" if video_tox < 0.3 else "negativo"},
        {"factor": "Controlled assets", "weight": f"{WEIGHTS['controlled_assets']:.0%}",
         "value": f"{controlled}/5", "impact": "positivo" if ctrl_bonus > 0.5 else "negativo"},
        {"factor": "Narrative momentum", "weight": f"{WEIGHTS['momentum']:.0%}",
         "value": npa_momentum, "impact": "positivo" if npa_momentum == "Declining" else "negativo"},
        {"factor": "Indexed persistence", "weight": f"{WEIGHTS['indexed_persistence']:.0%}",
         "value": f"{persistence:.0%}", "impact": "positivo" if persistence < 0.3 else "negativo"},
        {"factor": "Domain authority of negatives", "weight": f"{WEIGHTS['domain_authority']:.0%}",
         "value": f"{avg_top3_auth:.1f}", "impact": "positivo" if avg_top3_auth < 5 else "negativo"},
    ]

    return {
        "probability_pct": probability_pct,
        "level": level,
        "level_label": _level_label(level),
        "confidence": confidence,
        "band": None,  # removido: sem dados para calibrar intervalo
        "label": f"{probability_pct}% (confiança {confidence}) — estimativa indicativa, não calibrada",
        "estimated_time": estimated_time,
        "estimated_budget": estimated_budget,
        "difficulty": difficulty,
        "factors": factors,
        "raw_penalty": round(raw_penalty, 4),
        "positive_factors": sum(1 for f in factors if f["impact"] == "positivo"),
        "negative_factors": sum(1 for f in factors if f["impact"] == "negativo"),
    }


def _classify_level(pct: int) -> str:
    if pct >= 75:
        return "VERY_HIGH"
    if pct >= 55:
        return "HIGH"
    if pct >= 35:
        return "MEDIUM"
    if pct >= 15:
        return "LOW"
    return "VERY_LOW"


def _level_label(level: str) -> str:
    labels = {
        "VERY_HIGH": "Recuperação Provável — Estratégia viável em 60-90 dias",
        "HIGH": "Recuperação Viável — Esforço moderado, 90-180 dias",
        "MEDIUM": "Recuperação Possível — Requer investimento sustentado, 180-365 dias",
        "LOW": "Recuperação Difícil — Alta probabilidade de permanência negativa",
        "VERY_LOW": "Recuperação Improvável — Dano estrutural permanente ou semi-permanente",
    }
    return labels.get(level, "Indeterminado")


def _estimate_time(pct: int, legal_perm: float, wiki_contam: float) -> str:
    if pct >= 75:
        return "60-90 dias"
    if pct >= 55:
        return "90-180 dias"
    if pct >= 35:
        return "180-365 dias"
    if legal_perm > 0.5:
        return "365+ dias (permanência jurídica limita recuperação)"
    if wiki_contam:
        return "365+ dias (contaminação na Wikipédia requer processo editorial)"
    return "Improvável em menos de 365 dias"


def _estimate_budget(pct: int, has_legal: bool, high_tier1: bool) -> str:
    base = "R$ 5.000-15.000/mês" if pct >= 55 else "R$ 15.000-40.000/mês"
    if has_legal:
        return f"{base} + custo jurídico adicional"
    if high_tier1:
        return f"{base} + investimento em relações públicas"
    return base


def _estimate_difficulty(level: str, legal_perm: float, wiki_contam: float) -> str:
    if legal_perm > 0.5:
        return "MUITO DIFÍCIL — Permanência jurídica impede deslocamento completo"
    if wiki_contam:
        return "DIFÍCIL — Wikipedia requer processo editorial longo"
    difficulties = {
        "VERY_HIGH": "BAIXA",
        "HIGH": "BAIXA-MODERADA",
        "MEDIUM": "MODERADA",
        "LOW": "ALTA",
        "VERY_LOW": "MUITO ALTA",
    }
    return difficulties.get(level, "MODERADA")
