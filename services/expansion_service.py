"""
Intelligent Heuristic Search Expansion
Depth-1 contextual entity discovery from SERP + Firecrawl.
Supports debug mode with automatic query execution against SERPAPI and GNews.

Max recursion depth: 1
Max expansion queries: 20
Max crawled articles: 3
Max discovered entities: 8
"""
import re
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from services.firecrawl_service import scrape
from services.constants import PRIORITY_DOMAINS, EXCLUDED_DOMAINS

import os
if os.environ.get("VERCEL"):
    CACHE_DIR = Path("/tmp/cache")
else:
    CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_TTL_HOURS = 12

# ── Constants ────────────────────────────────────────────────────

MAX_QUERIES        = 20
MAX_ARTICLES       = 3
MAX_ENTITIES       = 8
RISK_TERMS         = ["investigação", "fraude", "processo", "denúncia", "corrupção",
                      "inquérito", "CPI", "operação", "preso", "condenado",
                      "escândalo", "desvio", "lavagem", "crime", "indiciado"]
VERTICAL_SITES     = [
    "metropoles.com", "jusbrasil.com.br", "escavador.com",
    "youtube.com", "linkedin.com/in", "conjur.com.br",
]
GEO_STOPLIST       = {
    "brasil", "são paulo", "rio de janeiro", "brasília", "minas gerais",
    "governo", "federal", "república", "ministério", "secretaria",
    "prefeitura", "câmara", "senado", "tribunal", "supremo",
    "nacional", "estadual", "municipal", "partido", "presidente",
    "diretor", "secretário", "ministro", "deputado", "senador",
}
LEGAL_TERMS        = {"processo", "sentença", "ação", "réu", "acusado",
                      "investigado", "indiciado", "inquérito", "mandado"}
INVESTIGATIVE_TERMS = {"fraude", "corrupção", "desvio", "lavagem", "esquema",
                       "denúncia", "escândalo", "operação", "CPI"}
MAINSTREAM_DOMAINS = {"metropoles.com", "g1.globo.com", "uol.com.br",
                      "folha.uol.com.br", "estadao.com.br", "cnnbrasil.com.br"}

MAX_EXECUTION_QUERIES = 10  # limit for debug execution to control cost/time


# ── Association type classifier ──────────────────────────────────

def _classify_type(entity: str) -> str:
    lower = entity.lower()
    if any(t in lower for t in ["ltda", "s.a.", "grupo", "bank", "capital",
                                 "fund", "holding", "invest", "corp", "tech"]):
        return "company"
    if any(t in lower for t in ["juiz", "promotor", "delegado", "polícia",
                                 "tribunal", "pf", "mpf", "cvm", "anatel"]):
        return "legal"
    if any(t in lower for t in ["jornal", "tv", "mídia", "imprensa",
                                 "portal", "notícia", "blog", "colunista"]):
        return "media"
    if any(t in lower for t in ["partido", "candidato", "deputado", "senador",
                                 "ministro", "vereador", "prefeito", "governador"]):
        return "political"
    if any(t in lower for t in ["instituto", "fundação", "conselho", "autarquia",
                                 "associação", "câmara", "crf", "cfm"]):
        return "institutional"
    return "unknown"


# ── Association risk classifier ──────────────────────────────────

def _classify_risk(entity: str, frequency: int,
                   source_domains: set, context_text: str) -> str:
    lower_ctx = context_text.lower()
    entity_lower = entity.lower()
    windows = []
    idx = 0
    while True:
        pos = lower_ctx.find(entity_lower, idx)
        if pos == -1:
            break
        windows.append(lower_ctx[max(0, pos - 100):pos + 100])
        idx = pos + 1
    scoped = " ".join(windows) if windows else lower_ctx[:500]

    has_legal        = any(t in scoped for t in LEGAL_TERMS)
    has_investigative = any(t in scoped for t in INVESTIGATIVE_TERMS)
    has_mainstream   = bool(source_domains & MAINSTREAM_DOMAINS)

    score = 0
    if has_legal:         score += 3
    if has_investigative: score += 3
    if has_mainstream:    score += 2
    if frequency >= 5:    score += 2
    elif frequency >= 3:  score += 1

    if score >= 7: return "CRITICAL"
    if score >= 4: return "HIGH"
    if score >= 2: return "MEDIUM"
    return "LOW"


# ── Name variations ──────────────────────────────────────────────

