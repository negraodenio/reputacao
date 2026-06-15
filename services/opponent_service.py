"""
Opponent Service — Análise Comparativa de Oponentes.

Audita o SERP do adversário, compara com o político principal,
e gera diagnóstico de posicionamento relativo.

Uso:
  report = analyze_opponent("João Silva", "Maria Santos")
  → {
      "politician_serp": [...],
      "opponent_serp": [...],
      "comparison": {...},
      "narrative_gap": 0.35,
      "strategic_insight": "..."
    }
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

logger = logging.getLogger("councilia.opponent")


def analyze_opponent(
    politician_name: str,
    opponent_name:   str,
    num_results:     int = 10,
) -> dict:
    """
    Compara o SERP do político com o do adversário.

    Faz 2 chamadas ao SerpAPI (2 créditos) e retorna um relatório comparativo.
    """
    from services.serpapi_service import search_raw

    logger.info(f"Analisando oponente: {politician_name} vs {opponent_name}")

    # Buscar ambos
    pol_raw  = search_raw(politician_name, num=num_results)
    opp_raw  = search_raw(opponent_name,   num=num_results)

    pol_serp = _extract_serp(pol_raw)
    opp_serp = _extract_serp(opp_raw)

    comparison = compare_serp(pol_serp, opp_serp, politician_name, opponent_name)
    insight    = generate_contrast_narrative(comparison, politician_name, opponent_name)

    return {
        "generated_at":    datetime.now(timezone.utc).isoformat(),
        "politician_name": politician_name,
        "opponent_name":   opponent_name,
        "politician_serp": pol_serp,
        "opponent_serp":   opp_serp,
        "comparison":      comparison,
        "strategic_insight": insight,
    }


def _extract_serp(raw_data: dict) -> list[dict]:
    """Extrai e enriquece resultados orgânicos do JSON do SerpAPI."""
    results = []
    for r in raw_data.get("organic_results", []):
        domain = urlparse(r.get("link", "")).netloc.replace("www.", "")
        sentiment = _classify_snippet(r.get("snippet", ""))
        results.append({
            "position": r.get("position"),
            "title":    r.get("title", ""),
            "link":     r.get("link", ""),
            "snippet":  r.get("snippet", ""),
            "domain":   domain,
            "sentiment": sentiment,
        })
    return results


def compare_serp(
    pol_serp:        list[dict],
    opp_serp:        list[dict],
    politician_name: str,
    opponent_name:   str,
) -> dict:
    """
    Compara dois SERPs e gera métricas comparativas.

    Retorna:
      - politician_score:   score de reputação do político (0-100)
      - opponent_score:     score do adversário
      - narrative_gap:      diferença (-1 a +1, positivo = político melhor)
      - politician_metrics: métricas detalhadas
      - opponent_metrics:   métricas detalhadas
      - advantage:          quem está melhor e em quê
    """
    pol_m = _compute_serp_metrics(pol_serp)
    opp_m = _compute_serp_metrics(opp_serp)

    pol_score = _reputation_score(pol_m)
    opp_score = _reputation_score(opp_m)
    gap       = round((pol_score - opp_score) / 100, 3)

    advantages = []
    if pol_m["positive_count"] > opp_m["positive_count"]:
        advantages.append(f"{politician_name} tem mais resultados positivos nas primeiras posições")
    if pol_m["negative_count"] < opp_m["negative_count"]:
        advantages.append(f"{politician_name} tem menos negativos que {opponent_name}")
    if pol_m["top3_negative"] < opp_m["top3_negative"]:
        advantages.append(f"Negativos de {politician_name} estão menos expostos (fora do top 3)")

    disadvantages = []
    if pol_m["positive_count"] < opp_m["positive_count"]:
        disadvantages.append(f"{opponent_name} domina mais resultados positivos")
    if pol_m["negative_count"] > opp_m["negative_count"]:
        disadvantages.append(f"{politician_name} tem mais negativos expostos")

    return {
        "politician_name":    politician_name,
        "opponent_name":      opponent_name,
        "politician_score":   pol_score,
        "opponent_score":     opp_score,
        "narrative_gap":      gap,
        "gap_label":          _gap_label(gap),
        "politician_metrics": pol_m,
        "opponent_metrics":   opp_m,
        "advantages":         advantages,
        "disadvantages":      disadvantages,
        "winner":             politician_name if gap > 0.05 else (opponent_name if gap < -0.05 else "Empatados"),
    }


def _compute_serp_metrics(serp: list[dict]) -> dict:
    """Calcula métricas de reputação a partir de uma lista de resultados SERP."""
    total    = len(serp) or 1
    positive = [r for r in serp if r.get("sentiment") == "positive"]
    negative = [r for r in serp if r.get("sentiment") == "negative"]
    neutral  = [r for r in serp if r.get("sentiment") == "neutral"]
    top3_neg = sum(1 for r in negative if r.get("position", 99) <= 3)
    top5_pos = sum(1 for r in positive if r.get("position", 99) <= 5)

    domains = set(r.get("domain", "") for r in serp if r.get("domain"))

    return {
        "total":             total,
        "positive_count":    len(positive),
        "negative_count":    len(negative),
        "neutral_count":     len(neutral),
        "top3_negative":     top3_neg,
        "top5_positive":     top5_pos,
        "positive_ratio":    round(len(positive) / total, 2),
        "negative_ratio":    round(len(negative) / total, 2),
        "distinct_domains":  len(domains),
        "top_results":       serp[:3],
    }


def _reputation_score(metrics: dict) -> int:
    """Score de reputação 0-100 baseado nas métricas SERP."""
    score = 50  # neutro
    score += metrics["positive_ratio"] * 30
    score -= metrics["negative_ratio"] * 30
    score -= metrics["top3_negative"] * 8
    score += metrics["top5_positive"] * 4
    return max(0, min(100, round(score)))


def _gap_label(gap: float) -> str:
    if gap > 0.3:
        return "VANTAGEM SÓLIDA"
    if gap > 0.1:
        return "VANTAGEM LEVE"
    if gap > -0.1:
        return "EMPATADOS"
    if gap > -0.3:
        return "DESVANTAGEM LEVE"
    return "DESVANTAGEM CRÍTICA"


def _classify_snippet(snippet: str) -> str:
    """Classifica sentimento de um snippet de SERP."""
    s = snippet.lower()
    NEG = [
        "corrupto", "preso", "condenado", "réu", "investigado",
        "escândalo", "fraude", "improbidade", "irregularidade",
        "denúncia", "polêmica", "crise", "processo",
    ]
    POS = [
        "inaugurou", "entregou", "realizou", "aprovado", "beneficiou",
        "conquista", "projeto aprovado", "investimento", "obra",
        "homenagem", "reconhecimento", "eleito", "melhor",
    ]
    if any(k in s for k in NEG):
        return "negative"
    if any(k in s for k in POS):
        return "positive"
    return "neutral"


def generate_contrast_narrative(
    comparison:      dict,
    politician_name: str,
    opponent_name:   str,
) -> str:
    """
    Usa LLM para gerar diagnóstico de posicionamento comparativo.
    Sem custo adicional — usa o mesmo modelo de auditoria.
    """
    try:
        from services.openrouter_service import call_openrouter

        pol_m = comparison.get("politician_metrics", {})
        opp_m = comparison.get("opponent_metrics", {})
        gap   = comparison.get("narrative_gap", 0)
        gap_l = comparison.get("gap_label", "")

        prompt = f"""Você é especialista em gestão de reputação política no Brasil.

