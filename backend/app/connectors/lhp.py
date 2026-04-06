"""LhpConnector: fetches water level data from LHP (Hochwasserportal).

Polls the Huttlingen gauge on the Kocher river via the lhpapi library.
Writes readings to the water_readings hypertable with domain='water'.

LHP API (via lhpapi PyPI package):
    HochwasserPortalAPI("BW_13490006")  # Huttlingen/Kocher gauge
    Attributes: level, flow, stage, last_update, name, url, hint

License: Datenlizenz Deutschland
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.config import ConnectorConfig, Town
from app.connectors.base import BaseConnector, Observation
from app.models.lhp import LhpGaugeReading

logger = logging.getLogger(__name__)


class LhpConnector(BaseConnector):
    """Fetches Kocher water level data from the Hochwasserportal (LHP).

    Config keys (from ConnectorConfig.config dict):
        ident: str        -- LHP gauge identifier (e.g. "BW_13490006")
        lat: float        -- Gauge latitude
        lon: float        -- Gauge longitude
        attribution: str  -- Attribution string for data provenance
    """

    def __init__(self, config: ConnectorConfig, town: Town) -> None:
        super().__init__(config, town)
        self._ident: str = self.config.config.get("ident", "BW_13490006")
        self._feature_id: str | None = None

    async def fetch(self) -> LhpGaugeReading:
        """Fetch current gauge reading from LHP via lhpapi.

        Uses asyncio.to_thread since lhpapi is synchronous/blocking.
        The HochwasserPortalAPI constructor auto-calls update().

        Returns:
            LhpGaugeReading validated from API attributes.

        Raises:
            ImportError: If lhpapi is not installed.
            Exception: On network/parsing failure from lhpapi.
        """
        try:
            from lhpapi import HochwasserPortalAPI
        except ImportError:
            raise ImportError(
                "lhpapi package is required for LhpConnector. "
                "Install with: pip install lhpapi"
            )

        def _fetch_sync() -> LhpGaugeReading:
            api = HochwasserPortalAPI(self._ident)
            return LhpGaugeReading(
                name=api.name or self._ident,
                level=api.level,
                flow=api.flow,
                stage=api.stage,
                last_update=api.last_update,
                url=api.url,
                hint=api.hint,
            )

        return await asyncio.to_thread(_fetch_sync)

    def normalize(self, raw: LhpGaugeReading) -> list[Observation]:
        """Transform LHP gauge reading into a water domain Observation.

        Produces a single Observation with domain="water".
        Includes stage and trend in values for downstream KPI use.

        Args:
            raw: LhpGaugeReading from fetch().

        Returns:
            List with one Observation for the gauge reading.
        """
        return [
            Observation(
                feature_id=self._feature_id or "",
                domain="water",
                values={
                    "level_cm": raw.level,
                    "flow_m3s": raw.flow,
                    "stage": raw.stage,
                    "trend": "stable",  # Default; run() computes actual trend
                },
                timestamp=raw.last_update,
                source_id=f"lhp:{self._ident}",
            )
        ]

    def _build_feature_properties(
        self, reading: LhpGaugeReading, trend: str = "stable"
    ) -> dict[str, Any]:
        """Build properties dict for the features table upsert."""
        return {
            "station_name": reading.name,
            "river": "Kocher",
            "stage": reading.stage,
            "trend": trend,
            "level_cm": reading.level,
            "flow_m3s": reading.flow,
            "warning_stage": reading.stage,
            "attribution": self.config.config.get(
                "attribution",
                "Hochwasserportal (LHP), Datenlizenz Deutschland",
            ),
        }

    async def _query_recent_levels(self, feature_id: str) -> list[float]:
        """Query the last 2 water level readings for trend computation.

        Returns:
            List of level_cm values ordered by time ASC (oldest first).
            Empty list if no readings found or on error.
        """
        try:
            from app.db import AsyncSessionLocal
            from sqlalchemy import text

            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    text(
                        "SELECT level_cm FROM water_readings "
                        "WHERE feature_id = :fid AND level_cm IS NOT NULL "
                        "ORDER BY time DESC LIMIT 2"
                    ),
                    {"fid": feature_id},
                )
                rows = result.fetchall()
                # Return in chronological order (oldest first)
                return [row[0] for row in reversed(rows)]
        except Exception:
            return []

    async def _compute_trend(self, feature_id: str) -> str:
        """Compute water level trend from recent readings.

        Compares last 2 readings:
        - Rising if diff > 2cm
        - Falling if diff < -2cm
        - Stable otherwise (or if insufficient data)

        Returns:
            "rising", "falling", or "stable"
        """
        levels = await self._query_recent_levels(feature_id)
        if len(levels) < 2:
            return "stable"
        diff = levels[-1] - levels[-2]
        if diff > 2:
            return "rising"
        elif diff < -2:
            return "falling"
        return "stable"

    async def run(self) -> None:
        """Full pipeline: fetch -> upsert feature -> compute trend -> persist.

        Overrides BaseConnector.run() to:
        1. Fetch raw gauge reading from LHP
        2. Upsert feature at lat/lon with properties
        3. Compute trend from historical data
        4. Normalize and persist to water_readings
        5. Update staleness timestamp
        """
        lat = self.config.config.get("lat", 48.8035)
        lon = self.config.config.get("lon", 10.0972)

        # Step 1: fetch
        raw = await self.fetch()

        # Step 2: upsert feature (initial, trend updated after)
        self._feature_id = await self.upsert_feature(
            source_id=f"lhp:{self._ident}",
            domain="water",
            geometry_wkt=f"POINT({lon} {lat})",
            properties=self._build_feature_properties(raw, trend="stable"),
        )

        # Step 3: compute trend from historical data
        trend = await self._compute_trend(self._feature_id)

        # Step 4: update feature with computed trend
        await self.upsert_feature(
            source_id=f"lhp:{self._ident}",
            domain="water",
            geometry_wkt=f"POINT({lon} {lat})",
            properties=self._build_feature_properties(raw, trend=trend),
        )

        # Step 5: normalize with actual trend and persist
        observations = self.normalize(raw)
        # Update the trend in the observation values
        if observations:
            observations[0].values["trend"] = trend
        await self.persist(observations)

        # Step 6: update staleness
        await self._update_staleness()
