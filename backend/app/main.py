"""FastAPI application factory.

On startup, loads and validates the town config identified by the TOWN
environment variable (default: "aalen"). Fails fast on missing or invalid config.
After town and DB are ready, starts APScheduler with all enabled connectors.
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.config import load_town, Town
from app.dependencies import set_current_town, get_current_town
from app.scheduler import scheduler, setup_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load and validate town config on startup."""
    town_id = os.environ.get("TOWN", "aalen")
    towns_dir = Path(os.environ.get("TOWNS_DIR", "towns"))

    town = load_town(town_id, towns_dir=towns_dir)
    set_current_town(town)
    print(f"[startup] Loaded town config: {town.display_name} ({town.id})")

    # Start APScheduler with all enabled connectors
    # NOTE: Must come after town config is loaded and verified.
    # Scheduler runs in the same asyncio event loop as FastAPI.
    setup_scheduler(town)
    scheduler.start()
    print(f"[startup] APScheduler started with {len([c for c in town.connectors if c.enabled])} connector(s)")

    yield

    # Shutdown
    scheduler.shutdown(wait=False)
    print("[shutdown] City Data Platform stopping")


app = FastAPI(
    title="City Data Platform API",
    description="Aggregates and serves public city data for German towns",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict:
    try:
        town = get_current_town()
        town_id = town.id
    except RuntimeError:
        town_id = "not loaded"
    return {"status": "ok", "town": town_id}
