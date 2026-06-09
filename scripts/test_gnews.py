import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")
from services.gnews_service import fetch_news

queries = [
    "Daniel Bueno Vorcaro",
    "Daniel Vorcaro",
    "Banco Master",
    "Daniel Vorcaro Banco Master",
    "Tiago Schiettini Batista",
    "Antonio Carlos Camilo Antunes",
    "Thiago Nigro",
]
for q in queries:
    results = fetch_news(q) or []
    print(f"{len(results):3d}  {q!r}")
    for a in results[:2]:
        src = a.get("source", "")
        title = a.get("title", "")[:55]
        print(f"      {src:22s} {title}")
