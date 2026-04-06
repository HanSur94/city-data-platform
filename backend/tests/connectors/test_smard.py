"""Tests for SmardConnector — Phase 7, Plan 03.

SMARD (Bundesnetzagentur) provides electricity generation and price data
for Germany via a two-step fetch pattern (index + data).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from app.connectors.smard import SmardConnector, GENERATION_FILTERS, PRICE_FILTER
from app.config import ConnectorConfig, Town, TownBbox


@pytest.fixture
def smard_config() -> ConnectorConfig:
    return ConnectorConfig(
        connector_class="SmardConnector",
        poll_interval_seconds=900,
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
def connector(smard_config: ConnectorConfig, aalen_town: Town) -> SmardConnector:
    return SmardConnector(smard_config, aalen_town)


def test_smard_two_step_fetch(connector: SmardConnector) -> None:
    """SMARD fetch requires two API calls: index then data.

    Step 1: GET /chart_data/{filter}/{region}/index_{resolution}.json
    Step 2: GET /chart_data/{filter}/{region}/{filter}_{region}_{resolution}_{timestamp}.json
    The connector must chain these calls and return the series list.
    """
    ts_ms = 1700000000000
    index_resp = MagicMock()
    index_resp.raise_for_status = MagicMock()
    index_resp.json.return_value = {"timestamps": [ts_ms]}

    data_resp = MagicMock()
    data_resp.raise_for_status = MagicMock()
    data_resp.json.return_value = {"series": [[ts_ms, 5000.0]]}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=[index_resp, data_resp])

    import asyncio
    result = asyncio.get_event_loop().run_until_complete(
        connector._fetch_latest(mock_client, GENERATION_FILTERS["solar"])
    )

    assert len(result) == 1
    assert result[0][0] == ts_ms
    assert result[0][1] == 5000.0
    # Verify two API calls were made
    assert mock_client.get.call_count == 2
    # First call should contain "index_quarterhour"
    first_call_url = mock_client.get.call_args_list[0].args[0]
    assert "index_quarterhour" in first_call_url


def test_smard_null_filtering(connector: SmardConnector) -> None:
    """SMARD data points with null values are filtered before persisting.

    SMARD API returns null for missing data points. These must be dropped
    rather than stored as None to avoid polluting the energy time-series.
    """
    ts1 = 1700000000000
    ts2 = 1700000900000
    ts3 = 1700001800000

    # Simulate raw JSON with a null in the middle
    raw_dict = {
        "solar": [[ts1, 5000.0], [ts2, None], [ts3, 3000.0]],
    }
    raw = json.dumps(raw_dict).encode()

    observations = connector.normalize(raw, feature_ids={"national": "test-uuid"})

    # Only ts1 and ts3 should produce observations (ts2 is null)
    solar_obs = [o for o in observations if o.values.get("source_type") == "solar"]
    assert len(solar_obs) == 2
    # None values must not appear
    for obs in solar_obs:
        assert obs.values.get("value_kw") is not None


def test_smard_renewable_percent_calculation(connector: SmardConnector) -> None:
    """renewable_percent is correctly computed from generation mix.

    Given: solar=10000 MW, wind_onshore=8000 MW, gas=5000 MW, lignite=3000 MW
    renewables = 10000 + 8000 = 18000
    total = 10000 + 8000 + 5000 + 3000 = 26000
    renewable_percent = 18000 / 26000 * 100 = 69.23%
    """
    generation = {
        "solar": 10000.0,
        "wind_onshore": 8000.0,
        "gas": 5000.0,
        "lignite": 3000.0,
    }

    result = connector.compute_renewable_percent(generation)

    assert result is not None
    assert abs(result - 69.23) < 0.1  # within 0.1%


def test_smard_renewable_percent_zero_total(connector: SmardConnector) -> None:
    """compute_renewable_percent returns None when total is 0 to avoid division by zero."""
    result = connector.compute_renewable_percent({})
    assert result is None


def test_smard_generation_filters_count() -> None:
    """GENERATION_FILTERS contains exactly 9 source entries."""
    assert len(GENERATION_FILTERS) == 9


def test_smard_price_filter() -> None:
    """PRICE_FILTER is set to the correct SMARD filter code."""
    assert PRICE_FILTER == 4169
