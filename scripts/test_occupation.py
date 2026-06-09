import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from services.occupation_service import generate_occupation, parse_occupation_sections

ENTITY = "Daniel Bueno Vorcaro"
print(f"Testando: {ENTITY} (CRITICAL)")
print("=" * 60)

r = generate_occupation(ENTITY, "CRITICAL", "HIGH", "mainstream", "metropoles.com, g1.globo.com")
s = parse_occupation_sections(r["text"])

print(f"Texto gerado: {len(r['text'])} chars")
print(f"Asset table:  {len(r['asset_table'])} ativos")
print(f"SERP:         {len(r['serp_results'])} resultados")
print()

for k, v in s.items():
    print(f"  {k:22s} {len(v):4d} chars")

print()
print("--- PRIMEIROS 600 CHARS ---")
print(r["text"][:600])
