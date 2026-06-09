import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from services.serpapi_service import search
from services.gnews_service import fetch_news
from services.expansion_service import expand_entity

ENTITY = sys.argv[1] if len(sys.argv) > 1 else "Daniel Bueno Vorcaro"

print(f"Entidade: {ENTITY}")
print("=" * 60)

serp = search(ENTITY)
print(f"SERP: {len(serp)} resultados")

news = fetch_news(ENTITY)
print(f"GNews (exato): {len(news)} artigos")

expansion = expand_entity(ENTITY, serp, debug=False)
assocs = expansion["associations"]
variations = expansion.get("name_variations", [])
print(f"Expansao: {len(assocs)} assoc, variacoes={variations[:3]}")
print()

seen_urls = {a.get("url","") for a in news}
expanded = []

def try_gnews(q):
    arts = fetch_news(q) or []
    new = [a for a in arts if a.get("url","") not in seen_urls]
    for a in new:
        seen_urls.add(a.get("url",""))
        expanded.append(a)
    print(f"  {len(arts):3d} brutos  {len(new):3d} novos  q={q!r}")

print("Buscas GNews expandidas:")
for v in variations[:2]:
    try_gnews(v)
for a in assocs[:4]:
    try_gnews(a["entity"])
if assocs:
    tokens = ENTITY.split()
    short = f"{tokens[0]} {tokens[-1]}" if len(tokens) >= 2 else ENTITY
    try_gnews(f"{short} {assocs[0]['entity']}")

all_news = news + expanded
print(f"\nTotal all_news: {len(all_news)} artigos para o NPA")
for a in all_news[:5]:
    print(f"  {a.get('source',''):20s} {a.get('title','')[:55]}")
