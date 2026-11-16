"""ParkingConnector: scrapes parking garage occupancy from Stadtwerke Aalen.

Polls https://www.sw-aalen.de/privatkunden/dienstleistungen/parken/parkhausbelegung
and reads the garage table: one row per garage with the name in a row header
(<th scope="row">), the free spaces in the first cell ("75 freie Plätze") and the
open state in a badge ("geöffnet", "besetzt", "geschlossen"). The opening-hours table
further down the page has no row headers and is ignored.

The page publishes neither capacity nor coordinates. Positions (and capacities, where
known) come from the static GARAGES table below; a garage without an entry is placed at
the town centre and flagged location_approximate.

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

USER_AGENT = "city-data-platform/0.1 (open-source city dashboard)"

# Static garage table. Keys are ASCII-normalised name fragments (lowercase, ae/oe/ue/ss,
# garage code such as "p2 " removed); the first key contained in the normalised scraped
# name wins. Values: lat, lon and an optional integer "capacity" (only when verified).
# Garages without an entry here (currently P1 Rathaus, P3 Spritzenhausplatz, P6 Bahnhof,
# P1 Kubus) are placed at the town centre — no coordinates are guessed.
GARAGES: dict[str, dict[str, float]] = {
    "stadtmitte": {"lat": 48.8365, "lon": 10.0940},
    "gmuender": {"lat": 48.8372, "lon": 10.0980},
    "reichsstaedter": {"lat": 48.8358, "lon": 10.0920},
    "spitalstr": {"lat": 48.8350, "lon": 10.0960},
}

# Default center-of-Aalen coordinates for garages without a table entry
DEFAULT_LAT = 48.8360
DEFAULT_LON = 10.0935

_GARAGE_CODE_RE = re.compile(r"^(p\d+)\b", re.IGNORECASE)
_FREE_SPOTS_RE = re.compile(r"(\d+)\s*freie", re.IGNORECASE)


def _ascii_normalise(name: str) -> str:
    """Lowercase and fold German umlauts / sharp s to ASCII."""
    text = name.lower().strip()
    return text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")


def _slugify(name: str) -> str:
    """Create a URL-safe slug from a garage name."""
    slug = re.sub(r"[^a-z0-9]+", "-", _ascii_normalise(name))
    return slug.strip("-")


def _garage_code(name: str) -> str | None:
    """Return the garage code at the start of a name ("P1 Rathaus" -> "P1")."""
    match = _GARAGE_CODE_RE.match(name.strip())
    return match.group(1).upper() if match else None


def _find_entry(name: str) -> dict[str, float] | None:
    """Find the static table entry of a garage by name fragment, or None."""
    normalised = re.sub(r"^p\d+\s+", "", _ascii_normalise(name))
    for key, entry in GARAGES.items():
        if key in normalised:
            return entry
    return None


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
            response = await client.get(self._url, headers={"User-Agent": USER_AGENT})
            response.raise_for_status()
            return response.text

    def normalize(self, raw: Any) -> list[ParkingGarage]:
        """Parse HTML and extract parking garage data.

        One garage per table row that has a row header (<th scope="row">). Free spaces
        come from the "<n> freie" text of the first cell, or are 0 when the row says
        "geschlossen". Rows with neither are skipped. Returns an empty list for markup
        without matching rows -- graceful degradation.

        Args:
            raw: HTML string from fetch().

        Returns:
            List of ParkingGarage objects in page order.
        """
        garages: list[ParkingGarage] = []

        try:
            soup = BeautifulSoup(raw, "html.parser")

            for row in soup.find_all("tr"):
                header = row.find("th", attrs={"scope": "row"})
                if header is None:
                    continue
                try:
                    name = " ".join(header.get_text().split())
                    cells = row.find_all("td")
                    first_cell = cells[0].get_text(" ", strip=True) if cells else ""
                    row_text = row.get_text(" ", strip=True).lower()

                    free_match = _FREE_SPOTS_RE.search(first_cell)
                    if free_match:
                        free_spots = int(free_match.group(1))
                    elif "geschlossen" in row_text:
                        free_spots = 0
                    else:
                        logger.warning("Cannot read free spaces for %s: %r", name, first_cell)
                        continue

                    badge = row.find(class_="badge")
                    status_text = badge.get_text(strip=True) if badge else None
                    status_lower = (status_text or "").lower()
                    if "geschlossen" in status_lower:
                        is_open: bool | None = False
                    elif status_lower in ("geöffnet", "besetzt"):
                        is_open = True
                    else:
                        is_open = None

                    total_spots: int | None = None
                    occupancy_pct: float | None = None
                    entry = _find_entry(name)
                    capacity = entry.get("capacity") if entry else None
                    if capacity:
                        total_spots = int(capacity)
                        free_spots = min(free_spots, total_spots)
                        occupancy_pct = round((total_spots - free_spots) / total_spots * 100, 1)

                    garages.append(
                        ParkingGarage(
                            name=name,
                            free_spots=free_spots,
                            total_spots=total_spots,
                            occupancy_pct=occupancy_pct,
                            is_open=is_open,
                            status_text=status_text or None,
                        )
                    )
                except Exception as exc:
                    logger.warning("Failed to parse parking garage row: %s", exc)
                    continue

            if not garages:
                logger.warning("No parking garage rows found in HTML")

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

        approximate: list[str] = []
        for garage in garages:
            entry = _find_entry(garage.name)
            if entry is None:
                lat, lon = DEFAULT_LAT, DEFAULT_LON
                approximate.append(garage.name)
            else:
                lat, lon = entry["lat"], entry["lon"]
            slug = _slugify(garage.name)
            source_id = f"parking:{slug}"

            properties: dict[str, Any] = {
                "category": "parking",
                "name": garage.name,
                "garage_code": _garage_code(garage.name),
                "free_spots": garage.free_spots,
                "total_spots": garage.total_spots,
                "occupancy_pct": garage.occupancy_pct,
                "is_open": garage.is_open,
                "status_text": garage.status_text,
                "data_type": "SCRAPED",
            }
            if entry is None:
                properties["location_approximate"] = True
            properties = {k: v for k, v in properties.items() if v is not None}

            try:
                await self.upsert_feature(
                    source_id=source_id,
                    domain="infrastructure",
                    geometry_wkt=f"POINT({lon} {lat})",
                    properties=properties,
                )
            except Exception as exc:
                logger.error("Failed to upsert parking feature %s: %s", source_id, exc)

        if approximate:
            logger.warning(
                "ParkingConnector: no coordinates known for %s — placed at the town centre",
                ", ".join(approximate),
            )

        await self._update_staleness()
        logger.info("ParkingConnector: upserted %d garages", len(garages))
