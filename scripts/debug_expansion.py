"""
Semantic Expansion Validation Mode.
Debug tool for validating the semantic search expansion pipeline.

Usage:
    python scripts/debug_expansion.py
    python scripts/debug_expansion.py "Thiago Nigro"
    python scripts/debug_expansion.py "Tiago Schiettini Batista"
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

ENTITY = sys.argv[1] if len(sys.argv) > 1 else "Tiago Schiettini Batista"

print("=" * 72)
print("VALIDACAO DE EXPANSAO SEMANTICA — DEBUG MODE")
print("=" * 72)
print(f"Entidade: {ENTITY}")
print()

# ── 1. Run standard SERP + expansion ──────────────────────────
print("[1/6] Buscando SERP padrao...")
from services.serpapi_service import search
serp = search(ENTITY)
print(f"       SERPAPI: {len(serp)} resultados para nome exato\n")

# ── 2. Expand with debug ──────────────────────────────────────
print("[2/6] Executando expansao semantica com DEBUG=True...")
from services.expansion_service import expand_entity, format_expansion_context
expansion = expand_entity(ENTITY, serp, debug=True)
print(f"       Associacoes: {len(expansion['associations'])}")
print(f"       Variacoes de nome: {expansion['name_variations']}")
print(f"       Queries de expansao: {len(expansion['expansion_queries'])}")
print()

# ── 3. Debug trace ────────────────────────────────────────────
dbg = expansion.get("debug")
if not dbg:
    print("ERRO: debug mode nao retornou trace. Verifique expand_entity(debug=True).")
    sys.exit(1)

trace = dbg["query_trace"]
print(f"[3/6] EXECUCAO DE QUERIES — {len(trace)} queries executadas")
print(f"       {dbg['summary']['total_gnews_articles']} artigos GNews unicos apos dedup")
print(f"       {dbg['summary']['total_serp_results']} resultados SERP unicos apos dedup")
print(f"       {dbg['summary']['total_discarded']} entradas descartadas na dedup")
print()

# ── 4. Query effectiveness ────────────────────────────────────
print("[4/6] EFETIVIDADE POR QUERY")
print(f"   {'ENGINE':8s} {'KEPT':4s} {'DISCARD':7s} {'SCORE':10s}  QUERY")
print(f"   {'-'*8} {'-'*4} {'-'*7} {'-'*10}  {'-'*50}")
for entry in trace:
    eng = entry["engine"]
    kept = str(entry["kept"])
    disc = str(entry["discarded"])
    eff = entry.get("effectiveness", "?")
    q = entry["query"]
    print(f"   {eng:8s} {kept:>4s} {disc:>7s} {eff:10s}  {q}")
print()

# ── 5. Source overlap map ─────────────────────────────────────
print("[5/6] MAPA DE SOBREPOSICAO DE FONTES (dominios por query)")
overlap = dbg.get("source_overlap", {})
for query, domains in list(overlap.items())[:10]:
    doms_str = ", ".join(domains[:5]) if domains else "(sem dominios)"
    print(f"   {query[:45]:45s} → {doms_str}")
print()

# ── 6. NPA source origin ──────────────────────────────────────
print("[6/6] ORIGEM DOS ARTIGOS DO NPA")
origin = dbg.get("npa_source_origin", {})
total_origin = sum(origin.values())
if total_origin > 0:
    for key, count in origin.items():
        pct = round(count / total_origin * 100, 1)
        key_label = key.replace("_", " ").title()
        print(f"   {key_label:35s}: {count:3d} artigos ({pct}%)")
    print(f"   {'Total':35s}: {total_origin:3d} artigos")
else:
    print("   Nenhum artigo encontrado por nenhuma origem")
print()

# ── Summary ────────────────────────────────────────────────────
s = dbg["summary"]
print("=" * 72)
print("RESUMO DA VALIDACAO")
print("=" * 72)
print(f"  Queries geradas:             {len(expansion['expansion_queries'])}")
print(f"  Queries executadas:          {s['total_queries_executed']}")
print(f"  Artigos GNews (brutos):      {sum(e['total_found'] for e in trace if e['engine']=='gnews')}")
print(f"  Artigos GNews (unicos):      {s['gnews_unique_urls']}")
print(f"  Resultados SERP (unicos):    {s['serp_unique_urls']}")
print(f"  Descartados (dedup):         {s['total_discarded']}")
print()

# Alert if NPA would have been empty before
if total_origin == 0:
    print("  ALERTA: NPA ficaria VAZIO — nenhum artigo encontrado por nenhuma query expandida")
elif origin.get("from_exact_entity", 0) == 0 and total_origin > 0:
    print("  ALERTA: NPA exato = 0, mas expansao encontrou artigos — BUG ANTIGO CONFIRMADO")
    print(f"          {total_origin} artigos estavam sendo ignorados pelo GNews exato")
else:
    print(f"  STATUS: NPA com {total_origin} artigos — pipeline semantico operacional")
print("=" * 72)

# Save full trace to JSON for inspection
out_path = os.path.join(os.path.dirname(__file__), "..", "outputs", "debug_expansion_trace.json")
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({
        "entity": ENTITY,
        "summary": s,
        "npa_origin": origin,
        "query_trace": trace,
        "source_overlap": {k: list(v) for k, v in overlap.items()},
        "associations": expansion["associations"],
        "expansion_queries": expansion["expansion_queries"],
        "name_variations": expansion["name_variations"],
    }, f, indent=2, ensure_ascii=False)

print(f"\nTrace completo salvo em: outputs/debug_expansion_trace.json")
