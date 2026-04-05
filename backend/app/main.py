"""FastAPI application factory."""
from contextlib import asynccontextmanager
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: validate environment (Phase 1 stub)
    yield
    # Shutdown


app = FastAPI(
    title="City Data Platform API",
    description="Aggregates and serves public city data",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
