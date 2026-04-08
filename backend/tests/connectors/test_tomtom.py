"""Tests for TomTomConnector — Phase 11, Plan 01 (REQ-TRAFFIC-01/03/04).

TomTom Flow Segment Data API provides real-time speed/congestion data for road segments.
Tests cover: normalize() congestion ratio, rush hour detection, adaptive poll intervals,
fetch() URL construction, grid-scan discovery, cache, FRC filtering, deduplication.

License: TomTom Traffic Flow API
"""
from __future__ import annotations

import json
import os
import time
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

from app.config import ConnectorConfig, Town, TownBbox
from app.connectors.base import Observation


# ---------------------------------------------------------------------------
# Sample TomTom API response
# ---------------------------------------------------------------------------

SAMPLE_TOMTOM_RESPONSE = {
    "flowSegmentData": {
        "frc": "FRC2",
        "currentSpeed": 45,
        "freeFlowSpeed": 60,
        "currentTravelTime": 120,
        "freeFlowTravelTime": 90,
        "confidence": 0.95,
        "coordinates": {
            "coordinate": [
                {"latitude": 48.840, "longitude": 10.090},
                {"latitude": 48.841, "longitude": 10.092},
                {"latitude": 48.842, "longitude": 10.095},
            ]
        },
    }
}

# Updated SAMPLE_SEGMENT_DEF to match new discovery-produced shape
SAMPLE_SEGMENT_DEF = {
    "id": "48.84000,10.09000|48.84200,10.09500",
    "name": "FRC2",
    "lat": 48.840,
    "lon": 10.090,
    "frc": "FRC2",
    "road_key": "48.84000,10.09000|48.84200,10.09500",
}


