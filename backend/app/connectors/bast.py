"""BastConnector: annual traffic count results from BASt (Bundesanstalt fuer Strassenwesen).

Implements TRAF-03: reads the permanent traffic count stations near the town from the
annual results CSV of the BASt automatic traffic counts and stores each station as a
'traffic' feature.

BASt data source:
    One CSV per year, newest published year first (current year minus 1, 2, 3):
    https://www.bast.de/DE/Themen/Digitales/HF_1/Massnahmen/verkehrszaehlung/Daten/<Y>_1/Jawe<Y>.csv?view=renderTcDataExportCSV
    A year that is not published yet answers 404 or an HTML page and is skipped.

CSV format (ISO-8859-15, semicolon-delimited, German numbers: "." thousands, "," decimal).
Columns used: DZ_Nr (station number), DZ_Name, Str_Kl / Str_Nr / Str_Zus (road),
Fernziel_Ri1 / Fernziel_Ri2 (directions), Anz_Fs_Q (lanes), DTV_Kfz_MobisSo_Q and
DTV_SV_MobisSo_Q (average vehicles and heavy vehicles per day), pSV_MobisSo_Q (heavy
vehicle share in %), Koor_WGS84_N / Koor_WGS84_E (position) and Anmerkungen (remark).

The file holds annual averages, not a time series, so they are stored as feature
properties (average vehicles per hour = DTV / 24) and no traffic_readings rows are written.

License: Datenlizenz Deutschland – Namensnennung – Version 2.0 (DL-DE-BY-2.0)
"""
from __future__ import annotations

import csv
import io
import logging
import re
from datetime import datetime, timezone
from typing import Any

import httpx

from app.connectors.base import BaseConnector, Observation
from app.config import ConnectorConfig, Town, TownBbox

logger = logging.getLogger(__name__)

USER_AGENT = "city-data-platform/0.1 (open-source city dashboard)"

# Annual results CSV; {year} is the data year.
BAST_CSV_URL_TEMPLATE = (
    "https://www.bast.de/DE/Themen/Digitales/HF_1/Massnahmen/verkehrszaehlung/Daten/"
    "{year}_1/Jawe{year}.csv?view=renderTcDataExportCSV"
)

# How many past years are tried (current year - 1 ... current year - 3).
YEARS_BACK = 3

# Stations this far (degrees) outside the town bbox are still shown; config key buffer_deg.
DEFAULT_BUFFER_DEG = 0.2

# Road capacity per lane per hour (standard German autobahn estimate)
LANE_CAPACITY_VEH_H = 800

DEFAULT_ATTRIBUTION = (
    "Bundesanstalt fuer Strassenwesen (BASt), "
    "Datenlizenz Deutschland – Namensnennung – Version 2.0"
)


def _current_year() -> int:
    return datetime.now(timezone.utc).year


def candidate_csv_urls(current_year: int) -> list[tuple[int, str]]:
    """Return (year, url) pairs for current_year - 1 down to current_year - YEARS_BACK."""
    return [
        (year, BAST_CSV_URL_TEMPLATE.format(year=year))
        for year in range(current_year - 1, current_year - 1 - YEARS_BACK, -1)
    ]


def _compute_congestion(count: int, lanes: int) -> str:
    """Compute congestion level from vehicle count and lane count.

    Args:
        count: Vehicles per hour (KFZ/h).
        lanes: Number of lanes (Fahrstreifen).

    Returns:
        'free' if ratio < 0.5, 'moderate' if 0.5 <= ratio < 0.8, 'congested' if >= 0.8.
        Defaults to 'free' if lanes is 0 to avoid division by zero.
    """
    if lanes <= 0:
        return "free"
    capacity = lanes * LANE_CAPACITY_VEH_H
    ratio = count / capacity
    if ratio < 0.5:
        return "free"
    elif ratio < 0.8:
        return "moderate"
    else:
        return "congested"


