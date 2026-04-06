"""Tests for LubwWfsConnector.

Tests:
- run() with 2 features per endpoint calls upsert_feature() 4 times
- run() with empty features list completes without error
- normalize() returns [] (unused by run())
- LubwWfsFeatureCollection validates with empty features list
- Properties stored as-is from WFS response
"""
from __future__ import annotations

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
