import re
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse
from pathlib import Path
from services.serpapi_service import search
from services.openrouter_service import call_openrouter
from services.firecrawl_service import scrape
from services.gnews_service import fetch_news
from services.snapshot_service import save_snapshot
from services.serp_screenshot import capture_synthetic_serp, save_screenshot
from services.expansion_service import expand_entity, format_expansion_context
from services.constants import PRIORITY_DOMAINS, EXCLUDED_DOMAINS, domain_authority, classify_domain
from services.cost_tracker import track
from services.metrics import compute_news_counts, compute_momentum, compute_npa_domains

logger = logging.getLogger("councilia.audit")

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
MAX_ARTICLE_CHARS = 3000
_NEWS_DOMAIN_TYPES = {"mainstream", "investigative", "blog"}

# Autoridade mínima para busca GNews ativa a partir da SERP
_SERP_GNEWS_MIN_AUTHORITY = 6
# Máximo de domínios da SERP para buscar ativamente no GNews
_SERP_GNEWS_MAX_DOMAINS = 4


def _select_urls(results: list[dict]) -> list[str]:
    priority, fallback = [], []
    for r in results:
        link = r.get("link", "")
        if any(d in link for d in EXCLUDED_DOMAINS):
            continue
        if any(d in link for d in PRIORITY_DOMAINS):
            priority.append(link)
        else:
            fallback.append(link)
    return (priority + fallback)[:3]


