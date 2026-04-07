"""PoliceConnector: fetches police press releases from Presseportal RSS feed
for Polizeipräsidium Aalen and creates map features with geocoded positions.

Uses Nominatim (OSM) for geocoding location names extracted from report titles.
German police reports typically start with "Aalen: ..." or "Ellwangen: ...".
"""
from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

from app.connectors.base import BaseConnector, Observation

logger = logging.getLogger(__name__)

# Presseportal RSS feed for Polizeipräsidium Aalen (ID 110969)
DEFAULT_RSS_URL = "https://www.presseportal.de/rss/dienststelle_110969.rss2"

# Simple geocode cache to avoid repeated Nominatim requests
_geocode_cache: dict[str, tuple[float, float] | None] = {}


def _extract_location(title: str) -> str | None:
    """Extract location from a German police report title.

    Typical formats:
      "POL-AA: Aalen: Unfall auf der B29"
      "POL-AA: Ellwangen/Jagst: Einbruch in Wohnhaus"
      "POL-AA: Schwäbisch Gmünd - Diebstahl aus Kfz"
    """
    # Remove the POL-AA: prefix
    cleaned = re.sub(r'^POL-[A-Z]{1,4}:\s*', '', title)
    # Extract location before the first colon, dash, or period
    match = re.match(r'^([^:–\-\.]+)', cleaned)
    if match:
        loc = match.group(1).strip()
        # Remove common suffixes like /Jagst
        loc = re.sub(r'/\w+$', '', loc).strip()
        if loc and len(loc) > 2:
            return loc
    return None


def _categorize_report(title: str, description: str) -> str:
    """Categorize a police report based on keywords."""
    text = f"{title} {description}".lower()
    if any(w in text for w in ['unfall', 'verkehrsunfall', 'kollision']):
        return 'accident'
    if any(w in text for w in ['einbruch', 'diebstahl', 'raub']):
        return 'theft'
    if any(w in text for w in ['brand', 'feuer']):
        return 'fire'
    if any(w in text for w in ['vermisst', 'suche']):
        return 'missing'
    if any(w in text for w in ['betrug', 'taeuschung']):
        return 'fraud'
    return 'general'


