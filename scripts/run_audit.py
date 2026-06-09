"""
Runs a minimal reputation audit for a hardcoded entity.
Usage: python scripts/run_audit.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from services.audit_service import run_audit

ENTITY = "Thiago Nigro"

print(f"Running reputation audit for: {ENTITY}\n")
print("-" * 60)
result = run_audit(ENTITY)
text = result["text"] if isinstance(result, dict) else result
print(text)
