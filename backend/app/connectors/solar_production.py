"""SolarProductionConnector: computes live solar output per building.

Computation connector -- multiplies MaStR installed capacity (kW) by a
Bright Sky irradiance factor to estimate current solar production.

Writes to energy_readings hypertable and updates feature properties with
current_output_kw and irradiance_factor for frontend display.

Data sources:
- MaStR solar installations (already in features table from MastrConnector)
- Bright Sky current_weather API (cloud_cover, solar irradiance)

License: Datenlizenz Deutschland / CC BY 4.0
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.connectors.base import BaseConnector, Observation
from app.config import ConnectorConfig, Town

logger = logging.getLogger(__name__)

# Clear-sky summer reference for central Europe: ~500 W/m2 = 30 J/cm2 per 10 min
_CLEAR_SKY_SOLAR_REF = 30.0


def compute_irradiance_factor(
    cloud_cover: float | None,
    solar_j_cm2: float | None,
) -> float:
    """Compute irradiance factor (0.0-1.0) from weather data.

    Priority:
    1. If solar_j_cm2 is available and > 0: factor = min(solar/30, 1.0)
    2. Else if cloud_cover is available: factor = max(1.0 - cloud_cover/100 * 0.9, 0.1)
    3. Else: return 0.5 (fallback)

    Args:
        cloud_cover: Cloud cover percentage (0-100) from Bright Sky.
        solar_j_cm2: Global irradiance in J/cm2 per 10 min from Bright Sky.

    Returns:
        Irradiance factor between 0.0 and 1.0.
    """
    if solar_j_cm2 is not None and solar_j_cm2 > 0:
        return min(solar_j_cm2 / _CLEAR_SKY_SOLAR_REF, 1.0)

    if cloud_cover is not None:
        return max(1.0 - cloud_cover / 100.0 * 0.9, 0.1)

    return 0.5


def compute_solar_output(capacity_kw: float, irradiance_factor: float) -> float:
    """Compute current solar output in kW.

    Args:
        capacity_kw: Installed capacity in kW (from MaStR).
        irradiance_factor: Irradiance factor (0.0-1.0).

    Returns:
        Current output in kW.
    """
    return capacity_kw * irradiance_factor


class SolarProductionConnector(BaseConnector):
    """Computation connector: estimates live solar production per installation.

    Overrides run() directly (not fetch/normalize) because this connector
    reads from the database (MaStR installations) and an external API
    (Bright Sky weather) to compute derived values.

    Config keys (from ConnectorConfig.config dict):
        lat (float): Latitude for weather query. Default 48.84 (Aalen).
        lon (float): Longitude for weather query. Default 10.09 (Aalen).
    """

    async def fetch(self) -> Any:
        """Not used -- run() handles everything."""
        return None

    def normalize(self, raw: Any) -> list[Observation]:
        """Not used -- run() handles everything."""
        return []

    async def run(self) -> None:
        """Full solar production computation pipeline.

        1. Fetch current weather from Bright Sky for irradiance data
        2. Compute irradiance factor
        3. Query all solar installations from features table
        4. For each installation, compute current output
        5. Write energy_readings + update feature properties
        6. Update staleness
        """
        lat = self.config.config.get("lat", 48.84)
        lon = self.config.config.get("lon", 10.09)

        # 1. Fetch weather data from Bright Sky
        cloud_cover = None
        solar_j_cm2 = None
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(
                    "https://api.brightsky.dev/current_weather",
                    params={"lat": lat, "lon": lon},
                )
                r.raise_for_status()
                weather_data = r.json()
                weather = weather_data.get("weather", {})
                cloud_cover = weather.get("cloud_cover")
                solar_j_cm2 = weather.get("solar")
        except Exception as exc:
            logger.warning(
                "SolarProductionConnector: failed to fetch weather: %s", exc
            )

        # 2. Compute irradiance factor
        factor = compute_irradiance_factor(cloud_cover, solar_j_cm2)
        logger.info(
            "SolarProductionConnector: irradiance_factor=%.3f "
            "(cloud_cover=%s, solar_j_cm2=%s)",
            factor, cloud_cover, solar_j_cm2,
        )

        # 3. Query solar installations from features table
        installations = await self._fetch_solar_installations()
        if not installations:
            logger.warning(
                "SolarProductionConnector: no solar installations found, skipping."
            )
            await self._update_staleness()
            return

        logger.info(
            "SolarProductionConnector: computing output for %d installations",
            len(installations),
        )

        # 4+5. Compute output and create observations
        now = datetime.now(timezone.utc)
        observations: list[Observation] = []

        for inst in installations:
            current_output_kw = compute_solar_output(inst["capacity_kw"], factor)

            observations.append(
                Observation(
                    feature_id=inst["feature_id"],
                    domain="energy",
                    values={
                        "value_kw": current_output_kw,
                        "source_type": "solar_production",
                    },
                    timestamp=now,
                )
            )

            # Update feature properties for frontend display
            await self._update_feature_properties(
                inst["feature_id"], current_output_kw, factor
            )

        # Persist energy readings
        await self.persist(observations)

        # 6. Update staleness
        await self._update_staleness()
        logger.info(
            "SolarProductionConnector: wrote %d energy readings, factor=%.3f",
            len(observations), factor,
        )

    async def _fetch_solar_installations(self) -> list[dict]:
        """Query all solar installations from features table.

        Returns:
            List of dicts with feature_id, capacity_kw, lon, lat.
        """
        from app.db import AsyncSessionLocal
        from sqlalchemy import text

        installations: list[dict] = []
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    text("""
                        SELECT
                            id::text AS feature_id,
                            COALESCE((properties->>'capacity_kw')::float, 0) AS capacity_kw,
                            ST_X(geometry) AS lon,
                            ST_Y(geometry) AS lat
                        FROM features
                        WHERE town_id = :town_id
                          AND domain = 'energy'
                          AND (properties->>'installation_type' LIKE 'solar_%')
                    """),
                    {"town_id": self.town.id},
                )
                for row in result.mappings():
                    installations.append({
                        "feature_id": row["feature_id"],
                        "capacity_kw": float(row["capacity_kw"]),
                        "lon": float(row["lon"]),
                        "lat": float(row["lat"]),
                    })
        except Exception as exc:
            logger.error(
                "SolarProductionConnector: failed to query installations: %s", exc
            )

        return installations

    async def _update_feature_properties(
        self,
        feature_id: str,
        current_output_kw: float,
        irradiance_factor: float,
    ) -> None:
        """Update feature properties with current output for frontend display."""
        from app.db import AsyncSessionLocal
        from sqlalchemy import text

        try:
            async with AsyncSessionLocal() as session:
                await session.execute(
                    text("""
                        UPDATE features
                        SET properties = properties || CAST(:patch AS jsonb)
                        WHERE id = CAST(:feature_id AS uuid)
                    """),
                    {
                        "feature_id": feature_id,
                        "patch": json.dumps({
                            "current_output_kw": round(current_output_kw, 3),
                            "irradiance_factor": round(irradiance_factor, 3),
                        }),
                    },
                )
                await session.commit()
        except Exception as exc:
            logger.warning(
                "SolarProductionConnector: failed to update feature %s: %s",
                feature_id, exc,
            )
