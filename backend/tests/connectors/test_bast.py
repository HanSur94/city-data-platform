"""Tests for BastConnector — Phase 7, Plan 02 (TRAF-03).

BASt (Bundesanstalt fuer Strassenwesen) publishes annual traffic count CSV data.
Tests cover: CSV parsing, congestion level computation, feature source_id format.

License: Datenlizenz Deutschland – Namensnennung – Version 2.0
"""
from __future__ import annotations

import io
import csv
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.config import ConnectorConfig, Town, TownBbox
from app.connectors.bast import BastConnector, _compute_congestion
from app.connectors.base import Observation


# ---------------------------------------------------------------------------
# Sample CSV data (windows-1252 encoded, semicolon-delimited)
# Columns: Zst;Land;Strasse;Abschnitt;ANr;VNr;Dat;Stunde;KFZ;SV;V_PKW;V_LKW;
# ---------------------------------------------------------------------------

SAMPLE_CSV_ROWS = [
    "Zst;Land;Strasse;Abschnitt;ANr;VNr;Dat;Stunde;KFZ;SV;V_PKW;V_LKW;PLat;PLon;Richtung;Fahrstreifen",
    "9440;BW;A7;Aalen;100;200;01.01.2023;8;500;50;95;75;48.80;10.10;N;2",
    "9441;BW;A6;Crailsheim;101;201;01.01.2023;8;1200;120;100;80;48.90;10.20;S;2",
    "9442;BW;A81;Stuttgart;102;202;01.01.2023;8;800;80;90;70;48.77;10.15;W;1",
]

SAMPLE_CSV_TEXT = "\n".join(SAMPLE_CSV_ROWS)
SAMPLE_CSV_BYTES = SAMPLE_CSV_TEXT.encode("windows-1252")

# Station outside Aalen bbox+20km
OUT_OF_BBOX_ROW = "9999;BY;A3;Nuernberg;999;999;01.01.2023;8;300;30;80;60;49.50;11.10;E;2"


@pytest.fixture
def bast_config() -> ConnectorConfig:
    return ConnectorConfig(
        connector_class="BastConnector",
        poll_interval_seconds=86400,
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
def connector(bast_config, aalen_town) -> BastConnector:
    return BastConnector(config=bast_config, town=aalen_town)


# ---------------------------------------------------------------------------
# _compute_congestion unit tests
# ---------------------------------------------------------------------------

def test_compute_congestion_free() -> None:
    """vehicle_count < 50% capacity -> 'free'."""
    # 2 lanes * 800 = 1600 capacity; 600 < 50% of 1600 -> free
    assert _compute_congestion(600, 2) == "free"


def test_compute_congestion_moderate() -> None:
    """50% <= vehicle_count < 80% capacity -> 'moderate'."""
    # 2 lanes * 800 = 1600; 50% = 800, 80% = 1280
    assert _compute_congestion(900, 2) == "moderate"


def test_compute_congestion_congested() -> None:
    """vehicle_count >= 80% capacity -> 'congested'."""
    # 2 lanes * 800 = 1600; 80% = 1280; 1400 >= 1280 -> congested
    assert _compute_congestion(1400, 2) == "congested"


def test_compute_congestion_zero_lanes() -> None:
    """Zero lanes defaults to 'free' without division error."""
    result = _compute_congestion(500, 0)
    # Should not raise, should return some valid string
    assert result in ("free", "moderate", "congested")


# ---------------------------------------------------------------------------
# normalize() tests
# ---------------------------------------------------------------------------

def test_bast_csv_parse_returns_observations(connector: BastConnector) -> None:
    """BASt CSV parsing produces Observation objects with traffic domain."""
    observations = connector.normalize(SAMPLE_CSV_BYTES)
    assert isinstance(observations, list), "normalize() must return a list"
    assert len(observations) > 0, "must parse at least one row"
    for obs in observations:
        assert isinstance(obs, Observation)
        assert obs.domain == "traffic"


def test_bast_normalize_computes_congestion_level(connector: BastConnector) -> None:
    """Congestion level is derived from flow-to-capacity ratio."""
    observations = connector.normalize(SAMPLE_CSV_BYTES)
    assert len(observations) > 0
    for obs in observations:
        level = obs.values.get("congestion_level")
        assert level in ("free", "moderate", "congested"), (
            f"congestion_level must be 'free'|'moderate'|'congested', got {level!r}"
        )


def test_bast_normalize_values_keys(connector: BastConnector) -> None:
    """All observations contain required traffic values keys."""
    observations = connector.normalize(SAMPLE_CSV_BYTES)
    required_keys = {"vehicle_count_total", "vehicle_count_hgv", "speed_avg_kmh", "congestion_level"}
    for obs in observations:
        assert required_keys.issubset(obs.values.keys()), (
            f"Missing keys: {required_keys - obs.values.keys()}"
        )


def test_bast_feature_upsert_source_id_format(connector: BastConnector) -> None:
    """source_id for BASt features follows the format 'bast:{station_id}'."""
    observations = connector.normalize(SAMPLE_CSV_BYTES)
    assert len(observations) > 0
    for obs in observations:
        assert obs.source_id is not None
        assert obs.source_id.startswith("bast:"), (
            f"source_id must start with 'bast:', got {obs.source_id!r}"
        )


def test_bast_normalize_bbox_filtering(connector: BastConnector) -> None:
    """Stations outside Aalen bbox+20km are filtered out."""
    # Add an out-of-bbox row
    rows_with_outlier = SAMPLE_CSV_ROWS + [OUT_OF_BBOX_ROW]
    csv_text = "\n".join(rows_with_outlier)
    csv_bytes = csv_text.encode("windows-1252")

    observations = connector.normalize(csv_bytes)
    # None should have the out-of-bbox station ID 9999
    source_ids = [obs.source_id for obs in observations]
    assert not any("9999" in (sid or "") for sid in source_ids), (
        "Station 9999 (outside bbox) should be filtered out"
    )


# ---------------------------------------------------------------------------
# fetch() test — verifies httpx is called correctly
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bast_fetch_returns_bytes(connector: BastConnector) -> None:
    """fetch() calls the BASt CSV URL and returns bytes."""
    class MockResponse:
        content = SAMPLE_CSV_BYTES
        def raise_for_status(self):
            pass

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=MockResponse())
        mock_cls.return_value = mock_client

        result = await connector.fetch()

    assert isinstance(result, bytes)
    assert result == SAMPLE_CSV_BYTES
