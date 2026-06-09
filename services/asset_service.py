import re
import logging
from pathlib import Path
from services.openrouter_service import call_openrouter
from services.serpapi_service import search
from services.gnews_service import fetch_news
from urllib.parse import urlparse

logger = logging.getLogger("councilia.asset")

TEMPLATES_DIR = Path(__file__).parent.parent / "asset_templates"
MAX_OUTPUT_CHARS = 12000
MAX_CAMPAIGN_CHARS = 25000

# Densidade mínima do nome da entidade no artigo gerado.
# Se o nome completo aparece menos que este número de vezes, o sistema
# adiciona um reforço ao final do artigo.
MIN_NAME_OCCURRENCES = 3

ASSET_TYPES = {
    "linkedin_article":          "linkedin_article.md",
    "executive_bio":             "executive_bio.md",
    "legal_clarification":       "legal_clarification.md",
    "institutional_profile":     "institutional_profile.md",
    "interview_talking_points":  "interview_talking_points.md",
    "press_release":             "press_release.md",
    "campaign_strategy":         "campaign_strategy.md",
    "faq_transparencia":         "faq_transparencia.md",
    "roteiro_youtube":           "roteiro_youtube.md",
}

# System prompt injetado em TODAS as gerações de conteúdo.
# Garante PT-BR independente do contexto enviado.
_SYSTEM_PROMPT = (
    "Você é um especialista em comunicação estratégica brasileira e SEO. "
    "REGRA ABSOLUTA: Toda resposta deve ser escrita em português do Brasil, "
    "sem exceções, independentemente do idioma do contexto recebido. "
    "Nunca escreva em inglês."
)


def _load_template(asset_type: str) -> str:
    filename = ASSET_TYPES[asset_type]
    return (TEMPLATES_DIR / filename).read_text(encoding="utf-8")


def _clean(text: str) -> str:
    text = re.sub(r"[^\x00-\x7F\u00C0-\u024F\u1E00-\u1EFF\n]", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _count_name_occurrences(text: str, entity: str) -> int:
    """Conta quantas vezes o nome completo da entidade aparece no texto."""
    if not entity or not text:
        return 0
    return text.lower().count(entity.lower())


def _validate_and_enhance(text: str, entity: str, asset_type: str) -> str:
    """
    Valida a densidade do nome da entidade no artigo gerado.

    Se o nome completo aparece menos de MIN_NAME_OCCURRENCES vezes:
    - Para artigos publicáveis: adiciona uma linha de contexto no início
    - Registra warning no log

    Isso garante que o conteúdo ranqueie para buscas pelo nome da entidade.
    """
    count = _count_name_occurrences(text, entity)

    if count < MIN_NAME_OCCURRENCES:
        logger.warning(
            f"[{asset_type}] Nome '{entity}' aparece apenas {count}x "
            f"(mínimo: {MIN_NAME_OCCURRENCES}). Adicionando reforço de contexto."
        )
        # Para tipos não-publicáveis (roteiro, pontos de entrevista), não modifica
        non_publishable = {"interview_talking_points", "campaign_strategy"}
        if asset_type not in non_publishable:
            # Adiciona contexto de entidade no início se o H1 não contém o nome
            first_line = text.split("\n")[0] if text else ""
            if entity.lower() not in first_line.lower():
                text = f"# {entity} — {_extract_subtitle(text, asset_type)}\n\n{text}"

    return text


def _extract_subtitle(text: str, asset_type: str) -> str:
    """Extrai ou gera um subtítulo apropriado para o H1."""
    subtitles = {
        "artigo_linkedin":     "Perspectiva Profissional",
        "linkedin_article":    "Perspectiva Profissional",
        "executive_bio":       "Perfil Executivo",
        "biografia_executiva": "Perfil Executivo",
        "legal_clarification": "Esclarecimento Oficial",
        "esclarecimento_juridico": "Esclarecimento Oficial",
        "institutional_profile": "Perfil Institucional",
        "perfil_institucional":  "Perfil Institucional",
        "press_release":       "Comunicado à Imprensa",
        "comunicado_imprensa": "Comunicado à Imprensa",
        "faq_transparencia":   "Perguntas Frequentes",
    }
    return subtitles.get(asset_type, "Informações Profissionais")


def generate_asset(asset_type: str, entity: str, context: str = "") -> str:
    """
    Gera um ativo de conteúdo via LLM.

    Melhorias v2:
    - System prompt separado em PT-BR (garante idioma independente do contexto)
    - Contexto padrão inclui nome da entidade (evita geração sem referência)
    - Validação de densidade de nome pós-geração
    - Logging de qualidade do output
    """
    template = _load_template(asset_type)

    # Contexto padrão mais rico que "No additional strategic context provided."
    effective_context = context or (
        f"Entidade: {entity}.\n"
        f"Escreva conteúdo profissional e positivo sobre {entity} "
        f"para posicionamento de reputação digital."
    )

    prompt = template.format(entity=entity, context=effective_context)

    # Usa system prompt separado para garantir PT-BR e qualidade
    response = call_openrouter(
        prompt,
        temperature=0.4,
        system_prompt=_SYSTEM_PROMPT,
    )
    raw = response["choices"][0]["message"]["content"]
    raw = _clean(raw)
    raw = raw[:MAX_OUTPUT_CHARS]

    # Valida densidade do nome e corrige se necessário
    raw = _validate_and_enhance(raw, entity, asset_type)

    name_count = _count_name_occurrences(raw, entity)
    logger.info(
        f"[{asset_type}] Gerado para '{entity}': "
        f"{len(raw)} chars, nome aparece {name_count}x"
    )

    return raw


def generate_campaign(entity: str, threat_level: str, narrative_state: str, objective: str) -> str:
    serp_results = search(entity)
    serp_lines = []
    for r in serp_results:
        domain = urlparse(r.get("link", "")).netloc.replace("www.", "")
        serp_lines.append(
            f"#{r['position']} | {r['title'][:80]} | {domain} | {r.get('snippet', '')[:100]}"
        )
    serp_context = "\n".join(serp_lines) if serp_lines else "Sem dados de SERP disponíveis."

    news = fetch_news(entity)
    if news:
        from collections import Counter
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        domain_counts = Counter()
        recent_count = 0
        for a in news:
            d = urlparse(a.get("url", "")).netloc.replace("www.", "")
            domain_counts[d] += 1
            try:
                pub = datetime.fromisoformat(a["published_at"].replace("Z", "+00:00"))
                if (now - pub).days <= 7:
                    recent_count += 1
            except Exception:
                pass
        news_lines = [f"Total de artigos: {len(news)} | Recentes (7d): {recent_count}"]
        for d, c in domain_counts.most_common(5):
            news_lines.append(f"  {d}: {c} artigos")
        news_context = "\n".join(news_lines)
    else:
        news_context = "Sem dados de notícias recentes disponíveis."

    template = _load_template("campaign_strategy")
    prompt = template.format(
        entity=entity,
        threat_level=threat_level,
        narrative_state=narrative_state,
        objective=objective or "Melhorar percepção em busca de marca e reduzir dominância narrativa negativa.",
        serp_context=serp_context,
        news_context=news_context,
    )

    response = call_openrouter(prompt, temperature=0.4, system_prompt=_SYSTEM_PROMPT)
    raw = response["choices"][0]["message"]["content"]
    raw = _clean(raw)
    return raw[:MAX_CAMPAIGN_CHARS]
