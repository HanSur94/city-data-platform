"""FastAPI application factory.

On startup, loads and validates the town config identified by the TOWN
environment variable (default: "aalen"). Fails fast on missing or invalid config.
After town and DB are ready, starts APScheduler with all enabled connectors.
"""
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text

from app.config import load_town, Town
from app.db import AsyncSessionLocal
from app.dependencies import set_current_town, get_current_town
from app.scheduler import scheduler, setup_scheduler
from app.routers import layers, timeseries, kpi, connectors, admin, metadata, features


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load and validate town config on startup."""
    town_id = os.environ.get("TOWN", "aalen")
    towns_dir = Path(os.environ.get("TOWNS_DIR", "towns"))

    town = load_town(town_id, towns_dir=towns_dir)
    set_current_town(town)
    print(f"[startup] Loaded town config: {town.display_name} ({town.id})")

    # Ensure town row exists in database (required FK for features/sources)
    async with AsyncSessionLocal() as session:
        bbox = [town.bbox.lon_min, town.bbox.lat_min, town.bbox.lon_max, town.bbox.lat_max]
        await session.execute(
            text(
                "INSERT INTO towns (id, display_name, country, bbox) "
                "VALUES (:id, :display_name, :country, CAST(:bbox AS jsonb)) "
                "ON CONFLICT (id) DO UPDATE SET "
                "display_name = EXCLUDED.display_name, bbox = EXCLUDED.bbox"
            ),
            {"id": town.id, "display_name": town.display_name, "country": town.country,
             "bbox": json.dumps(bbox)},
        )
        await session.commit()
    print(f"[startup] Ensured town '{town.id}' exists in database")

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(layers.router, prefix="/api")
app.include_router(timeseries.router, prefix="/api")
app.include_router(kpi.router, prefix="/api")
app.include_router(connectors.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(metadata.router, prefix="/api")
app.include_router(features.router, prefix="/api")


@app.get("/health")
async def health() -> dict:
    try:
        town = get_current_town()
        town_id = town.id
    except RuntimeError:
        town_id = "not loaded"
    return {"status": "ok", "town": town_id}
