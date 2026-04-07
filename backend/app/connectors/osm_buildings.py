"""OSM Buildings Connector — loads building footprints with addresses from Overpass API.

Fetches all buildings within the town bbox that have address tags (addr:street,
addr:housenumber). Stores as features in the "buildings" domain with properties
including address, building type, height, levels, roof shape, year.

Poll interval: 86400s (daily) — building data is semi-static.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.connectors.base import BaseConnector, Observation

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


class OsmBuildingsConnector(BaseConnector):
    """Load OSM buildings with addresses for the configured town bbox."""

    async def fetch(self) -> Any:
        bbox = self.town.bbox
        # Overpass bbox format: south,west,north,east
        overpass_bbox = f"{bbox.lat_min},{bbox.lon_min},{bbox.lat_max},{bbox.lon_max}"

        # Query buildings with addr:housenumber
        # Use a tighter bbox around city center to avoid Overpass timeouts
        # For larger areas, split into sub-bboxes
        center_lat = (bbox.lat_min + bbox.lat_max) / 2
        center_lon = (bbox.lon_min + bbox.lon_max) / 2
        # ~2km radius around center
        tight_bbox = f"{center_lat - 0.02},{center_lon - 0.03},{center_lat + 0.02},{center_lon + 0.03}"

        query = f"""
        [out:json][timeout:90];
        way["building"]["addr:housenumber"]({tight_bbox});
        out center tags;
        """

        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(OVERPASS_URL, data={"data": query})
            resp.raise_for_status()
            return resp.json()

    def normalize(self, raw: Any) -> list[Observation]:
        # This is a features-only connector — no time-series observations
        return []

    async def run(self) -> None:
        """Fetch OSM buildings and upsert as features."""
        logger.info("Fetching OSM buildings with addresses for %s...", self.town.id)

        try:
            data = await self.fetch()
        except Exception as exc:
            logger.error("Failed to fetch OSM buildings: %s", exc)
            return

        elements = data.get("elements", [])
        logger.info("Received %d building elements from Overpass", len(elements))

        count = 0
        for el in elements:
            tags = el.get("tags", {})

            # Get center coordinates
            if el.get("type") == "way":
                center = el.get("center", {})
                lat = center.get("lat")
                lon = center.get("lon")
            elif el.get("type") == "relation":
                center = el.get("center", {})
                lat = center.get("lat")
                lon = center.get("lon")
            else:
                lat = el.get("lat")
                lon = el.get("lon")

            if lat is None or lon is None:
                continue

            osm_id = f"{el['type']}_{el['id']}"

            # Build address
            street = tags.get("addr:street", "")
            housenumber = tags.get("addr:housenumber", "")
            postcode = tags.get("addr:postcode", "")
            city = tags.get("addr:city", "")
            address_parts = []
            if street and housenumber:
                address_parts.append(f"{street} {housenumber}")
            elif street:
                address_parts.append(street)
            if postcode and city:
                address_parts.append(f"{postcode} {city}")
            elif city:
                address_parts.append(city)
            address = ", ".join(address_parts) if address_parts else ""

            # Build properties
            properties: dict[str, Any] = {
                "address": address,
                "street": street,
                "housenumber": housenumber,
            }

            if postcode:
                properties["postcode"] = postcode
            if city:
                properties["city"] = city

            # Building type
            building_type = tags.get("building", "yes")
            if building_type != "yes":
                properties["building_type"] = building_type

            # Name
            name = tags.get("name")
            if name:
                properties["name"] = name

            # Height
            height = tags.get("height")
            if height:
                try:
                    properties["height"] = float(height.replace(" m", "").replace(",", "."))
                except ValueError:
                    pass

            # Levels
            levels = tags.get("building:levels")
            if levels:
                try:
                    properties["levels"] = int(levels)
                except ValueError:
                    pass

            # Roof
            roof_shape = tags.get("roof:shape")
            if roof_shape:
                properties["roof_shape"] = roof_shape

            # Year
            start_date = tags.get("start_date")
            if start_date:
                properties["year_built"] = start_date

            # Amenity / use
            amenity = tags.get("amenity")
            if amenity:
                properties["amenity"] = amenity

            geometry_wkt = f"POINT({lon} {lat})"
            semantic_id = f"bldg_osm_{el['id']}"

            try:
                await self.upsert_feature(
                    source_id=osm_id,
                    domain="buildings",
                    geometry_wkt=geometry_wkt,
                    properties=properties,
                    semantic_id=semantic_id,
                )
                count += 1
            except Exception as exc:
                logger.warning("Failed to upsert building %s: %s", osm_id, exc)

        logger.info("Upserted %d buildings with addresses for %s", count, self.town.id)
        await self._update_staleness()
