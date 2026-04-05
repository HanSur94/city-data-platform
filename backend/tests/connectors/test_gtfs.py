"""Tests for GTFSConnector: bbox-filtered GTFS stops and route shapes.

Fast unit tests (fixture-based, no download) run by default.
Slow live download tests require: pytest tests/connectors/test_gtfs.py -v -m slow
"""
import io
import zipfile
import pytest
import pandas as pd
from app.connectors.gtfs import GTFSConnector
from app.config import ConnectorConfig

GTFS_URL = "https://www.nvbw.de/fileadmin/user_upload/service/open_data/fahrplandaten_mit_liniennetz/bwgesamt.zip"


def make_minimal_gtfs_zip(stops: list[dict], shapes: list[dict] | None = None) -> bytes:
    """Create a minimal valid GTFS zip in memory for unit tests.

    stops: list of dicts with stop_id, stop_name, stop_lat, stop_lon
    shapes: list of dicts with shape_id, shape_pt_lat, shape_pt_lon, shape_pt_sequence
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        # stops.txt
        stop_lines = ["stop_id,stop_name,stop_lat,stop_lon"]
        for s in stops:
            stop_lines.append(f"{s['stop_id']},{s['stop_name']},{s['stop_lat']},{s['stop_lon']}")
        zf.writestr("stops.txt", "\n".join(stop_lines))
        # agency.txt (required)
        zf.writestr("agency.txt", "agency_id,agency_name,agency_url,agency_timezone\n1,Test,http://test.com,Europe/Berlin")
        # routes.txt (required)
        zf.writestr("routes.txt", "route_id,agency_id,route_short_name,route_long_name,route_type\nr1,1,1,Test Route,3")
        # trips.txt (required)
        zf.writestr("trips.txt", "route_id,service_id,trip_id\nr1,s1,t1")
        # stop_times.txt (required)
        zf.writestr("stop_times.txt", "trip_id,arrival_time,departure_time,stop_id,stop_sequence\nt1,08:00:00,08:00:00,stop1,1")
        # calendar.txt (required)
        zf.writestr("calendar.txt", "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\ns1,1,1,1,1,1,0,0,20260101,20261231")
        # shapes.txt (optional)
        if shapes:
            shape_lines = ["shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence"]
            for sh in shapes:
                shape_lines.append(f"{sh['shape_id']},{sh['shape_pt_lat']},{sh['shape_pt_lon']},{sh['shape_pt_sequence']}")
            zf.writestr("shapes.txt", "\n".join(shape_lines))
    return buf.getvalue()


@pytest.fixture
def gtfs_config():
    return ConnectorConfig(
        connector_class="GTFSConnector",
        poll_interval_seconds=86400,
        enabled=True,
        config={"gtfs_url": GTFS_URL},
    )


@pytest.fixture
def connector(gtfs_config, aalen_town):
    return GTFSConnector(config=gtfs_config, town=aalen_town)


# --- FAST TESTS (no network) ---

def test_normalize_bbox_filter(connector):
    """Stops outside Aalen bbox are excluded; stops inside are included."""
    gtfs_bytes = make_minimal_gtfs_zip([
        {"stop_id": "inside", "stop_name": "In Aalen", "stop_lat": 48.84, "stop_lon": 10.09},
        {"stop_id": "outside", "stop_name": "In Stuttgart", "stop_lat": 48.78, "stop_lon": 9.18},
    ])
    obs = connector.normalize(gtfs_bytes)
    stop_obs = [o for o in obs if o.values.get("feature_type") == "stop"]
    stop_source_ids = [o.source_id for o in stop_obs]
    assert "stop:inside" in stop_source_ids
    assert "stop:outside" not in stop_source_ids


def test_normalize_returns_geometry_types(connector):
    """Stops have Point geometry; shapes have LineString geometry."""
    gtfs_bytes = make_minimal_gtfs_zip(
        stops=[{"stop_id": "s1", "stop_name": "Stop 1", "stop_lat": 48.84, "stop_lon": 10.09}],
        shapes=[
            {"shape_id": "sh1", "shape_pt_lat": 48.84, "shape_pt_lon": 10.09, "shape_pt_sequence": 1},
            {"shape_id": "sh1", "shape_pt_lat": 48.85, "shape_pt_lon": 10.10, "shape_pt_sequence": 2},
        ],
    )
    obs = connector.normalize(gtfs_bytes)
    geom_types = {o.values.get("geometry_type") for o in obs}
    assert "Point" in geom_types
    assert "LineString" in geom_types


def test_shape_outside_bbox_excluded(connector):
    """Shape with no points in bbox is excluded."""
    gtfs_bytes = make_minimal_gtfs_zip(
        stops=[],
        shapes=[
            {"shape_id": "far", "shape_pt_lat": 48.00, "shape_pt_lon": 9.00, "shape_pt_sequence": 1},
        ],
    )
    obs = connector.normalize(gtfs_bytes)
    shape_obs = [o for o in obs if o.values.get("feature_type") == "shape"]
    assert len(shape_obs) == 0


def test_normalize_stop_has_lat_lon_in_values(connector):
    """Stops include lat/lon in values dict for bbox verification."""
    gtfs_bytes = make_minimal_gtfs_zip([
        {"stop_id": "s1", "stop_name": "Central", "stop_lat": 48.84, "stop_lon": 10.09},
    ])
    obs = connector.normalize(gtfs_bytes)
    stop_obs = [o for o in obs if o.values.get("feature_type") == "stop"]
    assert len(stop_obs) == 1
    assert abs(stop_obs[0].values["lat"] - 48.84) < 0.001
    assert abs(stop_obs[0].values["lon"] - 10.09) < 0.001


# --- SLOW TESTS (live NVBW download, ~3 min) ---

@pytest.mark.slow
async def test_gtfs_fetch_returns_bytes(connector):
    raw = await connector.fetch()
    assert isinstance(raw, bytes)
    assert len(raw) > 0


@pytest.mark.slow
async def test_gtfs_normalize_filters_to_bbox(connector):
    raw = await connector.fetch()
    obs = connector.normalize(raw)
    stop_obs = [o for o in obs if o.values.get("feature_type") == "stop"]
    bbox = connector.town.bbox
    for o in stop_obs:
        lat = o.values.get("lat")
        lon = o.values.get("lon")
        if lat is not None and lon is not None:
            assert bbox.lat_min <= lat <= bbox.lat_max, f"Stop lat {lat} outside bbox"
            assert bbox.lon_min <= lon <= bbox.lon_max, f"Stop lon {lon} outside bbox"


@pytest.mark.slow
async def test_gtfs_stop_count_reasonable(connector):
    raw = await connector.fetch()
    obs = connector.normalize(raw)
    stops = [o for o in obs if o.values.get("feature_type") == "stop"]
    assert 10 <= len(stops) <= 1000, f"Unexpected stop count: {len(stops)}"


@pytest.mark.slow
async def test_gtfs_shapes_exist(connector):
    raw = await connector.fetch()
    obs = connector.normalize(raw)
    shapes = [o for o in obs if o.values.get("feature_type") == "shape"]
    assert len(shapes) > 0, "Expected at least one route shape in Aalen area"
