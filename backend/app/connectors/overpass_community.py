"""OverpassCommunityConnector: fetches community POIs from OpenStreetMap Overpass API.

Implements COMM-01 through COMM-04: retrieves schools, healthcare facilities,
parks/leisure areas, and waste/recycling points from the Overpass API and stores
them as 'community' domain features.

A single consolidated Overpass query retrieves all community POI types at once
(schools, healthcare, parks, waste), minimizing API requests.

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

# Consolidated Overpass query template for all community POI types.
# {bbox} is replaced with lat_min,lon_min,lat_max,lon_max.
COMMUNITY_QUERY_TEMPLATE = """[out:json][timeout:60];
(
  node["amenity"~"school|kindergarten|pharmacy|hospital|doctors|clinic|dentist|recycling|waste_disposal"]({bbox});
  way["amenity"~"school|kindergarten|pharmacy|hospital|doctors|clinic|dentist|recycling|waste_disposal"]({bbox});
  node["leisure"~"park|playground|sports_centre|pitch"]({bbox});
  way["leisure"~"park|playground|sports_centre|pitch"]({bbox});
);
out center;
"""

# Category mapping: OSM tag value -> community category
CATEGORY_MAP: dict[str, str] = {
    # Education
    "school": "school",
    "kindergarten": "school",
    # Healthcare
    "pharmacy": "healthcare",
    "hospital": "healthcare",
    "doctors": "healthcare",
    "clinic": "healthcare",
    "dentist": "healthcare",
    # Parks and leisure
    "park": "park",
    "playground": "park",
    "sports_centre": "park",
    "pitch": "park",
    # Waste
    "recycling": "waste",
    "waste_disposal": "waste",
}


class OverpassCommunityConnector(BaseConnector):
    """Fetches community POIs from OpenStreetMap Overpass API.

    Overrides run() — uses upsert_feature() directly rather than the
    fetch→normalize→persist pipeline (features-only connector pattern).

    Fetches a consolidated query covering all 4 community categories:
    school, healthcare, park, waste.
    """

    def __init__(self, config: ConnectorConfig, town: Town) -> None:
        super().__init__(config, town)

    async def fetch(self) -> dict[str, Any]:
        """Fetch all community POIs from Overpass API in one request.

        Returns:
            Parsed JSON response dict from Overpass API.

        Raises:
            httpx.HTTPError: On network failure.
            ValueError: On empty or malformed response.
        """
        bbox = self.town.bbox
        bbox_str = f"{bbox.lat_min},{bbox.lon_min},{bbox.lat_max},{bbox.lon_max}"
        query = COMMUNITY_QUERY_TEMPLATE.format(bbox=bbox_str)

        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(OVERPASS_URL, data={"data": query})
            response.raise_for_status()
            data = response.json()

        if "elements" not in data:
            raise ValueError(f"Unexpected Overpass response structure: {list(data.keys())}")

        logger.info(
            "OverpassCommunityConnector: fetched %d elements for %s",
            len(data["elements"]),
            self.town.id,
        )
        return data

    def normalize(self, raw: Any) -> list[Observation]:
        """Returns empty list — community connector is features-only.

        Required by BaseConnector ABC. Data is upserted directly via
        upsert_feature() in run().
        """
        return []

    def _extract_mappings(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract POI mappings from Overpass API response.

        For each element, determine category, coordinates, and source_id.
        Skips elements with missing coordinates.

        Args:
            raw: Parsed Overpass API JSON response.

        Returns:
            List of dicts with: source_id, lat, lon, domain, category, tags.
        """
        mappings: list[dict[str, Any]] = []
        for element in raw.get("elements", []):
            tags = element.get("tags", {})

            # Determine category from amenity or leisure tag
            amenity = tags.get("amenity", "")
            leisure = tags.get("leisure", "")
            category = CATEGORY_MAP.get(amenity) or CATEGORY_MAP.get(leisure)
            if category is None:
                # Element has no recognized community tag — skip
                continue

            # Extract coordinates: nodes have lat/lon at top level,
            # ways have center.lat/center.lon
            lat = element.get("lat") or (element.get("center") or {}).get("lat")
            lon = element.get("lon") or (element.get("center") or {}).get("lon")
            if lat is None or lon is None:
                logger.debug(
                    "Skipping element %s/%s: missing coordinates",
                    element.get("type"),
                    element.get("id"),
                )
                continue

            source_id = f"osm:{element['type']}:{element['id']}"

            mappings.append({
                "source_id": source_id,
                "lat": lat,
                "lon": lon,
                "domain": "community",
                "category": category,
                "tags": tags,
            })
        return mappings

    async def run(self) -> None:
        """Full pipeline: fetch → upsert features → update staleness.

        Overrides BaseConnector.run() to use upsert_feature() directly.
        """
        raw = await self.fetch()
        mappings = self._extract_mappings(raw)

        upserted = 0
        for m in mappings:
            tags = m["tags"]
            properties: dict[str, Any] = {
                "category": m["category"],
                "name": tags.get("name"),
                "amenity": tags.get("amenity"),
                "leisure": tags.get("leisure"),
                "address": " ".join(filter(None, [
                    tags.get("addr:street"),
                    tags.get("addr:housenumber"),
                ])) or None,
                "opening_hours": tags.get("opening_hours"),
            }
            # Remove None values to keep properties clean
            properties = {k: v for k, v in properties.items() if v is not None}

            geometry_wkt = f"POINT({m['lon']} {m['lat']})"
            try:
                await self.upsert_feature(
                    source_id=m["source_id"],
                    domain="community",
                    geometry_wkt=geometry_wkt,
                    properties=properties,
                )
                upserted += 1
            except Exception as exc:
                logger.warning(
                    "Failed to upsert community feature %s: %s",
                    m["source_id"],
                    exc,
                )

        logger.info(
            "OverpassCommunityConnector: upserted %d/%d features for %s",
            upserted,
            len(mappings),
            self.town.id,
        )
        await self._update_staleness()