def _name_variations(entity: str) -> list[str]:
    # Include tokens of any length — single-char particles (e.g. "e", "d'")
    # are filtered by the seen-set, not by length
    tokens = [t for t in entity.strip().split() if t and not t.lower() in
              {"de", "da", "do", "dos", "das", "e", "van", "von", "di", "del"}]
    variations = []
    if len(tokens) == 2:
        variations.append(tokens[0])   # primeiro nome
        variations.append(tokens[1])   # sobrenome
    elif len(tokens) >= 3:
        variations.append(f"{tokens[0]} {tokens[-1]}")   # primeiro + último
        variations.append(f"{tokens[0]} {tokens[1]}")    # primeiro + segundo
        variations.append(f"{tokens[1]} {tokens[2]}")    # segundo + terceiro
    seen = {entity.lower()}
    return [v for v in variations if v.lower() not in seen][:4]


# ── Entity extraction from article text ─────────────────────────

def _extract_entities(text: str, entity_name: str) -> list[str]:
    proper = re.findall(
        r'\b[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÚÜÇ][a-záàâãéèêíïóôõúüç]+(?:\s[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÚÜÇ][a-záàâãéèêíïóôõúüç]+){1,3}\b',
        text
    )
    quoted = re.findall(r'["\u201c\u201d]([^"\u201c\u201d]{5,40})["\u201c\u201d]', text)

    FRAG_STOPWORDS = {"do", "da", "de", "dos", "das", "no", "na", "em",
                      "um", "uma", "os", "as", "logo", "novo", "sua", "seu"}

    candidates = proper + quoted
    name_tokens = set(entity_name.lower().split())

    seen, result = set(), []
    for c in candidates:
        cl = c.lower().strip()
        first_word = cl.split()[0] if cl.split() else ""
        if cl in seen:
            continue
        seen.add(cl)
        if cl in GEO_STOPLIST:
            continue
        if first_word in FRAG_STOPWORDS:
            continue
        if all(t in name_tokens for t in cl.split()):
            continue
        if len(cl) < 5:
            continue
        tokens = cl.split()
        if any(len(t) < 3 for t in tokens):
            continue
        result.append(c.strip())

    return result[:MAX_ENTITIES * 2]


# ── Vertical query builder ───────────────────────────────────────

def _vertical_queries(entities: list[str]) -> list[str]:
    queries = []
    for entity in entities[:3]:
        for site in VERTICAL_SITES[:3]:
            queries.append(f'site:{site} "{entity}"')
    return queries


# ── Risk query builder ───────────────────────────────────────────

def _risk_queries(variations: list[str]) -> list[str]:
    queries = []
    for v in variations[:3]:
        for term in RISK_TERMS[:3]:
            queries.append(f'"{v}" {term}')
    return queries


# ── Semantic query execution ──────────────────────────────────────

