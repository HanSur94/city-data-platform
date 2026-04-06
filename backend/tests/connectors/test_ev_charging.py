"""Tests for EvChargingConnector pure functions and normalize logic.

Tests OCPDB status mapping, power classification, and response normalization.
No database required -- tests pure functions and normalize with mock data.
"""
import pytest
from unittest.mock import MagicMock


# -- Pure function tests --

def test_classify_power_ac_slow():
    """<=22 kW is ac_slow."""
    from app.connectors.ev_charging import classify_power
    assert classify_power(22.0) == "ac_slow"
    assert classify_power(11.0) == "ac_slow"
    assert classify_power(3.7) == "ac_slow"


def test_classify_power_ac_fast():
    """22-43 kW is ac_fast."""
    from app.connectors.ev_charging import classify_power
    assert classify_power(22.1) == "ac_fast"
    assert classify_power(43.0) == "ac_fast"


def test_classify_power_dc_fast():
    """>43 kW is dc_fast."""
    from app.connectors.ev_charging import classify_power
    assert classify_power(43.1) == "dc_fast"
    assert classify_power(150.0) == "dc_fast"
    assert classify_power(350.0) == "dc_fast"


def test_map_ocpdb_status_available():
    """AVAILABLE maps to AVAILABLE."""
    from app.connectors.ev_charging import map_ocpdb_status
    assert map_ocpdb_status("AVAILABLE") == "AVAILABLE"


def test_map_ocpdb_status_charging():
    """CHARGING maps to OCCUPIED."""
    from app.connectors.ev_charging import map_ocpdb_status
    assert map_ocpdb_status("CHARGING") == "OCCUPIED"


def test_map_ocpdb_status_inoperative():
    """INOPERATIVE, OUT_OF_ORDER, BLOCKED map to INOPERATIVE."""
    from app.connectors.ev_charging import map_ocpdb_status
    assert map_ocpdb_status("INOPERATIVE") == "INOPERATIVE"
    assert map_ocpdb_status("OUT_OF_ORDER") == "INOPERATIVE"
    assert map_ocpdb_status("BLOCKED") == "INOPERATIVE"


def test_map_ocpdb_status_unknown():
    """Unknown status maps to UNKNOWN."""
    from app.connectors.ev_charging import map_ocpdb_status
    assert map_ocpdb_status("SOMETHING_ELSE") == "UNKNOWN"
    assert map_ocpdb_status("") == "UNKNOWN"


# -- Normalize tests --

def _make_connector(bbox_lat_min=48.76, bbox_lat_max=48.90,
                    bbox_lon_min=9.97, bbox_lon_max=10.22):
    """Create a minimal EvChargingConnector with mock town config."""
    from app.connectors.ev_charging import EvChargingConnector
    from app.config import ConnectorConfig, Town, TownBbox

    config = ConnectorConfig(
        connector_class="EvChargingConnector",
        poll_interval_seconds=300,
        enabled=True,
        config={"radius_km": 15},
    )
    town = Town(
        id="test-town",
        display_name="Test Town",
        bbox=TownBbox(
            lon_min=bbox_lon_min,
            lat_min=bbox_lat_min,
            lon_max=bbox_lon_max,
            lat_max=bbox_lat_max,
        ),
    )
    return EvChargingConnector(config=config, town=town)


def _make_ocpdb_location(
    location_id="LOC1",
    lat=48.84,
    lon=10.09,
    evses=None,
    operator_name="TestOp",
    address="Test Street 1",
):
    """Create a mock OCPDB location dict."""
    if evses is None:
        evses = [
            {
                "uid": "EVSE1",
                "status": "AVAILABLE",
                "connectors": [
                    {
                        "standard": "IEC_62196_T2",
                        "max_electric_power": 22000,
                    }
                ],
            }
        ]
    return {
        "id": location_id,
        "coordinates": {"latitude": str(lat), "longitude": str(lon)},
        "evses": evses,
        "operator": {"name": operator_name},
        "address": address,
    }


