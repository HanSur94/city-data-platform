"""Unit tests for LhpConnector (LHP / Hochwasserportal water level)."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import ConnectorConfig, Town
from app.connectors.lhp import LhpConnector
from app.models.lhp import LhpGaugeReading


def _make_connector() -> LhpConnector:
    """Create an LhpConnector with test config."""
    town = Town(
        id="aalen",
        display_name="Aalen",
        country="DE",
        timezone="Europe/Berlin",
        bbox={"lon_min": 9.97, "lat_min": 48.76, "lon_max": 10.22, "lat_max": 48.90},
        connectors=[],
    )
    config = ConnectorConfig(
        connector_class="LhpConnector",
        poll_interval_seconds=900,
        enabled=True,
        config={
            "ident": "BW_13490006",
            "lat": 48.8035,
            "lon": 10.0972,
            "attribution": "Hochwasserportal (LHP), Datenlizenz Deutschland",
        },
    )
    return LhpConnector(config=config, town=town)


def _sample_reading(
    level: float | None = 123.4,
    flow: float | None = 5.67,
    stage: int | None = 1,
) -> LhpGaugeReading:
    """Create a sample LhpGaugeReading for testing."""
    return LhpGaugeReading(
        name="Huttlingen",
        level=level,
        flow=flow,
        stage=stage,
        last_update=datetime(2026, 4, 6, 12, 0, 0, tzinfo=timezone.utc),
        url="https://www.hochwasser.baden-wuerttemberg.de/",
        hint="",
    )


class TestNormalize:
    """Tests for LhpConnector.normalize()."""

    def test_produces_water_domain_observation(self):
        """normalize() produces Observation with domain='water' and correct values."""
        connector = _make_connector()
        reading = _sample_reading(level=123.4, flow=5.67)
        observations = connector.normalize(reading)

        assert len(observations) == 1
        obs = observations[0]
        assert obs.domain == "water"
        assert obs.values["level_cm"] == 123.4
        assert obs.values["flow_m3s"] == 5.67

    def test_handles_none_values(self):
        """normalize() handles None level/flow gracefully."""
        connector = _make_connector()
        reading = _sample_reading(level=None, flow=None, stage=None)
        observations = connector.normalize(reading)

        assert len(observations) == 1
        obs = observations[0]
        assert obs.domain == "water"
        assert obs.values["level_cm"] is None
        assert obs.values["flow_m3s"] is None

    def test_includes_stage_and_trend(self):
        """normalize() includes stage and trend in values dict."""
        connector = _make_connector()
        reading = _sample_reading(stage=2)
        observations = connector.normalize(reading)

        obs = observations[0]
        assert "stage" in obs.values
        assert obs.values["stage"] == 2
        assert "trend" in obs.values
        # Default trend when no prior readings exist
        assert obs.values["trend"] == "stable"

    def test_source_id_format(self):
        """source_id uses lhp:{ident} format."""
        connector = _make_connector()
        reading = _sample_reading()
        observations = connector.normalize(reading)

        obs = observations[0]
        assert obs.source_id == "lhp:BW_13490006"

    def test_timestamp_from_reading(self):
        """Observation timestamp comes from reading.last_update."""
        connector = _make_connector()
        reading = _sample_reading()
        observations = connector.normalize(reading)

        obs = observations[0]
        assert obs.timestamp == datetime(2026, 4, 6, 12, 0, 0, tzinfo=timezone.utc)


class TestGaugeIdent:
    """Tests for gauge ident format."""

    def test_bw_ident_format(self):
        """Gauge ident should follow BW_XXXXX format for Baden-Wuerttemberg."""
        connector = _make_connector()
        ident = connector.config.config["ident"]
        assert ident.startswith("BW_")


class TestFeatureProperties:
    """Tests for feature properties built by the connector."""

    def test_properties_contain_required_keys(self):
        """Feature properties include station_name, river, stage, trend, attribution."""
        connector = _make_connector()
        reading = _sample_reading(stage=1)

        props = connector._build_feature_properties(reading, trend="rising")

        assert props["station_name"] == "Huttlingen"
        assert props["river"] == "Kocher"
        assert props["stage"] == 1
        assert props["trend"] == "rising"
        assert "attribution" in props


class TestComputeTrend:
    """Tests for _compute_trend logic."""

    @pytest.mark.asyncio
    async def test_rising_trend(self):
        """Trend is 'rising' when level increases by more than 2cm."""
        connector = _make_connector()
        # Mock the DB query to return two readings with rising level
        with patch.object(connector, "_query_recent_levels", return_value=[100.0, 105.0]):
            result = await connector._compute_trend("test-feature-id")
        assert result == "rising"

    @pytest.mark.asyncio
    async def test_falling_trend(self):
        """Trend is 'falling' when level drops by more than 2cm."""
        connector = _make_connector()
        with patch.object(connector, "_query_recent_levels", return_value=[105.0, 100.0]):
            result = await connector._compute_trend("test-feature-id")
        assert result == "falling"

    @pytest.mark.asyncio
    async def test_stable_trend(self):
        """Trend is 'stable' when level change is within 2cm."""
        connector = _make_connector()
        with patch.object(connector, "_query_recent_levels", return_value=[100.0, 101.0]):
            result = await connector._compute_trend("test-feature-id")
        assert result == "stable"

    @pytest.mark.asyncio
    async def test_stable_fallback_insufficient_data(self):
        """Trend is 'stable' when insufficient data (fewer than 2 readings)."""
        connector = _make_connector()
        with patch.object(connector, "_query_recent_levels", return_value=[100.0]):
            result = await connector._compute_trend("test-feature-id")
        assert result == "stable"

    @pytest.mark.asyncio
    async def test_stable_fallback_no_data(self):
        """Trend is 'stable' when no prior readings exist."""
        connector = _make_connector()
        with patch.object(connector, "_query_recent_levels", return_value=[]):
            result = await connector._compute_trend("test-feature-id")
        assert result == "stable"
