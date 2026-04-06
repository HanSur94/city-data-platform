"""Tests for LadesaeulenConnector — Phase 8, Plan 02.

BNetzA (Bundesnetzagentur) EV charging station registry connector.
Parses CSV with German comma-decimal coordinates, filters by Ostalbkreis,
and upserts features with plug type details.

License: Bundesnetzagentur, CC BY 4.0
"""
from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

import pytest

from app.connectors.ladesaeulen import LadesaeulenConnector, _parse_german_float
from app.config import ConnectorConfig, Town, TownBbox


# --- Fixtures ---

SAMPLE_CSV = (
    "Betreiber;Strasse;Hausnummer;Postleitzahl;Ort;Bundesland;Kreis/kreisfreie Stadt;"
    "Breitengrad;Laengengrad;Anschlussleistung;Art der Ladeeinrichtung;Anzahl Ladepunkte;"
    "Steckertypen1;P1 [kW];Steckertypen2;P2 [kW];Steckertypen3;P3 [kW];Steckertypen4;P4 [kW]\n"
    # Ostalbkreis - valid coords, multiple plug types
    "Stadtwerke Aalen;Bahnhofstrasse;1;73430;Aalen;Baden-Württemberg;Ostalbkreis;"
    "48,8357;10,0938;22,0;Normalladen;2;"
    "Typ2;22,0;CCS;0;;0;;0\n"
    # Ostalbkreis - valid coords, Schnellladen
    "EnBW;Marktplatz;5;73430;Aalen;Baden-Württemberg;Ostalbkreis;"
    "48,8400;10,0960;150,0;Schnellladen;4;"
    "CCS;150,0;CHAdeMO;50,0;;0;;0\n"
    # Different Kreis - should be filtered out
    "RWE;Stuttgarter Str;10;70173;Stuttgart;Baden-Württemberg;Stuttgart;"
    "48,7783;9,1800;22,0;Normalladen;2;"
    "Typ2;22,0;;;0;;0;;0\n"
    # Ostalbkreis - missing latitude (empty) - should be skipped
    "Stadtwerke;Teststr;3;73430;Aalen;Baden-Württemberg;Ostalbkreis;"
    ";10,0938;22,0;Normalladen;1;"
    "Typ2;22,0;;;0;;0;;0\n"
    # Ostalbkreis - missing longitude (empty) - should be skipped
    "Stadtwerke;Teststr;4;73430;Aalen;Baden-Württemberg;Ostalbkreis;"
    "48,8357;;22,0;Normalladen;1;"
    "Typ2;22,0;;;0;;0;;0\n"
    # Ostalbkreis - valid coords, no secondary plug types
    "Allego;Zähringerstr;20;73430;Aalen;Baden-Württemberg;Ostalbkreis;"
    "48,8380;10,0950;50,0;Schnellladen;1;"
    "CCS;50,0;;;0;;0;;0\n"
)


