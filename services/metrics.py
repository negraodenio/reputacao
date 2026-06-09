"""
metrics.py — Fonte canônica de cálculo de métricas do CouncilIA.

REGRA: nenhum outro serviço recalcula momentum, neg_ratio, count_7d/count_30d
ou top_domains. Todos importam daqui. Mudança em uma função aqui propaga para
todo o sistema.
"""
from datetime import datetime, timezone
from collections import Counter
from urllib.parse import urlparse


def compute_momentum(count_7d: int, count_30d: int) -> str:
    """Classifica o momentum narrativo baseado em artigos recentes vs histórico."""
    if count_7d >= max(1, count_30d // 2):
        return "Escalating"
    if count_7d == 0:
        return "Declining"
    return "Stable"


def compute_news_counts(news: list[dict]) -> tuple[int, int]:
    """Conta artigos nos últimos 7 e 30 dias. Retorna (count_7d, count_30d)."""
    now = datetime.now(timezone.utc)
    count_7d = count_30d = 0
    for a in news:
        published = a.get("published_at", "") or a.get("publishedAt", "")
        try:
            dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
            days_ago = (now - dt).days
            if days_ago <= 7:
                count_7d += 1
                count_30d += 1
            elif days_ago <= 30:
                count_30d += 1
        except Exception:
            pass
    return count_7d, count_30d


def compute_neg_ratio(serp: list[dict]) -> float:
    """Calcula o ratio de resultados negativos na SERP enriquecida."""
    total = len(serp) or 1
    neg = sum(1 for r in serp if r.get("sentiment") == "negative")
    return round(neg / total, 3)


def compute_npa_domains(
    news: list[dict],
    serp: list[dict] | None = None,
) -> dict:
    """
    Fonte canônica para cálculo de domínios do NPA.

    Combina GNews + SERP num único pipeline:
      1. Conta artigos GNews por domínio
      2. Adiciona domínios de alta autoridade da SERP que não estão no GNews
         (captura Metrópoles, CNN Brasil, Folha que aparecem na SERP mas não no GNews)
      3. Ranqueia top_domains por AUTHORITY × (count + recency), não por contagem pura
         (evita blogs de baixa qualidade com volume alto dominarem o ranking)
      4. Calcula most_aggressive com a mesma fórmula authority-weighted
      5. Retorna estrutura única usada por _build_npa, _parse_npa_struct e save_snapshot

    Retorna:
        {
          "count_7d": int,
          "count_30d": int,
          "momentum": str,
          "concentration": str,
          "most_aggressive": str,
          "most_aggressive_count": int,
          "top_domains": [(domain, count, domain_type), ...],  # top 5 por authority×count
          "total_articles": int,
        }
    """
    from services.constants import classify_domain, domain_authority

    _NEWS_DOMAIN_TYPES = {"mainstream", "investigative", "blog"}

    now = datetime.now(timezone.utc)
    domain_counts: Counter = Counter()
    domain_recency: Counter = Counter()
    count_7d = count_30d = 0

    # ── 1. GNews articles ──────────────────────────────────────────────
    for a in news:
        url = a.get("url", "")
        if not url:
            continue
        domain = urlparse(url).netloc.replace("www.", "")
        if not domain:
            continue
        domain_counts[domain] += 1
        published = a.get("published_at", "") or a.get("publishedAt", "")
        try:
            dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
            days_ago = (now - dt).days
            if days_ago <= 7:
                count_7d += 1
                count_30d += 1
                domain_recency[domain] += 2
            elif days_ago <= 30:
                count_30d += 1
                domain_recency[domain] += 1
        except Exception:
            pass

    # ── 2. SERP enrichment ─────────────────────────────────────────────
    # Adiciona domínios de alta autoridade que aparecem na SERP mas não no GNews.
    # Usa authority mínima de 5 para filtrar blogs desconhecidos.
    if serp:
        seen_news_domains = set(domain_counts.keys())
        for r in serp:
            domain = urlparse(r.get("link", "")).netloc.replace("www.", "")
            if not domain:
                continue
            dtype = classify_domain(domain)
            if dtype not in _NEWS_DOMAIN_TYPES:
                continue
            auth = domain_authority(domain)
            # Incluir da SERP apenas se: não está no GNews E é domínio de autoridade
            # (authority >= 5 elimina a maioria de blogs desconhecidos)
            if domain not in seen_news_domains and auth >= 5:
                domain_counts[domain] += 1
                domain_recency[domain] += 2  # tratar como recente (está na SERP agora)
                seen_news_domains.add(domain)

    # ── 3. Authority-weighted ranking ──────────────────────────────────
    # Score = (count + recency) × authority
    # Isso garante que CNN Brasil (authority 9) com 1 artigo (score 9×3=27)
    # apareça acima de um blog desconhecido (authority 2) com 5 artigos (score 2×5=10)
    def _score(d: str) -> float:
        return (domain_counts[d] + domain_recency.get(d, 0)) * domain_authority(d)

    # top_domains: top 5 por authority-weighted score
    all_domains = list(domain_counts.keys())
    all_domains.sort(key=_score, reverse=True)
    top5 = all_domains[:5]
    top_domains = [(d, domain_counts[d], classify_domain(d)) for d in top5]

    # ── 4. Most aggressive ────────────────────────────────────────────────
    # "Fonte Mais Agressiva" = fonte com maior potencial de dano reputacional.
    # Prioridade 1: domínios com authority >= 6 (mainstream, investigativo, jurídico)
    # Prioridade 2: se nenhum domínio de alta autoridade, usa o de maior volume
    # Isso garante que Metrópoles (auth 6) apareça antes de brasil247 (auth 2)
    # mesmo que brasil247 tenha 10× mais artigos.
    high_auth_domains = [d for d in all_domains if domain_authority(d) >= 6]
    if high_auth_domains:
        most_aggressive = max(high_auth_domains, key=_score)
    else:
        most_aggressive = max(all_domains, key=_score) if all_domains else "—"
    most_aggressive_count = domain_counts.get(most_aggressive, 0)

    # ── 5. Concentration ──────────────────────────────────────────────
    total = sum(domain_counts.values()) or 1
    top_count = domain_counts.get(top5[0], 0) if top5 else 0
    concentration = "Concentrated" if top_count / total > 0.5 else "Distributed"

    return {
        "count_7d":             count_7d,
        "count_30d":            count_30d,
        "momentum":             compute_momentum(count_7d, count_30d),
        "concentration":        concentration,
        "most_aggressive":      most_aggressive,
        "most_aggressive_count": most_aggressive_count,
        "top_domains":          top_domains,
        "total_articles":       total,
    }


def snapshot_age_hours(snapshot: dict) -> float | None:
    generated_at = snapshot.get("generated_at")
    if not generated_at:
        return None
    try:
        dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).total_seconds() / 3600
    except Exception:
        return None


def snapshot_is_stale(snapshot: dict, max_hours: int = 48) -> bool:
    age = snapshot_age_hours(snapshot)
    if age is None:
        return False
    return age > max_hours
