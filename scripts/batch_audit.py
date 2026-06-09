"""
Batch reputation audit runner.
Runs audits sequentially for a hardcoded list of entities.
Saves each result to outputs/<slug>.txt

Usage: python scripts/batch_audit.py
"""
import sys
import os
import time
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from services.audit_service import run_audit

ENTITIES = [
    "Thiago Nigro",
    "Flavio Augusto",
    "Joel Jota",
]

OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)


def slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s]", "", slug)
    slug = re.sub(r"\s+", "_", slug)
    return slug


for i, entity in enumerate(ENTITIES):
    print(f"\n{'=' * 60}")
    print(f"Auditing: {entity}")
    print(f"{'=' * 60}\n")

    result = run_audit(entity)
    text = result["text"] if isinstance(result, dict) else result
    print(text)

    filename = f"{slugify(entity)}.txt"
    filepath = os.path.join(OUTPUTS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"REPUTATION AUDIT: {entity}\n")
        f.write(f"{'=' * 60}\n\n")
        f.write(text)

    print(f"\n[saved] outputs/{filename}")

    if i < len(ENTITIES) - 1:
        print("[waiting 3s before next audit...]")
        time.sleep(3)

print(f"\n{'=' * 60}")
print(f"Batch complete. {len(ENTITIES)} audits saved to outputs/")
print(f"{'=' * 60}")
