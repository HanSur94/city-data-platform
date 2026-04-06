"""Tests for TomTomConnector — Phase 11, Plan 01 (REQ-TRAFFIC-01/03/04).

TomTom Flow Segment Data API provides real-time speed/congestion data for road segments.
Tests cover: normalize() congestion ratio, rush hour detection, adaptive poll intervals,
fetch() URL construction.

License: TomTom Traffic Flow API
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
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

SAMPLE_SEGMENT_DEF = {
    "id": "b29-east-01",
    "name": "B29",
    "lat": 48.840,
    "lon": 10.090,
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
    # Pre-populate feature_ids so normalize can map segment IDs
    connector._feature_ids = {"b29-east-01": "fake-uuid-001"}

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
    connector._feature_ids = {"b29-east-01": "fake-uuid-001"}
    response = _make_response(current_speed=50, freeflow_speed=60)  # ratio=0.833
    raw = [(SAMPLE_SEGMENT_DEF, response)]
    observations = connector.normalize(raw)
    assert observations[0].values["congestion_level"] == "free"


def test_congestion_ratio_moderate(connector) -> None:
    """0.50 <= congestion_ratio < 0.75 -> 'moderate'."""
    connector._feature_ids = {"b29-east-01": "fake-uuid-001"}
    response = _make_response(current_speed=40, freeflow_speed=60)  # ratio=0.667
    raw = [(SAMPLE_SEGMENT_DEF, response)]
    observations = connector.normalize(raw)
    assert observations[0].values["congestion_level"] == "moderate"


def test_congestion_ratio_congested(connector) -> None:
    """congestion_ratio < 0.50 -> 'congested'."""
    connector._feature_ids = {"b29-east-01": "fake-uuid-001"}
    response = _make_response(current_speed=20, freeflow_speed=60)  # ratio=0.333
    raw = [(SAMPLE_SEGMENT_DEF, response)]
    observations = connector.normalize(raw)
    assert observations[0].values["congestion_level"] == "congested"


def test_congestion_ratio_severe(connector) -> None:
    """congestion_ratio < 0.25 -> 'congested' (severe)."""
    connector._feature_ids = {"b29-east-01": "fake-uuid-001"}
    response = _make_response(current_speed=10, freeflow_speed=60)  # ratio=0.167
    raw = [(SAMPLE_SEGMENT_DEF, response)]
    observations = connector.normalize(raw)
    assert observations[0].values["congestion_level"] == "congested"


# ---------------------------------------------------------------------------
# Test 3: one Observation per road segment
# ---------------------------------------------------------------------------

def test_normalize_one_observation_per_segment(connector) -> None:
    """normalize() produces one Observation per road segment in the response."""
    connector._feature_ids = {
        "b29-east-01": "fake-uuid-001",
        "b19-north-01": "fake-uuid-002",
    }
    seg1 = {"id": "b29-east-01", "name": "B29", "lat": 48.840, "lon": 10.090}
    seg2 = {"id": "b19-north-01", "name": "B19", "lat": 48.850, "lon": 10.095}
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
# Test 6: fetch() calls correct TomTom endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fetch_calls_tomtom_endpoint(connector) -> None:
    """fetch() calls the TomTom Flow Segment Data endpoint with API key."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SAMPLE_TOMTOM_RESPONSE
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_client

        result = await connector.fetch()

    # Should have called get() for each segment
    assert mock_client.get.call_count > 0
    # Check first call URL contains tomtom API domain
    first_call_url = mock_client.get.call_args_list[0][0][0]
    assert "api.tomtom.com" in first_call_url
    assert "test-api-key-12345" in first_call_url
    assert "flowSegmentData" in first_call_url


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
