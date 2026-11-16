"""EvChargingConnector: fetches EV charging locations from MobiData BW OCPDB.

Replaces static BNetzA Ladesaeulenregister data with the Open Charge Point
Database (OCPDB) published by MobiData BW.

Each location is upserted as an infrastructure feature with its status
(AVAILABLE/OCCUPIED/INOPERATIVE where the operator reports live status,
UNKNOWN for registry-only points), power classification, and connector details.

API: https://api.mobidata-bw.de/ocpdb/api/public/v1/locations
Parameters: lat, lon, radius (metres), limit, offset. The answer is
{"items": [...], "total_count": n, "next_offset": m}; pages are read until
next_offset is missing (at most MAX_PAGES pages per run).
No authentication required (public API).

License: MobiData BW, open data
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.connectors.base import BaseConnector, Observation
from app.config import ConnectorConfig, Town

logger = logging.getLogger(__name__)

OCPDB_API_URL = "https://api.mobidata-bw.de/ocpdb/api/public/v1/locations"
USER_AGENT = "city-data-platform/0.1 (open-source city dashboard)"
PAGE_SIZE = 100
MAX_PAGES = 20


def classify_power(max_kw: float) -> str:
    """Classify charging power into categories.

    Args:
        max_kw: Maximum power in kW.

    Returns:
        "ac_slow" (<=22kW), "ac_fast" (22-43kW), or "dc_fast" (>43kW).
    """
    if max_kw <= 22.0:
        return "ac_slow"
    if max_kw <= 43.0:
        return "ac_fast"
    return "dc_fast"


def map_ocpdb_status(status: str) -> str:
    """Map OCPDB/OCPI EVSE status to simplified status.

    Args:
        status: OCPI 2.2 EVSE status string.

    Returns:
        Simplified status: AVAILABLE, OCCUPIED, INOPERATIVE, or UNKNOWN.
    """
    mapping = {
        # STATIC: points registered by the Bundesnetzagentur without live status.
        "STATIC": "UNKNOWN",
        "AVAILABLE": "AVAILABLE",
        "CHARGING": "OCCUPIED",
        "INOPERATIVE": "INOPERATIVE",
        "OUT_OF_ORDER": "INOPERATIVE",
        "BLOCKED": "INOPERATIVE",
    }
    return mapping.get(status, "UNKNOWN")


class EvChargingConnector(BaseConnector):
    """Fetches EV charging locations from OCPDB and upserts them as features.

    Features-only connector (like LadesaeulenConnector) -- no time-series data.
    Each OCPDB location is upserted with live status, power, and connector info.

    Config keys (from ConnectorConfig.config dict):
        radius_km (int): Search radius in km from town center. Default 15.
        attribution (str): Attribution string.
    """

    async def fetch(self) -> list[dict]:
        """Fetch all OCPDB locations within radius_km of the town center.

        Reads page after page (limit/offset) until next_offset is missing, a page
        is empty or MAX_PAGES is reached.

        Returns:
            List of OCPDB location dicts.

        Raises:
            httpx.HTTPError: On network/HTTP failure.
            ValueError: If an answer has no "items" list.
        """
        lat = self.config.config.get("lat", (self.town.bbox.lat_min + self.town.bbox.lat_max) / 2)
        lon = self.config.config.get("lon", (self.town.bbox.lon_min + self.town.bbox.lon_max) / 2)
        radius_m = int(self.config.config.get("radius_km", 15) * 1000)

        items: list[dict] = []
        offset = 0
        async with httpx.AsyncClient(timeout=30.0) as client:
            for page_number in range(1, MAX_PAGES + 1):
                r = await client.get(
                    OCPDB_API_URL,
                    params={
                        "lat": lat,
                        "lon": lon,
                        "radius": radius_m,
                        "limit": PAGE_SIZE,
                        "offset": offset,
                    },
                    headers={"User-Agent": USER_AGENT},
                )
                r.raise_for_status()
                data = r.json()

                page = data.get("items") if isinstance(data, dict) else None
                if not isinstance(page, list):
                    raise ValueError("OCPDB answer has no 'items' list")
                items.extend(page)

                next_offset = data.get("next_offset")
                if next_offset is None or not page:
                    break
                if page_number == MAX_PAGES:
                    logger.warning(
                        "EvChargingConnector: stopped after %d pages, more locations available",
                        MAX_PAGES,
                    )
                    break
                offset = next_offset

        return items

    def normalize(self, raw: Any) -> list[Observation]:
        """Return empty list -- features-only connector.

        Actual parsing happens in _parse_locations() called by run().
        """
        return []

    def _parse_locations(self, raw: list[dict]) -> list[dict]:
        """Parse and filter OCPDB locations to structured dicts.

        Filters by town bounding box and extracts status/power from EVSEs.

        Args:
            raw: List of OCPDB location dicts.

        Returns:
            List of parsed location dicts with keys: location_id, lat, lon,
            status, power_kw, power_class, operator, address, connector_types,
            evse_count, num_connectors.
        """
        bbox = self.town.bbox
        parsed: list[dict] = []

        for location in raw:
            # Extract coordinates
            coords = location.get("coordinates", {})
            try:
                lat = float(coords.get("latitude", 0))
                lon = float(coords.get("longitude", 0))
            except (TypeError, ValueError):
                continue

            # Filter by bbox
            if not (bbox.lat_min <= lat <= bbox.lat_max and
                    bbox.lon_min <= lon <= bbox.lon_max):
                continue

            # Extract EVSEs
            evses = location.get("evses", [])
            if not evses:
                continue

            # Find representative EVSE (highest power)
            best_status = "UNKNOWN"
            best_power_kw = 0.0
            connector_types: set[str] = set()
            total_connectors = 0

            for evse in evses:
                evse_status = evse.get("status", "UNKNOWN")
                connectors = evse.get("connectors", [])
                total_connectors += len(connectors)

                for conn in connectors:
                    # Extract connector type
                    standard = conn.get("standard", "")
                    if standard:
                        connector_types.add(standard)

                    # Extract power (watts -> kW)
                    power_w = conn.get("max_electric_power", 0)
                    try:
                        power_kw = float(power_w) / 1000.0
                    except (TypeError, ValueError):
                        power_kw = 0.0

                    if power_kw > best_power_kw:
                        best_power_kw = power_kw
                        best_status = evse_status

            # If no connector had power, use status from first EVSE
            if best_power_kw == 0.0 and evses:
                best_status = evses[0].get("status", "UNKNOWN")

            location_id = location.get("id", "")
            operator = ""
            op_data = location.get("operator", {})
            if isinstance(op_data, dict):
                operator = op_data.get("name", "")

            address = location.get("address", "")
            if isinstance(address, dict):
                address = address.get("address", "")
            city_line = " ".join(
                part for part in (location.get("postal_code"), location.get("city")) if part
            )
            address = ", ".join(part for part in (address, city_line) if part)

            parsed.append({
                "location_id": location_id,
                "lat": lat,
                "lon": lon,
                "status": map_ocpdb_status(best_status),
                "power_kw": best_power_kw,
                "power_class": classify_power(best_power_kw),
                "operator": operator,
                "address": address,
                "connector_types": sorted(connector_types),
                "evse_count": len(evses),
                "num_connectors": total_connectors,
            })

        return parsed

    async def run(self) -> None:
        """Full pipeline: fetch OCPDB data, parse, upsert features.

        1. Fetch OCPDB locations (a failure propagates to the scheduler and does
           NOT advance the staleness timestamp)
        2. Parse and filter by bbox
        3. Upsert each valid location as infrastructure feature
        4. Update staleness (an empty answer is a successful fetch)
        """
        raw = await self.fetch()

        locations = self._parse_locations(raw)
        logger.info(
            "EvChargingConnector: fetched %d locations, %d within bbox",
            len(raw), len(locations),
        )

        upserted = 0
        for loc in locations:
            properties = {
                "category": "ev_charging",
                "status": loc["status"],
                "power_kw": loc["power_kw"],
                "power_class": loc["power_class"],
                "operator": loc["operator"],
                "address": loc["address"],
                "num_connectors": loc["num_connectors"],
                "connector_types": loc["connector_types"],
                "evse_count": loc["evse_count"],
                "source": "ocpdb",
                "attribution": self.config.config.get(
                    "attribution", "MobiData BW OCPDB, open data"
                ),
            }

            try:
                await self.upsert_feature(
                    source_id=f"ev-charging-{loc['location_id']}",
                    domain="infrastructure",
                    geometry_wkt=f"POINT({loc['lon']} {loc['lat']})",
                    properties=properties,
                )
                upserted += 1
            except Exception as exc:
                logger.warning(
                    "EvChargingConnector: failed to upsert %s: %s",
                    loc["location_id"], exc,
                )

        await self._update_staleness()
        logger.info(
            "EvChargingConnector: upserted %d stations from %d fetched",
            upserted, len(raw),
        )
