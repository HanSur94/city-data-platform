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


@pytest.mark.asyncio
async def test_layer_features_not_duplicated_by_sources(client):
    """F2: several sources rows per domain must not multiply feature rows."""
    import json
    from unittest.mock import MagicMock
    from app.db import get_db

    feature_rows = [
        {
            "id": f"feat-{i}",
            "geometry": json.dumps({"type": "Point", "coordinates": [10.0 + i, 48.8]}),
            "properties": {"name": f"Sensor {i}"},
            "source_id": f"src-{i}",
            "pm25": 5.0,
        }
        for i in (1, 2)
    ]
    attribution_rows = [
        {"connector_class": "UBAConnector"},
        {"connector_class": "SensorCommunityConnector"},
        {"connector_class": "AirQualityGridConnector"},
    ]
    executed: list[str] = []

    async def fake(stmt, params=None):
        sql = str(stmt)
        executed.append(sql)
        result = MagicMock()
        if "FROM sources" in sql:
            result.mappings.return_value.all.return_value = attribution_rows
        else:
            result.mappings.return_value.all.return_value = feature_rows
        return result

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=fake)

    async def _db():
        yield session

    app.dependency_overrides[get_db] = _db
    resp = await client.get("/api/layers/air_quality?town=aalen")

    assert resp.status_code == 200
    data = resp.json()
    ids = [f["id"] for f in data["features"]]
    assert len(ids) == 2 and len(set(ids)) == 2
    assert [a["source_name"] for a in data["attribution"]] == [
        "IDW Interpolation",
        "Sensor.Community",
        "Umweltbundesamt (UBA)",
    ]
    sources_stmts = [sql for sql in executed if "sources" in sql]
    assert len(sources_stmts) == 1
    assert "SELECT DISTINCT connector_class" in sources_stmts[0]