def _clean(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _sanitize(text: str) -> str:
    return re.sub(r"[^\x00-\x7F\u00C0-\u024F\u1E00-\u1EFF\n]", "", text).strip()


def _build_npa(news: list[dict], serp: list[dict] | None = None) -> str:
    """
    Constrói o bloco de texto NPA para injeção no prompt do LLM.
    Usa compute_npa_domains() como fonte canônica — mesma lógica do UI.
    """
    if not news and not serp:
        return "NPA: Nenhum artigo encontrado nas buscas padrão e expandidas."

    npa = compute_npa_domains(news, serp)

    top_lines = "\n".join(
        f"  - {d} ({c} artigos) [{dtype}]"
        for d, c, dtype in npa["top_domains"]
    ) or "  (nenhum)"

    concentration = npa["concentration"]
    top_domain = npa["top_domains"][0][0] if npa["top_domains"] else "—"
    top_dtype = classify_domain(top_domain) if top_domain != "—" else "unknown"

    return "\n".join([
        f"Artigos últimos 7 dias:   {npa['count_7d']}",
        f"Artigos últimos 30 dias:  {npa['count_30d']}",
        f"Momentum Narrativo:       {npa['momentum']}",
        f"",
        f"Domínios principais (por autoridade × volume):",
        top_lines,
        f"",
        f"Concentração de Fontes:   {concentration} (tipo dominante: {top_dtype})",
        f"Fonte Mais Agressiva:     {npa['most_aggressive']} — {npa['most_aggressive_count']} artigos",
    ])


def _capture_serp_screenshot(entity_name: str, results: list[dict]):
    import asyncio
    try:
        png = asyncio.run(capture_synthetic_serp(entity_name, results))
        if png:
            save_screenshot(entity_name, png)
    except Exception:
        pass


def run_audit(entity_name: str, country: str = "Brazil", industry: str = "General") -> dict:
    """
    Returns dict with:
      - text: sanitized analysis text
      - debug_expansion: full expansion debug trace (for NPA struct in console)
      - all_news: merged GNews articles (for report template)
    """
    results = search(entity_name, num=20)
    track("serpapi", entity_name)

    serp_block = "\n".join(
        f"{r['position']}. {r['title']}\n   {r['link']}\n   {r['snippet']}"
        for r in results
    )

    urls = _select_urls(results)
    articles = []
    for url in urls:
        raw = scrape(url)
        track("firecrawl", entity_name)
        if raw:
            cleaned = _clean(raw)[:MAX_ARTICLE_CHARS]
            articles.append(f"URL: {url}\n\n{cleaned}")

    article_context = "\n\n---\n\n".join(articles) if articles else "No articles extracted."

    news = fetch_news(entity_name)
    track("gnews", entity_name)
    expansion = expand_entity(entity_name, results, debug=False)
    expansion_context = format_expansion_context(expansion)

    # Semantic GNews enrichment — tries multiple query strategies
    # to maximize article recall without heavy SERPAPI loop.
    expanded_news = []
    seen_urls = {a.get("url", "") for a in news if a.get("url")}

    def _try_gnews(query: str) -> None:
        """Fetch GNews for query, add unseen articles to expanded_news."""
        try:
            track("gnews", entity_name)
            for a in fetch_news(query) or []:
                url = a.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    expanded_news.append(a)
        except Exception:
            pass

    # 1. Name variations (first+last, short forms)
    for variation in expansion.get("name_variations", [])[:2]:
        _try_gnews(variation)

    # 2. Top associations regardless of risk level (max 4)
    for assoc in expansion["associations"][:4]:
        _try_gnews(assoc["entity"])

    # 3. Contextual compound query: name + top association
    if expansion["associations"]:
        top = expansion["associations"][0]["entity"]
        tokens = entity_name.split()
        short_name = f"{tokens[0]} {tokens[-1]}" if len(tokens) >= 2 else entity_name
        _try_gnews(f"{short_name} {top}")

    # 4. GNews ativo para domínios de alta autoridade da SERP
    # ── Se Metrópoles, CNN Brasil, Folha aparecem na SERP mas não no GNews,
    #    busca ativamente por "[domínio] entidade" para garantir cobertura real.
    _serp_high_auth_domains = []
    _seen_gnews_domains = {
        urlparse(a.get("url", "")).netloc.replace("www.", "")
        for a in news + expanded_news
        if a.get("url")
    }
    for _r in results:
        _domain = urlparse(_r.get("link", "")).netloc.replace("www.", "")
        if not _domain:
            continue
        if classify_domain(_domain) not in _NEWS_DOMAIN_TYPES:
            continue
        if domain_authority(_domain) < _SERP_GNEWS_MIN_AUTHORITY:
            continue
        if _domain in _seen_gnews_domains:
            continue
        if _domain not in _serp_high_auth_domains:
            _serp_high_auth_domains.append(_domain)
        if len(_serp_high_auth_domains) >= _SERP_GNEWS_MAX_DOMAINS:
            break

    tokens = entity_name.split()
    short_name = f"{tokens[0]} {tokens[-1]}" if len(tokens) >= 2 else entity_name
    for _domain in _serp_high_auth_domains:
        # Busca pelo nome da entidade + nome do portal (sem TLD)
        _site_short = _domain.split(".")[0]  # "metropoles" de "metropoles.com"
        logger.info(f"GNews ativo para domínio SERP de alta autoridade: {_domain}")
        _try_gnews(f"{short_name} {_site_short}")

    all_news = news + expanded_news
    narrative_pressure = _build_npa(all_news, results)

    prompt_template = (PROMPTS_DIR / "reputation_analysis.txt").read_text(encoding="utf-8")
    prompt = prompt_template.format(
        entity_name=entity_name,
        country=country,
        industry=industry,
        serp_results=serp_block,
        article_context=article_context,
        narrative_pressure=narrative_pressure,
        expansion_context=expansion_context,
    )

    response = call_openrouter(prompt)
    usage = response.get("usage", {})
    track("openrouter", entity_name,
          tokens_input=usage.get("prompt_tokens", 0),
          tokens_output=usage.get("completion_tokens", 0))
    raw = response["choices"][0]["message"]["content"]

    save_snapshot(entity_name, results, all_news, expansion["associations"])
    _capture_serp_screenshot(entity_name, results)

    # ── Post-Audit Pipeline — geração automática por threat level ─────────
    # Determina threat level a partir do snapshot recém-salvo
    try:
        from services.snapshot_service import get_latest_snapshot
        from services.post_audit_pipeline import run_post_audit_pipeline
        import re as _re
        slug = _re.sub(r"\s+", "_", entity_name.lower().strip())
        slug = _re.sub(r"[^\w]", "", slug)
        snap = get_latest_snapshot(slug)
        if snap:
            threat = snap.get("threat_level", "LOW")
            if not threat:
                # fallback: inferir do texto da análise
                text_lower = _sanitize(raw).lower()
                if any(w in text_lower for w in ["criminal", "prisão", "condenação", "fraude"]):
                    threat = "CRITICAL"
                elif any(w in text_lower for w in ["investigação", "processo", "escândalo"]):
                    threat = "HIGH"
                elif any(w in text_lower for w in ["crise", "queda", "negativo"]):
                    threat = "MEDIUM"
                else:
                    threat = "LOW"
            run_post_audit_pipeline(
                entity_name=entity_name,
                threat_level=threat,
                slug=slug,
                async_mode=True,  # não bloqueia o request HTTP
            )
    except Exception as _e:
        import logging as _logging
        _logging.getLogger("councilia.audit").warning(f"Pipeline pós-audit não iniciado: {_e}")

    return {
        "text": _sanitize(raw),
        "all_news": all_news,
        "serp": results,
    }