Análise comparativa de SERP (Google — 10 primeiros resultados):

POLÍTICO: {politician_name}
  Positivos: {pol_m.get("positive_count", 0)} | Negativos: {pol_m.get("negative_count", 0)} | Negativos no TOP 3: {pol_m.get("top3_negative", 0)}
  Score de Reputação: {comparison.get("politician_score", 0)}/100

ADVERSÁRIO: {opponent_name}
  Positivos: {opp_m.get("positive_count", 0)} | Negativos: {opp_m.get("negative_count", 0)} | Negativos no TOP 3: {opp_m.get("top3_negative", 0)}
  Score de Reputação: {comparison.get("opponent_score", 0)}/100

Diferencial de Narrativa: {gap_l} (gap = {gap:+.2f})

Vantagens identificadas para {politician_name}:
{chr(10).join(f"- {a}" for a in comparison.get("advantages", [])) or "- Nenhuma vantagem clara"}

Desvantagens:
{chr(10).join(f"- {d}" for d in comparison.get("disadvantages", [])) or "- Nenhuma"}

Gere em português, em 3 parágrafos curtos (máx 150 palavras total):
1. DIAGNÓSTICO: Estado atual da batalha de narrativa no Google
2. OPORTUNIDADE: O que {politician_name} pode explorar da fraqueza do adversário
3. AÇÃO IMEDIATA: Uma ação concreta de conteúdo para virar a disputa nos próximos 30 dias

Seja direto. Zero introduções genéricas."""

        response = call_openrouter(prompt, max_tokens=400)
        return response["choices"][0]["message"]["content"]

    except Exception as e:
        logger.warning(f"LLM para análise de oponente falhou: {e}")
        gap = comparison.get("narrative_gap", 0)
        pol_score = comparison.get("politician_score", 50)
        opp_score = comparison.get("opponent_score", 50)

        if gap > 0:
            return (
                f"{politician_name} está em posição favorável no Google com score {pol_score}/100 "
                f"vs {opponent_name} com {opp_score}/100. "
                f"A diferença de {abs(gap)*100:.0f}% indica vantagem narrativa. "
                f"Recomendação: manter ritmo de publicação e expandir para portais regionais."
            )
        else:
            return (
                f"{politician_name} está em desvantagem narrativa ({pol_score}/100 "
                f"vs {opp_score}/100 do adversário). "
                f"Prioridade: publicar realizações do mandato nos portais regionais para "
                f"deslocar resultados negativos das primeiras posições."
            )