# Legacy hourly-format parser, still imported by MobiDataBWConnector (disabled in
# towns/aalen.yaml, code kept). It keeps its own fixed filter box; BastConnector itself
# derives the box from the town (see _parse_stations).
_LEGACY_BBOX_LAT_MIN = 48.56
_LEGACY_BBOX_LAT_MAX = 49.10
_LEGACY_BBOX_LON_MIN = 9.77
_LEGACY_BBOX_LON_MAX = 10.42


def _parse_bast_csv(raw: bytes) -> list[dict]:
    """Parse a windows-1252 hourly-count CSV into row dicts inside the legacy filter box.

    Used by MobiDataBWConnector only; BastConnector reads the annual results through
    _parse_stations().
    """
    text = raw.decode("windows-1252", errors="replace")
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    rows = []
    for row in reader:
        row = {k.strip(): v.strip() for k, v in row.items() if k}
        try:
            lat = float(row.get("PLat", "").replace(",", "."))
            lon = float(row.get("PLon", "").replace(",", "."))
        except (ValueError, KeyError):
            continue
        if not (
            _LEGACY_BBOX_LAT_MIN <= lat <= _LEGACY_BBOX_LAT_MAX
            and _LEGACY_BBOX_LON_MIN <= lon <= _LEGACY_BBOX_LON_MAX
        ):
            continue
        rows.append(row)
    return rows


def _german_int(value: str | None) -> int | None:
    """Parse '24.073' -> 24073. Empty or malformed -> None."""
    if value is None:
        return None
    text = value.strip().replace(".", "")
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _german_float(value: str | None) -> float | None:
    """Parse '48,80440378' -> 48.80440378. Empty or malformed -> None."""
    if value is None:
        return None
    text = value.strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _parse_stations(
    raw: bytes,
    bbox: TownBbox,
    buffer_deg: float,
    data_year: int | None = None,
) -> list[dict[str, Any]]:
    """Parse the BASt annual CSV into station dicts inside the town bbox plus buffer.

    Rows without both WGS84 coordinates are skipped. vehicle_count_total,
    vehicle_count_hgv and congestion_level are only present when the station has a DTV.

    Args:
        raw: Raw CSV bytes (ISO-8859-15).
        bbox: Town bounding box.
        buffer_deg: Degrees added on every side of the bbox.
        data_year: Year of the file, stored on every station.
    """
    text = raw.decode("iso-8859-15", errors="replace")
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    stations: list[dict[str, Any]] = []

    for row in reader:
        lat = _german_float(row.get("Koor_WGS84_N"))
        lon = _german_float(row.get("Koor_WGS84_E"))
        station_id = _clean(row.get("DZ_Nr"))
        if lat is None or lon is None or not station_id:
            continue
        if not (
            bbox.lat_min - buffer_deg <= lat <= bbox.lat_max + buffer_deg
            and bbox.lon_min - buffer_deg <= lon <= bbox.lon_max + buffer_deg
        ):
            continue

        road_name = " ".join(
            part for part in (_clean(row.get("Str_Kl")), _clean(row.get("Str_Nr"))) if part
        )
        road_name = (road_name + _clean(row.get("Str_Zus"))).strip()
        direction_parts = [_clean(row.get("Fernziel_Ri1")), _clean(row.get("Fernziel_Ri2"))]
        direction = " - ".join(direction_parts) if all(direction_parts) else ""

        lanes = _german_int(row.get("Anz_Fs_Q"))
        dtv_kfz = _german_int(row.get("DTV_Kfz_MobisSo_Q"))
        dtv_sv = _german_int(row.get("DTV_SV_MobisSo_Q"))

        station: dict[str, Any] = {
            "station_id": station_id,
            "station_name": _clean(row.get("DZ_Name")),
            "road_name": road_name,
            "lanes": lanes,
            "data_year": data_year,
            "lat": lat,
            "lon": lon,
        }
        if direction:
            station["direction"] = direction
        if dtv_kfz is not None:
            station["dtv_kfz"] = dtv_kfz
            station["vehicle_count_total"] = round(dtv_kfz / 24)
            station["congestion_level"] = _compute_congestion(
                station["vehicle_count_total"], lanes or 1
            )
        if dtv_sv is not None:
            station["dtv_sv"] = dtv_sv
            if dtv_kfz is not None:
                station["vehicle_count_hgv"] = round(dtv_sv / 24)
        sv_share = _german_float(row.get("pSV_MobisSo_Q"))
        if sv_share is not None:
            station["sv_share_pct"] = sv_share
        remark = _clean(row.get("Anmerkungen"))
        if remark:
            station["remark"] = remark

        stations.append(station)

    return stations


