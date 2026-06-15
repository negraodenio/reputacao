import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from api.routes import reputation
from api.routes import console
from api.routes import automation
from api.routes import political

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("councilia")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicia o background monitor ao arrancar o servidor."""
    import os
    if os.environ.get("VERCEL"):
        logger.info("Executando no Vercel: background monitoring desativado.")
        yield
    else:
        from services.monitoring_engine import run_background_monitoring
        task = asyncio.create_task(run_background_monitoring())
        logger.info("Background monitoring task iniciada.")
        yield
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        logger.info("Background monitoring task encerrada.")


app = FastAPI(
    title="CouncilIA Reputation",
    description="Reputation analysis API powered by LLMs",
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(console.router)
app.include_router(reputation.router, prefix="/reputation", tags=["reputation"])
app.include_router(automation.router)
app.include_router(political.router, prefix="/political", tags=["political"])


@app.get("/health", tags=["health"])
def health_check():
    from services.monitoring_engine import get_monitored_slugs
    slugs = get_monitored_slugs()
    return {
        "status": "ok",
        "version": "0.2.0",
        "monitored_entities": len(slugs),
        "background_monitor": "active",
    }


@app.get("/status", tags=["health"])
def system_status():
    """Dashboard de saúde do sistema — última auditoria, alertas recentes, custos."""
    from services.snapshot_service import list_entities
    from services.monitoring_engine import get_monitored_slugs, get_monitor_summary
    from services.cost_tracker import get_costs
    from datetime import datetime, timezone

    entities = list_entities()
    monitored = get_monitored_slugs()
    costs = get_costs(last_n=100)

    entity_status = []
    for e in entities[:20]:
        slug = e.get("slug", "")
        mon = get_monitor_summary(slug) if slug in monitored else None
        entity_status.append({
            "entity": e.get("entity", slug),
            "slug": slug,
            "threat": e.get("latest_threat", ""),
            "latest_snapshot": e.get("latest_snapshot", ""),
            "monitoring": {
                "active": slug in monitored,
                "last_check": mon.get("last_check") if mon else None,
                "crisis_alerts_7d": mon.get("crisis_alerts_7d", 0) if mon else 0,
            } if mon else {"active": False},
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entities_total": len(entities),
        "entities_monitored": len(monitored),
        "cost_week": costs.get("total_cost", 0),
        "entities": entity_status,
    }


@app.get("/health", tags=["health"])
def health_check():
    from services.monitoring_engine import get_monitored_slugs
    slugs = get_monitored_slugs()
    return {
        "status": "ok",
        "version": "0.2.0",
        "monitored_entities": len(slugs),
        "background_monitor": "active",
    }


@app.get("/status", tags=["health"])
def system_status():
    """Dashboard de saúde do sistema — última auditoria, alertas recentes, custos."""
    from services.snapshot_service import list_entities
    from services.monitoring_engine import get_monitored_slugs, get_monitor_summary
    from services.cost_tracker import get_costs
    from datetime import datetime, timezone

    entities = list_entities()
    monitored = get_monitored_slugs()
    costs = get_costs(last_n=100)

    entity_status = []
    for e in entities[:20]:  # top 20 mais recentes
        slug = e.get("slug", "")
        mon = get_monitor_summary(slug) if slug in monitored else None
        entity_status.append({
            "entity": e.get("entity", slug),
            "slug": slug,
            "threat": e.get("latest_threat", ""),
            "latest_snapshot": e.get("latest_snapshot", ""),
            "monitoring": {
                "active": slug in monitored,
                "last_check": mon.get("last_check") if mon else None,
                "crisis_alerts_7d": mon.get("crisis_alerts_7d", 0) if mon else 0,
            } if mon else {"active": False},
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entities_total": len(entities),
        "entities_monitored": len(monitored),
        "cost_week": costs.get("total_cost", 0),
        "entities": entity_status,
    }
