"""CyclingInfraConnector: fetches cycling infrastructure from OpenStreetMap Overpass API.

Queries OSM for roads and cycleways within the town bbox and classifies each
way's cycling infrastructure into one of 5 types: separated, lane, advisory,
shared, or none.

License: OpenStreetMap data (c) OpenStreetMap contributors, ODbL 1.0
Attribution: https://www.openstreetmap.org/copyright
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.connectors.base import BaseConnector, Observation
from app.config import ConnectorConfig, Town

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Overpass query: roads + cycleways with bicycle not explicitly banned
CYCLING_QUERY_TEMPLATE = """[out:json][timeout:60];
way["highway"~"primary|secondary|tertiary|residential|cycleway"]["bicycle"!~"no"]({bbox});
out geom;
"""

# Highway types that get infra_type="none" when no cycling tags present
MAJOR_ROADS = frozenset({"primary", "secondary", "tertiary"})


def classify_cycling_infra(tags: dict[str, str]) -> str | None:
    """Classify cycling infrastructure type from OSM tags.

    Returns:
        infra_type string, or None if the way should be skipped
        (residential with no cycling tags).
    """
    highway = tags.get("highway", "")

    # Dedicated cycleway
    if highway == "cycleway":
        return "separated"

    cycleway = tags.get("cycleway", "")
    cycleway_left = tags.get("cycleway:left", "")
    cycleway_right = tags.get("cycleway:right", "")
    bicycle = tags.get("bicycle", "")

    # Lane
    if cycleway == "lane" or cycleway_left == "lane" or cycleway_right == "lane":
        return "lane"

    # Advisory
    if cycleway == "advisory" or cycleway_left == "advisory" or cycleway_right == "advisory":
        return "advisory"

    # Shared
    if cycleway == "shared_lane" or bicycle == "designated":
        return "shared"

    # Major road with no cycling infrastructure
    if highway in MAJOR_ROADS:
        return "none"

    # Residential with no cycling tags -- skip
    return None


class CyclingInfraConnector(BaseConnector):
    """Fetches cycling infrastructure from OpenStreetMap Overpass API.

    Classifies each way into one of 5 infra_type categories:
    - separated: dedicated cycleway (highway=cycleway)
    - lane: marked cycle lane
    - advisory: advisory cycle lane (Schutzstreifen)
    - shared: shared lane or bicycle=designated
    - none: major road with no cycling infrastructure

    Residential roads without cycling tags are skipped.

    Overrides run() to upsert features with LINESTRING geometry.
    """

    def __init__(self, config: ConnectorConfig, town: Town) -> None:
        super().__init__(config, town)

    async def fetch(self) -> dict[str, Any]:
        """Fetch cycling-relevant ways from Overpass API.

        Returns:
            Parsed JSON response dict from Overpass API.
        """
        bbox = self.town.bbox
        bbox_str = f"{bbox.lat_min},{bbox.lon_min},{bbox.lat_max},{bbox.lon_max}"
        query = CYCLING_QUERY_TEMPLATE.format(bbox=bbox_str)

        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(OVERPASS_URL, data={"data": query})
            response.raise_for_status()
            data = response.json()

        if "elements" not in data:
            raise ValueError(f"Unexpected Overpass response: {list(data.keys())}")

        logger.info(
            "CyclingInfraConnector: fetched %d elements for %s",
            len(data["elements"]),
            self.town.id,
        )
        return data

    def normalize(self, raw: Any) -> list[Observation]:
        """Transform Overpass response into cycling Observations.

        Args:
            raw: Overpass API JSON response with 'elements' key.

        Returns:
            List of Observations with domain='infrastructure' and infra_type.
        """
        elements = raw.get("elements", []) if isinstance(raw, dict) else []
        if not elements:
            return []

        observations: list[Observation] = []
        for element in elements:
            if element.get("type") != "way":
                continue

            tags = element.get("tags", {})
            infra_type = classify_cycling_infra(tags)

            # Skip residential roads with no cycling tags
            if infra_type is None:
                continue

            way_id = element.get("id", 0)
            source_id = f"cycling:way:{way_id}"
            road_name = tags.get("name")

            values: dict[str, Any] = {
                "infra_type": infra_type,
                "feature_type": "cycling",
                "highway": tags.get("highway", ""),
            }
            if road_name:
                values["road_name"] = road_name

            observations.append(
                Observation(
                    feature_id="",  # Set in run() after upsert
                    domain="infrastructure",
                    values=values,
                    source_id=source_id,
                )
            )

        return observations

    def _geometry_from_element(self, element: dict[str, Any]) -> str | None:
        """Build WKT LINESTRING from Overpass geometry array.

        Returns None if geometry has fewer than 2 points.
        """
        geom = element.get("geometry", [])
        if len(geom) < 2:
            return None

        coords = ", ".join(f"{p['lon']} {p['lat']}" for p in geom)
        return f"LINESTRING({coords})"

    async def run(self) -> None:
        """Full pipeline: fetch -> normalize -> upsert features -> update staleness."""
        raw = await self.fetch()
        elements = raw.get("elements", [])
        observations = self.normalize(raw)

        # Build element lookup for geometry
        element_by_id: dict[int, dict] = {}
        for el in elements:
            if el.get("type") == "way":
                element_by_id[el.get("id", 0)] = el

        upserted = 0
        valid_obs: list[Observation] = []
        for obs in observations:
            # Extract way ID from source_id
            way_id = int(obs.source_id.split(":")[-1]) if obs.source_id else 0
            element = element_by_id.get(way_id)
            if not element:
                continue

            geometry_wkt = self._geometry_from_element(element)
            if not geometry_wkt:
                continue

            try:
                feature_id = await self.upsert_feature(
                    source_id=obs.source_id or f"cycling:way:{way_id}",
                    domain="infrastructure",
                    geometry_wkt=geometry_wkt,
                    properties=obs.values,
                )
                obs.feature_id = feature_id
                valid_obs.append(obs)
                upserted += 1
            except Exception as exc:
                logger.warning(
                    "Failed to upsert cycling feature %s: %s",
                    obs.source_id,
                    exc,
                )

        # Cycling is features-only — no hypertable writes needed
        # (infrastructure domain has no readings table)
        await self._update_staleness()
        logger.info(
            "CyclingInfraConnector: upserted %d/%d ways for %s",
            upserted,
            len(observations),
            self.town.id,
        )
