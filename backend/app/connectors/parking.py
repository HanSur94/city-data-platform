"""ParkingConnector: scrapes parking garage occupancy from Stadtwerke Aalen.

Polls https://www.sw-aalen.de/privatkunden/dienstleistungen/parken/parkhausbelegung
and extracts garage name, free spots, total capacity via BeautifulSoup4.

Features are upserted into the infrastructure domain with category=parking.
No hypertable writes -- parking is feature-properties-only.

License: scraping (Stadtwerke Aalen public page)
"""
from __future__ import annotations

import logging
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.config import ConnectorConfig, Town
from app.connectors.base import BaseConnector, Observation
from app.models.parking import ParkingGarage

logger = logging.getLogger(__name__)

# Known Aalen parking garages with approximate coordinates (from OSM).
# Keyed by normalized name substring for fuzzy matching against scraped names.
GARAGES: dict[str, dict[str, float]] = {
    "stadtmitte": {"lat": 48.8365, "lon": 10.0940},
    "gmünder": {"lat": 48.8372, "lon": 10.0980},
    "gmuender": {"lat": 48.8372, "lon": 10.0980},
    "reichsstädter": {"lat": 48.8358, "lon": 10.0920},
    "reichsstaedter": {"lat": 48.8358, "lon": 10.0920},
    "spitalstr": {"lat": 48.8350, "lon": 10.0960},
}

# Default center-of-Aalen coordinates for unknown garages
DEFAULT_LAT = 48.8360
DEFAULT_LON = 10.0935


def _slugify(name: str) -> str:
    """Create a URL-safe slug from a garage name."""
    slug = name.lower().strip()
    slug = slug.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def _find_coords(name: str) -> dict[str, float]:
    """Find coordinates for a garage by matching name substrings."""
    lower = name.lower()
    for key, coords in GARAGES.items():
        if key in lower:
            return coords
    return {"lat": DEFAULT_LAT, "lon": DEFAULT_LON}


class ParkingConnector(BaseConnector):
    """Scrapes parking garage occupancy from Stadtwerke Aalen.

    Config keys (from ConnectorConfig.config dict):
        url: str          -- URL of the parking page
        attribution: str  -- Attribution string
    """

    def __init__(self, config: ConnectorConfig, town: Town) -> None:
        super().__init__(config, town)
        self._url: str = self.config.config.get(
            "url",
            "https://www.sw-aalen.de/privatkunden/dienstleistungen/parken/parkhausbelegung",
        )

    async def fetch(self) -> str:
        """Fetch HTML page from Stadtwerke Aalen parking page.

        Returns:
            Raw HTML string.

        Raises:
            httpx.HTTPError: On network failure.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self._url)
            response.raise_for_status()
            return response.text

    def normalize(self, raw: Any) -> list[ParkingGarage]:
        """Parse HTML and extract parking garage data.

        Extracts each parking garage row with name, free spots, total capacity.
        Handles "geschlossen" (closed) as 0 free spots.
        Returns empty list for unparseable HTML -- graceful degradation.

        Args:
            raw: HTML string from fetch().

        Returns:
            List of ParkingGarage objects.
        """
        garages: list[ParkingGarage] = []

        try:
            soup = BeautifulSoup(raw, "html.parser")
            items = soup.select(".parkhaus-item")

            if not items:
                logger.warning("No parking garage items found in HTML")
                return []

            for item in items:
                try:
                    name_el = item.select_one("h3")
                    free_el = item.select_one(".free")
                    total_el = item.select_one(".total")

                    if not name_el or not total_el:
                        continue

                    name = name_el.get_text(strip=True)

                    # Parse total spots
                    total_text = total_el.get_text(strip=True)
                    try:
                        total_spots = int(total_text)
                    except ValueError:
                        logger.warning("Cannot parse total spots for %s: %s", name, total_text)
                        continue

                    if total_spots <= 0:
                        continue

                    # Parse free spots -- "geschlossen" or non-numeric means 0
                    free_spots = 0
                    if free_el:
                        free_text = free_el.get_text(strip=True).lower()
                        if free_text == "geschlossen":
                            free_spots = 0
                        else:
                            try:
                                free_spots = max(0, int(free_text))
                            except ValueError:
                                free_spots = 0

                    # Clamp free spots to total
                    free_spots = min(free_spots, total_spots)

                    occupancy_pct = (total_spots - free_spots) / total_spots * 100

                    garages.append(
                        ParkingGarage(
                            name=name,
                            free_spots=free_spots,
                            total_spots=total_spots,
                            occupancy_pct=round(occupancy_pct, 1),
                        )
                    )
                except Exception as exc:
                    logger.warning("Failed to parse parking garage item: %s", exc)
                    continue

        except Exception as exc:
            logger.warning("Failed to parse parking HTML: %s", exc)
            return []

        return garages

    async def run(self) -> None:
        """Full pipeline: fetch -> normalize -> upsert features -> update staleness.

        Overrides BaseConnector.run() because parking uses feature-properties-only
        (no hypertable observations). Each garage is upserted as an infrastructure
        feature with category=parking.
        """
        try:
            raw = await self.fetch()
        except Exception as exc:
            logger.error("ParkingConnector fetch failed: %s", exc)
            return

        garages = self.normalize(raw)

        if not garages:
            logger.warning("ParkingConnector: no garages parsed, skipping upsert")
            return

        for garage in garages:
            coords = _find_coords(garage.name)
            slug = _slugify(garage.name)
            source_id = f"parking:{slug}"

            try:
                await self.upsert_feature(
                    source_id=source_id,
                    domain="infrastructure",
                    geometry_wkt=f"POINT({coords['lon']} {coords['lat']})",
                    properties={
                        "category": "parking",
                        "name": garage.name,
                        "free_spots": garage.free_spots,
                        "total_spots": garage.total_spots,
                        "occupancy_pct": garage.occupancy_pct,
                        "data_type": "SCRAPED",
                    },
                )
            except Exception as exc:
                logger.error("Failed to upsert parking feature %s: %s", source_id, exc)

        await self._update_staleness()
        logger.info("ParkingConnector: upserted %d garages", len(garages))
