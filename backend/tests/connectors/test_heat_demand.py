"""Tests for HeatDemandConnector — Phase 17, Plan 01.

Tests verify heat_class thresholds, domain assignment, and edge cases
for simulated building-level heat demand data.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.connectors.heat_demand import HeatDemandConnector
from app.config import ConnectorConfig, Town, TownBbox


@pytest.fixture
def heat_config() -> ConnectorConfig:
    return ConnectorConfig(
        connector_class="HeatDemandConnector",
        poll_interval_seconds=86400,
        enabled=True,
        config={"attribution": "KEA-BW Waermeatlas (simulated)"},
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
def connector(heat_config: ConnectorConfig, aalen_town: Town) -> HeatDemandConnector:
    return HeatDemandConnector(heat_config, aalen_town)


def test_normalize_returns_observations(connector: HeatDemandConnector) -> None:
    """normalize() returns non-empty list of Observations for valid input."""
    raw = [
        {"lon": 10.09, "lat": 48.84, "area_m2": 200, "heat_demand_kwh_m2_y": 120},
    ]
    result = connector.normalize(raw)
    assert len(result) == 1
    assert result[0].domain == "energy"
    assert result[0].values["heat_demand_kwh_m2_y"] == 120
    assert result[0].values["feature_type"] == "heat_demand"


def test_normalize_empty_input(connector: HeatDemandConnector) -> None:
    """normalize() with empty input returns []."""
    assert connector.normalize([]) == []


def test_normalize_heat_class_blue(connector: HeatDemandConnector) -> None:
    """heat_demand < 50 -> heat_class='blue'."""
    raw = [{"lon": 10.09, "lat": 48.84, "area_m2": 200, "heat_demand_kwh_m2_y": 30}]
    result = connector.normalize(raw)
    assert result[0].values["heat_class"] == "blue"


def test_normalize_heat_class_light_blue(connector: HeatDemandConnector) -> None:
    """50 <= heat_demand < 100 -> heat_class='light_blue'."""
    raw = [{"lon": 10.09, "lat": 48.84, "area_m2": 200, "heat_demand_kwh_m2_y": 75}]
    result = connector.normalize(raw)
    assert result[0].values["heat_class"] == "light_blue"


def test_normalize_heat_class_green(connector: HeatDemandConnector) -> None:
    """100 <= heat_demand < 150 -> heat_class='green'."""
    raw = [{"lon": 10.09, "lat": 48.84, "area_m2": 200, "heat_demand_kwh_m2_y": 120}]
    result = connector.normalize(raw)
    assert result[0].values["heat_class"] == "green"


def test_normalize_heat_class_yellow(connector: HeatDemandConnector) -> None:
    """150 <= heat_demand < 200 -> heat_class='yellow'."""
    raw = [{"lon": 10.09, "lat": 48.84, "area_m2": 200, "heat_demand_kwh_m2_y": 175}]
    result = connector.normalize(raw)
    assert result[0].values["heat_class"] == "yellow"


def test_normalize_heat_class_orange(connector: HeatDemandConnector) -> None:
    """200 <= heat_demand < 250 -> heat_class='orange'."""
    raw = [{"lon": 10.09, "lat": 48.84, "area_m2": 200, "heat_demand_kwh_m2_y": 225}]
    result = connector.normalize(raw)
    assert result[0].values["heat_class"] == "orange"


def test_normalize_heat_class_red(connector: HeatDemandConnector) -> None:
    """heat_demand >= 250 -> heat_class='red'."""
    raw = [{"lon": 10.09, "lat": 48.84, "area_m2": 200, "heat_demand_kwh_m2_y": 300}]
    result = connector.normalize(raw)
    assert result[0].values["heat_class"] == "red"


def test_normalize_boundary_50(connector: HeatDemandConnector) -> None:
    """Exactly 50 -> light_blue (boundary test)."""
    raw = [{"lon": 10.09, "lat": 48.84, "area_m2": 200, "heat_demand_kwh_m2_y": 50}]
    result = connector.normalize(raw)
    assert result[0].values["heat_class"] == "light_blue"


def test_normalize_boundary_250(connector: HeatDemandConnector) -> None:
    """Exactly 250 -> red (boundary test, >= 250)."""
    raw = [{"lon": 10.09, "lat": 48.84, "area_m2": 200, "heat_demand_kwh_m2_y": 250}]
    result = connector.normalize(raw)
    assert result[0].values["heat_class"] == "red"


def test_normalize_multiple_buildings(connector: HeatDemandConnector) -> None:
    """normalize() handles multiple buildings."""
    raw = [
        {"lon": 10.09, "lat": 48.84, "area_m2": 200, "heat_demand_kwh_m2_y": 30},
        {"lon": 10.10, "lat": 48.85, "area_m2": 150, "heat_demand_kwh_m2_y": 275},
    ]
    result = connector.normalize(raw)
    assert len(result) == 2
    assert result[0].values["heat_class"] == "blue"
    assert result[1].values["heat_class"] == "red"


def test_normalize_source_field(connector: HeatDemandConnector) -> None:
    """Each observation has source='KEA-BW Waermeatlas (simulated)' in values."""
    raw = [{"lon": 10.09, "lat": 48.84, "area_m2": 200, "heat_demand_kwh_m2_y": 100}]
    result = connector.normalize(raw)
    assert result[0].values["source"] == "KEA-BW Waermeatlas (simulated)"
