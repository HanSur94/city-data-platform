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
async def test_kpi_fields(client):
    """PLAT-03: KPI endpoint returns air_quality, weather, transit fields."""
    with patch("app.routers.kpi.get_db", return_value=AsyncMock()):
        resp = await client.get("/api/kpi?town=aalen")
    assert resp.status_code == 200
    data = resp.json()
    assert "air_quality" in data
    assert "weather" in data
    assert "transit" in data
    assert "last_updated" in data
    assert "attribution" in data


@pytest.mark.asyncio
async def test_kpi_unknown_town_404(client):
    """PLAT-03: unknown town returns 404."""
    with patch("app.routers.kpi.get_db", return_value=AsyncMock()):
        resp = await client.get("/api/kpi?town=notexist")
    assert resp.status_code == 404