def _execute_semantic_queries(expansion: dict) -> dict:
    """
    Executes expansion queries against SERPAPI and GNews.
    GNews receives only plain-text queries (no site: syntax — unsupported).
    SERPAPI receives all queries including site: directives.
    Returns full execution trace with dedup, effectiveness, source overlap,
    and NPA source origin for observability.
    """
    from services.gnews_service import fetch_news
    from services.serpapi_service import search
    from urllib.parse import urlparse

    entity_name     = expansion.get("_entity_name", "")
    queries_to_run  = expansion["expansion_queries"][:MAX_EXECUTION_QUERIES]

    # Base queries: exact entity + name variations + top discovered associations
    base_queries = (
        [entity_name]
        + expansion["name_variations"][:2]
        + [a["entity"] for a in expansion["associations"][:3]]
    )

    query_trace      = []
    all_gnews        = []
    all_serp         = []
    seen_gnews_urls  = set()
    seen_serp_urls   = set()
    total_discarded  = 0
    gnews_per_query  = {}

    # ── GNews: base queries + plain expansion queries only ────────
    # site: syntax is silently ignored by GNews and yields false positives.
    gnews_queries = base_queries + [
        q for q in queries_to_run if not q.startswith("site:")
    ]

    for q in gnews_queries:
        try:
            articles = fetch_news(q) or []
            kept, discarded = [], []
            domains_in_query = set()

            for a in articles:
                url   = a.get("url", "")
                title = a.get("title", "")
                d     = urlparse(url).netloc.replace("www.", "") if url else ""
                if d:
                    domains_in_query.add(d)
                if not url:
                    continue
                if url in seen_gnews_urls:
                    discarded.append({"url": url, "reason": "duplicate URL", "title": title})
                    continue
                seen_gnews_urls.add(url)
                kept.append(a)
                all_gnews.append(a)

            total_discarded += len(discarded)
            gnews_per_query[q] = {"articles": kept, "domains": sorted(domains_in_query)}

            query_trace.append({
                "query":                q,
                "engine":               "gnews",
                "status":               "completed",
                "total_found":          len(articles),
                "kept":                 len(kept),
                "discarded":            len(discarded),
                "discard_details":      discarded[:3],
                "articles_kept_titles": [a.get("title", "")[:60] for a in kept[:3]],
                "effectiveness":        "HIGH" if len(articles) >= 5 else "MEDIUM" if len(articles) >= 2 else "LOW",
            })
        except Exception as e:
            gnews_per_query[q] = {"articles": [], "domains": []}
            query_trace.append({
                "query": q, "engine": "gnews",
                "status": f"error: {str(e)[:80]}",
                "total_found": 0, "kept": 0, "discarded": 0,
                "effectiveness": "ERROR",
            })

    # ── SERPAPI: all expansion queries (supports site: syntax) ────
    for q in queries_to_run:
        try:
            results = search(q) or []
            kept, discarded = [], []
            for r in results:
                url = r.get("link", "")
                if not url:
                    continue
                if url in seen_serp_urls:
                    discarded.append({"url": url, "reason": "duplicate URL"})
                    continue
                seen_serp_urls.add(url)
                kept.append(r)
                all_serp.append(r)

            total_discarded += len(discarded)
            query_trace.append({
                "query":           q,
                "engine":          "serpapi",
                "status":          "completed",
                "total_found":     len(results),
                "kept":            len(kept),
                "discarded":       len(discarded),
                "discard_details": discarded[:3],
                "effectiveness":   "HIGH" if len(results) >= 8 else "MEDIUM" if len(results) >= 3 else "LOW",
            })
        except Exception as e:
            query_trace.append({
                "query": q, "engine": "serpapi",
                "status": f"error: {str(e)[:80]}",
                "total_found": 0, "kept": 0, "discarded": 0,
                "effectiveness": "ERROR",
            })

    # ── Source overlap map (from stored domain data, no re-fetch) ─
    source_overlap = {
        q: data["domains"]
        for q, data in gnews_per_query.items()
        if data["domains"]
    }

    # ── NPA source origin ─────────────────────────────────────────
    base_entity_lower = entity_name.lower()
    variation_lowers  = [v.lower() for v in expansion["name_variations"]]
    assoc_lowers      = [a["entity"].lower() for a in expansion["associations"][:3]]

    npa_origin = {
        "from_exact_entity":       0,
        "from_name_variations":    0,
        "from_associated_entities": 0,
        "from_expansion_queries":  0,
    }
    for entry in query_trace:
        if entry["engine"] != "gnews" or entry["status"] != "completed":
            continue
        q_lower = entry["query"].lower()
        kept    = entry["kept"]
        if q_lower == base_entity_lower or (base_entity_lower in q_lower and '"' not in q_lower):
            npa_origin["from_exact_entity"] += kept
        elif any(v in q_lower for v in variation_lowers):
            npa_origin["from_name_variations"] += kept
        elif any(a in q_lower for a in assoc_lowers):
            npa_origin["from_associated_entities"] += kept
        else:
            npa_origin["from_expansion_queries"] += kept

    # ── Article → query trace ─────────────────────────────────────
    article_query_trace = [
        {"query": entry["query"], "title": t, "engine": "gnews"}
        for entry in query_trace
        if entry["engine"] == "gnews" and entry.get("articles_kept_titles")
        for t in entry["articles_kept_titles"]
    ]

    return {
        "query_trace":        query_trace,
        "gnews_articles":     all_gnews,
        "serp_results":       all_serp,
        "source_overlap":     source_overlap,
        "npa_source_origin":  npa_origin,
        "article_query_trace": article_query_trace,
        "summary": {
            "total_queries_executed": len(query_trace),
            "total_gnews_articles":   len(all_gnews),
            "total_serp_results":     len(all_serp),
            "total_discarded":        total_discarded,
            "gnews_unique_urls":      len(seen_gnews_urls),
            "serp_unique_urls":       len(seen_serp_urls),
        },
    }