def test_normalize_available_evse():
    """AVAILABLE EVSE maps to feature with status=AVAILABLE."""
    connector = _make_connector()
    raw = [_make_ocpdb_location(evses=[{
        "uid": "E1",
        "status": "AVAILABLE",
        "connectors": [{"standard": "IEC_62196_T2", "max_electric_power": 22000}],
    }])]
    result = connector.normalize(raw)
    # Features-only connector returns empty observations
    assert result == []
    # But we can check the parsed locations
    locations = connector._parse_locations(raw)
    assert len(locations) == 1
    assert locations[0]["status"] == "AVAILABLE"


def test_normalize_charging_evse():
    """CHARGING EVSE maps to status=OCCUPIED."""
    connector = _make_connector()
    raw = [_make_ocpdb_location(evses=[{
        "uid": "E1",
        "status": "CHARGING",
        "connectors": [{"standard": "CCS", "max_electric_power": 150000}],
    }])]
    locations = connector._parse_locations(raw)
    assert len(locations) == 1
    assert locations[0]["status"] == "OCCUPIED"


def test_normalize_inoperative_evse():
    """INOPERATIVE EVSE maps to status=INOPERATIVE."""
    connector = _make_connector()
    raw = [_make_ocpdb_location(evses=[{
        "uid": "E1",
        "status": "INOPERATIVE",
        "connectors": [{"standard": "IEC_62196_T2", "max_electric_power": 11000}],
    }])]
    locations = connector._parse_locations(raw)
    assert len(locations) == 1
    assert locations[0]["status"] == "INOPERATIVE"


def test_normalize_extracts_max_power():
    """Extracts max power_kw from connectors list (watts -> kW)."""
    connector = _make_connector()
    raw = [_make_ocpdb_location(evses=[{
        "uid": "E1",
        "status": "AVAILABLE",
        "connectors": [
            {"standard": "IEC_62196_T2", "max_electric_power": 22000},
            {"standard": "CCS", "max_electric_power": 150000},
        ],
    }])]
    locations = connector._parse_locations(raw)
    assert len(locations) == 1
    assert locations[0]["power_kw"] == pytest.approx(150.0)
    assert locations[0]["power_class"] == "dc_fast"


def test_normalize_classifies_power():
    """Classifies power as ac_slow/ac_fast/dc_fast."""
    connector = _make_connector()

    # ac_slow
    raw = [_make_ocpdb_location(evses=[{
        "uid": "E1", "status": "AVAILABLE",
        "connectors": [{"standard": "Type2", "max_electric_power": 11000}],
    }])]
    locations = connector._parse_locations(raw)
    assert locations[0]["power_class"] == "ac_slow"

    # dc_fast
    raw = [_make_ocpdb_location(evses=[{
        "uid": "E1", "status": "AVAILABLE",
        "connectors": [{"standard": "CCS", "max_electric_power": 350000}],
    }])]
    locations = connector._parse_locations(raw)
    assert locations[0]["power_class"] == "dc_fast"


def test_normalize_skips_outside_bbox():
    """Skips locations outside town bbox."""
    connector = _make_connector()
    raw = [_make_ocpdb_location(lat=50.0, lon=12.0)]  # Outside Aalen bbox
    locations = connector._parse_locations(raw)
    assert len(locations) == 0


def test_normalize_handles_missing_evses():
    """Handles missing/null EVSE list gracefully."""
    connector = _make_connector()

    # No evses key
    raw = [{"id": "LOC1", "coordinates": {"latitude": "48.84", "longitude": "10.09"}}]
    locations = connector._parse_locations(raw)
    assert len(locations) == 0

    # Empty evses list
    raw = [_make_ocpdb_location(evses=[])]
    locations = connector._parse_locations(raw)
    assert len(locations) == 0
