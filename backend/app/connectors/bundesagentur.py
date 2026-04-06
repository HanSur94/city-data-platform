"""BundesagenturConnector: fetches employment data from Bundesagentur fuer Arbeit.

Implements DEMO-04: retrieves unemployment rate, total employed, and open positions
for a municipality/district from the Bundesagentur fuer Arbeit REST API.

Primary endpoint (Arbeitsmarktberichte REST API):
    GET https://rest.arbeitsagentur.de/infosysbub/abm/pc/v1/arbeitsmarktberichte
        ?ags={ags_5digit}
    Note: Uses 5-digit AGS (Landkreis level) e.g. "08136" for Ostalbkreis.

Fallback: If REST API requires OAuth or returns errors, log and return empty list.
Data is also available via CSV downloads from the Bundesagentur statistics portal.

License: Datenlizenz Deutschland – Zero – Version 2.0 (DL-DE-Zero-2.0)
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.connectors.base import BaseConnector, Observation
from app.config import ConnectorConfig, Town

logger = logging.getLogger(__name__)

BUNDESAGENTUR_API_BASE = (
    "https://rest.arbeitsagentur.de/infosysbub/abm/pc/v1/arbeitsmarktberichte"
)

AALEN_LON = 10.09
AALEN_LAT = 48.84


class BundesagenturConnector(BaseConnector):
    """Fetches employment statistics from Bundesagentur fuer Arbeit REST API.

    Config keys (from ConnectorConfig.config dict):
        ags: 5-digit Landkreis AGS (default "08136" for Ostalbkreis)
        attribution: Data attribution string
    """

    def __init__(self, config: ConnectorConfig, town: Town) -> None:
        super().__init__(config, town)
        self._feature_id: str | None = None

    async def fetch(self) -> dict:
        """Fetch employment data for the configured district.

        Attempts the REST API; degrades gracefully on auth errors or network failure.

        Returns:
            Dict with employment data, or empty dict on failure.
        """
        ags = self.config.config.get("ags", "08136")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    BUNDESAGENTUR_API_BASE,
                    params={"ags": ags},
                    headers={
                        "Accept": "application/json",
                        "User-Agent": "CityDataPlatform/1.0 (open-source; contact@example.com)",
                    },
                )
                if response.status_code == 200:
                    return {"ags": ags, "data": response.json()}
                elif response.status_code in (401, 403):
                    logger.warning(
                        "BundesagenturConnector: API requires authentication "
                        "(status %d) for AGS %s — skipping",
                        response.status_code,
                        ags,
                    )
                    return {}
                else:
                    logger.warning(
                        "BundesagenturConnector: API returned %d for AGS %s",
                        response.status_code,
                        ags,
                    )
                    return {}
        except Exception as exc:
            logger.warning(
                "BundesagenturConnector: fetch failed for AGS %s: %s", ags, exc
            )
            return {}

    def normalize(self, raw: dict) -> list[Observation]:
        """Transform Bundesagentur API response into Observations.

        Extracts unemployment_rate, total_employed, and open_positions if available.

        Args:
            raw: Dict returned by fetch().

        Returns:
            List of Observation objects with domain="demographics".
        """
        if not raw:
            return []

        ags = raw.get("ags", self.config.config.get("ags", "08136"))
        feature_id = self._feature_id or ""
        data = raw.get("data", {})

        values: dict[str, Any] = {"ags": ags, "data_source": "bundesagentur"}

        def _safe_float(d: Any, *keys: str) -> float | None:
            if not isinstance(d, dict):
                return None
            for k in keys:
                v = d.get(k)
                if v is not None:
                    try:
                        return float(str(v).replace(",", ".").replace(" ", ""))
                    except (TypeError, ValueError):
                        pass
            return None

        if isinstance(data, dict):
            # Direct field mapping
            unemployment_rate = _safe_float(
                data,
                "arbeitslosenquote",
                "unemployment_rate",
                "alq",
                "arbeitslosenquoteInsgesamt",
            )
            total_employed = _safe_float(
                data,
                "sozialversicherungspflichtigBeschaeftigte",
                "total_employed",
                "beschaeftigte",
                "svpBeschaeftigte",
            )
            open_positions = _safe_float(
                data,
                "offeneStellen",
                "open_positions",
                "stellenangebote",
                "gemeldeteStellen",
            )

            # Handle nested "data" key (API may wrap results)
            if unemployment_rate is None and "data" in data:
                nested = data["data"]
                if isinstance(nested, list) and nested:
                    nested = nested[0]
                if isinstance(nested, dict):
                    unemployment_rate = _safe_float(
                        nested,
                        "arbeitslosenquote",
                        "unemployment_rate",
                        "alq",
                    )
                    total_employed = _safe_float(
                        nested,
                        "sozialversicherungspflichtigBeschaeftigte",
                        "beschaeftigte",
                    )
                    open_positions = _safe_float(
                        nested, "offeneStellen", "gemeldeteStellen"
                    )

            if unemployment_rate is not None:
                values["unemployment_rate"] = unemployment_rate
            if total_employed is not None:
                values["total_employed"] = total_employed
            if open_positions is not None:
                values["open_positions"] = open_positions

        elif isinstance(data, list) and data:
            # List of records — use first (latest) record
            record = data[0] if isinstance(data[0], dict) else {}
            unemployment_rate = _safe_float(
                record,
                "arbeitslosenquote",
                "unemployment_rate",
                "alq",
                "arbeitslosenquoteInsgesamt",
            )
            total_employed = _safe_float(
                record,
                "sozialversicherungspflichtigBeschaeftigte",
                "beschaeftigte",
            )
            open_positions = _safe_float(
                record, "offeneStellen", "gemeldeteStellen"
            )
            if unemployment_rate is not None:
                values["unemployment_rate"] = unemployment_rate
            if total_employed is not None:
                values["total_employed"] = total_employed
            if open_positions is not None:
                values["open_positions"] = open_positions

        real_values = {k: v for k, v in values.items() if v is not None}
        employment_keys = {"unemployment_rate", "total_employed", "open_positions"}
        if not employment_keys.intersection(real_values.keys()):
            logger.warning(
                "BundesagenturConnector: no employment data extracted for AGS %s", ags
            )
            return []

        return [
            Observation(
                feature_id=feature_id,
                domain="demographics",
                values=real_values,
                source_id=f"bundesagentur:{ags}",
            )
        ]

    async def run(self) -> None:
        """Full pipeline: upsert feature -> fetch -> normalize -> persist -> update staleness."""
        ags = self.config.config.get("ags", "08136")
        lon = self.config.config.get("lon", AALEN_LON)
        lat = self.config.config.get("lat", AALEN_LAT)

        self._feature_id = await self.upsert_feature(
            source_id=f"bundesagentur:{ags}",
            domain="demographics",
            geometry_wkt=f"POINT({lon} {lat})",
            properties={
                "ags": ags,
                "source": "Bundesagentur fuer Arbeit",
                "attribution": self.config.config.get(
                    "attribution",
                    "Bundesagentur fuer Arbeit, DL-DE-Zero-2.0",
                ),
            },
        )

        raw = await self.fetch()
        observations = self.normalize(raw)
        await self.persist(observations)
        await self._update_staleness()
