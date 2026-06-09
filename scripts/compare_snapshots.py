"""
Compare two SERP snapshots to measure reputation movement.
Usage: python scripts/compare_snapshots.py

Edit OLD_PATH and NEW_PATH to point to real snapshot files.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

import json
from services.snapshot_service import compare_snapshots

# ── Edit these paths ────────────────────────────────────────────
OLD_PATH = "snapshots/thiago_nigro/2026-05-16.json"
NEW_PATH  = "snapshots/thiago_nigro/2026-05-17.json"
# ────────────────────────────────────────────────────────────────

result = compare_snapshots(OLD_PATH, NEW_PATH)

print("=" * 60)
print(f"NARRATIVE MOVEMENT REPORT")
print(f"Period: {result['period']['from']}  →  {result['period']['to']}")
print("=" * 60)

print(f"\nNegative Displacement:     {result['negative_displacement']:+d}  (positive = improvement)")
print(f"Controlled Asset Growth:   {result['asset_penetration_growth']:+d}")
print(f"Narrative Share Change:    {result['narrative_share_change_pp']:+.1f} pp")
print(f"Page 1 Negative Ratio Δ:  {result['page_1_negative_ratio_delta']:+.1%}")
print(f"Top 3 Negative Δ:         {result['top_3_negative_delta']:+d}")

rm = result["ranking_movement"]

if rm["moved_up"]:
    print("\nMoved Up:")
    for d in rm["moved_up"]:
        print(f"  ↑  {d['domain']}  #{d['from']} → #{d['to']}")

if rm["moved_down"]:
    print("\nMoved Down:")
    for d in rm["moved_down"]:
        print(f"  ↓  {d['domain']}  #{d['from']} → #{d['to']}")

if rm["entered"]:
    print("\nEntered Top 10:")
    for d in rm["entered"]:
        print(f"  +  {d['domain']}  at #{d['position']}")

if rm["exited"]:
    print("\nExited Top 10:")
    for d in rm["exited"]:
        print(f"  -  {d['domain']}  was at #{d['last_position']}")

if rm["new_negative_entrants"]:
    print("\n⚠  New Negative Entrants:")
    for d in rm["new_negative_entrants"]:
        print(f"  !  {d['domain']}  at #{d['position']}")
else:
    print("\nNo new negative entrants.")

print("\n" + "=" * 60)
