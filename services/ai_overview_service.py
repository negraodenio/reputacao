"""
Google AI Overview Service — Análise do Resumo de IA do Google.

O Google AI Overview (ex-SGE) aparece ACIMA dos resultados orgânicos para
queries de pessoas e marcas conhecidas. É o novo "position zero" da IA.

Por que é crítico para reputação:
  - Apresentado ANTES de qualquer resultado orgânico
  - Usuário percebe como "resposta do Google" — credibilidade máxima
  - Sintetiza e consolida múltiplas fontes, incluindo negativas
  - Não é suprimível via SEO clássico (push-down não funciona se o AIO
    já incorporou aquele conteúdo em seu resumo)
  - Varia por usuário/localização, mas é mais consistente em queries de marca

Fontes de dados:
  1. Campo `ai_overview` na resposta padrão do SerpAPI Google Search
  2. Endpoint secundário `engine=google_ai_overview` via page_token (lazy-loaded)

AIO Risk Score (0-100):
  0:      Sem AI Overview (entidade não tem overview ou está em branco)
  1-25:   Overview neutro ou positivo
  26-60:  Overview misto — requer contraposição
  61-100: Overview tóxico — ação urgente necessária
"""
import logging
from datetime import datetime, timezone
from pathlib import Path

from services.serpapi_service import fetch_ai_overview_by_token
from services.openrouter_service import call_openrouter
from services.cost_tracker import track

logger = logging.getLogger("councilia.ai_overview")

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

# Keywords de risco que aumentam o AIO Risk Score quando presentes no texto do overview
NEGATIVE_KEYWORDS = [
    "fraude", "escândalo", "escandalo", "crime", "prisão", "prisao",
    "preso", "condenado", "golpe", "denúncia", "denuncia", "acusação",
    "acusacao", "polêmica", "polemica", "investigação", "investigacao",
    "frauda", "lawsuit", "scandal", "fraud", "criminal", "indicted",
    "corruption", "corrupção", "processo", "condenação",
]

POSITIVE_KEYWORDS = [
    "fundador", "founder", "líder", "lider", "award", "prêmio", "premio",
    "sucesso", "success", "reconhecido", "empreendedor", "entrepreneur",
    "inovador", "autor", "author", "CEO", "destaque", "referência",
]


def extract_and_analyze(
    entity_name: str,
    raw_search_data: dict,
    enable_llm: bool = True,
) -> dict:
    """
    Entry point principal.

    1. Extrai ai_overview do raw_search_data já obtido da SERP (sem custo extra)
    2. Se lazy-loaded (page_token presente), faz 1 chamada extra imediata
    3. Analisa deterministicamente e opcionalmente via LLM

    Args:
        entity_name:     Nome da entidade
        raw_search_data: JSON completo retornado por serpapi_service.search_raw()
        enable_llm:      Se True, usa LLM para análise qualitativa do texto

    Returns:
        AIOverviewReport dict
    """
    ai_data = _resolve_ai_overview(entity_name, raw_search_data)
    return analyze_ai_overview(entity_name, ai_data, enable_llm=enable_llm)


def _resolve_ai_overview(entity_name: str, raw_search_data: dict) -> dict:
    """
    Extrai e resolve o AI Overview do raw SerpAPI response.

    Trata dois cenários:
      A: Dados já presentes em raw_search_data["ai_overview"]
      B: Lazy-loaded — usa page_token para resolver
    """
    aio_raw = raw_search_data.get("ai_overview", {})
    if not aio_raw:
        logger.debug(f"AI Overview ausente para '{entity_name}'")
        return {}

    # Cenário B: lazy-loaded via page_token
    if "page_token" in aio_raw and not aio_raw.get("text_blocks"):
        page_token = aio_raw["page_token"]
        logger.info(f"AI Overview lazy-loaded para '{entity_name}' — resolvendo via page_token")
        try:
            track("serpapi", entity_name)
            resolved = fetch_ai_overview_by_token(page_token)
            if resolved:
                return resolved
        except Exception as e:
            logger.warning(f"Falha ao resolver page_token do AI Overview: {e}")
        return {}  # Falhou na resolução — tratar como sem overview

    # Cenário A: dados diretos
    return aio_raw


