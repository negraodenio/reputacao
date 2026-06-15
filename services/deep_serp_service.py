"""
Deep SERP Service — Monitoramento de Páginas Profundas (9-11).

Captura e analisa resultados nas posições 81-110 do Google para:
  1. Detectar negativos que ainda vivem no "limbo" de supressão
  2. Medir progresso de campanhas de deslocamento narrativo
  3. Alertar sobre risco de ressurgimento de conteúdo tóxico
  4. Fornecer Deep Negative Index (DNI) como KPI de saúde reputacional

Custo: +3 créditos SerpAPI por chamada completa (p.9 + p.10 + p.11)
       Rodar apenas em auditorias HIGH/CRITICAL para economizar quota.

DNI (Deep Negative Index) Scale:
  0-20:   Zona segura — negativos efetivamente suprimidos
  21-50:  Limbo instável — monitorar ressurgimento
  51-80:  Alta ameaça latente — supressão incompleta
  81-100: Perigo imediato — negativos podem resurgir
"""
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

from services.serpapi_service import search_page
from services.constants import domain_authority, classify_domain
from services.cost_tracker import track

logger = logging.getLogger("councilia.deep_serp")

# Páginas profundas a auditar (posições 81-110)
DEEP_PAGES = [9, 10, 11]

# Keywords que sinalizam conteúdo negativo
NEGATIVE_KEYWORDS = [
    "fraude", "escândalo", "escandalo", "crime", "prisão", "prisao",
    "preso", "condenado", "golpe", "denúncia", "denuncia", "acusação",
    "acusacao", "polêmica", "polemica", "investigação", "investigacao",
    "frauda", "lawsuit", "scandal", "fraud", "criminal", "indicted",
    "arrested", "controversy", "crise", "crise", "corruption", "corrupção",
]


def fetch_deep_serp(
    entity_name: str,
    pages: list[int] | None = None,
    page1_results: list[dict] | None = None,
) -> dict:
    """
    Busca e analisa os resultados das páginas profundas do Google.

    Args:
        entity_name:   Nome da entidade monitorada
        pages:         Quais páginas buscar (default: [9, 10, 11])
        page1_results: Resultados da página 1 já capturados (para análise comparativa)

    Returns:
        DeepSerpReport dict com scores e listas detalhadas
    """
    if pages is None:
        pages = DEEP_PAGES

    deep_results: list[dict] = []
    fetch_errors: list[str] = []

    for page_num in pages:
        try:
            logger.info(f"Deep SERP: buscando página {page_num} para '{entity_name}'")
            page_results = search_page(entity_name, page_num)
            track("serpapi", entity_name)
            deep_results.extend(page_results)
        except RuntimeError as e:
            msg = str(e)
            if "quota" in msg.lower():
                logger.warning(f"Quota SerpAPI esgotada em página {page_num} — abortando deep audit")
                fetch_errors.append(f"p.{page_num}: quota esgotada")
                break
            else:
                logger.warning(f"Erro ao buscar página {page_num}: {e}")
                fetch_errors.append(f"p.{page_num}: {msg[:80]}")
        except Exception as e:
            logger.warning(f"Erro inesperado na página {page_num}: {e}")
            fetch_errors.append(f"p.{page_num}: erro inesperado")

    return analyze_deep_serp(
        entity_name=entity_name,
        deep_results=deep_results,
        page1_results=page1_results or [],
        pages_fetched=pages[:len(pages) - len(fetch_errors)],
        fetch_errors=fetch_errors,
    )


def analyze_deep_serp(
    entity_name: str,
    deep_results: list[dict],
    page1_results: list[dict],
    pages_fetched: list[int],
    fetch_errors: list[str],
) -> dict:
    """
    Analisa os resultados profundos e produz o DeepSerpReport.
    Toda a análise é determinística — sem chamada LLM.
    """
    if not deep_results:
        return _empty_report(entity_name, pages_fetched, fetch_errors)

    # ── 1. Classificar e enriquecer resultados profundos ──────────────────────
    enriched = []
    for r in deep_results:
        link = r.get("link", "") or ""
        title = r.get("title", "") or ""
        snippet = r.get("snippet", "") or ""
        domain = urlparse(link).netloc.replace("www.", "")

        text = (title + " " + snippet).lower()
        is_negative = any(kw in text for kw in NEGATIVE_KEYWORDS)
        sentiment = "negative" if is_negative else "neutral"

        enriched.append({
            "position":  r.get("position"),
            "page":      r.get("page"),
            "domain":    domain,
            "title":     title[:100],
            "link":      link,
            "snippet":   snippet[:200],
            "sentiment": sentiment,
            "authority": domain_authority(domain),
            "type":      classify_domain(domain),
        })

    # ── 2. Separar negativos profundos ────────────────────────────────────────
    deep_negatives = [r for r in enriched if r["sentiment"] == "negative"]
    total_deep = len(enriched) or 1

    # ── 3. Detectar supressão confirmada ──────────────────────────────────────
    # Domínios que estão nas páginas profundas MAS NÃO na página 1
    page1_domains = {
        urlparse(r.get("link", "")).netloc.replace("www.", "")
        for r in page1_results
    }
    suppressed_domains = []
    for r in deep_negatives:
        dom = r["domain"]
        if dom and dom not in page1_domains:
            if dom not in [s["domain"] for s in suppressed_domains]:
                suppressed_domains.append({
                    "domain":    dom,
                    "position":  r["position"],
                    "authority": r["authority"],
                    "title":     r["title"],
                })

    # ── 4. Risco de ressurgimento ─────────────────────────────────────────────
    # Negativos de alta autoridade nas páginas profundas podem subir
    high_authority_negatives = [r for r in deep_negatives if r["authority"] >= 7]
    resurface_risk = "HIGH" if len(high_authority_negatives) >= 3 else \
                     "MODERATE" if len(high_authority_negatives) >= 1 else "LOW"

    # ── 5. Calcular DNI (Deep Negative Index) ─────────────────────────────────
    dni = _compute_dni(deep_negatives, total_deep, high_authority_negatives)

    # ── 6. Avaliação narrativa ────────────────────────────────────────────────
    assessment = _build_assessment(dni, deep_negatives, suppressed_domains, resurface_risk)

    return {
        "entity_name":         entity_name,
        "fetched_at":          datetime.now(timezone.utc).isoformat(),
        "pages_fetched":       pages_fetched,
        "fetch_errors":        fetch_errors,
        "total_results":       len(enriched),
        "total_negatives":     len(deep_negatives),
        "deep_negative_index": dni,
        "dni_label":           _dni_label(dni),
        "resurface_risk":      resurface_risk,
        "suppressed_domains":  suppressed_domains,
        "deep_negatives":      deep_negatives,
        "all_deep_results":    enriched,
        "assessment":          assessment,
    }


