"""
Quick smoke test for the SerpAPI integration.
Usage: python scripts/test_serpapi.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

import json
from services.serpapi_service import search

results = search("Thiago Nigro investidor")
print(json.dumps(results, indent=2, ensure_ascii=False))
