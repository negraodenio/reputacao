import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import os
if os.environ.get("VERCEL"):
    COST_LOG = Path("/tmp/costs/cost_log.json")
else:
    COST_LOG = Path(__file__).parent.parent / "costs" / "cost_log.json"

ESTIMATED_COSTS = {
    "serpapi":           0.01,
    "gnews":             0.0,
    "firecrawl":         0.005,
    "openrouter_input":  0.000003,
    "openrouter_output": 0.000015,
}


def _ensure_log():
    COST_LOG.parent.mkdir(parents=True, exist_ok=True)
    if not COST_LOG.exists():
        COST_LOG.write_text("[]", encoding="utf-8")


def _load_log() -> list:
    _ensure_log()
    try:
        return json.loads(COST_LOG.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return []


def _atomic_write_log(entries: list) -> None:
    """Escrita atômica do log de custos — sem risco de corrupção."""
    COST_LOG.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(entries, indent=2, ensure_ascii=False)
    fd, tmp = tempfile.mkstemp(dir=COST_LOG.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, COST_LOG)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def track(service: str, entity: str, tokens_input: int = 0, tokens_output: int = 0):
    cost = 0.0
    if service == "openrouter":
        cost = (tokens_input * ESTIMATED_COSTS["openrouter_input"]
                + tokens_output * ESTIMATED_COSTS["openrouter_output"])
    else:
        cost = ESTIMATED_COSTS.get(service, 0)
    entry = {
        "entity":        entity,
        "service":       service,
        "cost":          round(cost, 6),
        "tokens_input":  tokens_input,
        "tokens_output": tokens_output,
        "timestamp":     datetime.now(timezone.utc).isoformat(),
    }
    log = _load_log()
    log.append(entry)
    _atomic_write_log(log)


def get_costs(entity: str | None = None, last_n: int = 0) -> dict:
    _ensure_log()
    log = _load_log()
    if entity:
        log = [e for e in log if e["entity"] == entity]
    if last_n > 0:
        log = log[-last_n:]
    total = round(sum(e["cost"] for e in log), 4)
    by_service = {}
    for e in log:
        s = e["service"]
        by_service[s] = round(by_service.get(s, 0) + e["cost"], 4)
    return {
        "entries":     log[-50:],
        "total_cost":  total,
        "by_service":  by_service,
        "count":       len(log),
    }


def get_latest_audit_cost(entity: str) -> dict:
    """Return cost breakdown for the most recent audit of an entity."""
    _ensure_log()
    log = _load_log()
    entity_entries = [e for e in log if e["entity"] == entity]
    if not entity_entries:
        return {"total": 0, "breakdown": {}, "tokens": 0}
    last = entity_entries[-1]["timestamp"]
    last_dt = datetime.fromisoformat(last)
    batch = [e for e in entity_entries
             if abs((datetime.fromisoformat(e["timestamp"]) - last_dt).total_seconds()) < 300]
    total = round(sum(e["cost"] for e in batch), 4)
    breakdown = {}
    tokens = 0
    for e in batch:
        s = e["service"]
        breakdown[s] = round(breakdown.get(s, 0) + e["cost"], 4)
        tokens += e.get("tokens_input", 0) + e.get("tokens_output", 0)
    return {"total": total, "breakdown": breakdown, "tokens": tokens}
