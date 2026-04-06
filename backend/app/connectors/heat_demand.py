"""HeatDemandConnector: simulated building-level heat demand data.

Generates simulated KEA-BW Waermeatlas data for buildings within the town bbox.
Since the actual KEA-BW GeoPackage download is not publicly available, this
connector creates deterministic simulated building-level heat demand values.

Each building gets a heat_demand_kwh_m2_y value and a 6-tier heat_class color
classification based on energy efficiency thresholds from the KEA-BW methodology.

License: Datenlizenz Deutschland - Namensnennung - Version 2.0
Attribution: KEA-BW Waermeatlas (simulated)
"""
from __future__ import annotations

import hashlib
import logging
import random
from typing import Any

from app.connectors.base import BaseConnector, Observation
from app.config import ConnectorConfig, Town

logger = logging.getLogger(__name__)

# Heat class thresholds (kWh/m2/y) per KEA-BW Waermeatlas methodology
HEAT_CLASS_THRESHOLDS: list[tuple[float, str]] = [
    (50, "blue"),        # < 50: excellent efficiency
    (100, "light_blue"), # 50-99: good efficiency
    (150, "green"),      # 100-149: moderate
    (200, "yellow"),     # 150-199: below average
    (250, "orange"),     # 200-249: poor
]
HEAT_CLASS_DEFAULT = "red"  # >= 250: very poor efficiency

NUM_SIMULATED_BUILDINGS = 50


def classify_heat_demand(kwh_m2_y: float) -> str:
    """Return heat_class string for a given kWh/m2/y value.

    Thresholds: <50 blue, 50-99 light_blue, 100-149 green,
    150-199 yellow, 200-249 orange, >=250 red.
    """
    for threshold, heat_class in HEAT_CLASS_THRESHOLDS:
        if kwh_m2_y < threshold:
            return heat_class
    return HEAT_CLASS_DEFAULT


class HeatDemandConnector(BaseConnector):
    """Simulated building-level heat demand connector.

    Generates ~50 deterministic building points within the town bbox with
    random heat_demand_kwh_m2_y values (30-350 range). Uses town ID as
    seed for reproducibility.

    Overrides run() to upsert features then persist observations.
    """

    def __init__(self, config: ConnectorConfig, town: Town) -> None:
        super().__init__(config, town)

    async def fetch(self) -> list[dict[str, Any]]:
        """Generate simulated building data within town bbox.

        Returns:
            List of dicts with lon, lat, area_m2, heat_demand_kwh_m2_y.
        """
        bbox = self.town.bbox
        # Deterministic seed from town ID
        seed = int(hashlib.md5(self.town.id.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)

        buildings: list[dict[str, Any]] = []
        for i in range(NUM_SIMULATED_BUILDINGS):
            lon = rng.uniform(bbox.lon_min, bbox.lon_max)
            lat = rng.uniform(bbox.lat_min, bbox.lat_max)
            area_m2 = rng.uniform(80, 500)
            heat_demand = rng.uniform(30, 350)
            buildings.append({
                "lon": round(lon, 6),
                "lat": round(lat, 6),
                "area_m2": round(area_m2, 1),
                "heat_demand_kwh_m2_y": round(heat_demand, 1),
            })

        logger.info(
            "HeatDemandConnector: generated %d simulated buildings for %s",
            len(buildings),
            self.town.id,
        )
        return buildings

    def normalize(self, raw: Any) -> list[Observation]:
        """Transform simulated building data into Observations.

        Args:
            raw: List of building dicts from fetch().

        Returns:
            List of Observations with domain='energy' and heat_class.
        """
        if not raw:
            return []

        observations: list[Observation] = []
        for i, building in enumerate(raw):
            kwh = building["heat_demand_kwh_m2_y"]
            heat_class = classify_heat_demand(kwh)

            source_id = f"heat-demand:building:{i}"
            observations.append(
                Observation(
                    feature_id="",  # Will be set in run() after upsert
                    domain="energy",
                    values={
                        "heat_demand_kwh_m2_y": kwh,
                        "heat_class": heat_class,
                        "feature_type": "heat_demand",
                        "source": "KEA-BW Waermeatlas (simulated)",
                        "area_m2": building["area_m2"],
                    },
                    source_id=source_id,
                )
            )
        return observations

    async def run(self) -> None:
        """Full pipeline: fetch -> normalize -> upsert features -> persist -> staleness."""
        raw = await self.fetch()
        observations = self.normalize(raw)

        for i, (building, obs) in enumerate(zip(raw, observations)):
            geometry_wkt = f"POINT({building['lon']} {building['lat']})"
            feature_id = await self.upsert_feature(
                source_id=obs.source_id or f"heat-demand:building:{i}",
                domain="energy",
                geometry_wkt=geometry_wkt,
                properties={
                    "heat_demand_kwh_m2_y": obs.values["heat_demand_kwh_m2_y"],
                    "heat_class": obs.values["heat_class"],
                    "feature_type": "heat_demand",
                    "source": "KEA-BW Waermeatlas (simulated)",
                    "area_m2": obs.values["area_m2"],
                },
            )
            obs.feature_id = feature_id

        await self.persist(observations)
        await self._update_staleness()
        logger.info(
            "HeatDemandConnector: upserted %d buildings for %s",
            len(observations),
            self.town.id,
        )
