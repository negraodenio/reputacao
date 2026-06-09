"""
Quick smoke test for the OpenRouter integration.
Usage: python scripts/test_openrouter.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from services.openrouter_service import call_openrouter

response = call_openrouter("Say hello in one sentence.")
sys.stdout.reconfigure(encoding="utf-8")
print(json.dumps(response, indent=2, ensure_ascii=False))