def _compute_dni(
    deep_negatives: list[dict],
    total_results: int,
    high_authority: list[dict],
) -> float:
    """
    DNI (Deep Negative Index) — escala 0-100.

    Componentes:
      · Volume de negativos profundos (0-40 pts)
      · Autoridade média dos negativos (0-30 pts)
      · Proporção de alta autoridade (0-30 pts)
    """
    # Componente 1: Volume (0-40)
    # 0 negativos=0, 3=15, 6=30, 10+=40
    vol_score = min(len(deep_negatives) / 10 * 40, 40)

    # Componente 2: Autoridade média (0-30)
    if deep_negatives:
        avg_auth = sum(r["authority"] for r in deep_negatives) / len(deep_negatives)
        auth_score = (avg_auth / 10) * 30
    else:
        auth_score = 0

    # Componente 3: Alta autoridade (0-30)
    if total_results > 0:
        ha_ratio = len(high_authority) / max(len(deep_negatives), 1)
        ha_score = ha_ratio * 30
    else:
        ha_score = 0

    return round(min(vol_score + auth_score + ha_score, 100), 1)


def _dni_label(score: float) -> str:
    if score <= 20:
        return "SEGURO"
    elif score <= 50:
        return "INSTÁVEL"
    elif score <= 80:
        return "AMEAÇA LATENTE"
    else:
        return "PERIGO IMEDIATO"


def _build_assessment(
    dni: float,
    deep_negatives: list[dict],
    suppressed: list[dict],
    resurface_risk: str,
) -> str:
    """Gera avaliação textual determinística do relatório deep SERP."""
    lines = []
    label = _dni_label(dni)

    lines.append(f"DNI: {dni}/100 — {label}")

    if not deep_negatives:
        lines.append("Nenhum conteúdo negativo detectado nas páginas 9-11.")
        lines.append("A supressão está operando com eficácia total nesta faixa.")
    else:
        lines.append(
            f"{len(deep_negatives)} resultado(s) negativo(s) detectados "
            f"nas páginas profundas (posições 81-110)."
        )
        top_neg = sorted(deep_negatives, key=lambda x: x["authority"], reverse=True)[:3]
        for r in top_neg:
            lines.append(
                f"  · [{r['authority']}/10] p.{r['page']} #{r['position']} "
                f"{r['domain']} — {r['title'][:60]}"
            )

    if suppressed:
        lines.append(
            f"\n{len(suppressed)} domínio(s) negativos foram suprimidos da página 1 "
            f"e agora vivem nas páginas profundas:"
        )
        for s in suppressed[:3]:
            lines.append(f"  · {s['domain']} (auth {s['authority']}/10) — posição {s['position']}")

    lines.append(f"\nRisco de ressurgimento: {resurface_risk}")
    if resurface_risk in ("HIGH", "MODERATE"):
        lines.append(
            "  → Negativos de alta autoridade nas páginas profundas podem escalar "
            "se um evento de mídia aumentar a volumetria de busca."
        )

    return "\n".join(lines)


def _empty_report(entity_name: str, pages: list[int], errors: list[str]) -> dict:
    """Relatório vazio para quando não foi possível obter dados."""
    return {
        "entity_name":         entity_name,
        "fetched_at":          datetime.now(timezone.utc).isoformat(),
        "pages_fetched":       pages,
        "fetch_errors":        errors,
        "total_results":       0,
        "total_negatives":     0,
        "deep_negative_index": 0.0,
        "dni_label":           "INDISPONÍVEL",
        "resurface_risk":      "DESCONHECIDO",
        "suppressed_domains":  [],
        "deep_negatives":      [],
        "all_deep_results":    [],
        "assessment":          "Dados insuficientes — verifique quota da SerpAPI.",
    }
