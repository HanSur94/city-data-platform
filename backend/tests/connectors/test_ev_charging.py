"""Tests for EvChargingConnector pure functions and normalize logic.

Tests OCPDB status mapping, power classification, and response normalization.
No database required -- tests pure functions and normalize with mock data.
"""
import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


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


# -- MobiData BW OCPDB: fetch with pagination, real item, honest failure --

OCPDB_URL = "https://api.mobidata-bw.de/ocpdb/api/public/v1/locations"

# Location 187777 cut from a real answer, trimmed to two EVSEs (50 kW DC, 22 kW AC).
REAL_OCPDB_ITEM = {
    "address": "Daimlerstr. 9",
    "postal_code": "73431",
    "city": "Aalen",
    "state": "Baden-Württemberg",
    "country": "DEU",
    "id": "187777",
    "source": "bnetza_api",
    "coordinates": {
        "latitude": 48.825694,
        "longitude": 10.065097,
        "lat": 48.825694,
        "lon": 10.065097,
    },
    "operator": {"name": "E-Merge Mobility GmbH"},
    "evses": [
        {
            "uid": "260004386",
            "evse_id": "BNETZA*1011615*1",
            "status": "STATIC",
            "connectors": [
                {
                    "standard": "IEC_62196_T2_COMBO",
                    "format": "CABLE",
                    "power_type": "DC",
                    "max_voltage": 400,
                    "max_amperage": 375,
                    "max_electric_power": 50000,
                }
            ],
        },
        {
            "uid": "260004387",
            "evse_id": "BNETZA*1011615*2",
            "status": "STATIC",
            "connectors": [
                {
                    "standard": "IEC_62196_T2",
                    "format": "SOCKET",
                    "power_type": "AC_3_PHASE",
                    "max_voltage": 400,
                    "max_amperage": 32,
                    "max_electric_power": 22000,
                }
            ],
        },
    ],
}


def _page(items, next_offset=None, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    body = {"items": items, "total_count": 161}
    if next_offset is not None:
        body["next_offset"] = next_offset
    resp.json = MagicMock(return_value=body)
    resp.raise_for_status = MagicMock()
    return resp


def _patched_client(responses):
    queue = list(responses)
    calls = []

    async def mock_get(url, **kwargs):
        calls.append({"url": url, **kwargs})
        return queue.pop(0)

    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get = AsyncMock(side_effect=mock_get)
    return client, calls


def test_map_ocpdb_status_static_is_unknown():
    """BNetzA registered points report STATIC (no live status) -> UNKNOWN."""
    from app.connectors.ev_charging import map_ocpdb_status
    assert map_ocpdb_status("STATIC") == "UNKNOWN"


@pytest.mark.asyncio
async def test_fetch_reads_every_page():
    connector = _make_connector()
    client, calls = _patched_client([
        _page([{"id": "1"}, {"id": "2"}], next_offset=2),
        _page([{"id": "3"}]),
    ])
    with patch("httpx.AsyncClient") as cls:
        cls.return_value = client
        items = await connector.fetch()

    assert [i["id"] for i in items] == ["1", "2", "3"]
    assert len(calls) == 2
    for call in calls:
        assert call["url"] == OCPDB_URL
        assert call["params"]["radius"] == 15000
        assert call["params"]["limit"] == 100
        assert "lat" in call["params"] and "lon" in call["params"]
        assert "city-data-platform" in call["headers"]["User-Agent"]
    assert [c["params"]["offset"] for c in calls] == [0, 2]
    assert calls[0]["params"]["lat"] == pytest.approx(48.83)
    assert calls[0]["params"]["lon"] == pytest.approx(10.095)


@pytest.mark.asyncio
async def test_fetch_raises_without_items_list():
    connector = _make_connector()
    resp = MagicMock()
    resp.status_code = 200
    resp.json = MagicMock(return_value={"detail": "maintenance"})
    resp.raise_for_status = MagicMock()
    client, _ = _patched_client([resp])
    with patch("httpx.AsyncClient") as cls:
        cls.return_value = client
        with pytest.raises(ValueError, match="items"):
            await connector.fetch()


@pytest.mark.asyncio
async def test_fetch_stops_after_max_pages():
    from app.connectors.ev_charging import MAX_PAGES

    connector = _make_connector()
    client, calls = _patched_client([
        _page([{"id": str(n)}], next_offset=n + 1) for n in range(MAX_PAGES + 5)
    ])
    with patch("httpx.AsyncClient") as cls:
        cls.return_value = client
        items = await connector.fetch()

    assert len(calls) == MAX_PAGES
    assert len(items) == MAX_PAGES


def test_parse_real_ocpdb_item():
    connector = _make_connector()
    parsed = connector._parse_locations([REAL_OCPDB_ITEM])

    assert len(parsed) == 1
    loc = parsed[0]
    assert loc["location_id"] == "187777"
    assert loc["status"] == "UNKNOWN"
    assert loc["power_kw"] == 50.0
    assert loc["power_class"] == "dc_fast"
    assert loc["operator"] == "E-Merge Mobility GmbH"
    assert loc["address"] == "Daimlerstr. 9, 73431 Aalen"
    assert loc["connector_types"] == ["IEC_62196_T2", "IEC_62196_T2_COMBO"]
    assert loc["evse_count"] == 2
    assert loc["num_connectors"] == 2
    assert loc["lat"] == pytest.approx(48.825694)


@pytest.mark.asyncio
async def test_run_does_not_advance_staleness_when_fetch_fails():
    connector = _make_connector()
    connector.fetch = AsyncMock(side_effect=httpx.ConnectError("refused"))
    connector.upsert_feature = AsyncMock()
    connector._update_staleness = AsyncMock()

    with pytest.raises(httpx.ConnectError):
        await connector.run()

    connector._update_staleness.assert_not_awaited()
    connector.upsert_feature.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_empty_answer_is_a_successful_fetch():
    connector = _make_connector()
    connector.fetch = AsyncMock(return_value=[])
    connector.upsert_feature = AsyncMock()
    connector._update_staleness = AsyncMock()

    await connector.run()

    connector._update_staleness.assert_awaited_once()
