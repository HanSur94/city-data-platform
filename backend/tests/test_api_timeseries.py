import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

from app.main import app
from app.config import Town, TownBbox

MOCK_TOWN = Town(
    id="aalen",
    display_name="Aalen",
    country="DE",
    bbox=TownBbox(lon_min=9.9, lat_min=48.7, lon_max=10.2, lat_max=48.9),
    connectors=[],
)


@pytest.fixture
async def client():
    from app.dependencies import get_current_town
    app.dependency_overrides[get_current_town] = lambda: MOCK_TOWN
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_timeseries_ordered(client):
    """PLAT-03: timeseries returns time-ordered readings."""
    with patch("app.routers.timeseries.get_db", return_value=AsyncMock()):
        resp = await client.get(
            "/api/timeseries/air_quality?town=aalen"
            "&start=2026-01-01T00:00:00Z&end=2026-01-02T00:00:00Z"
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "points" in data
    assert "count" in data


@pytest.mark.asyncio
async def test_timeseries_last_updated(client):
    """PLAT-04: timeseries response includes last_updated field."""
    with patch("app.routers.timeseries.get_db", return_value=AsyncMock()):
        resp = await client.get(
            "/api/timeseries/air_quality?town=aalen"
            "&start=2026-01-01T00:00:00Z&end=2026-01-02T00:00:00Z"
        )
    assert resp.status_code == 200
    assert "last_updated" in resp.json()


@pytest.mark.asyncio
async def test_timeseries_unknown_town_404(client):
    """PLAT-03: unknown town returns 404."""
    with patch("app.routers.timeseries.get_db", return_value=AsyncMock()):
        resp = await client.get(
            "/api/timeseries/air_quality?town=unknown"
            "&start=2026-01-01T00:00:00Z&end=2026-01-02T00:00:00Z"
        )
    assert resp.status_code == 404
