"""Tests for CyclingInfraConnector — Phase 17, Plan 01.

Tests verify infra_type classification from OSM cycling tags,
domain assignment, and edge cases.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.connectors.cycling import CyclingInfraConnector
from app.config import ConnectorConfig, Town, TownBbox


@pytest.fixture
def cycling_config() -> ConnectorConfig:
    return ConnectorConfig(
        connector_class="CyclingInfraConnector",
        poll_interval_seconds=86400,
        enabled=True,
        config={"attribution": "OpenStreetMap contributors, ODbL"},
    )


@pytest.fixture
def aalen_town() -> Town:
    return Town(
        id="aalen",
        display_name="Aalen (Wuerttemberg)",
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
def connector(cycling_config: ConnectorConfig, aalen_town: Town) -> CyclingInfraConnector:
    return CyclingInfraConnector(cycling_config, aalen_town)


def _make_overpass_response(elements: list[dict]) -> dict:
    return {"elements": elements}


def test_normalize_cycleway_separated(connector: CyclingInfraConnector) -> None:
    """highway=cycleway -> infra_type='separated'."""
    raw = _make_overpass_response([
        {
            "type": "way",
            "id": 1001,
            "tags": {"highway": "cycleway", "name": "Radweg Aalen"},
            "geometry": [{"lat": 48.84, "lon": 10.09}, {"lat": 48.85, "lon": 10.10}],
        }
    ])
    result = connector.normalize(raw)
    assert len(result) == 1
    assert result[0].values["infra_type"] == "separated"
    assert result[0].domain == "infrastructure"
    assert result[0].values["feature_type"] == "cycling"


def test_normalize_lane(connector: CyclingInfraConnector) -> None:
    """cycleway=lane -> infra_type='lane'."""
    raw = _make_overpass_response([
        {
            "type": "way",
            "id": 1002,
            "tags": {"highway": "secondary", "cycleway": "lane"},
            "geometry": [{"lat": 48.84, "lon": 10.09}, {"lat": 48.85, "lon": 10.10}],
        }
    ])
    result = connector.normalize(raw)
    assert len(result) == 1
    assert result[0].values["infra_type"] == "lane"


def test_normalize_lane_left(connector: CyclingInfraConnector) -> None:
    """cycleway:left=lane -> infra_type='lane'."""
    raw = _make_overpass_response([
        {
            "type": "way",
            "id": 1003,
            "tags": {"highway": "primary", "cycleway:left": "lane"},
            "geometry": [{"lat": 48.84, "lon": 10.09}, {"lat": 48.85, "lon": 10.10}],
        }
    ])
    result = connector.normalize(raw)
    assert result[0].values["infra_type"] == "lane"


def test_normalize_lane_right(connector: CyclingInfraConnector) -> None:
    """cycleway:right=lane -> infra_type='lane'."""
    raw = _make_overpass_response([
        {
            "type": "way",
            "id": 1004,
            "tags": {"highway": "tertiary", "cycleway:right": "lane"},
            "geometry": [{"lat": 48.84, "lon": 10.09}, {"lat": 48.85, "lon": 10.10}],
        }
    ])
    result = connector.normalize(raw)
    assert result[0].values["infra_type"] == "lane"


def test_normalize_advisory(connector: CyclingInfraConnector) -> None:
    """cycleway=advisory -> infra_type='advisory'."""
    raw = _make_overpass_response([
        {
            "type": "way",
            "id": 1005,
            "tags": {"highway": "secondary", "cycleway": "advisory"},
            "geometry": [{"lat": 48.84, "lon": 10.09}, {"lat": 48.85, "lon": 10.10}],
        }
    ])
    result = connector.normalize(raw)
    assert result[0].values["infra_type"] == "advisory"


def test_normalize_shared(connector: CyclingInfraConnector) -> None:
    """cycleway=shared_lane -> infra_type='shared'."""
    raw = _make_overpass_response([
        {
            "type": "way",
            "id": 1006,
            "tags": {"highway": "secondary", "cycleway": "shared_lane"},
            "geometry": [{"lat": 48.84, "lon": 10.09}, {"lat": 48.85, "lon": 10.10}],
        }
    ])
    result = connector.normalize(raw)
    assert result[0].values["infra_type"] == "shared"


def test_normalize_bicycle_designated(connector: CyclingInfraConnector) -> None:
    """bicycle=designated -> infra_type='shared'."""
    raw = _make_overpass_response([
        {
            "type": "way",
            "id": 1007,
            "tags": {"highway": "tertiary", "bicycle": "designated"},
            "geometry": [{"lat": 48.84, "lon": 10.09}, {"lat": 48.85, "lon": 10.10}],
        }
    ])
    result = connector.normalize(raw)
    assert result[0].values["infra_type"] == "shared"


def test_normalize_no_cycling_tags_primary(connector: CyclingInfraConnector) -> None:
    """Primary road with no cycling tags -> infra_type='none'."""
    raw = _make_overpass_response([
        {
            "type": "way",
            "id": 1008,
            "tags": {"highway": "primary", "name": "B19"},
            "geometry": [{"lat": 48.84, "lon": 10.09}, {"lat": 48.85, "lon": 10.10}],
        }
    ])
    result = connector.normalize(raw)
    assert len(result) == 1
    assert result[0].values["infra_type"] == "none"


def test_normalize_residential_no_tags_skipped(connector: CyclingInfraConnector) -> None:
    """Residential road with no cycling tags -> skipped."""
    raw = _make_overpass_response([
        {
            "type": "way",
            "id": 1009,
            "tags": {"highway": "residential", "name": "Wohnstrasse"},
            "geometry": [{"lat": 48.84, "lon": 10.09}, {"lat": 48.85, "lon": 10.10}],
        }
    ])
    result = connector.normalize(raw)
    assert len(result) == 0


def test_normalize_empty_elements(connector: CyclingInfraConnector) -> None:
    """Empty elements returns []."""
    raw = _make_overpass_response([])
    result = connector.normalize(raw)
    assert result == []


def test_normalize_road_name(connector: CyclingInfraConnector) -> None:
    """road_name is extracted from tags."""
    raw = _make_overpass_response([
        {
            "type": "way",
            "id": 1010,
            "tags": {"highway": "cycleway", "name": "Aalener Radweg"},
            "geometry": [{"lat": 48.84, "lon": 10.09}, {"lat": 48.85, "lon": 10.10}],
        }
    ])
    result = connector.normalize(raw)
    assert result[0].values["road_name"] == "Aalener Radweg"


def test_normalize_source_id_format(connector: CyclingInfraConnector) -> None:
    """source_id uses 'cycling:way:{id}' format."""
    raw = _make_overpass_response([
        {
            "type": "way",
            "id": 1011,
            "tags": {"highway": "cycleway"},
            "geometry": [{"lat": 48.84, "lon": 10.09}, {"lat": 48.85, "lon": 10.10}],
        }
    ])
    result = connector.normalize(raw)
    assert result[0].source_id == "cycling:way:1011"
