"""BastConnector: fetches annual traffic count data from BASt (Bundesanstalt fuer Strassenwesen).

Implements TRAF-03: retrieves vehicle counts for stations near Aalen from BASt CSV
and writes traffic readings to the traffic_readings hypertable.

BASt data source:
    Annual hourly traffic count CSV at:
    https://www.bast.de/DE/Verkehrstechnik/Fachthemen/v2-verkehrszaehlung/Daten/

CSV format (windows-1252 encoded, semicolon-delimited):
    Zst;Land;Strasse;Abschnitt;ANr;VNr;Dat;Stunde;KFZ;SV;V_PKW;V_LKW;PLat;PLon;Richtung;Fahrstreifen

License: Datenlizenz Deutschland – Namensnennung – Version 2.0 (DL-DE-BY-2.0)
"""
from __future__ import annotations

import csv
import io
import math
from datetime import datetime, timezone
from typing import Any

import httpx

from app.connectors.base import BaseConnector, Observation
from app.config import ConnectorConfig, Town


# Latest annual hourly data CSV from BASt (2023 data)
BAST_CSV_URL = (
    "https://www.bast.de/DE/Verkehrstechnik/Fachthemen/v2-verkehrszaehlung/"
    "Daten/2023_1/Jawe2023.csv?__blob=publicationFile&v=13"
)

# Aalen bounding box + ~20km buffer
# Aalen center: lat=48.84, lon=10.09
# 20km ~ 0.18 deg lat, 0.26 deg lon
BBOX_LAT_MIN = 48.56
BBOX_LAT_MAX = 49.10
BBOX_LON_MIN = 9.77
BBOX_LON_MAX = 10.42

# Road capacity per lane per hour (standard German autobahn estimate)
LANE_CAPACITY_VEH_H = 800


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


def _parse_bast_csv(raw: bytes) -> list[dict]:
    """Parse BASt CSV bytes into a list of row dicts.

    Handles windows-1252 encoding and semicolon delimiter.
    Filters rows to those within Aalen bbox + 20km buffer.

    Args:
        raw: Raw CSV bytes from BASt.

    Returns:
        List of dicts with keys matching CSV column names, filtered by bbox.
    """
    text = raw.decode("windows-1252", errors="replace")
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    rows = []
    for row in reader:
        # Strip whitespace from keys and values
        row = {k.strip(): v.strip() for k, v in row.items() if k}
        try:
            lat = float(row.get("PLat", "").replace(",", "."))
            lon = float(row.get("PLon", "").replace(",", "."))
        except (ValueError, KeyError):
            continue
        # Filter to Aalen bbox + 20km buffer
        if not (BBOX_LAT_MIN <= lat <= BBOX_LAT_MAX and BBOX_LON_MIN <= lon <= BBOX_LON_MAX):
            continue
        rows.append(row)
    return rows


class BastConnector(BaseConnector):
    """Fetches BASt annual traffic count data for stations near Aalen.

    Config keys (from ConnectorConfig.config dict):
        csv_url: Override for the BASt CSV URL (optional, uses default if absent).
        attribution: Attribution string (optional).
    """

    def __init__(self, config: ConnectorConfig, town: Town) -> None:
        super().__init__(config, town)
        # Maps BASt station_id -> features table UUID
        self._feature_ids: dict[str, str] = {}

    async def fetch(self) -> bytes:
        """Fetch the BASt annual traffic count CSV.

        Returns:
            Raw CSV bytes.

        Raises:
            httpx.HTTPError: On network/HTTP failure.
        """
        url = self.config.config.get("csv_url", BAST_CSV_URL)
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    def normalize(self, raw: bytes, **kwargs) -> list[Observation]:
        """Transform BASt CSV bytes into Observations.

        Decodes using windows-1252 encoding, parses CSV with semicolon delimiter,
        filters to Aalen bbox+20km, computes congestion level, returns Observations.

        Args:
            raw: CSV bytes returned by fetch().

        Returns:
            List of Observation objects with domain='traffic'.
        """
        rows = _parse_bast_csv(raw)
        observations: list[Observation] = []

        for row in rows:
            station_id = row.get("Zst", "").strip()
            if not station_id:
                continue

            try:
                vehicle_count_total = int(row.get("KFZ", "0") or "0")
                vehicle_count_hgv = int(row.get("SV", "0") or "0")
                speed_avg_pkw = float(row.get("V_PKW", "0").replace(",", ".") or "0")
                speed_avg_lkw = float(row.get("V_LKW", "0").replace(",", ".") or "0")
                lanes = int(row.get("Fahrstreifen", "1") or "1")
            except (ValueError, KeyError):
                continue

            # Average speed weighted roughly between PKW and HGV
            speed_avg_kmh: float | None = None
            if speed_avg_pkw > 0 or speed_avg_lkw > 0:
                speed_avg_kmh = (speed_avg_pkw + speed_avg_lkw) / 2.0

            congestion_level = _compute_congestion(vehicle_count_total, lanes)

            # Parse timestamp from Dat + Stunde columns
            ts: datetime | None = None
            dat = row.get("Dat", "")
            stunde = row.get("Stunde", "")
            if dat and stunde:
                try:
                    # BASt format: DD.MM.YYYY, hour as integer 1-24
                    hour = int(stunde) % 24
                    ts = datetime.strptime(dat, "%d.%m.%Y").replace(
                        hour=hour, tzinfo=timezone.utc
                    )
                except (ValueError, TypeError):
                    ts = None

            feature_id = self._feature_ids.get(station_id, "")

            observations.append(
                Observation(
                    feature_id=feature_id,
                    domain="traffic",
                    values={
                        "vehicle_count_total": vehicle_count_total,
                        "vehicle_count_hgv": vehicle_count_hgv,
                        "speed_avg_kmh": speed_avg_kmh,
                        "congestion_level": congestion_level,
                    },
                    timestamp=ts,
                    source_id=f"bast:{station_id}",
                )
            )

        return observations

    async def run(self) -> None:
        """Full pipeline: fetch CSV, upsert features, normalize, persist, update staleness.

        Overrides BaseConnector.run() to:
        1. Fetch raw CSV bytes
        2. Parse CSV to get station list
        3. Upsert each station as a spatial feature
        4. Normalize into Observations (using cached _feature_ids)
        5. Persist to traffic_readings
        6. Update staleness timestamp
        """
        attribution = self.config.config.get(
            "attribution",
            "Bundesanstalt fuer Strassenwesen (BASt), Datenlizenz Deutschland – Namensnennung – Version 2.0",
        )

        # Step 1: fetch raw CSV
        raw = await self.fetch()

        # Step 2: parse stations (already bbox-filtered)
        rows = _parse_bast_csv(raw)

        # Step 3: upsert features
        for row in rows:
            station_id = row.get("Zst", "").strip()
            if not station_id:
                continue
            try:
                lat = float(row.get("PLat", "").replace(",", "."))
                lon = float(row.get("PLon", "").replace(",", "."))
            except (ValueError, KeyError):
                continue

            road = row.get("Strasse", "")
            direction = row.get("Richtung", "")

            feature_id = await self.upsert_feature(
                source_id=f"bast:{station_id}",
                domain="traffic",
                geometry_wkt=f"POINT({lon} {lat})",
                properties={
                    "station_id": station_id,
                    "road": road,
                    "direction": direction,
                    "attribution": attribution,
                    "data_source": "BASt",
                },
            )
            self._feature_ids[station_id] = feature_id

        # Step 4-6: normalize -> persist -> update staleness
        observations = self.normalize(raw)
        await self.persist(observations)
        await self._update_staleness()
