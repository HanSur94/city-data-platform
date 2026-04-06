"""Tests for OverpassRoadworksConnector — Phase 8, Plan 01.

Tests verify domain/category mapping for roadworks, coordinate handling,
and graceful handling of empty result sets.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.connectors.overpass_roadworks import OverpassRoadworksConnector
from app.config import ConnectorConfig, Town, TownBbox


@pytest.fixture
def roadworks_config() -> ConnectorConfig:
    return ConnectorConfig(
        connector_class="OverpassRoadworksConnector",
        poll_interval_seconds=3600,
        enabled=True,
        config={},
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
def connector(roadworks_config: ConnectorConfig, aalen_town: Town) -> OverpassRoadworksConnector:
    return OverpassRoadworksConnector(roadworks_config, aalen_town)


def _make_overpass_response(elements: list[dict]) -> dict:
    return {"elements": elements}


def test_roadworks_domain_and_category(connector: OverpassRoadworksConnector) -> None:
    """highway=construction elements map to domain='infrastructure', category='roadwork'."""
    elements = [
        {
            "type": "node",
            "id": 9001,
            "lat": 48.84,
            "lon": 10.09,
            "tags": {"highway": "construction", "name": "B29 Baustelle"},
        }
    ]
    raw = _make_overpass_response(elements)
    mappings = connector._extract_mappings(raw)
    assert len(mappings) == 1
    assert mappings[0]["domain"] == "infrastructure"
    assert mappings[0]["category"] == "roadwork"


def test_roadworks_way_element_center_coordinates(connector: OverpassRoadworksConnector) -> None:
    """Way elements use center.lat/center.lon for coordinates."""
    elements = [
        {
            "type": "way",
            "id": 9002,
            "center": {"lat": 48.860, "lon": 10.110},
            "tags": {"highway": "construction"},
        }
    ]
    raw = _make_overpass_response(elements)
    mappings = connector._extract_mappings(raw)
    assert len(mappings) == 1
    assert mappings[0]["lat"] == pytest.approx(48.860)
    assert mappings[0]["lon"] == pytest.approx(10.110)


def test_roadworks_source_id_format(connector: OverpassRoadworksConnector) -> None:
    """source_id is formatted as 'osm:{type}:{id}'."""
    elements = [
        {
            "type": "node",
            "id": 9003,
            "lat": 48.84,
            "lon": 10.09,
            "tags": {"highway": "construction"},
        },
        {
            "type": "way",
            "id": 9004,
            "center": {"lat": 48.85, "lon": 10.10},
            "tags": {"highway": "construction"},
        },
    ]
    raw = _make_overpass_response(elements)
    mappings = connector._extract_mappings(raw)
    assert len(mappings) == 2
    assert mappings[0]["source_id"] == "osm:node:9003"
    assert mappings[1]["source_id"] == "osm:way:9004"


def test_roadworks_includes_name_and_construction_tags(connector: OverpassRoadworksConnector) -> None:
    """Properties include name and highway construction details from OSM tags."""
    elements = [
        {
            "type": "node",
            "id": 9005,
            "lat": 48.84,
            "lon": 10.09,
            "tags": {
                "highway": "construction",
                "construction": "primary",
                "name": "Hauptstraße Baustelle",
                "note": "Kanalsanierung bis Ende 2026",
            },
        }
    ]
    raw = _make_overpass_response(elements)
    mappings = connector._extract_mappings(raw)
    assert len(mappings) == 1
    # Tags are preserved in the mapping
    assert mappings[0]["tags"]["name"] == "Hauptstraße Baustelle"
    assert mappings[0]["tags"]["construction"] == "primary"
    assert mappings[0]["tags"]["note"] == "Kanalsanierung bis Ende 2026"


@pytest.mark.asyncio
async def test_empty_results_handled_gracefully(connector: OverpassRoadworksConnector) -> None:
    """run() completes without error when no roadworks are found."""
    empty_response = _make_overpass_response([])

    with (
        patch.object(connector, "fetch", new=AsyncMock(return_value=empty_response)),
        patch.object(connector, "upsert_feature", new=AsyncMock(return_value="uuid-1")),
        patch.object(connector, "_update_staleness", new=AsyncMock()),
    ):
        # Should not raise any exception
        await connector.run()
        # upsert_feature should NOT be called when there are no roadworks
        assert not connector.upsert_feature.called  # type: ignore[attr-defined]
        # staleness should still be updated
        assert connector._update_staleness.called  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_run_upserts_roadwork_features(connector: OverpassRoadworksConnector) -> None:
    """run() upserts features and updates staleness when roadworks are found."""
    mock_response = _make_overpass_response([
        {
            "type": "node",
            "id": 9006,
            "lat": 48.84,
            "lon": 10.09,
            "tags": {"highway": "construction", "name": "Test Baustelle"},
        }
    ])

    with (
        patch.object(connector, "fetch", new=AsyncMock(return_value=mock_response)),
        patch.object(connector, "upsert_feature", new=AsyncMock(return_value="uuid-rw")),
        patch.object(connector, "_update_staleness", new=AsyncMock()),
    ):
        await connector.run()
        assert connector.upsert_feature.called  # type: ignore[attr-defined]
        assert connector._update_staleness.called  # type: ignore[attr-defined]

        # Verify upsert was called with correct domain
        call_kwargs = connector.upsert_feature.call_args.kwargs  # type: ignore[attr-defined]
        assert call_kwargs["domain"] == "infrastructure"


def test_normalize_returns_empty(connector: OverpassRoadworksConnector) -> None:
    """normalize() returns empty list — roadworks connector is features-only."""
    result = connector.normalize({})
    assert result == []
