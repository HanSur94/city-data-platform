"""Tests for MobiDataBWConnector — Phase 7, Plan 02 (TRAF-05).

MobiData BW provides traffic count data for Baden-Wuerttemberg roads.
Tests cover: CSV parsing, shared normalize output format with BASt.

License: Datenlizenz Deutschland – Namensnennung – Version 2.0
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.config import ConnectorConfig, Town, TownBbox
from app.connectors.mobidata_bw import MobiDataBWConnector
from app.connectors.base import Observation


# ---------------------------------------------------------------------------
# Sample CSV (same format as BASt, BW-specific stations)
# ---------------------------------------------------------------------------

SAMPLE_BW_CSV_ROWS = [
    "Zst;Land;Strasse;Abschnitt;ANr;VNr;Dat;Stunde;KFZ;SV;V_PKW;V_LKW;PLat;PLon;Richtung;Fahrstreifen",
    "8801;BW;B29;Aalen;100;200;01.01.2023;8;350;35;88;68;48.82;10.08;N;1",
    "8802;BW;B19;Aalen;101;201;01.01.2023;8;900;90;92;72;48.85;10.12;S;2",
]

SAMPLE_BW_CSV_TEXT = "\n".join(SAMPLE_BW_CSV_ROWS)
SAMPLE_BW_CSV_BYTES = SAMPLE_BW_CSV_TEXT.encode("windows-1252")


@pytest.fixture
def mobidata_config() -> ConnectorConfig:
    return ConnectorConfig(
        connector_class="MobiDataBWConnector",
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
def connector(mobidata_config, aalen_town) -> MobiDataBWConnector:
    return MobiDataBWConnector(config=mobidata_config, town=aalen_town)


# ---------------------------------------------------------------------------
# normalize() tests
# ---------------------------------------------------------------------------

def test_mobidata_csv_parse(connector: MobiDataBWConnector) -> None:
    """MobiData BW CSV traffic data is parsed correctly."""
    observations = connector.normalize(SAMPLE_BW_CSV_BYTES)
    assert isinstance(observations, list), "normalize() must return a list"
    assert len(observations) > 0, "must parse at least one row"
    for obs in observations:
        assert isinstance(obs, Observation)
        assert obs.domain == "traffic"


def test_mobidata_normalize_shares_bast_format(connector: MobiDataBWConnector) -> None:
    """MobiData BW normalize() output matches BASt output schema.

    Both connectors produce Observations with identical values keys:
    vehicle_count_total, vehicle_count_hgv, speed_avg_kmh, congestion_level.
    """
    observations = connector.normalize(SAMPLE_BW_CSV_BYTES)
    assert len(observations) > 0
    required_keys = {"vehicle_count_total", "vehicle_count_hgv", "speed_avg_kmh", "congestion_level"}
    for obs in observations:
        assert obs.domain == "traffic"
        assert required_keys.issubset(obs.values.keys()), (
            f"MobiData BW output missing keys vs BASt format: {required_keys - obs.values.keys()}"
        )


def test_mobidata_source_id_format(connector: MobiDataBWConnector) -> None:
    """source_id for MobiData BW features follows 'mobidata_bw:{station_id}' format."""
    observations = connector.normalize(SAMPLE_BW_CSV_BYTES)
    assert len(observations) > 0
    for obs in observations:
        assert obs.source_id is not None
        assert obs.source_id.startswith("mobidata_bw:"), (
            f"source_id must start with 'mobidata_bw:', got {obs.source_id!r}"
        )


def test_mobidata_congestion_level_values(connector: MobiDataBWConnector) -> None:
    """Congestion level values are valid strings."""
    observations = connector.normalize(SAMPLE_BW_CSV_BYTES)
    for obs in observations:
        level = obs.values.get("congestion_level")
        assert level in ("free", "moderate", "congested"), (
            f"congestion_level must be 'free'|'moderate'|'congested', got {level!r}"
        )


# ---------------------------------------------------------------------------
# fetch() test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mobidata_fetch_returns_bytes(connector: MobiDataBWConnector) -> None:
    """fetch() calls the MobiData BW CSV URL and returns bytes."""
    class MockResponse:
        content = SAMPLE_BW_CSV_BYTES
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
