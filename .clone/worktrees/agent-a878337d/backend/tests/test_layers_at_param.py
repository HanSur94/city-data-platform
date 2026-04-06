"""Tests for the optional ?at= query parameter on GET /api/layers/{domain}.

MAP-06: time slider needs historical snapshot support.
Verifies the HTTP contract — correct status codes for valid/invalid inputs.
Does not require a real database connection (uses autouse mock from conftest.py).
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.config import Town, TownBbox
from app.dependencies import get_current_town

MOCK_TOWN = Town(
    id="aalen",
    display_name="Aalen",
    country="DE",
    bbox=TownBbox(lon_min=9.9, lat_min=48.7, lon_max=10.2, lat_max=48.9),
    connectors=[],
)


@pytest.fixture(autouse=True)
def override_town():
    """Override get_current_town for all tests in this module."""
    app.dependency_overrides[get_current_town] = lambda: MOCK_TOWN
    yield
    app.dependency_overrides.pop(get_current_town, None)


@pytest.fixture
async def client():
    """Async test client with mocked dependencies."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_air_quality_no_at_param(client):
    """Test 1: No ?at= param — endpoint accepts request without crashing."""
    resp = await client.get("/api/layers/air_quality?town=aalen")
    # 200 (empty features from mock DB) or 404 (no real data) — not 422 or 500
    assert resp.status_code in (200, 404), f"Expected 200 or 404, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_air_quality_with_valid_at_param(client):
    """Test 2: Valid ISO8601 ?at= param — accepted without 422 validation error."""
    resp = await client.get("/api/layers/air_quality?town=aalen&at=2026-01-01T00:00:00Z")
    # 200 (empty features from mock DB) or 404 (no real data) — not 422 or 500
    assert resp.status_code in (200, 404), f"Expected 200 or 404, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_transit_ignores_at_param(client):
    """Test 3: Transit domain accepts ?at= without error (param is accepted, not used)."""
    resp = await client.get("/api/layers/transit?town=aalen&at=2026-01-01T00:00:00Z")
    # 200 or 404 — not 422 (transit domain should not crash on extra at param)
    assert resp.status_code in (200, 404), f"Expected 200 or 404, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_invalid_at_param_returns_422(client):
    """Test 4: Non-ISO8601 ?at= value returns 422 (FastAPI validates datetime type)."""
    resp = await client.get("/api/layers/air_quality?town=aalen&at=not-a-date")
    assert resp.status_code == 422, f"Expected 422 for invalid datetime, got {resp.status_code}: {resp.text}"
