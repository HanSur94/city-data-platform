"""FastAPI application factory.

On startup, loads and validates the town config identified by the TOWN
environment variable (default: "aalen"). Fails fast on missing or invalid config.
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.config import load_town, Town

# Application-level state (populated on startup)
_current_town: Town | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load and validate town config on startup."""
    global _current_town
    town_id = os.environ.get("TOWN", "aalen")
    towns_dir = Path(os.environ.get("TOWNS_DIR", "towns"))

    _current_town = load_town(town_id, towns_dir=towns_dir)
    print(f"[startup] Loaded town config: {_current_town.display_name} ({_current_town.id})")

    yield

    # Shutdown
    print("[shutdown] City Data Platform stopping")


app = FastAPI(
    title="City Data Platform API",
    description="Aggregates and serves public city data for German towns",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict:
    town_id = _current_town.id if _current_town else "not loaded"
    return {"status": "ok", "town": town_id}


def get_current_town() -> Town:
    """FastAPI dependency: returns the currently loaded town."""
    if _current_town is None:
        raise RuntimeError("Town not loaded — lifespan not started")
    return _current_town