def analyze_ai_overview(
    entity_name: str,
    ai_data: dict,
    enable_llm: bool = True,
) -> dict:
    """
    Analisa o conteúdo do AI Overview e produz o AIOverviewReport.

    Args:
        entity_name: Nome da entidade
        ai_data:     Dict do AI Overview (pode ser {})
        enable_llm:  Se True, usa LLM para análise qualitativa

    Returns:
        AIOverviewReport dict com todos os scores e metadados
    """
    if not ai_data:
        return _absent_report(entity_name)

    # ── 1. Extrair texto completo do overview ─────────────────────────────────
    full_text = _extract_text(ai_data)
    text_lower = full_text.lower()

    # ── 2. Extrair fontes/referências citadas ─────────────────────────────────
    cited_sources = _extract_sources(ai_data)

    # ── 3. Análise de keywords ────────────────────────────────────────────────
    neg_hits = [kw for kw in NEGATIVE_KEYWORDS if kw in text_lower]
    pos_hits = [kw for kw in POSITIVE_KEYWORDS if kw in text_lower]

    # ── 4. Determinar sentimento do overview ──────────────────────────────────
    sentiment = _determine_sentiment(neg_hits, pos_hits, len(cited_sources))

    # ── 5. Calcular AIO Risk Score ────────────────────────────────────────────
    risk_score = _compute_aio_risk(
        neg_hits=neg_hits,
        cited_sources=cited_sources,
        sentiment=sentiment,
        full_text=full_text,
    )

    # ── 6. Análise qualitativa via LLM (opcional) ─────────────────────────────
    llm_analysis = ""
    if enable_llm and full_text and risk_score > 20:
        # Só chama LLM se há overview real e risco relevante
        llm_analysis = _run_llm_analysis(entity_name, full_text, cited_sources)
        if llm_analysis:
            track("openrouter", entity_name, tokens_input=300, tokens_output=200)

    return {
        "has_overview":    True,
        "entity_name":     entity_name,
        "fetched_at":      datetime.now(timezone.utc).isoformat(),
        "risk_score":      risk_score,
        "risk_label":      _risk_label(risk_score),
        "sentiment":       sentiment,
        "full_text":       full_text[:2000],   # cap para storage
        "negative_hits":   neg_hits,
        "positive_hits":   pos_hits,
        "cited_sources":   cited_sources,
        "source_count":    len(cited_sources),
        "llm_analysis":    llm_analysis,
        "raw_data":        {k: v for k, v in ai_data.items() if k != "text_blocks"},  # excluir texto bruto
    }


def _extract_text(ai_data: dict) -> str:
    """Consolida todo o texto dos text_blocks do AI Overview."""
    blocks = ai_data.get("text_blocks", [])
    if not blocks:
        # Tentar campo alternativo "snippet"
        return ai_data.get("snippet", "")

    parts = []
    for block in blocks:
        if isinstance(block, dict):
            text = block.get("snippet", "") or block.get("text", "") or ""
            if text:
                parts.append(text.strip())
        elif isinstance(block, str):
            parts.append(block.strip())

    return " ".join(parts)


def _extract_sources(ai_data: dict) -> list[dict]:
    """Extrai e normaliza as fontes/referências citadas no AI Overview."""
    references = ai_data.get("references", []) or ai_data.get("sources", [])
    sources = []
    for ref in references:
        if isinstance(ref, dict):
            link = ref.get("link", "") or ref.get("url", "")
            title = ref.get("title", "")
            snippet = ref.get("snippet", "")
            if link or title:
                sources.append({
                    "title":   title,
                    "link":    link,
                    "snippet": snippet[:200],
                })
    return sources


