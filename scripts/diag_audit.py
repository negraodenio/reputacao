"""
Diagnóstico cirúrgico: captura o output RAW do LLM e mostra
exatamente o que está sendo retornado antes do parser.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

ENTITY  = sys.argv[1] if len(sys.argv) > 1 else "Daniel Bueno Vorcaro"
COUNTRY = "Brazil"
INDUSTRY = "Finance"

print(f"Entidade: {ENTITY}")
print("=" * 70)

# ── 1. SERP ────────────────────────────────────────────────────────
from services.serpapi_service import search
serp = search(ENTITY)
print(f"[SERP] {len(serp)} resultados")
for r in serp[:5]:
    print(f"  #{r['position']} {r['title'][:70]}")

# ── 2. GNews ───────────────────────────────────────────────────────
from services.gnews_service import fetch_news
news = fetch_news(ENTITY)
print(f"\n[GNews] {len(news)} artigos (nome exato)")

# ── 3. Expansion ───────────────────────────────────────────────────
from services.expansion_service import expand_entity, format_expansion_context
expansion = expand_entity(ENTITY, serp, debug=False)
print(f"\n[Expansion] {len(expansion['associations'])} associações descobertas")
for a in expansion["associations"][:4]:
    print(f"  {a['entity']:35s} risco={a['risk']:8s} freq={a['frequency']}")

# ── 4. GNews para associações CRITICAL/HIGH ────────────────────────
top_assocs = [a["entity"] for a in expansion["associations"][:3]
              if a["risk"] in ("CRITICAL", "HIGH")]
print(f"\n[GNews Expandido] buscando {len(top_assocs)} entidades: {top_assocs}")
expanded = []
seen = {a.get("url","") for a in news}
for name in top_assocs:
    arts = fetch_news(name) or []
    new_arts = [a for a in arts if a.get("url","") not in seen]
    for a in new_arts:
        seen.add(a.get("url",""))
        expanded.append(a)
    print(f"  '{name}' → {len(arts)} total, {len(new_arts)} novos")

all_news = news + expanded
print(f"\n[NPA Total] {len(all_news)} artigos para o NPA")

# ── 5. Prompt montado ──────────────────────────────────────────────
from pathlib import Path
from services.audit_service import _build_npa, _select_urls, _clean, MAX_ARTICLE_CHARS
from services.firecrawl_service import scrape

urls = _select_urls(serp)
articles = []
for url in urls:
    raw = scrape(url)
    if raw:
        articles.append(f"URL: {url}\n\n{_clean(raw)[:MAX_ARTICLE_CHARS]}")

article_context  = "\n\n---\n\n".join(articles) if articles else "No articles extracted."
narrative_pressure = _build_npa(all_news)
expansion_context  = format_expansion_context(expansion)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
prompt_template = (PROMPTS_DIR / "reputation_analysis.txt").read_text(encoding="utf-8")
prompt = prompt_template.format(
    entity_name=ENTITY, country=COUNTRY, industry=INDUSTRY,
    serp_results="\n".join(f"{r['position']}. {r['title']}\n   {r['link']}\n   {r['snippet']}" for r in serp),
    article_context=article_context,
    narrative_pressure=narrative_pressure,
    expansion_context=expansion_context,
)
print(f"\n[Prompt] {len(prompt)} chars, {len(prompt.split())} words")
print(f"[NPA no prompt]:\n{narrative_pressure}")

# ── 6. LLM raw output ─────────────────────────────────────────────
print("\n[LLM] chamando OpenRouter...")
from services.openrouter_service import call_openrouter
response = call_openrouter(prompt)
raw = response["choices"][0]["message"]["content"]

print(f"\n[LLM RAW OUTPUT] {len(raw)} chars")
print("─" * 70)
print(raw[:3000])
print("─" * 70)
if len(raw) > 3000:
    print(f"... (+{len(raw)-3000} chars truncados)")

# ── 7. Parser ──────────────────────────────────────────────────────
import re
SECTION_PATTERNS = [
    ("reputation_summary",      r"1\.\s+SUM[ÁA]RIO EXECUTIVO"),
    ("negative_signals",        r"2\.\s+SINAIS NEGATIVOS"),
    ("positive_assets",         r"3\.\s+ATIVOS POSITIVOS"),
    ("narrative_analysis",      r"4\.\s+AN[ÁA]LISE NARRATIVA"),
    ("npa_interpretation",      r"5\.\s+INTERPRETA[CÇ][AÃ]O DA PRESS[ÃA]O NARRATIVA"),
    ("discovered_associations", r"6\.\s+ASSOCIA[CÇ][ÕO]ES DESCOBERTAS"),
    ("suggested_positioning",   r"7\.\s+POSICIONAMENTO RECOMENDADO"),
]
print("\n[Parser] Seções encontradas no raw output:")
for key, pattern in SECTION_PATTERNS:
    m = re.search(pattern, raw, re.IGNORECASE)
    status = f"ENCONTRADA na pos {m.start()}" if m else "NÃO ENCONTRADA"
    print(f"  {key:30s} → {status}")
