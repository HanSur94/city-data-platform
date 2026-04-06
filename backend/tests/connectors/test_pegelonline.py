"""Tests for PegelonlineConnector and base.py water branch.

Tests:
- persist() with domain="water" executes INSERT INTO water_readings
- persist() with unknown domain remains a silent no-op (existing behavior)
- PegelonlineConnector.normalize() returns Observation per station with domain="water"
- Station with None level_cm still produces an Observation
- filter by station_uuids config when non-empty
- run() calls upsert_feature() per station
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import ConnectorConfig, Town, TownBbox
from app.connectors.base import Observation
from app.connectors.pegelonline import PegelonlineConnector


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

SAMPLE_STATION_RESPONSE = [
    {
        "uuid": "aaaaaaaa-0000-0000-0000-000000000001",
        "shortname": "PLOCHINGEN",
        "water": {"longname": "NECKAR"},
        "latitude": 48.707,
        "longitude": 9.419,
        "timeseries": [
            {
                "shortname": "W",
                "unit": "cm",
                "currentMeasurement": {
                    "timestamp": "2026-04-06T01:30:00+02:00",
                    "value": 159.0,
                },
            }
        ],
    },
    {
        "uuid": "bbbbbbbb-0000-0000-0000-000000000002",
        "shortname": "HEIDELBERG",
        "water": {"longname": "NECKAR"},
        "latitude": 49.408,
        "longitude": 8.694,
        "timeseries": [],  # no current measurement
    },
]


@pytest.fixture
def pegelonline_config() -> ConnectorConfig:
    return ConnectorConfig(
        connector_class="PegelonlineConnector",
        poll_interval_seconds=900,
        enabled=True,
        config={
            "station_uuids": [],
            "attribution": "PEGELONLINE (WSV / BfG), DL-DE-Zero-2.0",
        },
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
def connector(pegelonline_config, aalen_town) -> PegelonlineConnector:
    return PegelonlineConnector(config=pegelonline_config, town=aalen_town)


# ---------------------------------------------------------------------------
# normalize() tests
# ---------------------------------------------------------------------------

def test_normalize_returns_one_observation_per_station(connector) -> None:
    """normalize() returns one Observation per station."""
    connector._feature_ids = {
        "aaaaaaaa-0000-0000-0000-000000000001": "uuid-feature-1",
        "bbbbbbbb-0000-0000-0000-000000000002": "uuid-feature-2",
    }
    observations = connector.normalize(SAMPLE_STATION_RESPONSE)
    assert len(observations) == 2


def test_normalize_domain_is_water(connector) -> None:
    """All observations from PegelonlineConnector have domain='water'."""
    connector._feature_ids = {
        "aaaaaaaa-0000-0000-0000-000000000001": "uuid-feature-1",
        "bbbbbbbb-0000-0000-0000-000000000002": "uuid-feature-2",
    }
    observations = connector.normalize(SAMPLE_STATION_RESPONSE)
    for obs in observations:
        assert obs.domain == "water"


def test_normalize_level_cm_from_timeseries(connector) -> None:
    """normalize() extracts level_cm from W timeseries."""
    connector._feature_ids = {
        "aaaaaaaa-0000-0000-0000-000000000001": "uuid-feature-1",
        "bbbbbbbb-0000-0000-0000-000000000002": "uuid-feature-2",
    }
    observations = connector.normalize(SAMPLE_STATION_RESPONSE)
    # First station has level_cm=159.0
    ploch_obs = next(o for o in observations if o.feature_id == "uuid-feature-1")
    assert ploch_obs.values["level_cm"] == pytest.approx(159.0)
    assert ploch_obs.values["flow_m3s"] is None


def test_normalize_station_with_no_timeseries_produces_observation(connector) -> None:
    """Station with no timeseries still produces Observation with level_cm=None."""
    connector._feature_ids = {
        "aaaaaaaa-0000-0000-0000-000000000001": "uuid-feature-1",
        "bbbbbbbb-0000-0000-0000-000000000002": "uuid-feature-2",
    }
    observations = connector.normalize(SAMPLE_STATION_RESPONSE)
    heidelberg_obs = next(o for o in observations if o.feature_id == "uuid-feature-2")
    assert heidelberg_obs.values["level_cm"] is None
    assert heidelberg_obs.values["flow_m3s"] is None


# ---------------------------------------------------------------------------
# fetch() with station_uuids filter
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fetch_filters_by_station_uuids(aalen_town) -> None:
    """Non-empty station_uuids filters stations to only those UUIDs."""
    config = ConnectorConfig(
        connector_class="PegelonlineConnector",
        poll_interval_seconds=900,
        enabled=True,
        config={
            "station_uuids": ["aaaaaaaa-0000-0000-0000-000000000001"],
            "attribution": "test",
        },
    )
    conn = PegelonlineConnector(config=config, town=aalen_town)

    class MockResponse:
        def json(self):
            return SAMPLE_STATION_RESPONSE
        def raise_for_status(self):
            pass

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=MockResponse())
        mock_cls.return_value = mock_client

        result = await conn.fetch()

    assert len(result) == 1
    assert result[0]["uuid"] == "aaaaaaaa-0000-0000-0000-000000000001"


@pytest.mark.asyncio
async def test_fetch_empty_station_uuids_returns_all(connector) -> None:
    """Empty station_uuids returns all stations from the API."""

    class MockResponse:
        def json(self):
            return SAMPLE_STATION_RESPONSE
        def raise_for_status(self):
            pass

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=MockResponse())
        mock_cls.return_value = mock_client

        result = await connector.fetch()

    assert len(result) == 2


@pytest.mark.asyncio
async def test_fetch_raises_value_error_on_empty_result(aalen_town) -> None:
    """fetch() raises ValueError if the filtered result is empty."""
    config = ConnectorConfig(
        connector_class="PegelonlineConnector",
        poll_interval_seconds=900,
        enabled=True,
        config={
            "station_uuids": ["non-existent-uuid"],
            "attribution": "test",
        },
    )
    conn = PegelonlineConnector(config=config, town=aalen_town)

    class MockResponse:
        def json(self):
            return SAMPLE_STATION_RESPONSE
        def raise_for_status(self):
            pass

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=MockResponse())
        mock_cls.return_value = mock_client

        with pytest.raises(ValueError):
            await conn.fetch()


# ---------------------------------------------------------------------------
# persist() water branch test (via base.py)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_persist_water_executes_insert(connector) -> None:
    """persist() with domain='water' executes INSERT INTO water_readings."""
    observations = [
        Observation(
            feature_id="test-uuid",
            domain="water",
            values={"level_cm": 150.0, "flow_m3s": None},
            timestamp=datetime(2026, 4, 6, 0, 0, tzinfo=timezone.utc),
        )
    ]

    mock_execute = AsyncMock()
    mock_commit = AsyncMock()

    mock_session = AsyncMock()
    mock_session.execute = mock_execute
    mock_session.commit = mock_commit
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_session_local = MagicMock(return_value=mock_session)

    with patch("app.db.AsyncSessionLocal", mock_session_local):
        await connector.persist(observations)

    # Should have called execute once for the water INSERT
    assert mock_execute.call_count == 1
    call_args = mock_execute.call_args
    sql_text = str(call_args[0][0])
    assert "water_readings" in sql_text
    params = call_args[0][1]
    assert params["level_cm"] == pytest.approx(150.0)
    assert params["flow_m3s"] is None
    assert "feature_id" in params


@pytest.mark.asyncio
async def test_persist_unknown_domain_is_noop(connector) -> None:
    """persist() with an unknown domain is a silent no-op (does not execute)."""
    observations = [
        Observation(
            feature_id="test-uuid",
            domain="unknown_domain",
            values={"some_val": 42},
            timestamp=datetime(2026, 4, 6, 0, 0, tzinfo=timezone.utc),
        )
    ]

    mock_execute = AsyncMock()
    mock_commit = AsyncMock()
    mock_session = AsyncMock()
    mock_session.execute = mock_execute
    mock_session.commit = mock_commit
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_session_local = MagicMock(return_value=mock_session)

    with patch("app.db.AsyncSessionLocal", mock_session_local):
        await connector.persist(observations)

    # execute should NOT have been called for unknown domain
    mock_execute.assert_not_called()