def _cache_get(key: str) -> dict | None:
    """Return cached expansion result if fresh, else None."""
    path = CACHE_DIR / f"{key}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        cached_at = datetime.fromisoformat(data["_cached_at"])
        age = (datetime.now(timezone.utc) - cached_at).total_seconds()
        if age < CACHE_TTL_HOURS * 3600:
            return data
    except Exception:
        pass
    return None


def _cache_set(key: str, data: dict):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data["_cached_at"] = datetime.now(timezone.utc).isoformat()
    path = CACHE_DIR / f"{key}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def expand_entity(entity_name: str, serp_results: list[dict], debug: bool = False) -> dict:
    """
    Depth-1 contextual entity discovery.
    Results are cached for CACHE_TTL_HOURS hours.
    When debug=True, also executes expansion queries against SERPAPI and GNews
    and returns full execution trace for NPA validation.
    PRIORITY_DOMAINS and EXCLUDED_DOMAINS are shared from services.constants.
    """
    slug = entity_name.lower().strip().replace(" ", "_")
    slug = re.sub(r"[^\w]", "", slug)

    cached = _cache_get(slug) if not debug else None
    if cached:
        cached["_cached"] = True
        return cached
    # Select up to MAX_ARTICLES URLs to scrape
    priority, fallback = [], []
    for r in serp_results:
        link = r.get("link", "")
        if any(d in link for d in EXCLUDED_DOMAINS):
            continue
        if any(d in link for d in PRIORITY_DOMAINS):
            priority.append(link)
        else:
            fallback.append(link)
    urls_to_scrape = (priority + fallback)[:MAX_ARTICLES]

    # Scrape + extract entities
    all_text      = ""
    entity_freq   = Counter()
    source_map    = {}
    domain_entity = {}

    for url in urls_to_scrape:
        text = scrape(url)
        if not text:
            continue
        all_text += " " + text
        domain = re.sub(r"https?://(www\.)?", "", url).split("/")[0]
        found = _extract_entities(text, entity_name)

        for ent in found:
            entity_freq[ent] += text.lower().count(ent.lower())
            source_map.setdefault(ent, set()).add(domain)
            domain_entity.setdefault(domain, [])
            if ent not in domain_entity[domain]:
                domain_entity[domain].append(ent)

    # Build association records
    top_entities = [e for e, _ in entity_freq.most_common(MAX_ENTITIES)]
    associations = []
    for ent in top_entities:
        freq    = entity_freq[ent]
        domains = source_map.get(ent, set())
        atype   = _classify_type(ent)
        risk    = _classify_risk(ent, freq, domains, all_text)
        associations.append({
            "entity":   ent,
            "type":     atype,
            "frequency": freq,
            "domains":  sorted(domains),
            "risk":     risk,
        })

    risk_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    associations.sort(key=lambda x: (risk_order[x["risk"]], -x["frequency"]))

    source_map_clean = {
        domain: ents[:5]
        for domain, ents in domain_entity.items()
        if ents
    }

    # Build expansion queries
    variations = _name_variations(entity_name)
    discovered = [a["entity"] for a in associations[:4]]

    risk_q     = _risk_queries([entity_name] + variations)
    vertical_q = _vertical_queries([entity_name] + discovered)
    all_queries = list(dict.fromkeys(risk_q + vertical_q))[:MAX_QUERIES]

    result = {
        "associations":      associations,
        "name_variations":   variations,
        "expansion_queries": all_queries,
        "source_map":        source_map_clean,
        "articles_scraped":  len(urls_to_scrape),
        "_entity_name":      entity_name,
    }

    if debug:
        result["debug"] = _execute_semantic_queries(result)

    if not debug:
        _cache_set(slug, result)
    return result


# ── Plain text formatter for prompt injection ────────────────────

def format_expansion_context(expansion: dict) -> str:
    if not expansion["associations"]:
        return "Nenhuma entidade associada descoberta."

    lines = []
    for a in expansion["associations"]:
        domains_str = ", ".join(a["domains"]) if a["domains"] else "fonte desconhecida"
        lines.append(
            f"  {a['entity']}\n"
            f"    Tipo: {a['type']} | Frequência: {a['frequency']} | "
            f"Risco: {a['risk']} | Domínios: {domains_str}"
        )

    if expansion["source_map"]:
        lines.append("\nMapa de Fontes:")
        for domain, ents in expansion["source_map"].items():
            lines.append(f"  {domain}: {', '.join(ents[:3])}")

    return "\n".join(lines)
