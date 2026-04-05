"""Integration tests for SensorCommunityConnector — WAIR-04.

These tests call the live Sensor.community API (data.sensor.community).
They require network access and verify real data shapes/values.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.config import ConnectorConfig, Town, TownBbox
from app.connectors.sensor_community import SensorCommunityConnector
from app.connectors.base import Observation


@pytest.fixture
def sc_config() -> ConnectorConfig:
    return ConnectorConfig(
        connector_class="SensorCommunityConnector",
        poll_interval_seconds=300,
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
def connector(sc_config, aalen_town) -> SensorCommunityConnector:
    return SensorCommunityConnector(config=sc_config, town=aalen_town)


@pytest.mark.asyncio
async def test_sensor_community_fetch_returns_sensors(connector: SensorCommunityConnector) -> None:
    """fetch() hits live Sensor.community API and returns non-empty list.

    Skips if the live API returns no sensors — this can happen during API
    outages or when no sensors are actively reporting in the area.
    """
    try:
        raw = await connector.fetch()
    except ValueError as e:
        if "empty" in str(e).lower():
            pytest.skip(f"Sensor.community API returned no sensors (API outage?): {e}")
        raise
    assert isinstance(raw, list), "fetch() must return a list"
    assert len(raw) > 0, "must return at least one sensor within 25km of Aalen"


@pytest.mark.asyncio
async def test_sensor_community_normalize_returns_observations(connector: SensorCommunityConnector) -> None:
    """normalize() returns list[Observation] with domain='air_quality'.

    Uses mock data if live API is unavailable — the normalize() logic
    is the important contract to test here.
    """
    # Try live API first; fall back to mock data if unavailable
    try:
        raw = await connector.fetch()
    except ValueError:
        # Live API unavailable — test normalize() with mock data
        raw = [
            {
                "id": 1,
                "sensor": {"id": 42, "sensor_type": {"name": "SDS011"}},
                "location": {"latitude": "48.84", "longitude": "10.09"},
                "sensordatavalues": [
                    {"value_type": "P1", "value": "12.5"},
                    {"value_type": "P2", "value": "6.3"},
                ],
            }
        ]

    # Simulate feature_ids as run() would populate
    connector._feature_ids = {}
    for entry in raw:
        sensor_id = entry["sensor"]["id"]
        connector._feature_ids[sensor_id] = f"test-uuid-{sensor_id}"

    observations = connector.normalize(raw)
    assert isinstance(observations, list)
    # Should have at least some SDS011 or SPS30 sensors
    if observations:
        for obs in observations:
            assert isinstance(obs, Observation)
            assert obs.domain == "air_quality"
            # Values dict should have pm10 and/or pm25 keys
            assert "pm10" in obs.values or "pm25" in obs.values


@pytest.mark.asyncio
async def test_sensor_community_user_agent(connector: SensorCommunityConnector) -> None:
    """fetch() must set User-Agent header on all requests."""
    captured_headers = {}

    class MockResponse:
        def json(self):
            return [
                {
                    "id": 1,
                    "sensor": {"id": 42, "sensor_type": {"name": "SDS011"}},
                    "location": {"latitude": "48.84", "longitude": "10.09"},
                    "sensordatavalues": [
                        {"value_type": "P1", "value": "12.5"},
                        {"value_type": "P2", "value": "6.3"},
                    ],
                }
            ]
        def raise_for_status(self):
            pass

    async def mock_get(url, **kwargs):
        captured_headers.update(kwargs.get("headers", {}))
        return MockResponse()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=mock_get)
        mock_client_cls.return_value = mock_client

        await connector.fetch()

    assert "User-Agent" in captured_headers, "User-Agent header must be set"
    assert "city-data-platform" in captured_headers["User-Agent"]


@pytest.mark.asyncio
async def test_sensor_community_fetch_raises_on_empty(connector: SensorCommunityConnector) -> None:
    """fetch() raises ValueError if response list is empty."""

    class MockResponse:
        def json(self):
            return []
        def raise_for_status(self):
            pass

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=MockResponse())
        mock_client_cls.return_value = mock_client

        with pytest.raises(ValueError, match="empty"):
            await connector.fetch()


@pytest.mark.asyncio
async def test_sensor_community_handles_missing_pollutants(connector: SensorCommunityConnector) -> None:
    """normalize() handles sensors with missing P1/P2 values gracefully — no KeyError."""
    raw = [
        {
            "id": 1,
            "sensor": {"id": 101, "sensor_type": {"name": "SDS011"}},
            "location": {"latitude": "48.84", "longitude": "10.09"},
            "sensordatavalues": [],  # No P1, P2 data
        },
        {
            "id": 2,
            "sensor": {"id": 102, "sensor_type": {"name": "SDS011"}},
            "location": {"latitude": "48.85", "longitude": "10.10"},
            "sensordatavalues": [
                {"value_type": "P1", "value": "15.2"},
                # P2 missing
            ],
        },
    ]
    connector._feature_ids = {101: "uuid-101", 102: "uuid-102"}
    # Should not raise KeyError
    observations = connector.normalize(raw)
    assert isinstance(observations, list)
    for obs in observations:
        assert obs.values.get("pm10") is None or isinstance(obs.values.get("pm10"), float)
        assert obs.values.get("pm25") is None or isinstance(obs.values.get("pm25"), float)
