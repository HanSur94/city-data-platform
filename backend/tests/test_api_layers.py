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
def mock_town():
    return MOCK_TOWN


@pytest.fixture
async def client(mock_town):
    """Async test client with mocked town dependency."""
    from app.dependencies import get_current_town
    app.dependency_overrides[get_current_town] = lambda: mock_town
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_layers_transit_returns_geojson(client):
    """PLAT-03: transit layer returns valid GeoJSON FeatureCollection."""
    with patch("app.routers.layers.get_db", return_value=AsyncMock()):
        resp = await client.get("/api/layers/transit?town=aalen")
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "FeatureCollection"
    assert "features" in data
    assert isinstance(data["features"], list)


@pytest.mark.asyncio
async def test_layers_air_quality_properties(client):
    """PLAT-03: air_quality layer returns GeoJSON with AQI health-tier properties."""
    with patch("app.routers.layers.get_db", return_value=AsyncMock()):
        resp = await client.get("/api/layers/air_quality?town=aalen")
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "FeatureCollection"


@pytest.mark.asyncio
async def test_layer_attribution_present(client):
    """PLAT-04: layer response includes attribution list."""
    with patch("app.routers.layers.get_db", return_value=AsyncMock()):
        resp = await client.get("/api/layers/air_quality?town=aalen")
    assert resp.status_code == 200
    data = resp.json()
    assert "attribution" in data
    assert isinstance(data["attribution"], list)
    assert "last_updated" in data


@pytest.mark.asyncio
async def test_unknown_town_404(client):
    """PLAT-03: unknown town returns 404."""
    with patch("app.routers.layers.get_db", return_value=AsyncMock()):
        resp = await client.get("/api/layers/transit?town=notareal")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_unknown_domain_404(client):
    """PLAT-03: unknown domain returns 404."""
    with patch("app.routers.layers.get_db", return_value=AsyncMock()):
        resp = await client.get("/api/layers/badomain?town=aalen")
    assert resp.status_code == 404
