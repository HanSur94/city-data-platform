"""Shared fixtures for connector integration tests."""
import pytest
from app.config import ConnectorConfig, Town, TownBbox


@pytest.fixture
def aalen_town() -> Town:
    """Aalen Town object with real bbox and no connectors configured."""
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
def stub_connector_config() -> ConnectorConfig:
    return ConnectorConfig(
        connector_class="StubConnector",
        poll_interval_seconds=300,
        enabled=True,
        config={},
    )
