"""
SERP Semantic Occupation Engine — Clusterização, Weighted Dominance,
Share Analysis e SERP Occupation Score.

YouTube video weight:
  Vídeos do YouTube recebem peso maior no SERP score porque:
  - Thumbnails ocupam mais espaço visual na SERP (estimativa: 1.5-2x)
  - CTR médio de vídeo é superior ao de texto em SERPs de marca
  - DA 100 (YouTube) significa permanência mais longa

  ESCOLHA DO PESO: 1.2x (conservador).
  Justificativa: literatura de CTR de vídeo em SERP varia de 1.2-2.5x
  dependendo de query type, device, e presença de thumbnail rico.
  Usamos 1.2x como piso conservador até termos dados próprios de CTR
  por entidade monitorada. Revisar quando houver ≥30 cases com vídeos.
"""
from collections import Counter
from services.constants import domain_authority

# Peso aplicado a resultados do YouTube no SERP score.
# Conservador (1.2x) até termos dados de CTR próprios.
# NÃO aumentar sem evidência empírica de cases reais.
YOUTUBE_WEIGHT = 1.2


def compute_serp_score(enriched_serp: list[dict]) -> dict:
    """
    Returns a composite SERP Occupation Score (0-100, higher = more toxic)
    with sub-metrics and detailed breakdown.

    Components:
      - Negative Share (30 pts): raw % of negative results (videos weighted 1.5x)
      - Tier-1 dominance (25 pts): authority-weighted negative impact
      - Top-3 contamination (20 pts): how many of top 3 are negative
      - Controlled Assets (15 pts): inverse of controlled ratio
      - Legal Domains (10 pts): legal domain count (capped)
    """
    total = len(enriched_serp) or 1

    def _is_video(r):
        domain = (r.get("domain", "") or "")
        url = (r.get("url", "") or "")
        return "youtube.com" in domain or "youtu.be" in url or r.get("type") == "video"

    # Negative Share (30 pts) — videos weighted 1.5x
    neg_count = 0
    for r in enriched_serp:
        w = YOUTUBE_WEIGHT if _is_video(r) else 1.0
        if r.get("sentiment") == "negative":
            neg_count += w
    weighted_total = sum(
        YOUTUBE_WEIGHT if _is_video(r) else 1.0 for r in enriched_serp
    ) or 1

    neg_share = neg_count / weighted_total
    neg_share_score = round(neg_share * 30, 1)

    sentiment_counts = Counter(r.get("sentiment", "neutral") for r in enriched_serp)
    pos_count = sentiment_counts.get("positive", 0)
    neu_count = sentiment_counts.get("neutral", 0)

    # Tier-1 dominance (25 pts)
    neg_authorities = [
        domain_authority(r.get("domain", ""))
        for r in enriched_serp
        if r.get("sentiment") == "negative"
    ]
    avg_neg_authority = sum(neg_authorities) / max(len(neg_authorities), 1)
    tier1_score = round((avg_neg_authority / 10) * 25, 1)

    # Top-3 contamination (20 pts)
    top3_neg = sum(
        1 for r in enriched_serp
        if r.get("position", 99) <= 3 and r.get("sentiment") == "negative"
    )
    top3_score = round((top3_neg / 3) * 20, 1)

    # Controlled Assets (15 pts) — inverse: less controlled = higher score
    ctrl_count = sum(1 for r in enriched_serp if r.get("controlled"))
    ctrl_ratio = ctrl_count / total
    ctrl_score = round((1 - ctrl_ratio) * 15, 1)

    # Legal Domains (10 pts)
    legal_count = sum(
        1 for r in enriched_serp
        if r.get("type") == "legal"
    )
    legal_score = round(min(legal_count, 5) * 2, 1)

    total_score = round(neg_share_score + tier1_score + top3_score + ctrl_score + legal_score, 1)

    return {
        "total": total_score,
        "breakdown": {
            "negative_share":     {"score": neg_share_score, "max": 30, "raw": round(neg_share * 100, 1)},
            "tier1_dominance":    {"score": tier1_score,     "max": 25, "raw": round(avg_neg_authority, 1)},
            "top3_contamination": {"score": top3_score,      "max": 20, "raw": top3_neg},
            "controlled_assets":  {"score": ctrl_score,      "max": 15, "raw": ctrl_ratio},
            "legal_domains":      {"score": legal_score,     "max": 10, "raw": legal_count},
        },
        "sentiment_shares": {
            "negative": round(neg_count / weighted_total * 100, 1),
            "neutral":  round(neu_count / total * 100, 1),
            "positive": round(pos_count / total * 100, 1),
        },
        "youtube_weighted": True,
        "youtube_weight": YOUTUBE_WEIGHT,
    }


def compute_domain_clusters(enriched_serp: list[dict]) -> list[dict]:
    """Group results by domain with sentiment breakdown and weighted dominance."""
    clusters: dict[str, dict] = {}
    for r in enriched_serp:
        domain = r.get("domain", "unknown")
        if domain not in clusters:
            clusters[domain] = {
                "domain": domain,
                "total": 0,
                "negative": 0,
                "neutral": 0,
                "positive": 0,
                "positions": [],
                "authority": domain_authority(domain),
            }
        c = clusters[domain]
        c["total"] += 1
        sentiment = r.get("sentiment", "neutral")
        c[sentiment] += 1
        c["positions"].append(r.get("position", 99))

    result = []
    for domain, data in clusters.items():
        neg_pct = round(data["negative"] / data["total"] * 100, 1) if data["total"] else 0
        weighted_dominance = round((data["negative"] * data["authority"]) / max(data["total"], 1), 1)
        result.append({
            "domain": domain,
            "total": data["total"],
            "negative": data["negative"],
            "neutral": data["neutral"],
            "positive": data["positive"],
            "neg_pct": neg_pct,
            "authority": data["authority"],
            "weighted_dominance": weighted_dominance,
            "positions": sorted(data["positions"]),
        })

    result.sort(key=lambda x: x["weighted_dominance"], reverse=True)
    return result


def compute_position_map(enriched_serp: list[dict]) -> list[dict]:
    """Rank-ordered SERP with sentiment, domain, type — the war map.
    Video results are flagged so operators can distinguish them from text."""
    sorted_serp = sorted(enriched_serp, key=lambda r: r.get("position", 99))
    return [
        {
            "position": r.get("position", "?"),
            "domain": r.get("domain", ""),
            "title": (r.get("title", "") or "")[:90],
            "sentiment": r.get("sentiment", "neutral"),
            "type": r.get("type", "blog"),
            "authority": domain_authority(r.get("domain", "")),
            "controlled": r.get("controlled", False),
            "is_video": "youtube.com" in (r.get("domain", "") or "")
                        or "youtu.be" in (r.get("url", "") or "")
                        or r.get("type") == "video",
        }
        for r in sorted_serp
    ]
