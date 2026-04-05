"""Integration tests for WeatherConnector — WAIR-01 (current) and WAIR-02 (forecast).

Tests call the live Bright Sky API (no mocking). Requires internet access.
"""
import pytest
from app.connectors.weather import WeatherConnector
from app.config import ConnectorConfig


@pytest.fixture
def weather_config():
    return ConnectorConfig(
        connector_class="WeatherConnector",
        poll_interval_seconds=3600,
        enabled=True,
        config={"lat": 48.84, "lon": 10.09},
    )


@pytest.fixture
def connector(weather_config, aalen_town):
    return WeatherConnector(config=weather_config, town=aalen_town)


async def test_current_weather_fetch(connector):
    raw = await connector.fetch()
    assert "current" in raw
    assert isinstance(raw["current"], dict)
    assert raw["current"]  # non-empty


async def test_forecast_fetch(connector):
    raw = await connector.fetch()
    assert "forecast" in raw
    assert isinstance(raw["forecast"], list)
    assert len(raw["forecast"]) > 0


async def test_normalize_current_observation(connector):
    raw = await connector.fetch()
    # Set _feature_id as run() would, using a placeholder UUID for unit testing normalize()
    connector._feature_id = "00000000-0000-0000-0000-000000000001"
    obs = connector.normalize(raw)
    current_obs = [o for o in obs if o.values.get("observation_type") == "current"]
    assert len(current_obs) >= 1


async def test_normalize_forecast_observations(connector):
    raw = await connector.fetch()
    connector._feature_id = "00000000-0000-0000-0000-000000000001"
    obs = connector.normalize(raw)
    forecast_obs = [o for o in obs if o.values.get("observation_type") == "forecast"]
    assert len(forecast_obs) >= 1


async def test_temperature_is_float_or_none(connector):
    raw = await connector.fetch()
    connector._feature_id = "00000000-0000-0000-0000-000000000001"
    obs = connector.normalize(raw)
    for o in obs:
        temp = o.values.get("temperature")
        assert temp is None or isinstance(temp, float), f"Expected float|None, got {type(temp)}"


def test_connector_class_name():
    assert WeatherConnector.__name__ == "WeatherConnector"
