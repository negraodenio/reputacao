import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")
from services.response_service import (
    _resolve_posture, _resolve_visibility, _resolve_temperature,
    _resolve_stakeholder_priority, _resolve_escalation_triggers,
    _build_redirection_map,
)

cases = [
    ("CRITICAL", "legal",      True),
    ("CRITICAL", "mainstream", False),
    ("HIGH",     "legal",      True),
    ("MEDIUM",   "blog",       False),
    ("LOW",      "mainstream", False),
]

for tl, sc, le in cases:
    p = _resolve_posture(tl, sc, le)
    v = _resolve_visibility(tl, le)
    t = _resolve_temperature(tl)
    s = _resolve_stakeholder_priority(tl, le)
    print(f"{tl:8} | {sc:12} | legal={str(le):5} | {p}")
    print(f"         vis={v} | temp={t} | {' > '.join(s)}")
    print()

themes = "fraude, investigacao, corrupção, escandalo"
redir = _build_redirection_map(themes)
print("Redirection map para temas:", themes)
print(redir)
