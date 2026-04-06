"""MobiDataBWConnector: fetches traffic count data from MobiData BW.

Implements TRAF-05: retrieves vehicle counts for Baden-Wuerttemberg roads near Aalen
from MobiData BW CSV and writes traffic readings to the traffic_readings hypertable.

MobiData BW provides traffic count data in the same CSV format as BASt (windows-1252,
semicolon-delimited) but for BW Landesstrassen and Bundesstrassen.

License: Datenlizenz Deutschland – Namensnennung – Version 2.0 (DL-DE-BY-2.0)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.connectors.base import BaseConnector, Observation
from app.connectors.bast import _compute_congestion, _parse_bast_csv
from app.config import ConnectorConfig, Town


# MobiData BW traffic count CSV endpoint
# Baden-Wuerttemberg traffic count data (BW Strassenverkehrszaehlung)
MOBIDATA_URL = (
    "https://www.mobidata-bw.de/dataset/strassenverkehrszahlung-bw/"
    "resource/bw-traffic-count.csv"
)


class MobiDataBWConnector(BaseConnector):
    """Fetches MobiData BW traffic count data for stations near Aalen.

    Uses the same CSV format and parsing logic as BastConnector,
    sharing _parse_bast_csv and _compute_congestion from bast.py.

    Config keys (from ConnectorConfig.config dict):
        csv_url: Override for the MobiData BW CSV URL (optional).
        attribution: Attribution string (optional).
    """

    def __init__(self, config: ConnectorConfig, town: Town) -> None:
        super().__init__(config, town)
        # Maps station_id -> features table UUID
        self._feature_ids: dict[str, str] = {}

    async def fetch(self) -> bytes:
        """Fetch the MobiData BW traffic count CSV.

        Returns:
            Raw CSV bytes.

        Raises:
            httpx.HTTPError: On network/HTTP failure.
        """
        url = self.config.config.get("csv_url", MOBIDATA_URL)
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    def normalize(self, raw: bytes, **kwargs) -> list[Observation]:
        """Transform MobiData BW CSV bytes into Observations.

        Reuses BASt CSV parsing logic (_parse_bast_csv) since MobiData BW
        uses the same CSV format. Output format matches BastConnector output.

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

            # Average speed
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
                    source_id=f"mobidata_bw:{station_id}",
                )
            )

        return observations

    async def run(self) -> None:
        """Full pipeline: fetch CSV, upsert features, normalize, persist, update staleness.

        Overrides BaseConnector.run() to:
        1. Fetch raw CSV bytes
        2. Parse CSV to get station list (bbox-filtered via _parse_bast_csv)
        3. Upsert each station as a spatial feature
        4. Normalize into Observations (using cached _feature_ids)
        5. Persist to traffic_readings
        6. Update staleness timestamp
        """
        attribution = self.config.config.get(
            "attribution",
            "MobiData BW, Datenlizenz Deutschland – Namensnennung – Version 2.0",
        )

        # Step 1: fetch raw CSV
        raw = await self.fetch()

        # Step 2: parse stations (already bbox-filtered via _parse_bast_csv)
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
                source_id=f"mobidata_bw:{station_id}",
                domain="traffic",
                geometry_wkt=f"POINT({lon} {lat})",
                properties={
                    "station_id": station_id,
                    "road": road,
                    "direction": direction,
                    "attribution": attribution,
                    "data_source": "MobiData BW",
                },
            )
            self._feature_ids[station_id] = feature_id

        # Step 4-6: normalize -> persist -> update staleness
        observations = self.normalize(raw)
        await self.persist(observations)
        await self._update_staleness()
