"""
Smoke test for the Intelligent Heuristic Search Expansion layer.
Usage: python scripts/test_expansion.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

import json
from services.serpapi_service import search
from services.expansion_service import expand_entity, format_expansion_context

ENTITY = "Thiago Nigro"

print(f"Entity: {ENTITY}")
print(f"{'=' * 60}")

print("Fetching SERP results...")
serp = search(ENTITY)
print(f"SERP results: {len(serp)}")

print("\nRunning expansion...")
expansion = expand_entity(ENTITY, serp)

print(f"\nName variations:       {expansion['name_variations']}")
print(f"Articles scraped:      {expansion['articles_scraped']}")
print(f"Associations found:    {len(expansion['associations'])}")
print(f"Expansion queries:     {len(expansion['expansion_queries'])}")

print(f"\n{'─' * 60}")
print("DISCOVERED ASSOCIATIONS:")
print(f"{'─' * 60}")
for a in expansion["associations"]:
    domains = ", ".join(a["domains"]) if a["domains"] else "unknown"
    print(f"  {a['entity']}")
    print(f"    Type: {a['type']} | Freq: {a['frequency']} | Risk: {a['risk']}")
    print(f"    Domains: {domains}")

print(f"\n{'─' * 60}")
print("SOURCE MAP:")
print(f"{'─' * 60}")
for domain, ents in expansion["source_map"].items():
    print(f"  {domain}: {', '.join(ents)}")

print(f"\n{'─' * 60}")
print("EXPANSION QUERIES (first 10):")
print(f"{'─' * 60}")
for q in expansion["expansion_queries"][:10]:
    print(f"  {q}")

print(f"\n{'─' * 60}")
print("FORMATTED CONTEXT (prompt-ready):")
print(f"{'─' * 60}")
print(format_expansion_context(expansion))
