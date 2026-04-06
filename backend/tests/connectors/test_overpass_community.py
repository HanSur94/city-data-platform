"""Tests for OverpassCommunityConnector — Phase 8, Plan 01.

Tests verify category mapping for community POIs (school, healthcare, park, waste),
coordinate extraction from node/way elements, and source_id format.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.connectors.overpass_community import OverpassCommunityConnector
from app.config import ConnectorConfig, Town, TownBbox


@pytest.fixture
def community_config() -> ConnectorConfig:
    return ConnectorConfig(
        connector_class="OverpassCommunityConnector",
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
def connector(community_config: ConnectorConfig, aalen_town: Town) -> OverpassCommunityConnector:
    return OverpassCommunityConnector(community_config, aalen_town)


def _make_overpass_response(elements: list[dict]) -> dict:
    return {"elements": elements}


def test_school_category(connector: OverpassCommunityConnector) -> None:
    """amenity=school maps to category='school', domain='community'."""
    elements = [
        {
            "type": "node",
            "id": 1001,
            "lat": 48.84,
            "lon": 10.09,
            "tags": {"amenity": "school", "name": "Grundschule Aalen"},
        }
    ]
    raw = _make_overpass_response(elements)
    mappings = connector._extract_mappings(raw)
    assert len(mappings) == 1
    assert mappings[0]["category"] == "school"
    assert mappings[0]["domain"] == "community"


def test_kindergarten_category(connector: OverpassCommunityConnector) -> None:
    """amenity=kindergarten maps to category='school', domain='community'."""
    elements = [
        {
            "type": "node",
            "id": 1002,
            "lat": 48.845,
            "lon": 10.095,
            "tags": {"amenity": "kindergarten", "name": "Kita Sonnenschein"},
        }
    ]
    raw = _make_overpass_response(elements)
    mappings = connector._extract_mappings(raw)
    assert len(mappings) == 1
    assert mappings[0]["category"] == "school"
    assert mappings[0]["domain"] == "community"


def test_healthcare_category(connector: OverpassCommunityConnector) -> None:
    """amenity in pharmacy/hospital/doctors/clinic/dentist maps to category='healthcare'."""
    healthcare_tags = ["pharmacy", "hospital", "doctors", "clinic", "dentist"]
    for tag in healthcare_tags:
        elements = [
            {
                "type": "node",
                "id": 2000 + healthcare_tags.index(tag),
                "lat": 48.84,
                "lon": 10.09,
                "tags": {"amenity": tag},
            }
        ]
        raw = _make_overpass_response(elements)
        mappings = connector._extract_mappings(raw)
        assert len(mappings) == 1, f"Expected 1 mapping for {tag}"
        assert mappings[0]["category"] == "healthcare", f"Expected 'healthcare' for amenity={tag}"
        assert mappings[0]["domain"] == "community"


def test_park_category(connector: OverpassCommunityConnector) -> None:
    """leisure in park/playground/sports_centre/pitch maps to category='park'."""
    park_tags = ["park", "playground", "sports_centre", "pitch"]
    for tag in park_tags:
        elements = [
            {
                "type": "node",
                "id": 3000 + park_tags.index(tag),
                "lat": 48.84,
                "lon": 10.09,
                "tags": {"leisure": tag},
            }
        ]
        raw = _make_overpass_response(elements)
        mappings = connector._extract_mappings(raw)
        assert len(mappings) == 1, f"Expected 1 mapping for {tag}"
        assert mappings[0]["category"] == "park", f"Expected 'park' for leisure={tag}"
        assert mappings[0]["domain"] == "community"


def test_waste_category(connector: OverpassCommunityConnector) -> None:
    """amenity in recycling/waste_disposal maps to category='waste'."""
    waste_tags = ["recycling", "waste_disposal"]
    for tag in waste_tags:
        elements = [
            {
                "type": "node",
                "id": 4000 + waste_tags.index(tag),
                "lat": 48.84,
                "lon": 10.09,
                "tags": {"amenity": tag},
            }
        ]
        raw = _make_overpass_response(elements)
        mappings = connector._extract_mappings(raw)
        assert len(mappings) == 1, f"Expected 1 mapping for {tag}"
        assert mappings[0]["category"] == "waste", f"Expected 'waste' for amenity={tag}"
        assert mappings[0]["domain"] == "community"


def test_way_element_uses_center_coordinates(connector: OverpassCommunityConnector) -> None:
    """Way elements use center.lat/center.lon, not top-level lat/lon."""
    elements = [
        {
            "type": "way",
            "id": 5001,
            "center": {"lat": 48.860, "lon": 10.110},
            "tags": {"amenity": "school", "name": "Gymnasium Aalen"},
        }
    ]
    raw = _make_overpass_response(elements)
    mappings = connector._extract_mappings(raw)
    assert len(mappings) == 1
    assert mappings[0]["lat"] == pytest.approx(48.860)
    assert mappings[0]["lon"] == pytest.approx(10.110)


def test_missing_coordinates_skipped(connector: OverpassCommunityConnector) -> None:
    """Elements with missing coordinates (no lat/lon and no center) are skipped."""
    elements = [
        {
            "type": "way",
            "id": 6001,
            "tags": {"amenity": "school", "name": "No Location School"},
            # No center, no lat/lon
        }
    ]
    raw = _make_overpass_response(elements)
    mappings = connector._extract_mappings(raw)
    assert len(mappings) == 0


def test_source_id_format(connector: OverpassCommunityConnector) -> None:
    """source_id is formatted as 'osm:{type}:{id}'."""
    elements = [
        {
            "type": "node",
            "id": 7001,
            "lat": 48.84,
            "lon": 10.09,
            "tags": {"amenity": "school"},
        },
        {
            "type": "way",
            "id": 7002,
            "center": {"lat": 48.85, "lon": 10.10},
            "tags": {"leisure": "park"},
        },
    ]
    raw = _make_overpass_response(elements)
    mappings = connector._extract_mappings(raw)
    assert len(mappings) == 2
    assert mappings[0]["source_id"] == "osm:node:7001"
    assert mappings[1]["source_id"] == "osm:way:7002"


@pytest.mark.asyncio
async def test_run_upserts_features(connector: OverpassCommunityConnector) -> None:
    """run() calls fetch, upserts all valid elements, then updates staleness."""
    mock_response = _make_overpass_response([
        {
            "type": "node",
            "id": 8001,
            "lat": 48.84,
            "lon": 10.09,
            "tags": {"amenity": "school", "name": "Test School"},
        }
    ])

    with (
        patch.object(connector, "fetch", new=AsyncMock(return_value=mock_response)),
        patch.object(connector, "upsert_feature", new=AsyncMock(return_value="uuid-1")),
        patch.object(connector, "_update_staleness", new=AsyncMock()),
    ):
        await connector.run()
        assert connector.upsert_feature.called  # type: ignore[attr-defined]
        assert connector._update_staleness.called  # type: ignore[attr-defined]
