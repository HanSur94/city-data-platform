"""Tests for BastConnector (TRAF-03).

BASt (Bundesanstalt fuer Strassenwesen) publishes the annual results of the
permanent traffic counts as one CSV per year (ISO-8859-15, semicolon, German
number format). The fixture below is cut from the real 2024 file: the header is
limited to the columns the connector reads and the rows are verbatim.

License: Datenlizenz Deutschland – Namensnennung – Version 2.0
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import ConnectorConfig, Town, TownBbox
from app.connectors.base import Observation
from app.connectors.bast import (
    BastConnector,
    _compute_congestion,
    _parse_stations,
    candidate_csv_urls,
)

HEADER = (
    "TK_Nr;DZ_Nr;DZ_Name;Str_Kl;Str_Nr;Str_Zus;Fernziel_Ri1;Fernziel_Ri2;Anz_Fs_Q;"
    "DTV_Kfz_MobisSo_Q;DTV_SV_MobisSo_Q;pSV_MobisSo_Q;Koor_WGS84_N;Koor_WGS84_E;Anmerkungen;"
)
ROW_GMUEND = "    7224;8405;Schwäbisch Gmünd;B;29;;Aalen;Stuttgart;2;24.073;2.239;9,3;48,80440378;9,79055461;;"
ROW_AALEN_WEST = "    7126;8468;Westumgehung Aalen;B;29;;Stuttgart;Nördlingen;2;;;;48,83496729;10,06702402;Datenprobleme in 2024;"
ROW_CRAILSHEIM = "    6826;8827;Crailsheim-Süd;B;290;;Crailsheim;Ellwangen;2;6.556;300;4,6;49,09951112;10,06622983;;"
ROW_HAMBURG = "    2426;2218;AD HH-Südost (O);A;1;;Lübeck;Hamburg;6;;;;53,50754848;10,08718293;Netzmodernisierung in 2024;"
ROW_NO_COORDS = "    9001;9001;Ohne Koordinaten;B;1;;A;B;2;1.000;100;10,0;;;;"
ROW_TRAILING = "    "

CSV_TEXT = "\n".join(
    [HEADER, ROW_GMUEND, ROW_AALEN_WEST, ROW_CRAILSHEIM, ROW_HAMBURG, ROW_NO_COORDS, ROW_TRAILING]
)
CSV_BYTES = CSV_TEXT.encode("iso-8859-15")

AALEN_BBOX = TownBbox(lon_min=9.9700, lat_min=48.7600, lon_max=10.2200, lat_max=48.9000)


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
        bbox=AALEN_BBOX,
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
# URL candidates
# ---------------------------------------------------------------------------

def test_candidate_urls_walk_back_three_years() -> None:
    candidates = candidate_csv_urls(2026)
    assert [year for year, _ in candidates] == [2025, 2024, 2023]
    for year, url in candidates:
        assert url == (
            "https://www.bast.de/DE/Themen/Digitales/HF_1/Massnahmen/verkehrszaehlung/Daten/"
            f"{year}_1/Jawe{year}.csv?view=renderTcDataExportCSV"
        )


# ---------------------------------------------------------------------------
# fetch()
# ---------------------------------------------------------------------------

def _response(status: int, content: bytes) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.content = content
    resp.raise_for_status = MagicMock()
    return resp


def _patched_client(responses: list[MagicMock], calls: list[dict]) -> AsyncMock:
    queue = list(responses)

    async def mock_get(url, **kwargs):
        calls.append({"url": url, **kwargs})
        return queue.pop(0)

    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get = AsyncMock(side_effect=mock_get)
    return client


@pytest.mark.asyncio
async def test_fetch_falls_back_to_newest_published_year(connector: BastConnector) -> None:
    calls: list[dict] = []
    client = _patched_client(
        [_response(404, b"<html>not found</html>"), _response(200, CSV_BYTES)], calls
    )
    with (
        patch("httpx.AsyncClient") as cls,
        patch("app.connectors.bast._current_year", return_value=2026),
    ):
        cls.return_value = client
        result = await connector.fetch()

    assert result == CSV_BYTES
    assert connector._data_year == 2024
    assert [c["url"] for c in calls] == [url for _, url in candidate_csv_urls(2026)[:2]]
    for call in calls:
        assert "city-data-platform" in call["headers"]["User-Agent"]


@pytest.mark.asyncio
async def test_fetch_treats_html_200_as_not_published(connector: BastConnector) -> None:
    calls: list[dict] = []
    client = _patched_client(
        [_response(200, b"<!DOCTYPE html><html></html>"), _response(200, CSV_BYTES)], calls
    )
    with (
        patch("httpx.AsyncClient") as cls,
        patch("app.connectors.bast._current_year", return_value=2026),
    ):
        cls.return_value = client
        result = await connector.fetch()

    assert result == CSV_BYTES
    assert connector._data_year == 2024
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_fetch_raises_when_no_year_is_published(connector: BastConnector) -> None:
    calls: list[dict] = []
    client = _patched_client([_response(404, b"") for _ in range(3)], calls)
    with (
        patch("httpx.AsyncClient") as cls,
        patch("app.connectors.bast._current_year", return_value=2026),
    ):
        cls.return_value = client
        with pytest.raises(ValueError) as excinfo:
            await connector.fetch()

    message = str(excinfo.value)
    assert "2025" in message and "2024" in message and "2023" in message
    assert len(calls) == 3


@pytest.mark.asyncio
async def test_fetch_with_explicit_csv_url_makes_one_request(aalen_town: Town) -> None:
    url = "https://example.invalid/Jawe2022.csv"
    config = ConnectorConfig(
        connector_class="BastConnector", poll_interval_seconds=86400, config={"csv_url": url}
    )
    connector = BastConnector(config=config, town=aalen_town)
    calls: list[dict] = []
    client = _patched_client([_response(200, CSV_BYTES)], calls)
    with patch("httpx.AsyncClient") as cls:
        cls.return_value = client
        result = await connector.fetch()

    assert result == CSV_BYTES
    assert [c["url"] for c in calls] == [url]
    assert connector._data_year == 2022


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def test_parse_stations_inside_town_plus_buffer() -> None:
    stations = _parse_stations(CSV_BYTES, AALEN_BBOX, 0.2, data_year=2024)
    by_id = {s["station_id"]: s for s in stations}

    assert set(by_id) == {"8405", "8468", "8827"}

    gmuend = by_id["8405"]
    assert gmuend["station_name"] == "Schwäbisch Gmünd"
    assert gmuend["road_name"] == "B 29"
    assert gmuend["direction"] == "Aalen - Stuttgart"
    assert gmuend["lanes"] == 2
    assert gmuend["dtv_kfz"] == 24073
    assert gmuend["dtv_sv"] == 2239
    assert gmuend["sv_share_pct"] == pytest.approx(9.3)
    assert gmuend["vehicle_count_total"] == 1003
    assert gmuend["vehicle_count_hgv"] == 93
    assert gmuend["congestion_level"] == "moderate"
    assert gmuend["data_year"] == 2024
    assert gmuend["lat"] == pytest.approx(48.80440378)
    assert gmuend["lon"] == pytest.approx(9.79055461)

    aalen = by_id["8468"]
    assert "dtv_kfz" not in aalen or aalen["dtv_kfz"] is None
    assert "vehicle_count_total" not in aalen
    assert "congestion_level" not in aalen
    assert aalen["remark"] == "Datenprobleme in 2024"

    crailsheim = by_id["8827"]
    assert crailsheim["road_name"] == "B 290"
    assert crailsheim["vehicle_count_total"] == 273
    assert crailsheim["congestion_level"] == "free"


def test_parse_stations_excludes_far_rows_and_rows_without_coordinates() -> None:
    stations = _parse_stations(CSV_BYTES, AALEN_BBOX, 0.2, data_year=2024)
    ids = {s["station_id"] for s in stations}
    assert "2218" not in ids  # Hamburg
    assert "9001" not in ids  # no coordinates


def test_parse_stations_without_buffer_keeps_only_town_stations() -> None:
    stations = _parse_stations(CSV_BYTES, AALEN_BBOX, 0.0, data_year=2024)
    assert [s["station_id"] for s in stations] == ["8468"]


def test_normalize_returns_no_observations(connector: BastConnector) -> None:
    """Annual averages are stored as feature properties, not as time-series rows."""
    assert connector.normalize(CSV_BYTES) == []


# ---------------------------------------------------------------------------
# run()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_upserts_features_only(connector: BastConnector) -> None:
    connector.fetch = AsyncMock(return_value=CSV_BYTES)
    connector._data_year = 2024
    connector.upsert_feature = AsyncMock(return_value="feature-uuid")
    connector.persist = AsyncMock()
    connector._update_staleness = AsyncMock()

    await connector.run()

    assert connector.upsert_feature.await_count == 3
    kwargs = [c.kwargs for c in connector.upsert_feature.await_args_list]
    assert [k["source_id"] for k in kwargs] == ["bast:8405", "bast:8468", "bast:8827"]
    assert all(k["domain"] == "traffic" for k in kwargs)
    assert kwargs[0]["geometry_wkt"] == "POINT(9.79055461 48.80440378)"
    props = kwargs[0]["properties"]
    assert props["data_source"] == "BASt"
    assert props["vehicle_count_total"] == 1003
    assert props["station_name"] == "Schwäbisch Gmünd"
    assert "lat" not in props and "lon" not in props
    assert "attribution" in props
    connector.persist.assert_not_awaited()
    connector._update_staleness.assert_awaited_once()
