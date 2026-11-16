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


# ---------------------------------------------------------------------------
# Transit layer: shapes clipped to the town bbox, simplified and de-duplicated
# ---------------------------------------------------------------------------

def _transit_line_row(row_id: str, route: str = "1", color: str = "#ff0000") -> dict:
    import json

    return {
        "id": row_id,
        "geometry": json.dumps(
            {
                "type": "MultiLineString",
                "coordinates": [[[10.0, 48.8], [10.01, 48.81]], [[10.02, 48.82], [10.03, 48.83]]],
            }
        ),
        "properties": {
            "feature_type": "shape",
            "route_short_name": route,
            "route_type_color": color,
        },
        "source_id": "src-gtfs",
        "last_updated": datetime(2026, 11, 16, 8, 0, tzinfo=timezone.utc),
        "is_line": True,
    }


def _transit_point_row(row_id: str, lon: float = 10.09) -> dict:
    import json

    return {
        "id": row_id,
        "geometry": json.dumps({"type": "Point", "coordinates": [lon, 48.84]}),
        "properties": {"feature_type": "stop", "name": "Hbf"},
        "source_id": "src-gtfs",
        "last_updated": datetime(2026, 11, 16, 8, 0, tzinfo=timezone.utc),
        "is_line": False,
    }


def _install_fake_transit_db(feature_rows: list[dict]):
    """Install a fake DB session; return the list that captures (sql, params)."""
    from unittest.mock import MagicMock
    from app.db import get_db

    captured: list[tuple[str, dict | None]] = []

    async def fake(stmt, params=None):
        sql = str(stmt)
        captured.append((sql, params))
        result = MagicMock()
        if "FROM sources" in sql:
            result.mappings.return_value.all.return_value = [{"connector_class": "GTFSConnector"}]
        else:
            result.mappings.return_value.all.return_value = feature_rows
        return result

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=fake)

    async def _db():
        yield session

    app.dependency_overrides[get_db] = _db
    return captured


def test_transit_shapes_query_binds_bbox_and_tolerance():
    from app.routers.layers import (
        SHAPE_SIMPLIFY_TOLERANCE_DEG,
        build_transit_layer_query,
    )

    sql, params = build_transit_layer_query("aalen", MOCK_TOWN.bbox, "shape")

    assert SHAPE_SIMPLIFY_TOLERANCE_DEG == 0.00005
    assert params == {
        "town_id": "aalen",
        "lon_min": 9.9,
        "lat_min": 48.7,
        "lon_max": 10.2,
        "lat_max": 48.9,
        "tolerance": 0.00005,
        "feature_type": "shape",
    }
    assert "ST_MakeEnvelope(:lon_min, :lat_min, :lon_max, :lat_max, 4326)" in sql
    for fragment in (
        "ST_Intersection(",
        "ST_CollectionExtract(",
        "ST_SimplifyPreserveTopology(",
        ":tolerance",
        ":feature_type",
        "ST_Dimension(",
        "ELSE",
    ):
        assert fragment in sql
    assert "ST_AsGeoJSON(geom, 5)" in sql
    # No request-derived value may be formatted into the statement text.
    assert "9.9" not in sql
    assert "48.7" not in sql
    assert "10.2" not in sql
    assert "48.9" not in sql
    assert "aalen" not in sql


def test_transit_shapes_query_without_feature_type_has_no_filter():
    from app.routers.layers import build_transit_layer_query

    sql, params = build_transit_layer_query("aalen", MOCK_TOWN.bbox, None)

    assert ":feature_type" not in sql
    assert "feature_type" not in params
    assert params["lon_min"] == 9.9
    assert params["lat_max"] == 48.9
    assert params["tolerance"] == 0.00005
    assert "ST_MakeEnvelope(:lon_min, :lat_min, :lon_max, :lat_max, 4326)" in sql


def test_transit_shapes_dedupe_keeps_smallest_id():
    import json
    from app.routers.layers import dedupe_shape_rows

    geom = '{"type":"LineString","coordinates":[[10,48],[10.1,48.1]]}'

    def line(row_id, route="1", color="#f00", props_as_json=False):
        props = {"route_short_name": route, "route_type_color": color}
        return {
            "id": row_id,
            "geometry": geom,
            "properties": json.dumps(props) if props_as_json else props,
            "is_line": True,
        }

    point = {"id": "p1", "geometry": '{"type":"Point","coordinates":[10,48]}', "properties": {}}
    point_twin = dict(point, id="p2")

    rows = [point, line("c"), line("a", props_as_json=True), line("x", route="2"), line("b"), point_twin]
    out = dedupe_shape_rows(rows)

    assert [r["id"] for r in out] == ["p1", "a", "x", "p2"]


@pytest.mark.asyncio
async def test_transit_shapes_endpoint_clips_dedupes_and_validates(client):
    captured = _install_fake_transit_db(
        [_transit_line_row("s2"), _transit_line_row("s1")]
    )

    resp = await client.get("/api/layers/transit?town=aalen&feature_type=shape")

    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "FeatureCollection"
    assert [f["id"] for f in data["features"]] == ["s1"]
    feature = data["features"][0]
    assert feature["geometry"]["type"] == "MultiLineString"
    assert "is_line" not in feature["properties"]
    assert data["town"] == "aalen"
    assert data["domain"] == "transit"
    assert data["last_updated"] is not None
    assert isinstance(data["attribution"], list)

    feature_sql, feature_params = next(c for c in captured if "FROM sources" not in c[0])
    assert "ST_MakeEnvelope" in feature_sql
    assert feature_params["lon_min"] == 9.9
    assert feature_params["lat_min"] == 48.7
    assert feature_params["lon_max"] == 10.2
    assert feature_params["lat_max"] == 48.9
    assert feature_params["tolerance"] == 0.00005
    assert feature_params["feature_type"] == "shape"


@pytest.mark.asyncio
async def test_transit_stops_endpoint_returns_points_unchanged(client):
    import json

    twin_a = _transit_point_row("stop-1")
    twin_b = _transit_point_row("stop-2")
    _install_fake_transit_db([twin_a, twin_b])

    resp = await client.get("/api/layers/transit?town=aalen&feature_type=stop")

    assert resp.status_code == 200
    data = resp.json()
    assert [f["id"] for f in data["features"]] == ["stop-1", "stop-2"]
    for feature, row in zip(data["features"], (twin_a, twin_b)):
        assert feature["geometry"] == json.loads(row["geometry"])
        assert feature["properties"] == row["properties"]