def _determine_sentiment(
    neg_hits: list[str],
    pos_hits: list[str],
    source_count: int,
) -> str:
    """Determina sentimento dominante do AI Overview."""
    if not neg_hits and not pos_hits:
        return "neutral"
    if neg_hits and not pos_hits:
        return "negative"
    if pos_hits and not neg_hits:
        return "positive"
    # Ambos presentes — misto, pesa negativos
    if len(neg_hits) > len(pos_hits):
        return "negative"
    elif len(pos_hits) > len(neg_hits):
        return "positive"
    return "mixed"


def _compute_aio_risk(
    neg_hits: list[str],
    cited_sources: list[dict],
    sentiment: str,
    full_text: str,
) -> float:
    """
    AIO Risk Score (0-100).

    Componentes:
      · Sentimento negativo do texto (0-40 pts)
      · Keywords tóxicas no texto (0-20 pts)
      · Fontes negativas citadas (0-30 pts)
      · Intensidade: texto longo + muitos hits (0-10 pts)
    """
    score = 0.0

    # Componente 1: Sentimento dominante (0-40)
    if sentiment == "negative":
        score += 40
    elif sentiment == "mixed":
        score += 20
    elif sentiment == "positive":
        score += 0
    else:  # neutral
        score += 5

    # Componente 2: Keywords tóxicas (0-20)
    # Cada keyword adiciona 4 pts, máximo 20
    kw_score = min(len(neg_hits) * 4, 20)
    score += kw_score

    # Componente 3: Fontes negativas citadas (0-30)
    # Fontes com keywords negativas no título/snippet
    neg_source_count = 0
    for src in cited_sources:
        src_text = ((src.get("title", "") or "") + " " + (src.get("snippet", "") or "")).lower()
        if any(kw in src_text for kw in NEGATIVE_KEYWORDS):
            neg_source_count += 1

    if cited_sources:
        neg_src_ratio = neg_source_count / len(cited_sources)
        score += round(neg_src_ratio * 30, 1)

    # Componente 4: Intensidade do texto (0-10)
    if len(full_text) > 500 and len(neg_hits) >= 3:
        score += 10
    elif len(full_text) > 200 and len(neg_hits) >= 1:
        score += 5

    return round(min(score, 100), 1)


def _risk_label(score: float) -> str:
    if score == 0:
        return "SEM OVERVIEW"
    elif score <= 25:
        return "BAIXO RISCO"
    elif score <= 60:
        return "RISCO MODERADO"
    elif score <= 80:
        return "ALTO RISCO"
    else:
        return "CRÍTICO"


def _run_llm_analysis(
    entity_name: str,
    overview_text: str,
    cited_sources: list[dict],
) -> str:
    """
    Análise qualitativa do AI Overview via LLM.
    Chamada apenas quando risk_score > 20 (há algo a analisar).
    """
    try:
        prompt_path = PROMPTS_DIR / "ai_overview_analysis.txt"
        if not prompt_path.exists():
            return ""

        sources_block = "\n".join(
            f"  - {s.get('title', '')} ({s.get('link', '')})"
            for s in cited_sources[:5]
        ) or "  Nenhuma fonte citada."

        template = prompt_path.read_text(encoding="utf-8")
        prompt = template.format(
            entity_name=entity_name,
            overview_text=overview_text[:1500],
            cited_sources=sources_block,
        )

        response = call_openrouter(prompt, temperature=0.3, max_tokens=400)
        raw = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        return raw.strip()
    except Exception as e:
        logger.warning(f"LLM análise AI Overview falhou: {e}")
        return ""


def _absent_report(entity_name: str) -> dict:
    """Relatório para quando não há AI Overview para a entidade."""
    return {
        "has_overview":  False,
        "entity_name":   entity_name,
        "fetched_at":    datetime.now(timezone.utc).isoformat(),
        "risk_score":    0.0,
        "risk_label":    "SEM OVERVIEW",
        "sentiment":     "absent",
        "full_text":     "",
        "negative_hits": [],
        "positive_hits": [],
        "cited_sources": [],
        "source_count":  0,
        "llm_analysis":  "",
        "raw_data":      {},
    }
