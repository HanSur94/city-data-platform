"""OverpassRoadworksConnector: fetches highway=construction features from OpenStreetMap Overpass API.

Implements INFR-01: retrieves active roadworks (highway=construction) from the
Overpass API and stores them as 'infrastructure' domain features with category=roadwork.

License: OpenStreetMap data © OpenStreetMap contributors, ODbL 1.0
Attribution: https://www.openstreetmap.org/copyright
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.connectors.base import BaseConnector, Observation
from app.config import ConnectorConfig, Town

logger = logging.getLogger(__name__)

# Overpass API endpoint
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Overpass query template for highway=construction features.
# {bbox} is replaced with lat_min,lon_min,lat_max,lon_max.
ROADWORKS_QUERY_TEMPLATE = """[out:json][timeout:25];
(
  node["highway"="construction"]({bbox});
  way["highway"="construction"]({bbox});
);
out center;
"""


class OverpassRoadworksConnector(BaseConnector):
    """Fetches highway=construction (roadworks) from OpenStreetMap Overpass API.

    Overrides run() — uses upsert_feature() directly rather than the
    fetch→normalize→persist pipeline (features-only connector pattern).

    Writes features to the 'infrastructure' domain with category='roadwork'.
    """

    def __init__(self, config: ConnectorConfig, town: Town) -> None:
        super().__init__(config, town)

    async def fetch(self) -> dict[str, Any]:
        """Fetch highway=construction elements from Overpass API.

        Returns:
            Parsed JSON response dict from Overpass API.

        Raises:
            httpx.HTTPError: On network failure.
            ValueError: On empty or malformed response.
        """
        bbox = self.town.bbox
        bbox_str = f"{bbox.lat_min},{bbox.lon_min},{bbox.lat_max},{bbox.lon_max}"
        query = ROADWORKS_QUERY_TEMPLATE.format(bbox=bbox_str)

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(OVERPASS_URL, data={"data": query})
            response.raise_for_status()
            data = response.json()

        if "elements" not in data:
            raise ValueError(f"Unexpected Overpass response structure: {list(data.keys())}")

        logger.info(
            "OverpassRoadworksConnector: fetched %d elements for %s",
            len(data["elements"]),
            self.town.id,
        )
        return data

    def normalize(self, raw: Any) -> list[Observation]:
        """Returns empty list — roadworks connector is features-only.

        Required by BaseConnector ABC. Data is upserted directly via
        upsert_feature() in run().
        """
        return []

    def _extract_mappings(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract roadwork mappings from Overpass API response.

        For each highway=construction element, extract coordinates and metadata.
        Skips elements with missing coordinates.

        Args:
            raw: Parsed Overpass API JSON response.

        Returns:
            List of dicts with: source_id, lat, lon, domain, category, tags.
        """
        mappings: list[dict[str, Any]] = []
        for element in raw.get("elements", []):
            tags = element.get("tags", {})

            # Extract coordinates: nodes have lat/lon at top level,
            # ways have center.lat/center.lon
            lat = element.get("lat") or (element.get("center") or {}).get("lat")
            lon = element.get("lon") or (element.get("center") or {}).get("lon")
            if lat is None or lon is None:
                logger.debug(
                    "Skipping roadwork element %s/%s: missing coordinates",
                    element.get("type"),
                    element.get("id"),
                )
                continue

            source_id = f"osm:{element['type']}:{element['id']}"

            mappings.append({
                "source_id": source_id,
                "lat": lat,
                "lon": lon,
                "domain": "infrastructure",
                "category": "roadwork",
                "tags": tags,
            })
        return mappings

    async def run(self) -> None:
        """Full pipeline: fetch → upsert features → update staleness.

        Overrides BaseConnector.run() to use upsert_feature() directly.
        Handles empty results gracefully (no roadworks in the area).
        """
        raw = await self.fetch()
        mappings = self._extract_mappings(raw)

        if not mappings:
            logger.info(
                "OverpassRoadworksConnector: no roadworks found for %s",
                self.town.id,
            )
            await self._update_staleness()
            return

        upserted = 0
        for m in mappings:
            tags = m["tags"]
            properties: dict[str, Any] = {
                "category": "roadwork",
                "domain": "infrastructure",
                "name": tags.get("name") or "Baustelle",
                "highway": tags.get("highway"),
                "construction": tags.get("construction"),
                "note": tags.get("note") or tags.get("description"),
                "address": " ".join(filter(None, [
                    tags.get("addr:street"),
                    tags.get("addr:housenumber"),
                ])) or None,
            }
            # Remove None values to keep properties clean
            properties = {k: v for k, v in properties.items() if v is not None}

            geometry_wkt = f"POINT({m['lon']} {m['lat']})"
            try:
                await self.upsert_feature(
                    source_id=m["source_id"],
                    domain="infrastructure",
                    geometry_wkt=geometry_wkt,
                    properties=properties,
                )
                upserted += 1
            except Exception as exc:
                logger.warning(
                    "Failed to upsert roadwork feature %s: %s",
                    m["source_id"],
                    exc,
                )

        logger.info(
            "OverpassRoadworksConnector: upserted %d/%d features for %s",
            upserted,
            len(mappings),
            self.town.id,
        )
        await self._update_staleness()
