"""StatistikBWConnector: fetches population data from Statistisches Landesamt BW.

Implements DEMO-01: retrieves population figures (total, male, female) for a
municipality from the Statistik BW GENESIS portal or Regionalstatistik fallback.

Primary endpoint (Statistik BW SRDB):
    GET https://www.statistik-bw.de/SRDB/Tabellen/api/?ags={ags}&tab=R0001

Fallback (Regionalstatistik.de free tier):
    GET https://www.regionalstatistik.de/genesisws/rest/2020/data/tablefile
        ?name=12411-01-02-4&ags={ags}&username=&password=

License: Datenlizenz Deutschland – Namensnennung – Version 2.0 (DL-DE-BY-2.0)
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.connectors.base import BaseConnector, Observation
from app.config import ConnectorConfig, Town

logger = logging.getLogger(__name__)

STATISTIK_BW_BASE = "https://www.statistik-bw.de/SRDB/Tabellen/api/"
REGIONALSTATISTIK_BASE = (
    "https://www.regionalstatistik.de/genesisws/rest/2020/data/tablefile"
)

AALEN_LON = 10.09
AALEN_LAT = 48.84


class StatistikBWConnector(BaseConnector):
    """Fetches population data from Statistik BW / Regionalstatistik.

    Config keys (from ConnectorConfig.config dict):
        ags: Amtlicher Gemeindeschluessel (default "08136088" for Aalen)
        attribution: Data attribution string
    """

    def __init__(self, config: ConnectorConfig, town: Town) -> None:
        super().__init__(config, town)
        self._feature_id: str | None = None

    async def _fetch_statistik_bw(
        self, client: httpx.AsyncClient, ags: str
    ) -> dict | None:
        """Attempt to fetch from Statistik BW SRDB API.

        Returns parsed JSON dict or None on failure.
        """
        try:
            response = await client.get(
                STATISTIK_BW_BASE,
                params={"ags": ags, "tab": "R0001"},
            )
            if response.status_code == 200:
                return response.json()
            logger.warning(
                "StatistikBWConnector: primary API returned %d for AGS %s",
                response.status_code,
                ags,
            )
        except Exception as exc:
            logger.warning(
                "StatistikBWConnector: primary API failed for AGS %s: %s", ags, exc
            )
        return None

    async def _fetch_regionalstatistik(
        self, client: httpx.AsyncClient, ags: str
    ) -> dict | None:
        """Fallback: fetch from Regionalstatistik.de (free tier, no auth).

        Returns parsed JSON dict or None on failure.
        """
        try:
            response = await client.get(
                REGIONALSTATISTIK_BASE,
                params={
                    "name": "12411-01-02-4",
                    "ags": ags,
                    "username": "",
                    "password": "",
                },
            )
            if response.status_code == 200:
                data = response.json()
                return data
            logger.warning(
                "StatistikBWConnector: fallback API returned %d for AGS %s",
                response.status_code,
                ags,
            )
        except Exception as exc:
            logger.warning(
                "StatistikBWConnector: fallback API failed for AGS %s: %s", ags, exc
            )
        return None

    async def fetch(self) -> dict:
        """Fetch population data, trying primary then fallback source.

        Returns:
            Dict with population data, or empty dict if both sources fail.
        """
        ags = self.config.config.get("ags", "08136088")

        async with httpx.AsyncClient(timeout=30.0) as client:
            data = await self._fetch_statistik_bw(client, ags)
            if data:
                return {"source": "statistik_bw", "data": data, "ags": ags}

            data = await self._fetch_regionalstatistik(client, ags)
            if data:
                return {"source": "regionalstatistik", "data": data, "ags": ags}

        logger.warning(
            "StatistikBWConnector: all sources failed for AGS %s", ags
        )
        return {}

    def normalize(self, raw: dict) -> list[Observation]:
        """Transform population API response into Observations.

        Extracts total population, and male/female breakdown if available.

        Args:
            raw: Dict returned by fetch().

        Returns:
            List of Observation objects with domain="demographics".
        """
        if not raw:
            return []

        ags = raw.get("ags", self.config.config.get("ags", "08136088"))
        feature_id = self._feature_id or ""
        source = raw.get("source", "unknown")
        data = raw.get("data", {})

        values: dict[str, Any] = {"ags": ags, "data_source": source}

        if isinstance(data, dict):
            # Statistik BW SRDB format: look for population fields
            def _safe_float(d: dict, *keys: str) -> float | None:
                for k in keys:
                    v = d.get(k)
                    if v is not None:
                        try:
                            return float(str(v).replace(",", ".").replace(" ", ""))
                        except (TypeError, ValueError):
                            pass
                return None

            population_total = _safe_float(
                data, "bevoelkerung", "population", "einwohner", "gesamt", "total"
            )
            population_male = _safe_float(data, "maennlich", "male", "m")
            population_female = _safe_float(data, "weiblich", "female", "w", "f")

            # Handle nested "rows"/"values" structure
            if population_total is None and "rows" in data:
                rows = data["rows"]
                if isinstance(rows, list) and rows:
                    first_row = rows[0]
                    if isinstance(first_row, (list, tuple)) and len(first_row) >= 1:
                        try:
                            population_total = float(first_row[0])
                        except (TypeError, ValueError):
                            pass

            if population_total is not None:
                values["population"] = population_total
            if population_male is not None:
                values["population_male"] = population_male
            if population_female is not None:
                values["population_female"] = population_female

        elif isinstance(data, list) and data:
            # Regionalstatistik may return a list of records
            for record in data:
                if not isinstance(record, dict):
                    continue
                for key, val in record.items():
                    if "insgesamt" in key.lower() or "gesamt" in key.lower():
                        try:
                            values["population"] = float(
                                str(val).replace(",", ".").replace(" ", "")
                            )
                        except (TypeError, ValueError):
                            pass
                    elif "maennl" in key.lower():
                        try:
                            values["population_male"] = float(
                                str(val).replace(",", ".").replace(" ", "")
                            )
                        except (TypeError, ValueError):
                            pass
                    elif "weibl" in key.lower():
                        try:
                            values["population_female"] = float(
                                str(val).replace(",", ".").replace(" ", "")
                            )
                        except (TypeError, ValueError):
                            pass

        real_values = {k: v for k, v in values.items() if v is not None}
        if len(real_values) <= 2:
            # Only ags + data_source — no real population data
            logger.warning(
                "StatistikBWConnector: no population data extracted for AGS %s", ags
            )
            return []

        return [
            Observation(
                feature_id=feature_id,
                domain="demographics",
                values=real_values,
                source_id=f"statistik_bw:{ags}",
            )
        ]

    async def run(self) -> None:
        """Full pipeline: upsert feature -> fetch -> normalize -> persist -> update staleness."""
        ags = self.config.config.get("ags", "08136088")
        lon = self.config.config.get("lon", AALEN_LON)
        lat = self.config.config.get("lat", AALEN_LAT)

        self._feature_id = await self.upsert_feature(
            source_id=f"statistik_bw:{ags}",
            domain="demographics",
            geometry_wkt=f"POINT({lon} {lat})",
            properties={
                "ags": ags,
                "source": "Statistik BW",
                "attribution": self.config.config.get(
                    "attribution",
                    "Statistisches Landesamt Baden-Wuerttemberg, DL-DE-BY-2.0",
                ),
            },
        )

        raw = await self.fetch()
        observations = self.normalize(raw)
        await self.persist(observations)
        await self._update_staleness()