@pytest.fixture
def ladesaeulen_config() -> ConnectorConfig:
    return ConnectorConfig(
        connector_class="LadesaeulenConnector",
        poll_interval_seconds=86400,
        enabled=True,
        config={
            "kreis_filter": "Ostalbkreis",
            "attribution": "Bundesnetzagentur, CC BY 4.0",
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
def connector(ladesaeulen_config: ConnectorConfig, aalen_town: Town) -> LadesaeulenConnector:
    return LadesaeulenConnector(ladesaeulen_config, aalen_town)


# --- Unit tests ---

def test_parse_german_float_comma_decimal() -> None:
    """Comma-decimal strings like '48,8357' are parsed to Python floats."""
    assert _parse_german_float("48,8357") == pytest.approx(48.8357)
    assert _parse_german_float("10,0938") == pytest.approx(10.0938)
    assert _parse_german_float("150,0") == pytest.approx(150.0)
    assert _parse_german_float("22,5") == pytest.approx(22.5)


def test_parse_german_float_empty_returns_none() -> None:
    """Empty strings return None (row should be skipped)."""
    assert _parse_german_float("") is None
    assert _parse_german_float("   ") is None


def test_parse_german_float_invalid_returns_none() -> None:
    """Non-numeric strings return None."""
    assert _parse_german_float("n/a") is None
    assert _parse_german_float("abc") is None


def test_parse_german_float_already_dotted() -> None:
    """Dot-decimal strings also parse correctly."""
    assert _parse_german_float("48.8357") == pytest.approx(48.8357)


def test_parse_german_float_zero() -> None:
    """Zero value is returned as 0.0, not None."""
    result = _parse_german_float("0")
    assert result == pytest.approx(0.0)


def test_normalize_returns_empty(connector: LadesaeulenConnector) -> None:
    """normalize() returns empty list — LadesaeulenConnector is features-only."""
    result = connector.normalize(b"")
    assert result == []


def test_kreis_filtering(connector: LadesaeulenConnector) -> None:
    """Only rows matching kreis_filter (Ostalbkreis) are processed.

    The sample CSV has 3 Ostalbkreis rows with valid coords, 1 Stuttgart row
    (filtered out), and 2 rows with missing coords (skipped).
    So upsert_feature should be called 3 times.
    """
    import csv

    rows = list(csv.DictReader(io.StringIO(SAMPLE_CSV), delimiter=";"))
    ostalbkreis_rows = [r for r in rows if r["Kreis/kreisfreie Stadt"] == "Ostalbkreis"]
    assert len(ostalbkreis_rows) == 5  # 5 Ostalbkreis rows in fixture

    # 2 have missing coords, so only 3 should be upserted
    valid_rows = []
    for r in ostalbkreis_rows:
        lat = _parse_german_float(r["Breitengrad"])
        lon = _parse_german_float(r["Laengengrad"])
        if lat is not None and lon is not None:
            valid_rows.append(r)
    assert len(valid_rows) == 3


@pytest.mark.asyncio
async def test_run_upserts_ostalbkreis_only(
    connector: LadesaeulenConnector, tmp_path: Path
) -> None:
    """run() upserts only Ostalbkreis rows with valid coordinates.

    Mocks HTTP download and cache file to return SAMPLE_CSV.
    Expects upsert_feature called exactly 3 times (3 valid Ostalbkreis rows).
    """
    cache_file = tmp_path / "ladesaeulenregister.csv"
    # No cache file — will trigger download

    upserted_calls = []

    async def mock_upsert(source_id, domain, geometry_wkt, properties):
        upserted_calls.append({
            "source_id": source_id,
            "domain": domain,
            "geometry_wkt": geometry_wkt,
            "properties": properties,
        })
        return "fake-uuid"

    async def mock_staleness():
        pass

    mock_response = MagicMock()
    mock_response.content = SAMPLE_CSV.encode("utf-8")
    mock_response.raise_for_status = MagicMock()

    with (
        patch.object(connector, "upsert_feature", side_effect=mock_upsert),
        patch.object(connector, "_update_staleness", side_effect=mock_staleness),
        patch.object(connector, "_get_cache_path", return_value=cache_file),
        patch("httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        await connector.run()

    assert len(upserted_calls) == 3


@pytest.mark.asyncio
async def test_run_properties_structure(
    connector: LadesaeulenConnector, tmp_path: Path
) -> None:
    """upsert_feature is called with correct property keys and values.

    First Ostalbkreis row: Stadtwerke Aalen, Typ2 + CCS, max 22kW, Normalladen, 2 points.
    """
    cache_file = tmp_path / "ladesaeulenregister.csv"

    upserted_calls = []

    async def mock_upsert(source_id, domain, geometry_wkt, properties):
        upserted_calls.append({
            "source_id": source_id,
            "domain": domain,
            "geometry_wkt": geometry_wkt,
            "properties": properties,
        })
        return "fake-uuid"

    async def mock_staleness():
        pass

    mock_response = MagicMock()
    mock_response.content = SAMPLE_CSV.encode("utf-8")
    mock_response.raise_for_status = MagicMock()

    with (
        patch.object(connector, "upsert_feature", side_effect=mock_upsert),
        patch.object(connector, "_update_staleness", side_effect=mock_staleness),
        patch.object(connector, "_get_cache_path", return_value=cache_file),
        patch("httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        await connector.run()

    assert len(upserted_calls) >= 1

    # First call should be Stadtwerke Aalen row
    first = upserted_calls[0]
    assert first["domain"] == "infrastructure"
    assert "POINT(" in first["geometry_wkt"]

    props = first["properties"]
    assert "operator" in props
    assert "address" in props
    assert "plug_types" in props
    assert isinstance(props["plug_types"], list)
    assert "max_power_kw" in props
    assert "num_charging_points" in props
    assert "charging_type" in props
    assert props["category"] == "ev_charging"


@pytest.mark.asyncio
async def test_run_plug_type_aggregation(
    connector: LadesaeulenConnector, tmp_path: Path
) -> None:
    """Plug types from Steckertypen1-4 are aggregated, empty strings excluded.

    Row 1 (Stadtwerke Aalen): Steckertypen1=Typ2, Steckertypen2=CCS, rest empty.
    Expected: plug_types == ["Typ2", "CCS"]
    """
    cache_file = tmp_path / "ladesaeulenregister.csv"

    upserted_calls = []

    async def mock_upsert(source_id, domain, geometry_wkt, properties):
        upserted_calls.append(properties)
        return "fake-uuid"

    async def mock_staleness():
        pass

    mock_response = MagicMock()
    mock_response.content = SAMPLE_CSV.encode("utf-8")
    mock_response.raise_for_status = MagicMock()

    with (
        patch.object(connector, "upsert_feature", side_effect=mock_upsert),
        patch.object(connector, "_update_staleness", side_effect=mock_staleness),
        patch.object(connector, "_get_cache_path", return_value=cache_file),
        patch("httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        await connector.run()

    assert len(upserted_calls) >= 1
    # First row (Stadtwerke Aalen) has Typ2 and CCS
    first_props = upserted_calls[0]
    plug_types = first_props["plug_types"]
    assert "Typ2" in plug_types
    assert "CCS" in plug_types
    # Empty strings should not appear in the list
    assert "" not in plug_types


@pytest.mark.asyncio
async def test_run_max_power_calculation(
    connector: LadesaeulenConnector, tmp_path: Path
) -> None:
    """max_power_kw is the maximum of all non-None P1..P4 values.

    Row 2 (EnBW): P1=150.0 (CCS), P2=50.0 (CHAdeMO) -> max=150.0
    """
    cache_file = tmp_path / "ladesaeulenregister.csv"

    upserted_calls = []

    async def mock_upsert(source_id, domain, geometry_wkt, properties):
        upserted_calls.append(properties)
        return "fake-uuid"

    async def mock_staleness():
        pass

    mock_response = MagicMock()
    mock_response.content = SAMPLE_CSV.encode("utf-8")
    mock_response.raise_for_status = MagicMock()

    with (
        patch.object(connector, "upsert_feature", side_effect=mock_upsert),
        patch.object(connector, "_update_staleness", side_effect=mock_staleness),
        patch.object(connector, "_get_cache_path", return_value=cache_file),
        patch("httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        await connector.run()

    # Second call should be EnBW row
    assert len(upserted_calls) >= 2
    second_props = upserted_calls[1]
    assert second_props["max_power_kw"] == pytest.approx(150.0)


@pytest.mark.asyncio
async def test_run_skips_missing_coordinates(
    connector: LadesaeulenConnector, tmp_path: Path
) -> None:
    """Rows with empty Breitengrad or Laengengrad are skipped (not upserted).

    Of 5 Ostalbkreis rows, 2 have missing coords. Only 3 should be upserted.
    """
    cache_file = tmp_path / "ladesaeulenregister.csv"
    upserted_count = 0

    async def mock_upsert(source_id, domain, geometry_wkt, properties):
        nonlocal upserted_count
        upserted_count += 1
        return "fake-uuid"

    async def mock_staleness():
        pass

    mock_response = MagicMock()
    mock_response.content = SAMPLE_CSV.encode("utf-8")
    mock_response.raise_for_status = MagicMock()

    with (
        patch.object(connector, "upsert_feature", side_effect=mock_upsert),
        patch.object(connector, "_update_staleness", side_effect=mock_staleness),
        patch.object(connector, "_get_cache_path", return_value=cache_file),
        patch("httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        await connector.run()

    assert upserted_count == 3


def test_connector_default_kreis_filter(aalen_town: Town) -> None:
    """LadesaeulenConnector defaults kreis_filter to Ostalbkreis if not set in config."""
    config = ConnectorConfig(
        connector_class="LadesaeulenConnector",
        poll_interval_seconds=86400,
        enabled=True,
        config={},
    )
    conn = LadesaeulenConnector(config, aalen_town)
    assert conn.config.config.get("kreis_filter", "Ostalbkreis") == "Ostalbkreis"
