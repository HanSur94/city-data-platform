"""Integration tests for UBAConnector — WAIR-03.

These tests call the live UBA API (luftdaten.umweltbundesamt.de).
They require network access and verify real data shapes/values.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.config import ConnectorConfig, Town, TownBbox
from app.connectors.uba import UBAConnector
from app.connectors.base import Observation


@pytest.fixture
def uba_config() -> ConnectorConfig:
    return ConnectorConfig(
        connector_class="UBAConnector",
        poll_interval_seconds=3600,
        enabled=True,
        config={"station_id": 238, "lat": 48.84, "lon": 10.09},
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
def connector(uba_config, aalen_town) -> UBAConnector:
    return UBAConnector(config=uba_config, town=aalen_town)


@pytest.mark.asyncio
async def test_uba_fetch_returns_data(connector: UBAConnector) -> None:
    """fetch() hits live UBA API and returns dict with 'data' key."""
    raw = await connector.fetch()
    assert isinstance(raw, dict), "fetch() must return a dict"
    assert "data" in raw, "response must contain 'data' key"
    assert raw["data"], "data must be non-empty"


@pytest.mark.asyncio
async def test_uba_normalize_returns_observations(connector: UBAConnector) -> None:
    """normalize() returns at least one Observation with domain='air_quality'."""
    raw = await connector.fetch()
    # Set _feature_id as run() would do
    connector._feature_id = "test-feature-uuid"
    observations = connector.normalize(raw)
    assert isinstance(observations, list), "normalize() must return a list"
    assert len(observations) > 0, "must return at least one Observation"
    for obs in observations:
        assert isinstance(obs, Observation)
        assert obs.domain == "air_quality"
        assert obs.feature_id == "test-feature-uuid"


@pytest.mark.asyncio
async def test_uba_no_negative_values(connector: UBAConnector) -> None:
    """All float values in Observation.values must be >= 0 or None."""
    raw = await connector.fetch()
    connector._feature_id = "test-feature-uuid"
    observations = connector.normalize(raw)
    for obs in observations:
        for key, val in obs.values.items():
            if val is not None:
                assert isinstance(val, float), f"{key} must be float or None"
                assert val >= 0, f"{key} = {val} is negative — must be rejected"


@pytest.mark.asyncio
async def test_uba_fetch_raises_on_empty_data(connector: UBAConnector) -> None:
    """fetch() raises ValueError if response 'data' is empty or missing."""
    import httpx

    class MockResponse:
        def json(self):
            return {"data": {}, "request": {}}
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
