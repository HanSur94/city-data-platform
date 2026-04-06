"""AutobahnConnector: fetches roadworks and closures from Autobahn GmbH REST API.

Implements TRAF-04: retrieves roadworks and closures for A7 and A6 near Aalen,
filters to 50km radius, and upserts features into the features table.

Autobahn API:
    GET https://verkehr.autobahn.de/o/autobahn/{road}/services/roadworks
    GET https://verkehr.autobahn.de/o/autobahn/{road}/services/closures
    Response: {"roadworks": [...]} or {"closures": [...]}
    Each entry: {identifier, coordinate: {lat, long}, title, subtitle, description,
                 isBlocked: bool, extent}

Note: Autobahn data is features-only — no time-series readings. normalize() returns [].
      All data is written to the features table via upsert_feature().

License: Datenlizenz Deutschland – Zero – Version 2.0
"""
from __future__ import annotations

import json
import math
from typing import Any

import httpx

from app.connectors.base import BaseConnector, Observation
from app.config import ConnectorConfig, Town


AUTOBAHN_BASE = "https://verkehr.autobahn.de/o/autobahn"

# Roads to monitor near Aalen
ROADS = ["A7", "A6"]

# Aalen city center coordinates (lat, lon)
AALEN_CENTER = (48.84, 10.09)

# Maximum distance in km from AALEN_CENTER to include a roadwork/closure
MAX_DISTANCE_KM = 50


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points using the Haversine formula.

    Args:
        lat1: Latitude of point 1 in decimal degrees.
        lon1: Longitude of point 1 in decimal degrees.
        lat2: Latitude of point 2 in decimal degrees.
        lon2: Longitude of point 2 in decimal degrees.

    Returns:
        Distance in kilometers.
    """
    R = 6371.0  # Earth radius in km

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


class AutobahnConnector(BaseConnector):
    """Fetches A7 and A6 roadworks/closures from Autobahn GmbH API.

    Filters entries to those within MAX_DISTANCE_KM of the town's bbox center
    (defaulting to AALEN_CENTER). Upserts matching entries as features.
    Does NOT persist time-series observations (features-only connector).

    Config keys (from ConnectorConfig.config dict):
        center_lat: Override town center latitude (default: AALEN_CENTER[0]).
        center_lon: Override town center longitude (default: AALEN_CENTER[1]).
        max_distance_km: Override maximum distance filter (default: 50).
        attribution: Attribution string (optional).
    """

    async def fetch(self) -> bytes:
        """Fetch all roadworks and closures for all configured roads.

        Makes 2 requests per road (roadworks + closures) for all roads in ROADS.
        Combines all results into a single JSON bytes payload.

        Returns:
            JSON bytes containing combined roadworks and closures dict.

        Raises:
            httpx.HTTPError: On network/HTTP failure.
        """
        all_roadworks: list[dict] = []
        all_closures: list[dict] = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            for road in ROADS:
                # Fetch roadworks
                rw_resp = await client.get(
                    f"{AUTOBAHN_BASE}/{road}/services/roadworks"
                )
                rw_resp.raise_for_status()
                rw_data = rw_resp.json()
                all_roadworks.extend(rw_data.get("roadworks", []))

                # Fetch closures
                cl_resp = await client.get(
                    f"{AUTOBAHN_BASE}/{road}/services/closures"
                )
                cl_resp.raise_for_status()
                cl_data = cl_resp.json()
                all_closures.extend(cl_data.get("closures", []))

        combined = {
            "roadworks": all_roadworks,
            "closures": all_closures,
        }
        return json.dumps(combined).encode()

    def normalize(self, raw: bytes, **kwargs) -> list[Observation]:
        """Return empty list — Autobahn data is features-only, not time-series.

        All data insertion happens via upsert_feature() in run().

        Args:
            raw: JSON bytes (ignored).

        Returns:
            Empty list.
        """
        return []

    async def run(self) -> None:
        """Full pipeline: fetch roadworks/closures, filter by distance, upsert features.

        Overrides BaseConnector.run() to:
        1. Fetch all roadworks and closures for A7 and A6
        2. Parse JSON, filter entries within MAX_DISTANCE_KM of town center
        3. Upsert each filtered entry as a spatial feature
        4. No persist() call — features-only connector
        5. Update staleness timestamp

        Does NOT call persist() because there are no time-series observations.
        """
        center_lat = self.config.config.get("center_lat", AALEN_CENTER[0])
        center_lon = self.config.config.get("center_lon", AALEN_CENTER[1])
        max_distance = self.config.config.get("max_distance_km", MAX_DISTANCE_KM)
        attribution = self.config.config.get(
            "attribution",
            "Autobahn GmbH des Bundes, Datenlizenz Deutschland – Zero – Version 2.0",
        )

        # Step 1: fetch all data
        raw = await self.fetch()

        # Step 2: parse and combine roadworks + closures
        data = json.loads(raw)
        roadworks = data.get("roadworks", [])
        closures = data.get("closures", [])

        all_entries = [
            (entry, "roadwork") for entry in roadworks
        ] + [
            (entry, "service_type_closure") for entry in closures
        ]

        # Step 3: filter by distance and upsert features
        for entry, default_type in all_entries:
            identifier = entry.get("identifier")
            if not identifier:
                continue

            coord = entry.get("coordinate", {})
            try:
                entry_lat = float(coord.get("lat", 0))
                entry_lon = float(coord.get("long", 0))
            except (ValueError, TypeError):
                continue

            # Filter to max distance from town center
            dist = _haversine(center_lat, center_lon, entry_lat, entry_lon)
            if dist > max_distance:
                continue

            # Determine type from isBlocked flag
            is_blocked: bool = bool(entry.get("isBlocked", False))
            entry_type = "closure" if is_blocked else "roadwork"

            await self.upsert_feature(
                source_id=f"autobahn:{identifier}",
                domain="traffic",
                geometry_wkt=f"POINT({entry_lon} {entry_lat})",
                properties={
                    "title": entry.get("title", ""),
                    "subtitle": entry.get("subtitle", ""),
                    "description": entry.get("description", ""),
                    "is_blocked": is_blocked,
                    "type": entry_type,
                    "extent": entry.get("extent", ""),
                    "attribution": attribution,
                    "distance_km": round(dist, 2),
                },
            )

        # Step 4: no persist() — features-only
        # Step 5: update staleness
        await self._update_staleness()