class PoliceConnector(BaseConnector):
    """Fetches police press releases from Presseportal RSS and geocodes them.

    Config keys:
        rss_url (str): Override RSS URL (default: PP Aalen feed).
        max_age_days (int): Max age of reports to keep (default: 7).
    """

    async def fetch(self) -> Any:
        """Download the RSS feed XML."""
        import httpx

        url = self.config.config.get("rss_url", DEFAULT_RSS_URL)
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(url, headers={"User-Agent": "CityDataPlatform/2.0"})
            r.raise_for_status()
            return r.text

    def normalize(self, raw: Any) -> list[Observation]:
        """Parse RSS XML into observations (geocoding happens in run())."""
        items: list[dict] = []
        try:
            root = ET.fromstring(raw)
            for item in root.findall('.//item'):
                title = item.findtext('title', '').strip()
                description = item.findtext('description', '').strip()
                link = item.findtext('link', '').strip()
                pub_date = item.findtext('pubDate', '').strip()

                if not title:
                    continue

                items.append({
                    'title': title,
                    'description': description,
                    'link': link,
                    'pub_date': pub_date,
                })
        except ET.ParseError as exc:
            logger.error("Failed to parse RSS XML: %s", exc)

        # Convert to observations with extracted metadata
        observations: list[Observation] = []
        for item in items:
            location = _extract_location(item['title'])
            category = _categorize_report(item['title'], item['description'])

            # Parse pub date
            ts = None
            if item['pub_date']:
                try:
                    # RSS date format: "Mon, 07 Apr 2026 14:30:00 +0200"
                    from email.utils import parsedate_to_datetime
                    ts = parsedate_to_datetime(item['pub_date'])
                except Exception:
                    ts = datetime.now(timezone.utc)

            observations.append(Observation(
                feature_id="PENDING",
                domain="police",
                source_id=f"police:{item['link'].split('/')[-1] if item['link'] else hash(item['title'])}",
                values={
                    'title': item['title'],
                    'description': item['description'][:500],
                    'link': item['link'],
                    'location_name': location or '',
                    'category': category,
                },
                timestamp=ts,
            ))

        return observations

    async def run(self) -> None:
        """Fetch RSS, geocode locations, upsert features."""
        raw = await self.fetch()
        normalized = self.normalize(raw)

        max_age_days = int(self.config.config.get("max_age_days", 7))
        now = datetime.now(timezone.utc)

        for obs in normalized:
            # Skip old reports
            if obs.timestamp:
                age_days = (now - obs.timestamp).total_seconds() / 86400
                if age_days > max_age_days:
                    continue

            location_name = obs.values.get('location_name', '')
            coords = await self._geocode(location_name) if location_name else None

            if not coords:
                # Fall back to town center with small random offset
                import random
                bbox = self.town.bbox
                center_lon = (bbox.lon_min + bbox.lon_max) / 2
                center_lat = (bbox.lat_min + bbox.lat_max) / 2
                coords = (
                    center_lon + random.uniform(-0.02, 0.02),
                    center_lat + random.uniform(-0.02, 0.02),
                )

            lon, lat = coords
            wkt = f"POINT({lon} {lat})"

            properties = {
                "feature_type": "police_report",
                "title": obs.values['title'],
                "description": obs.values['description'],
                "link": obs.values['link'],
                "location_name": location_name,
                "category": obs.values['category'],
                "pub_date": obs.timestamp.isoformat() if obs.timestamp else None,
            }

            await self.upsert_feature(
                source_id=obs.source_id,
                domain="police",
                geometry_wkt=wkt,
                properties=properties,
            )

        # Clean up old reports
        await self._cleanup_old_reports(max_age_days)
        await self._update_staleness()
        logger.info("PoliceConnector: processed %d reports.", len(normalized))

    async def _geocode(self, location: str) -> tuple[float, float] | None:
        """Geocode a location name using Nominatim (OSM).

        Caches results to avoid repeated requests. Adds town context
        for better results (e.g. "Aalen" -> "Aalen, Baden-Württemberg").
        """
        global _geocode_cache

        cache_key = location.lower().strip()
        if cache_key in _geocode_cache:
            return _geocode_cache[cache_key]

        import httpx

        # Add regional context for better geocoding
        query = f"{location}, Baden-Württemberg, Deutschland"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={
                        "q": query,
                        "format": "json",
                        "limit": 1,
                        "countrycodes": "de",
                    },
                    headers={"User-Agent": "CityDataPlatform/2.0"},
                )
                r.raise_for_status()
                results = r.json()

            if results:
                lon = float(results[0]["lon"])
                lat = float(results[0]["lat"])
                _geocode_cache[cache_key] = (lon, lat)
                return (lon, lat)
        except Exception as exc:
            logger.warning("Geocoding failed for '%s': %s", location, exc)

        _geocode_cache[cache_key] = None
        return None

    async def _cleanup_old_reports(self, max_age_days: int) -> None:
        """Remove police features older than max_age_days."""
        from app.db import AsyncSessionLocal
        from sqlalchemy import text

        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    text(
                        "DELETE FROM features "
                        "WHERE town_id = :town_id "
                        "AND domain = 'police' "
                        "AND (properties->>'pub_date')::timestamptz < NOW() - :interval::interval"
                    ),
                    {
                        "town_id": self.town.id,
                        "interval": f"{max_age_days} days",
                    },
                )
                await session.commit()
                deleted = result.rowcount
                if deleted:
                    logger.info("Cleaned up %d old police reports.", deleted)
        except Exception as exc:
            logger.warning("Failed to clean up old police reports: %s", exc)
