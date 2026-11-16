"""Tests for SensorCommunityConnector — WAIR-04.

The two tests marked slow call the live Sensor.community API (data.sensor.community);
they need network access. All other tests run offline against fixtures cut from a
real API answer.
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


@pytest.mark.slow
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


@pytest.mark.slow
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


# ---------------------------------------------------------------------------
# Offline tests: path-style URL and real-response fixtures
# ---------------------------------------------------------------------------

# Two entries cut from a real answer of the filter/area endpoint.
REAL_SDS011_ENTRY = {
    "sensor": {
        "sensor_type": {"manufacturer": "Nova Fitness", "name": "SDS011", "id": 14},
        "pin": "1",
        "id": 95858,
    },
    "sensordatavalues": [
        {"value": "0.20", "value_type": "P1", "id": 73503089642},
        {"value": "0.20", "value_type": "P2", "id": 73503089643},
    ],
    "location": {
        "indoor": 0,
        "country": "DE",
        "latitude": "48.764",
        "exact_location": 0,
        "altitude": "392.4",
        "longitude": "9.814",
        "id": 88056,
    },
    "sampling_rate": None,
    "timestamp": "2026-11-16 08:29:58",
    "id": 31385407559,
}
REAL_DHT22_ENTRY = {
    "sensor": {
        "sensor_type": {"manufacturer": "various", "name": "DHT22", "id": 9},
        "pin": "7",
        "id": 30304,
    },
    "sensordatavalues": [
        {"value": "11.70", "value_type": "temperature", "id": 73503090085},
        {"value": "69.30", "value_type": "humidity", "id": 73503090087},
    ],
    "location": {
        "indoor": 0,
        "country": "DE",
        "latitude": "48.636",
        "exact_location": 0,
        "altitude": "479.3",
        "longitude": "10.152",
        "id": 17112,
    },
    "sampling_rate": None,
    "timestamp": "2026-11-16 08:29:59",
    "id": 31385407721,
}


def _patched_client(captured: dict, payload: list[dict]):
    class MockResponse:
        def json(self):
            return payload

        def raise_for_status(self):
            pass

    async def mock_get(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return MockResponse()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(side_effect=mock_get)
    return mock_client


@pytest.mark.asyncio
async def test_fetch_requests_path_style_area_url(connector: SensorCommunityConnector) -> None:
    """fetch() requests the path-style URL; no area query parameter."""
    captured: dict = {}
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value = _patched_client(captured, [REAL_SDS011_ENTRY])
        await connector.fetch()

    assert captured["url"] == "https://data.sensor.community/airrohr/v1/filter/area=48.83,10.095,25"
    assert "params" not in captured["kwargs"]
    assert "city-data-platform" in captured["kwargs"]["headers"]["User-Agent"]


@pytest.mark.asyncio
async def test_fetch_uses_configured_radius(aalen_town: Town) -> None:
    config = ConnectorConfig(
        connector_class="SensorCommunityConnector",
        poll_interval_seconds=300,
        enabled=True,
        config={"radius_km": 10},
    )
    connector = SensorCommunityConnector(config=config, town=aalen_town)
    captured: dict = {}
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value = _patched_client(captured, [REAL_SDS011_ENTRY])
        await connector.fetch()

    assert captured["url"].endswith("area=48.83,10.095,10")


def test_normalize_real_entries_keeps_only_particulate_sensor(
    connector: SensorCommunityConnector,
) -> None:
    """One SDS011 entry and one DHT22 entry -> exactly one air_quality Observation."""
    connector._feature_ids = {95858: "feat-95858", 30304: "feat-30304"}

    observations = connector.normalize([REAL_SDS011_ENTRY, REAL_DHT22_ENTRY])

    assert len(observations) == 1
    obs = observations[0]
    assert obs.domain == "air_quality"
    assert obs.feature_id == "feat-95858"
    assert obs.values == {"pm10": 0.2, "pm25": 0.2}
