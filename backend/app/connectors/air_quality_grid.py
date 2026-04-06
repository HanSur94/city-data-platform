"""AirQualityGridConnector: IDW interpolation of air quality sensor readings.

Computation connector -- does NOT use the standard fetch/normalize/persist
pipeline. Instead, run() queries latest sensor readings from the database,
generates a grid covering the town bbox, computes IDW interpolation for
each pollutant at each grid cell, and upserts grid cell features.

Grid cells are stored as features with feature_type="air_grid" to
distinguish them from sensor point features.
"""
from __future__ import annotations

import logging
import math
from typing import Any

from app.connectors.base import BaseConnector, Observation
from app.config import TownBbox
from app.models.air_quality_grid import GridCell, SensorReading

logger = logging.getLogger(__name__)


def _haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Haversine distance in metres between two WGS84 points."""
    R = 6_371_000.0
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def idw_interpolate(
    sensors: list[SensorReading],
    lon: float,
    lat: float,
    pollutant: str,
    power: float = 2.0,
) -> float | None:
    """Inverse Distance Weighting interpolation for a single pollutant.

    Args:
        sensors: List of sensor readings with location and pollutant values.
        lon: Query point longitude.
        lat: Query point latitude.
        pollutant: Pollutant field name (pm25, pm10, no2, o3).
        power: Distance weighting exponent (default 2.0).

    Returns:
        Interpolated value, or None if no sensors have data for that pollutant.
    """
    weight_sum = 0.0
    value_sum = 0.0

    for sensor in sensors:
        value = getattr(sensor, pollutant, None)
        if value is None:
            continue

        dist = _haversine(lon, lat, sensor.lon, sensor.lat)

        # If query point coincides with sensor, return exact value
        if dist < 1.0:  # less than 1 metre
            return float(value)

        w = 1.0 / (dist ** power)
        weight_sum += w
        value_sum += w * value

    if weight_sum == 0.0:
        return None

    return value_sum / weight_sum


def generate_grid(
    bbox: TownBbox,
    step_deg: float = 0.005,
) -> list[tuple[float, float, int, int]]:
    """Generate grid points covering the bounding box.

    Args:
        bbox: Town bounding box.
        step_deg: Grid step size in degrees (default ~500m).

    Returns:
        List of (lon, lat, row, col) tuples.
    """
    cells: list[tuple[float, float, int, int]] = []
    row = 0
    lat = bbox.lat_min
    while lat <= bbox.lat_max:
        col = 0
        lon = bbox.lon_min
        while lon <= bbox.lon_max:
            cells.append((lon, lat, row, col))
            col += 1
            lon += step_deg
        row += 1
        lat += step_deg
    return cells


class AirQualityGridConnector(BaseConnector):
    """Computation connector: IDW interpolation of air quality on a grid.

    Does NOT use the standard fetch/normalize/persist pipeline.
    run() orchestrates the full computation:
    1. Query latest sensor readings from DB
    2. Generate grid covering town bbox
    3. Compute IDW interpolation per grid cell per pollutant
    4. Upsert grid cell features
    5. Update staleness
    """

    async def fetch(self) -> Any:
        """Not used -- run() handles everything."""
        return None

    def normalize(self, raw: Any) -> list[Observation]:
        """Not used -- run() handles everything."""
        return []

    async def run(self) -> None:
        """Full IDW grid computation pipeline."""
        # 1. Query latest reading per sensor
        sensors = await self._fetch_sensor_readings()
        if not sensors:
            logger.warning("AirQualityGridConnector: no sensor readings found, skipping.")
            await self._update_staleness()
            return

        logger.info("AirQualityGridConnector: %d sensors with readings.", len(sensors))

        # 2. Generate grid
        step = self.config.config.get("grid_step_deg", 0.005)
        grid_cells = generate_grid(self.town.bbox, step_deg=step)
        logger.info("AirQualityGridConnector: %d grid cells to compute.", len(grid_cells))

        # 3+4. Compute IDW and upsert each grid cell
        pollutants = ("pm25", "pm10", "no2", "o3")
        upserted = 0

        for lon, lat, row, col in grid_cells:
            props: dict[str, Any] = {"feature_type": "air_grid"}
            for p in pollutants:
                val = idw_interpolate(sensors, lon, lat, p)
                props[p] = val

            source_id = f"air-grid-{row}-{col}"
            geometry_wkt = f"POINT({lon} {lat})"

            await self.upsert_feature(
                source_id=source_id,
                domain="air_quality",
                geometry_wkt=geometry_wkt,
                properties=props,
            )
            upserted += 1

        # 5. Update staleness
        await self._update_staleness()
        logger.info(
            "AirQualityGridConnector: upserted %d grid cells from %d sensors.",
            upserted,
            len(sensors),
        )

    async def _fetch_sensor_readings(self) -> list[SensorReading]:
        """Query latest reading per air quality sensor from the database."""
        from app.db import AsyncSessionLocal
        from sqlalchemy import text

        sensors: list[SensorReading] = []
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    text("""
                        SELECT
                            f.id::text AS feature_id,
                            ST_X(f.geometry) AS lon,
                            ST_Y(f.geometry) AS lat,
                            r.pm25, r.pm10, r.no2, r.o3
                        FROM features f
                        LEFT JOIN LATERAL (
                            SELECT pm25, pm10, no2, o3
                            FROM air_quality_readings
                            WHERE feature_id = f.id
                            ORDER BY time DESC
                            LIMIT 1
                        ) r ON true
                        WHERE f.town_id = :town_id
                          AND f.domain = 'air_quality'
                          AND f.properties->>'feature_type' IS DISTINCT FROM 'air_grid'
                    """),
                    {"town_id": self.town.id},
                )
                for row in result.mappings():
                    sensors.append(SensorReading(
                        feature_id=row["feature_id"],
                        lon=float(row["lon"]),
                        lat=float(row["lat"]),
                        pm25=row.get("pm25"),
                        pm10=row.get("pm10"),
                        no2=row.get("no2"),
                        o3=row.get("o3"),
                    ))
        except Exception as exc:
            logger.error("Failed to fetch sensor readings: %s", exc)

        return sensors