class BastConnector(BaseConnector):
    """Fetches BASt annual traffic count results for stations near the town.

    Config keys (from ConnectorConfig.config dict):
        csv_url: Explicit CSV URL (optional). Without it the newest published year is used.
        data_year: Data year of csv_url (optional, else read from "Jawe<YYYY>" in the URL).
        buffer_deg: Degrees around the town bbox in which stations are kept (default 0.2).
        attribution: Attribution string (optional).
    """

    def __init__(self, config: ConnectorConfig, town: Town) -> None:
        super().__init__(config, town)
        self._data_year: int | None = None

    async def fetch(self) -> bytes:
        """Fetch the newest published BASt annual results CSV.

        Without config csv_url the years current-1, current-2, current-3 are tried in
        order; a year that answers anything but a CSV (404, other status, HTML) counts
        as not published yet.

        Returns:
            Raw CSV bytes. The data year is kept in self._data_year.

        Raises:
            httpx.HTTPError: On network failure.
            ValueError: No candidate year is published.
        """
        explicit_url = self.config.config.get("csv_url")
        async with httpx.AsyncClient(timeout=60.0) as client:
            headers = {"User-Agent": USER_AGENT}

            if explicit_url:
                response = await client.get(explicit_url, headers=headers)
                response.raise_for_status()
                configured_year = self.config.config.get("data_year")
                if configured_year is None:
                    match = re.search(r"Jawe(\d{4})", explicit_url)
                    configured_year = int(match.group(1)) if match else None
                self._data_year = int(configured_year) if configured_year is not None else None
                return response.content

            tried: list[int] = []
            for year, url in candidate_csv_urls(_current_year()):
                tried.append(year)
                response = await client.get(url, headers=headers)
                first_line = response.content.decode("iso-8859-15", errors="replace").split("\n", 1)[0]
                if response.status_code == 200 and first_line.startswith("TK_Nr"):
                    self._data_year = year
                    logger.info("BastConnector: using annual results of %d", year)
                    return response.content
                logger.info(
                    "BastConnector: year %d not published (HTTP %s)", year, response.status_code
                )

        raise ValueError(
            "BASt annual results CSV not found for years " + ", ".join(str(y) for y in tried)
        )

    def normalize(self, raw: bytes, **kwargs) -> list[Observation]:
        """Annual averages are stored as feature properties — no observations."""
        return []

    async def run(self) -> None:
        """Full pipeline: fetch CSV, parse stations, upsert features, update staleness.

        Overrides BaseConnector.run(). No traffic_readings rows are written: the file
        holds one annual average per station, and re-running every poll would only
        duplicate rows.
        """
        attribution = self.config.config.get("attribution", DEFAULT_ATTRIBUTION)
        buffer_deg = float(self.config.config.get("buffer_deg", DEFAULT_BUFFER_DEG))

        raw = await self.fetch()
        stations = _parse_stations(raw, self.town.bbox, buffer_deg, self._data_year)

        for station in stations:
            lat = station["lat"]
            lon = station["lon"]
            properties = {k: v for k, v in station.items() if k not in ("lat", "lon")}
            properties["attribution"] = attribution
            properties["data_source"] = "BASt"

            await self.upsert_feature(
                source_id=f"bast:{station['station_id']}",
                domain="traffic",
                geometry_wkt=f"POINT({lon} {lat})",
                properties=properties,
            )

        logger.info(
            "BastConnector: upserted %d stations for %s (data year %s)",
            len(stations),
            self.town.id,
            self._data_year,
        )
        await self._update_staleness()
