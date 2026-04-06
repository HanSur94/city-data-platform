"""ZensusConnector: fetches census data from Zensus 2022 REST API.

Implements DEMO-02: retrieves population count and household count from the
Zensus 2022 REST API. Also registers a WMS layer URL for the census grid
overlay in the frontend.

Primary endpoint (Zensus 2022 REST):
    GET https://ergebnisse2011.zensus2022.de/api/rest/2020/data/tablefile
        ?name=1000A-0001&ags={ags}

WMS overlay (census grid visualization):
    https://atlas.zensus2022.de/geoserver/ows

License: Statistisches Bundesamt, Zensus 2022, DL-DE-BY-2.0
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.connectors.base import BaseConnector, Observation
from app.config import ConnectorConfig, Town

logger = logging.getLogger(__name__)

ZENSUS_API_BASE = "https://ergebnisse2011.zensus2022.de/api/rest/2020/data/tablefile"
ZENSUS_WMS_URL = "https://atlas.zensus2022.de/geoserver/ows"

AALEN_LON = 10.09
AALEN_LAT = 48.84


class ZensusConnector(BaseConnector):
    """Fetches census data from Zensus 2022 REST API.

    Config keys (from ConnectorConfig.config dict):
        ags: Amtlicher Gemeindeschluessel (default "08136088" for Aalen)
        wms_url: WMS URL for census grid overlay (for frontend)
        attribution: Data attribution string
    """

    def __init__(self, config: ConnectorConfig, town: Town) -> None:
        super().__init__(config, town)
        self._feature_id: str | None = None

    async def fetch(self) -> dict:
        """Fetch census data for the configured municipality.

        Returns:
            Dict with census data, or empty dict on failure.
        """
        ags = self.config.config.get("ags", "08136088")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    ZENSUS_API_BASE,
                    params={"name": "1000A-0001", "ags": ags},
                )
                if response.status_code >= 400:
                    logger.warning(
                        "ZensusConnector: API returned %d for AGS %s",
                        response.status_code,
                        ags,
                    )
                    return {}
                # API may return JSON or CSV depending on format
                content_type = response.headers.get("content-type", "")
                if "json" in content_type:
                    return {"ags": ags, "format": "json", "data": response.json()}
                else:
                    # Plain text / CSV response
                    return {"ags": ags, "format": "text", "data": response.text}
        except Exception as exc:
            logger.warning(
                "ZensusConnector: fetch failed for AGS %s: %s", ags, exc
            )
            return {}

    def normalize(self, raw: dict) -> list[Observation]:
        """Transform Zensus 2022 API response into Observations.

        Extracts population count and household count from the census data.

        Args:
            raw: Dict returned by fetch().

        Returns:
            List of Observation objects with domain="demographics".
        """
        if not raw:
            return []

        ags = raw.get("ags", self.config.config.get("ags", "08136088"))
        feature_id = self._feature_id or ""
        data_format = raw.get("format", "unknown")
        data = raw.get("data", {})

        wms_url = self.config.config.get("wms_url", ZENSUS_WMS_URL)

        values: dict[str, Any] = {
            "ags": ags,
            "wms_url": wms_url,
            "data_source": "zensus_2022",
        }

        population: float | None = None
        households: float | None = None

        if data_format == "json" and isinstance(data, dict):
            # JSON format: look for population/household fields
            for key, val in data.items():
                key_lower = key.lower()
                if "einwohner" in key_lower or "bevoelkerung" in key_lower:
                    try:
                        population = float(str(val).replace(",", ".").replace(" ", ""))
                    except (TypeError, ValueError):
                        pass
                elif "haushalte" in key_lower or "household" in key_lower:
                    try:
                        households = float(str(val).replace(",", ".").replace(" ", ""))
                    except (TypeError, ValueError):
                        pass

        elif data_format == "text" and isinstance(data, str):
            # CSV/text format — parse line by line
            for line in data.splitlines():
                line = line.strip()
                if not line or line.startswith(("#", ";")):
                    continue
                parts = [p.strip().strip('"') for p in line.split(";")]
                if len(parts) < 2:
                    parts = [p.strip().strip('"') for p in line.split(",")]

                if len(parts) >= 2:
                    label = parts[0].lower()
                    value_str = parts[-1] if len(parts) > 1 else ""
                    if "einwohner" in label or "bevoelkerung" in label or "insgesamt" in label:
                        try:
                            population = float(
                                value_str.replace(",", ".").replace(" ", "").replace(".", "")
                                if "." in value_str and "," not in value_str
                                else value_str.replace(".", "").replace(",", ".")
                            )
                        except (TypeError, ValueError):
                            pass
                    elif "haushalte" in label or "household" in label:
                        try:
                            households = float(
                                value_str.replace(".", "").replace(",", ".")
                            )
                        except (TypeError, ValueError):
                            pass

        if population is not None:
            values["population"] = population
        if households is not None:
            values["households"] = households

        real_values = {k: v for k, v in values.items() if v is not None}
        # Must have at least one demographic value beyond metadata fields
        demographic_keys = {"population", "households"}
        if not demographic_keys.intersection(real_values.keys()):
            logger.warning(
                "ZensusConnector: no census data extracted for AGS %s "
                "(API may require authentication or data not available)", ags
            )
            # Still return an observation with WMS URL for frontend use
            return [
                Observation(
                    feature_id=feature_id,
                    domain="demographics",
                    values={"ags": ags, "wms_url": wms_url, "data_source": "zensus_2022"},
                    source_id=f"zensus:{ags}",
                )
            ]

        return [
            Observation(
                feature_id=feature_id,
                domain="demographics",
                values=real_values,
                source_id=f"zensus:{ags}",
            )
        ]

    async def run(self) -> None:
        """Full pipeline: upsert feature -> fetch -> normalize -> persist -> update staleness."""
        ags = self.config.config.get("ags", "08136088")
        lon = self.config.config.get("lon", AALEN_LON)
        lat = self.config.config.get("lat", AALEN_LAT)
        wms_url = self.config.config.get("wms_url", ZENSUS_WMS_URL)

        self._feature_id = await self.upsert_feature(
            source_id=f"zensus:{ags}",
            domain="demographics",
            geometry_wkt=f"POINT({lon} {lat})",
            properties={
                "ags": ags,
                "source": "Zensus 2022",
                "wms_url": wms_url,
                "attribution": self.config.config.get(
                    "attribution",
                    "Statistisches Bundesamt, Zensus 2022, DL-DE-BY-2.0",
                ),
            },
        )

        raw = await self.fetch()
        observations = self.normalize(raw)
        await self.persist(observations)
        await self._update_staleness()