@pytest.fixture
def tomtom_config() -> ConnectorConfig:
    return ConnectorConfig(
        connector_class="TomTomConnector",
        poll_interval_seconds=600,
        enabled=True,
        config={"api_key": "test-api-key-12345"},
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
def connector(tomtom_config, aalen_town):
    from app.connectors.tomtom import TomTomConnector
    return TomTomConnector(config=tomtom_config, town=aalen_town)


# ---------------------------------------------------------------------------
# Test 1: normalize() produces correct Observations
# ---------------------------------------------------------------------------

def test_normalize_produces_observations_with_traffic_domain(connector) -> None:
    """normalize() with sample TomTom response produces Observations with domain='traffic'."""
    road_key = SAMPLE_SEGMENT_DEF["id"]
    connector._feature_ids = {road_key: "fake-uuid-001"}

    raw = [(SAMPLE_SEGMENT_DEF, SAMPLE_TOMTOM_RESPONSE)]
    observations = connector.normalize(raw)

    assert len(observations) == 1
    obs = observations[0]
    assert isinstance(obs, Observation)
    assert obs.domain == "traffic"
    assert "speed_avg_kmh" in obs.values
    assert "congestion_level" in obs.values


# ---------------------------------------------------------------------------
# Test 2: congestion_ratio computation and level mapping
# ---------------------------------------------------------------------------

def test_congestion_ratio_free(connector) -> None:
    """congestion_ratio >= 0.75 -> 'free'."""
    road_key = SAMPLE_SEGMENT_DEF["id"]
    connector._feature_ids = {road_key: "fake-uuid-001"}
    response = _make_response(current_speed=50, freeflow_speed=60)  # ratio=0.833
    raw = [(SAMPLE_SEGMENT_DEF, response)]
    observations = connector.normalize(raw)
    assert observations[0].values["congestion_level"] == "free"


def test_congestion_ratio_moderate(connector) -> None:
    """0.50 <= congestion_ratio < 0.75 -> 'moderate'."""
    road_key = SAMPLE_SEGMENT_DEF["id"]
    connector._feature_ids = {road_key: "fake-uuid-001"}
    response = _make_response(current_speed=40, freeflow_speed=60)  # ratio=0.667
    raw = [(SAMPLE_SEGMENT_DEF, response)]
    observations = connector.normalize(raw)
    assert observations[0].values["congestion_level"] == "moderate"


def test_congestion_ratio_congested(connector) -> None:
    """congestion_ratio < 0.50 -> 'congested'."""
    road_key = SAMPLE_SEGMENT_DEF["id"]
    connector._feature_ids = {road_key: "fake-uuid-001"}
    response = _make_response(current_speed=20, freeflow_speed=60)  # ratio=0.333
    raw = [(SAMPLE_SEGMENT_DEF, response)]
    observations = connector.normalize(raw)
    assert observations[0].values["congestion_level"] == "congested"


def test_congestion_ratio_severe(connector) -> None:
    """congestion_ratio < 0.25 -> 'congested' (severe)."""
    road_key = SAMPLE_SEGMENT_DEF["id"]
    connector._feature_ids = {road_key: "fake-uuid-001"}
    response = _make_response(current_speed=10, freeflow_speed=60)  # ratio=0.167
    raw = [(SAMPLE_SEGMENT_DEF, response)]
    observations = connector.normalize(raw)
    assert observations[0].values["congestion_level"] == "congested"


# ---------------------------------------------------------------------------
# Test 3: one Observation per road segment
# ---------------------------------------------------------------------------

def test_normalize_one_observation_per_segment(connector) -> None:
    """normalize() produces one Observation per road segment in the response."""
    seg1 = {
        "id": "48.84000,10.09000|48.84100,10.09200",
        "name": "FRC2",
        "lat": 48.840,
        "lon": 10.090,
        "frc": "FRC2",
        "road_key": "48.84000,10.09000|48.84100,10.09200",
    }
    seg2 = {
        "id": "48.85000,10.09500|48.85200,10.09800",
        "name": "FRC1",
        "lat": 48.850,
        "lon": 10.095,
        "frc": "FRC1",
        "road_key": "48.85000,10.09500|48.85200,10.09800",
    }
    connector._feature_ids = {
        seg1["id"]: "fake-uuid-001",
        seg2["id"]: "fake-uuid-002",
    }
    raw = [
        (seg1, _make_response(45, 60)),
        (seg2, _make_response(30, 50)),
    ]
    observations = connector.normalize(raw)
    assert len(observations) == 2


# ---------------------------------------------------------------------------
# Test 4: _is_rush_hour()
# ---------------------------------------------------------------------------

def test_is_rush_hour_morning(connector) -> None:
    """_is_rush_hour() returns True for hours 6-8 in Europe/Berlin."""
    berlin_tz = ZoneInfo("Europe/Berlin")
    with patch("app.connectors.tomtom._now_berlin") as mock_now:
        # 7:30 AM Berlin time
        mock_now.return_value = datetime(2024, 6, 15, 7, 30, tzinfo=berlin_tz)
        assert connector._is_rush_hour() is True


def test_is_rush_hour_evening(connector) -> None:
    """_is_rush_hour() returns True for hours 16-18 in Europe/Berlin."""
    berlin_tz = ZoneInfo("Europe/Berlin")
    with patch("app.connectors.tomtom._now_berlin") as mock_now:
        mock_now.return_value = datetime(2024, 6, 15, 17, 0, tzinfo=berlin_tz)
        assert connector._is_rush_hour() is True


def test_is_not_rush_hour_midday(connector) -> None:
    """_is_rush_hour() returns False for midday hours."""
    berlin_tz = ZoneInfo("Europe/Berlin")
    with patch("app.connectors.tomtom._now_berlin") as mock_now:
        mock_now.return_value = datetime(2024, 6, 15, 12, 0, tzinfo=berlin_tz)
        assert connector._is_rush_hour() is False


def test_is_not_rush_hour_night(connector) -> None:
    """_is_rush_hour() returns False for night hours."""
    berlin_tz = ZoneInfo("Europe/Berlin")
    with patch("app.connectors.tomtom._now_berlin") as mock_now:
        mock_now.return_value = datetime(2024, 6, 15, 22, 0, tzinfo=berlin_tz)
        assert connector._is_rush_hour() is False


# ---------------------------------------------------------------------------
# Test 5: _get_poll_interval()
# ---------------------------------------------------------------------------

def test_get_poll_interval_rush(connector) -> None:
    """_get_poll_interval() returns 600 during rush hours."""
    with patch.object(connector, "_is_rush_hour", return_value=True):
        assert connector._get_poll_interval() == 600


def test_get_poll_interval_offpeak(connector) -> None:
    """_get_poll_interval() returns 1800 during off-peak."""
    with patch.object(connector, "_is_rush_hour", return_value=False):
        assert connector._get_poll_interval() == 1800


# ---------------------------------------------------------------------------
# Test 6: fetch() calls correct TomTom endpoint (uses cached segment list)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fetch_calls_tomtom_endpoint(connector) -> None:
    """fetch() calls the TomTom Flow Segment Data endpoint with API key using cached segments."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SAMPLE_TOMTOM_RESPONSE
    mock_response.raise_for_status = MagicMock()

    # Provide a small cached segment list so discovery is skipped
    cached_segments = [SAMPLE_SEGMENT_DEF]

    with patch("httpx.AsyncClient") as mock_cls, \
         patch.object(connector, "_load_cache", return_value=cached_segments):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_client

        result = await connector.fetch()

    # Should have called get() for each cached segment
    assert mock_client.get.call_count > 0
    # Check first call URL contains tomtom API domain
    first_call_url = mock_client.get.call_args_list[0][0][0]
    assert "api.tomtom.com" in first_call_url
    assert "test-api-key-12345" in first_call_url
    assert "flowSegmentData" in first_call_url


# ---------------------------------------------------------------------------
# Test 7: _generate_grid_points covers entire bbox
# ---------------------------------------------------------------------------

def test_generate_grid_points_covers_bbox() -> None:
    """_generate_grid_points produces points covering entire bbox."""
    from app.connectors.tomtom import _generate_grid_points
    from app.config import TownBbox

    # Small bbox: 0.02 degree span with 0.008 step -> 3-4 points per axis
    bbox = TownBbox(lon_min=10.0, lat_min=48.0, lon_max=10.02, lat_max=48.02)
    points = _generate_grid_points(bbox, step=0.008)

    assert len(points) > 0
    # All points within bbox bounds
    for lat, lon in points:
        assert bbox.lat_min <= lat <= bbox.lat_max
        assert bbox.lon_min <= lon <= bbox.lon_max

    # Should have at least a 3x3 grid for 0.02 span / 0.008 step
    assert len(points) >= 9


# ---------------------------------------------------------------------------
# Test 8: _make_road_key is deterministic
# ---------------------------------------------------------------------------

def test_make_road_key_deterministic() -> None:
    """_make_road_key produces same key for same coordinates."""
    from app.connectors.tomtom import _make_road_key

    coords = [
        {"latitude": 48.84000, "longitude": 10.09000},
        {"latitude": 48.84100, "longitude": 10.09200},
        {"latitude": 48.84200, "longitude": 10.09500},
    ]
    key1 = _make_road_key(coords)
    key2 = _make_road_key(coords)
    assert key1 == key2
    # Should use first and last coordinate
    assert "48.84000" in key1
    assert "10.09000" in key1
    assert "48.84200" in key1
    assert "10.09500" in key1


def test_make_road_key_different_segments() -> None:
    """_make_road_key produces different keys for different coordinate pairs."""
    from app.connectors.tomtom import _make_road_key

    coords_a = [
        {"latitude": 48.840, "longitude": 10.090},
        {"latitude": 48.842, "longitude": 10.095},
    ]
    coords_b = [
        {"latitude": 48.850, "longitude": 10.100},
        {"latitude": 48.852, "longitude": 10.105},
    ]
    assert _make_road_key(coords_a) != _make_road_key(coords_b)


# ---------------------------------------------------------------------------
# Test 9: FRC filtering in discover_segments
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_discover_filters_frc4_plus(connector) -> None:
    """_discover_segments keeps only FRC0-FRC3, discards FRC4+."""
    from app.connectors.tomtom import _generate_grid_points

    frc4_response = {
        "flowSegmentData": {
            "frc": "FRC4",
            "currentSpeed": 40,
            "freeFlowSpeed": 50,
            "confidence": 0.9,
            "coordinates": {
                "coordinate": [
                    {"latitude": 48.840, "longitude": 10.090},
                    {"latitude": 48.842, "longitude": 10.095},
                ]
            },
        }
    }
    frc2_response = {
        "flowSegmentData": {
            "frc": "FRC2",
            "currentSpeed": 45,
            "freeFlowSpeed": 60,
            "confidence": 0.95,
            "coordinates": {
                "coordinate": [
                    {"latitude": 48.850, "longitude": 10.100},
                    {"latitude": 48.852, "longitude": 10.105},
                ]
            },
        }
    }

    # Mock grid to produce just 2 probe points
    mock_points = [(48.840, 10.090), (48.850, 10.100)]
    responses = [frc4_response, frc2_response]
    call_count = [0]

    async def mock_get(url):
        r = MagicMock()
        r.raise_for_status = MagicMock()
        r.json.return_value = responses[call_count[0]]
        call_count[0] += 1
        return r

    with patch("app.connectors.tomtom._generate_grid_points", return_value=mock_points), \
         patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = mock_get
        mock_cls.return_value = mock_client

        with patch.object(connector, "_save_cache"):
            segments = await connector._discover_segments()

    # Only FRC2 segment should be kept
    assert len(segments) == 1
    assert segments[0]["frc"] == "FRC2"


# ---------------------------------------------------------------------------
# Test 10: Deduplication in discover_segments
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_discover_deduplicates_same_segment(connector) -> None:
    """Two probes returning same coordinates produce only one segment."""
    same_response = {
        "flowSegmentData": {
            "frc": "FRC2",
            "currentSpeed": 45,
            "freeFlowSpeed": 60,
            "confidence": 0.9,
            "coordinates": {
                "coordinate": [
                    {"latitude": 48.840, "longitude": 10.090},
                    {"latitude": 48.842, "longitude": 10.095},
                ]
            },
        }
    }

    mock_points = [(48.840, 10.090), (48.841, 10.091)]  # Two different probe points

    async def mock_get(url):
        r = MagicMock()
        r.raise_for_status = MagicMock()
        r.json.return_value = same_response
        return r

    with patch("app.connectors.tomtom._generate_grid_points", return_value=mock_points), \
         patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = mock_get
        mock_cls.return_value = mock_client

        with patch.object(connector, "_save_cache"):
            segments = await connector._discover_segments()

    # Both probes return the same segment — should deduplicate to 1
    assert len(segments) == 1


# ---------------------------------------------------------------------------
# Test 11: Cache roundtrip
# ---------------------------------------------------------------------------

def test_cache_roundtrip(connector, tmp_path) -> None:
    """_save_cache + _load_cache round-trip preserves segment data."""
    test_segments = [
        {
            "id": "48.84000,10.09000|48.84200,10.09500",
            "name": "FRC2",
            "lat": 48.840,
            "lon": 10.090,
            "frc": "FRC2",
            "road_key": "48.84000,10.09000|48.84200,10.09500",
        }
    ]

    cache_file = tmp_path / "test_cache.json"

    with patch.object(connector, "_cache_path", return_value=cache_file):
        connector._save_cache(test_segments)
        loaded = connector._load_cache()

    assert loaded is not None
    assert len(loaded) == 1
    assert loaded[0]["frc"] == "FRC2"
    assert loaded[0]["road_key"] == test_segments[0]["road_key"]


# ---------------------------------------------------------------------------
# Test 12: Cache returns None when file missing
# ---------------------------------------------------------------------------

def test_load_cache_returns_none_when_missing(connector, tmp_path) -> None:
    """_load_cache returns None when cache file does not exist."""
    missing_path = tmp_path / "nonexistent.json"

    with patch.object(connector, "_cache_path", return_value=missing_path):
        result = connector._load_cache()

    assert result is None


# ---------------------------------------------------------------------------
# Test 13: Cache returns None when expired
# ---------------------------------------------------------------------------

def test_cache_expired_returns_none(connector, tmp_path) -> None:
    """_load_cache returns None when cache is older than 7 days."""
    test_segments = [{"id": "test", "name": "FRC1", "lat": 48.0, "lon": 10.0, "frc": "FRC1", "road_key": "test"}]
    cache_file = tmp_path / "expired_cache.json"
    cache_file.write_text(json.dumps(test_segments))

    # Set mtime to 8 days ago
    eight_days_ago = time.time() - (8 * 24 * 3600)
    os.utime(cache_file, (eight_days_ago, eight_days_ago))

    with patch.object(connector, "_cache_path", return_value=cache_file):
        result = connector._load_cache()

    assert result is None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(current_speed: float, freeflow_speed: float) -> dict:
    """Create a TomTom-like API response with given speeds."""
    return {
        "flowSegmentData": {
            "frc": "FRC2",
            "currentSpeed": current_speed,
            "freeFlowSpeed": freeflow_speed,
            "currentTravelTime": 120,
            "freeFlowTravelTime": 90,
            "confidence": 0.90,
            "coordinates": {
                "coordinate": [
                    {"latitude": 48.840, "longitude": 10.090},
                    {"latitude": 48.841, "longitude": 10.092},
                ]
            },
        }
    }
