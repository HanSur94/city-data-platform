"""WegweiserKommuneConnector: fetches municipal indicator data from Wegweiser Kommune.

Implements DEMO-03: retrieves key social/demographic indicators for a municipality
from the Bertelsmann Stiftung Wegweiser Kommune API (CC0 license).

API endpoint:
    GET https://www.wegweiser-kommune.de/statistik/api/v1/gemeinde/{ags}/indikatoren
    Accept: application/json

License: CC0 — no attribution required, but included for completeness.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.connectors.base import BaseConnector, Observation
from app.config import ConnectorConfig, Town

logger = logging.getLogger(__name__)

WEGWEISER_BASE = "https://www.wegweiser-kommune.de/statistik/api/v1/gemeinde"

# Aalen centroid coordinates
AALEN_LON = 10.09
AALEN_LAT = 48.84


class WegweiserKommuneConnector(BaseConnector):
    """Fetches municipal indicators from Wegweiser Kommune (Bertelsmann Stiftung).

    Config keys (from ConnectorConfig.config dict):
        ags: Amtlicher Gemeindeschluessel (default "08136088" for Aalen)
        attribution: Data attribution string
    """

    def __init__(self, config: ConnectorConfig, town: Town) -> None:
        super().__init__(config, town)
        self._feature_id: str | None = None

    async def fetch(self) -> dict:
        """Fetch indicator data for the configured municipality.

        Returns:
            Raw API response dict or empty dict on error.
        """
        ags = self.config.config.get("ags", "08136088")
        url = f"{WEGWEISER_BASE}/{ags}/indikatoren"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers={"Accept": "application/json"})
                if response.status_code >= 400:
                    logger.warning(
                        "WegweiserKommuneConnector: API returned %d for AGS %s",
                        response.status_code,
                        ags,
                    )
                    return {}
                return response.json()
        except Exception as exc:
            logger.warning(
                "WegweiserKommuneConnector: fetch failed for AGS %s: %s", ags, exc
            )
            return {}

    def normalize(self, raw: dict) -> list[Observation]:
        """Transform Wegweiser Kommune API response into Observations.

        Extracts key indicators: population, age_under_18_pct, age_over_65_pct,
        unemployment_rate, migration_saldo.

        Args:
            raw: Dict returned by fetch().

        Returns:
            List of Observation objects with domain="demographics".
            Empty list if raw data is missing or malformed.
        """
        if not raw:
            return []

        ags = self.config.config.get("ags", "08136088")
        feature_id = self._feature_id or ""

        # Wegweiser API returns either a list of indicator dicts or a dict with
        # an "indikatoren" key. Handle both shapes gracefully.
        indicators: list[dict] = []
        if isinstance(raw, list):
            indicators = raw
        elif isinstance(raw, dict):
            indicators = raw.get("indikatoren", raw.get("data", []))
            if not isinstance(indicators, list):
                # Flat dict of indicator_key -> value
                indicators = [{"key": k, "value": v} for k, v in raw.items()]

        # Build a key -> latest value mapping
        indicator_map: dict[str, Any] = {}
        for item in indicators:
            if not isinstance(item, dict):
                continue
            key = item.get("indikator") or item.get("key") or item.get("name", "")
            value = item.get("wert") or item.get("value")
            if key and value is not None:
                indicator_map[str(key).lower()] = value

        # Extract known indicators (flexible key matching)
        def _get(*keys: str) -> float | None:
            for k in keys:
                v = indicator_map.get(k)
                if v is not None:
                    try:
                        return float(v)
                    except (TypeError, ValueError):
                        pass
            return None

        values: dict[str, Any] = {
            "population": _get("bevoelkerung", "einwohner", "population"),
            "age_under_18_pct": _get(
                "anteil_unter_18", "bevoelkerung_unter_18_pct", "age_under_18_pct"
            ),
            "age_over_65_pct": _get(
                "anteil_ab_65", "bevoelkerung_65_pct", "age_over_65_pct"
            ),
            "unemployment_rate": _get(
                "arbeitslosenquote", "unemployment_rate", "arbeitslos_quote"
            ),
            "migration_saldo": _get("wanderungssaldo", "migration_saldo"),
            "ags": ags,
        }

        # Filter out None values for cleanliness, but keep ags
        values = {k: v for k, v in values.items() if v is not None}
        if len(values) <= 1:
            # Only ags key — no real data
            logger.warning(
                "WegweiserKommuneConnector: no usable indicators found for AGS %s", ags
            )
            return []

        return [
            Observation(
                feature_id=feature_id,
                domain="demographics",
                values=values,
                source_id=f"wegweiser:{ags}",
            )
        ]

    async def run(self) -> None:
        """Full pipeline: upsert feature -> fetch -> normalize -> persist -> update staleness."""
        ags = self.config.config.get("ags", "08136088")
        lon = self.config.config.get("lon", AALEN_LON)
        lat = self.config.config.get("lat", AALEN_LAT)

        self._feature_id = await self.upsert_feature(
            source_id=f"wegweiser:{ags}",
            domain="demographics",
            geometry_wkt=f"POINT({lon} {lat})",
            properties={
                "ags": ags,
                "source": "Wegweiser Kommune",
                "attribution": self.config.config.get(
                    "attribution", "Wegweiser Kommune (Bertelsmann Stiftung), CC0"
                ),
            },
        )

        raw = await self.fetch()
        observations = self.normalize(raw)
        await self.persist(observations)
        await self._update_staleness()
