"""
Verificacao completa do fluxo de auditoria.
Testa cada API individualmente e depois o fluxo completo.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

ENTITY = "Tiago Schiettini Batista"

print("=" * 70)
print(f"VERIFICACAO COMPLETA DO FLUXO — {ENTITY}")
print("=" * 70)

# ── 1. SERPAPI ──────────────────────────────────────────────
print("\n[1/8] SERPAPI — search()")
from services.serpapi_service import search
try:
    serp = search(ENTITY)
    print(f"  OK — {len(serp)} resultados encontrados")
    for r in serp[:3]:
        print(f"    #{r['position']} {r['title'][:70]}")
except Exception as e:
    print(f"  ERRO: {e}")

# ── 2. GNEWS ────────────────────────────────────────────────
print("\n[2/8] GNEWS — fetch_news()")
from services.gnews_service import fetch_news
try:
    news = fetch_news(ENTITY)
    print(f"  OK — {len(news)} artigos encontrados")
    for a in news[:3]:
        print(f"    {a.get('title','')[:70]} | {a.get('source','')}")
except Exception as e:
    print(f"  ERRO: {e}")

# ── 3. FIRECRAWL ────────────────────────────────────────────
print("\n[3/8] FIRECRAWL — scrape()")
from services.firecrawl_service import scrape
test_urls = [r.get("link","") for r in serp[:2] if r.get("link")]
if test_urls:
    for url in test_urls:
        text = scrape(url)
        status = "OK" if text else "VAZIO"
        print(f"  {status} — {len(text)} chars — {url[:60]}")
else:
    print("  Sem URLs para testar")

# ── 4. OPENROUTER ───────────────────────────────────────────
print("\n[4/8] OPENROUTER — call_openrouter() (teste rapido)")
from services.openrouter_service import call_openrouter
try:
    resp = call_openrouter("Responda apenas: 'OK'. Nao escreva mais nada.", temperature=0.1)
    content = resp["choices"][0]["message"]["content"]
    print(f"  OK — resposta: {content[:50]}")
except Exception as e:
    print(f"  ERRO: {e}")

# ── 5. EXPANSION SERVICE ────────────────────────────────────
print("\n[5/8] EXPANSION SERVICE — expand_entity()")
from services.expansion_service import expand_entity, format_expansion_context
try:
    expansion = expand_entity(ENTITY, serp)
    print(f"  OK — {len(expansion['associations'])} assoc, {len(expansion['name_variations'])} variacoes, {expansion['articles_scraped']} artigos")
    for a in expansion["associations"]:
        print(f"    {a['entity']:30s} | type={a['type']:12s} | freq={a['frequency']:3d} | risk={a['risk']}")
    if expansion["expansion_queries"]:
        print(f"  Queries geradas: {len(expansion['expansion_queries'])} (primeiras 5):")
        for q in expansion["expansion_queries"][:5]:
            print(f"    {q}")
except Exception as e:
    print(f"  ERRO: {e}")
    import traceback; traceback.print_exc()

# ── 6. EXPANSION CONTEXT FORMATADO ──────────────────────────
print("\n[6/8] FORMAT_EXPANSION_CONTEXT — prompt-ready output")
try:
    ctx = format_expansion_context(expansion)
    print(f"  OK — {len(ctx)} chars")
    print(f"  Primeiras 200 chars:")
    print(f"    {ctx[:200]}")
except Exception as e:
    print(f"  ERRO: {e}")

# ── 7. PROMPT TEMPLATE ─────────────────────────────────────
print("\n[7/8] PROMPT TEMPLATE — reputation_analysis.txt")
from pathlib import Path
prompt_path = Path(__file__).parent.parent / "prompts" / "reputation_analysis.txt"
prompt = prompt_path.read_text(encoding="utf-8")
print(f"  OK — {len(prompt)} chars")
# Check for key requirements
assert "SUMÁRIO EXECUTIVO" in prompt, "SECTION NAME ERROR: SUMÁRIO EXECUTIVO not found"
assert "ASSOCIAÇÕES DESCOBERTAS" in prompt, "SECTION NAME ERROR: ASSOCIAÇÕES DESCOBERTAS not found"
assert "português do Brasil" in prompt, "LANGUAGE ERROR: Portuguese requirement not found"
assert "{expansion_context}" in prompt, "EXPANSION CONTEXT: placeholder not found"
assert "{narrative_pressure}" in prompt, "NPA PLACEHOLDER: not found"
assert "{serp_results}" in prompt, "SERP PLACEHOLDER: not found"
print("  Todas as verificacoes do template OK")

# ── 8. SANITIZE ────────────────────────────────────────────
print("\n[8/8] SANITIZE — _sanitize() preserva PT-BR?")
from services.audit_service import _sanitize
test_text = "São Paulo — investigação de corrupção na prefeitura. Ação judicial em andamento. Pronúncia: ç, ã, õ, á, é, í, ó, ú, â, ê, ô, à, è, ì, ò, ù"
sanitized = _sanitize(test_text)
if "ç" in sanitized and "ã" in sanitized and "é" in sanitized:
    print(f"  OK — caracteres PT-BR preservados: {sanitized}")
else:
    print(f"  PROBLEMA — sanitize removeu chars PT-BR!")
    print(f"  Original: {test_text}")
    print(f"  Sanitizado: {sanitized}")

print("\n" + "=" * 70)
print("VERIFICACAO CONCLUIDA")
print("=" * 70)
