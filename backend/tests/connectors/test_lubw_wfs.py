"""Tests for LubwWfsConnector.

Tests:
- run() with 2 features per endpoint calls upsert_feature() 4 times
- run() with empty features list completes without error
- normalize() returns [] (unused by run())
- LubwWfsFeatureCollection validates with empty features list
- Properties stored as-is from WFS response
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import ConnectorConfig, Town, TownBbox
from app.connectors.lubw_wfs import LubwWfsConnector
from app.models.lubw_wfs import LubwWfsFeatureCollection, LubwWfsFeature, LubwWfsGeometry


# ---------------------------------------------------------------------------
# Sample WFS response fixtures
# ---------------------------------------------------------------------------

SAMPLE_POLYGON_COORDS = [
    [10.05, 48.80],
    [10.06, 48.80],
    [10.06, 48.81],
    [10.05, 48.81],
    [10.05, 48.80],
]

def _make_feature(feat_id: str, name: str, nr_key: str) -> dict:
    return {
        "type": "Feature",
        "id": feat_id,
        "geometry": {
            "type": "Polygon",
            "coordinates": [SAMPLE_POLYGON_COORDS],
        },
        "properties": {
            nr_key: feat_id,
            "NAME": name,
            "FLAECHE_HA": 42.5,
        },
    }


SAMPLE_NATURSCHUTZ_FEATURES = [
    _make_feature("Naturschutzgebiet.1", "Welland", "NSG_NR"),
    _make_feature("Naturschutzgebiet.2", "Heide", "NSG_NR"),
]

SAMPLE_WASSERSCHUTZ_FEATURES = [
    _make_feature("Wasserschutzgebiet.10", "WSG-Aalen-1", "WSG_NR"),
    _make_feature("Wasserschutzgebiet.11", "WSG-Aalen-2", "WSG_NR"),
]


def _make_fc(features: list[dict]) -> dict:
    return {
        "type": "FeatureCollection",
        "features": features,
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def lubw_config() -> ConnectorConfig:
    return ConnectorConfig(
        connector_class="LubwWfsConnector",
        poll_interval_seconds=86400,
        enabled=True,
        config={
            "attribution": "LUBW, DL-DE-BY-2.0",
        },
    )


@pytest.fixture
def aalen_town() -> Town:
    return Town(
        id="aalen",
        display_name="Aalen (Württemberg)",
        country="DE",
        timezone="Europe/Berlin",
        bbox=TownBbox(
            lon_min=9.9700,
            lat_min=48.7600,
            lon_max=10.2200,
            lat_max=48.9000,
        ),
        connectors=[],
    )


@pytest.fixture
def connector(lubw_config, aalen_town) -> LubwWfsConnector:
    return LubwWfsConnector(config=lubw_config, town=aalen_town)


# ---------------------------------------------------------------------------
# Pydantic model tests
# ---------------------------------------------------------------------------

def test_feature_collection_empty_features() -> None:
    """LubwWfsFeatureCollection validates with empty features list."""
    fc = LubwWfsFeatureCollection.model_validate({"type": "FeatureCollection", "features": []})
    assert fc.features == []


def test_feature_collection_with_features() -> None:
    """LubwWfsFeatureCollection validates with polygon features."""
    fc = LubwWfsFeatureCollection.model_validate(_make_fc(SAMPLE_NATURSCHUTZ_FEATURES))
    assert len(fc.features) == 2
    assert fc.features[0].id == "Naturschutzgebiet.1"
    assert fc.features[0].properties["NAME"] == "Welland"
    assert fc.features[0].geometry is not None
    assert fc.features[0].geometry.type == "Polygon"


def test_feature_without_id_is_valid() -> None:
    """LubwWfsFeature with no id field (None) is valid."""
    feat = LubwWfsFeature.model_validate({
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [SAMPLE_POLYGON_COORDS],
        },
        "properties": {"NAME": "test"},
    })
    assert feat.id is None


# ---------------------------------------------------------------------------
# run() — 2 features per endpoint → 4 upsert_feature() calls
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_calls_upsert_feature_for_each_feature(connector) -> None:
    """run() with 2 features per endpoint calls upsert_feature() 4 times."""
    mock_responses = {
        "naturschutz": _make_fc(SAMPLE_NATURSCHUTZ_FEATURES),
        "wasserschutz": _make_fc(SAMPLE_WASSERSCHUTZ_FEATURES),
    }

    async def mock_fetch():
        return mock_responses

    connector.fetch = mock_fetch
    connector.upsert_feature = AsyncMock(return_value="some-uuid")
    connector._update_staleness = AsyncMock()

    await connector.run()

    assert connector.upsert_feature.call_count == 4


@pytest.mark.asyncio
async def test_run_upsert_uses_domain_water(connector) -> None:
    """run() passes domain='water' to every upsert_feature() call."""
    mock_responses = {
        "naturschutz": _make_fc(SAMPLE_NATURSCHUTZ_FEATURES),
        "wasserschutz": _make_fc(SAMPLE_WASSERSCHUTZ_FEATURES),
    }

    connector.fetch = AsyncMock(return_value=mock_responses)
    connector.upsert_feature = AsyncMock(return_value="some-uuid")
    connector._update_staleness = AsyncMock()

    await connector.run()

    for call in connector.upsert_feature.call_args_list:
        assert call.kwargs.get("domain") == "water" or call[1].get("domain") == "water" or "water" in str(call)


@pytest.mark.asyncio
async def test_run_with_empty_features_completes_without_error(connector) -> None:
    """run() with empty features list (no zones in bbox) completes without error."""
    mock_responses = {
        "naturschutz": _make_fc([]),
        "wasserschutz": _make_fc([]),
    }

    connector.fetch = AsyncMock(return_value=mock_responses)
    connector.upsert_feature = AsyncMock(return_value="some-uuid")
    connector._update_staleness = AsyncMock()

    # Should not raise
    await connector.run()

    connector.upsert_feature.assert_not_called()
    connector._update_staleness.assert_called_once()


@pytest.mark.asyncio
async def test_run_calls_update_staleness(connector) -> None:
    """run() always calls _update_staleness() at the end."""
    connector.fetch = AsyncMock(return_value={
        "naturschutz": _make_fc([]),
        "wasserschutz": _make_fc([]),
    })
    connector.upsert_feature = AsyncMock(return_value="uuid")
    connector._update_staleness = AsyncMock()

    await connector.run()

    connector._update_staleness.assert_called_once()


@pytest.mark.asyncio
async def test_run_source_id_format(connector) -> None:
    """run() uses source_id=f'{ft_type}:{feat.id}' for upsert_feature()."""
    mock_responses = {
        "naturschutz": _make_fc([SAMPLE_NATURSCHUTZ_FEATURES[0]]),
        "wasserschutz": _make_fc([]),
    }

    connector.fetch = AsyncMock(return_value=mock_responses)
    connector.upsert_feature = AsyncMock(return_value="some-uuid")
    connector._update_staleness = AsyncMock()

    await connector.run()

    call_kwargs = connector.upsert_feature.call_args_list[0][1]
    assert "naturschutz" in call_kwargs["source_id"]
    assert "Naturschutzgebiet.1" in call_kwargs["source_id"]


# ---------------------------------------------------------------------------
# normalize() — unused but must return []
# ---------------------------------------------------------------------------

def test_normalize_returns_empty_list(connector) -> None:
    """normalize() is not used by run() and returns empty list."""
    result = connector.normalize(None)
    assert result == []


# ---------------------------------------------------------------------------
# Real-response cuts: GeoJSON features without a feature-level id
# ---------------------------------------------------------------------------

def _trimmed_polygon(first_points: list[list[float]]) -> dict:
    """MultiPolygon with one short closed ring cut from a real LUBW geometry."""
    ring = first_points + [first_points[0]]
    return {"type": "MultiPolygon", "coordinates": [[ring]]}


REAL_NSG_FEATURE = {
    "type": "Feature",
    "geometry": _trimmed_polygon([
        [10.10117441, 48.88238868],
        [10.09879585, 48.8818789],
        [10.09881205, 48.88166617],
        [10.09887825, 48.8813881],
    ]),
    "properties": {
        "GmlID": "Naturschutzgebiet.922386",
        "OBJECTID": 922386,
        "OBJECT_ID": 929001000029.0,
        "OBJEKT_NR": 929001000029.0,
        "OBJEKT_KENNUNG": "1.245",
        "OBJEKT": "Goldshöfer Sande",
        "FLAECHE": 466343,
        "STATUS": "verordnet",
        "SCHUTZSTATUS": "Naturschutzgebiet",
        "DIENSTSTELLE_NR": 92,
        "VO_DATUM": "19.12.2000",
    },
}

REAL_WSG_FEATURE = {
    "type": "Feature",
    "geometry": _trimmed_polygon([
        [9.92076818, 48.6421296],
        [9.92111298, 48.64222634],
        [9.92153629, 48.64236231],
        [9.9232264, 48.64291959],
    ]),
    "properties": {
        "GmlID": "Wasserschutzgebiet.2687282",
        "OBJECTID": 2687282,
        "WSG_NR": 1350000000001.0,
        "DIENSTSTELLE": "Landratsamt Heidenheim",
        "STATUS": "festgesetzt",
        "KURZNAME": "Brenztal",
        "LANGNAME": "WSG Fassungen im Brenztal, mehrere Kommunen        135/001/1",
        "GEMEINDE": "Dischingen",
    },
}


def _response(body: str, content_type: str = "application/json") -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.text = body
    resp.headers = {"content-type": content_type}
    resp.json = lambda: json.loads(body)
    resp.raise_for_status = MagicMock()
    return resp


def _patched_client(responses: list[MagicMock], calls: list[dict]) -> AsyncMock:
    queue = list(responses)

    async def mock_get(url, **kwargs):
        calls.append({"url": url, **kwargs})
        return queue.pop(0)

    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get = AsyncMock(side_effect=mock_get)
    return client


@pytest.mark.asyncio
async def test_fetch_sends_qualified_type_names_and_geojson_format(connector) -> None:
    """fetch() asks each endpoint for <T>:<T> as GEOJSON in EPSG:4326 with the town bbox."""
    empty = json.dumps({"type": "FeatureCollection", "features": []})
    calls: list[dict] = []
    with patch("httpx.AsyncClient") as cls:
        cls.return_value = _patched_client([_response(empty), _response(empty)], calls)
        result = await connector.fetch()

    assert set(result) == {"naturschutz", "wasserschutz"}
    assert [c["params"]["typeNames"] for c in calls] == [
        "Naturschutzgebiet:Naturschutzgebiet",
        "Wasserschutzgebiet:Wasserschutzgebiet",
    ]
    for call in calls:
        assert call["params"]["outputFormat"] == "GEOJSON"
        assert call["params"]["srsName"] == "EPSG:4326"
        assert call["params"]["BBOX"] == "48.76,9.97,48.9,10.22,urn:ogc:def:crs:EPSG::4326"
        assert "city-data-platform" in call["headers"]["User-Agent"]


@pytest.mark.asyncio
async def test_fetch_raises_on_xml_exception_report(connector) -> None:
    """An ExceptionReport answer (XML) raises a clear ValueError."""
    report = '<?xml version="1.0"?><ows:ExceptionReport><ows:Exception exceptionCode="InvalidParameterValue"/></ows:ExceptionReport>'
    calls: list[dict] = []
    with patch("httpx.AsyncClient") as cls:
        cls.return_value = _patched_client([_response(report, "text/xml")], calls)
        with pytest.raises(ValueError) as excinfo:
            await connector.fetch()

    message = str(excinfo.value)
    assert "naturschutz" in message
    assert "<?xml" in message


@pytest.mark.asyncio
async def test_run_builds_unique_ids_from_gmlid_and_names(connector) -> None:
    """Real features without a feature-level id get GmlID based source_ids and a name."""
    connector.fetch = AsyncMock(return_value={
        "naturschutz": _make_fc([REAL_NSG_FEATURE]),
        "wasserschutz": _make_fc([REAL_WSG_FEATURE]),
    })
    connector.upsert_feature = AsyncMock(return_value="uuid")
    connector._update_staleness = AsyncMock()

    await connector.run()

    calls = {c.kwargs["source_id"]: c.kwargs for c in connector.upsert_feature.call_args_list}
    assert set(calls) == {
        "naturschutz:Naturschutzgebiet.922386",
        "wasserschutz:Wasserschutzgebiet.2687282",
    }
    nsg = calls["naturschutz:Naturschutzgebiet.922386"]
    assert nsg["domain"] == "water"
    assert nsg["geometry_wkt"].startswith("POINT(")
    assert nsg["properties"]["name"] == "Goldshöfer Sande"
    assert nsg["properties"]["zone_type"] == "naturschutz"
    assert nsg["properties"]["OBJEKT"] == "Goldshöfer Sande"  # raw keys are kept
    wsg = calls["wasserschutz:Wasserschutzgebiet.2687282"]
    assert wsg["properties"]["name"] == "Brenztal"
    assert wsg["properties"]["zone_type"] == "wasserschutz"
    connector._update_staleness.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_wsg_name_falls_back_to_langname(connector) -> None:
    feature = json.loads(json.dumps(REAL_WSG_FEATURE))
    feature["properties"]["KURZNAME"] = None
    feature["properties"]["LANGNAME"] = "  WSG Waschhaldenquelle, Stadtwerke Aalen  "
    connector.fetch = AsyncMock(return_value={
        "naturschutz": _make_fc([]),
        "wasserschutz": _make_fc([feature]),
    })
    connector.upsert_feature = AsyncMock(return_value="uuid")
    connector._update_staleness = AsyncMock()

    await connector.run()

    props = connector.upsert_feature.call_args_list[0].kwargs["properties"]
    assert props["name"] == "WSG Waschhaldenquelle, Stadtwerke Aalen"


@pytest.mark.asyncio
async def test_run_skips_features_without_any_id(connector) -> None:
    """No feature id, GmlID or OBJECTID -> skipped, never a shared fallback id."""
    anonymous = {
        "type": "Feature",
        "geometry": _trimmed_polygon([[10.0, 48.8], [10.01, 48.8], [10.01, 48.81]]),
        "properties": {"OBJEKT": "ohne Kennung"},
    }
    connector.fetch = AsyncMock(return_value={
        "naturschutz": _make_fc([anonymous, dict(anonymous)]),
        "wasserschutz": _make_fc([]),
    })
    connector.upsert_feature = AsyncMock(return_value="uuid")
    connector._update_staleness = AsyncMock()

    await connector.run()

    connector.upsert_feature.assert_not_called()
    connector._update_staleness.assert_awaited_once()
