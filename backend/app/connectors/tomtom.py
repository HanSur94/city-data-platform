"""TomTomConnector: fetches real-time traffic flow data from TomTom Flow Segment Data API.

Implements REQ-TRAFFIC-01/03/04: auto-discovers road segments by grid-scanning the
town's bounding box, then retrieves speed and congestion data for all FRC0-FRC3
road segments found (typically ~60+ for Aalen).

Discovery uses the town.bbox to generate a ~800m grid of probe points. Each point is
queried against TomTom Flow Segment API; results are filtered to FRC0-FRC3 and
deduplicated by first+last coordinate pair. Discovered segments are cached to
/tmp/tomtom_segments_{town_id}.json with a 7-day TTL to avoid re-discovery on
every polling cycle.

TomTom Flow Segment Data API:
    https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json
    ?point={lat},{lon}&key={api_key}&unit=KMPH

Returns currentSpeed, freeFlowSpeed, confidence, and road segment coordinates.
congestion_ratio = currentSpeed / freeFlowSpeed

Adaptive polling: 10min during rush hours (06-09, 16-19 Europe/Berlin), 30min off-peak.
The connector is scheduled at 600s (10min) intervals. During off-peak, it skips runs
if less than 1800s have elapsed since the last successful run.

License: TomTom Traffic Flow API (requires API key)
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from app.connectors.base import BaseConnector, Observation
from app.config import ConnectorConfig, Town, TownBbox

logger = logging.getLogger(__name__)

BERLIN_TZ = ZoneInfo("Europe/Berlin")

# TomTom Flow Segment Data API base URL
TOMTOM_FLOW_URL = (
    "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
)

# FRC classes to keep: FRC0 (motorway) through FRC4 (local connecting road).
# FRC5+ (minor local, residential) are excluded to reduce noise.
ALLOWED_FRC = {"FRC0", "FRC1", "FRC2", "FRC3", "FRC4"}

# Cache TTL: 7 days in seconds
_CACHE_TTL_SECONDS = 7 * 24 * 3600


def _now_berlin() -> datetime:
    """Return current time in Europe/Berlin timezone. Extracted for testability."""
    return datetime.now(BERLIN_TZ)


def _generate_grid_points(
    bbox: TownBbox, step: float = 0.008
) -> list[tuple[float, float]]:
    """Generate a grid of (lat, lon) probe points covering the bounding box.

    Args:
        bbox: Town bounding box with lat/lon min/max.
        step: Grid step in degrees (~800m at mid-European latitudes).

    Returns:
        List of (lat, lon) tuples covering the bbox.
    """
    points: list[tuple[float, float]] = []
    lat = bbox.lat_min
    while lat <= bbox.lat_max:
        lon = bbox.lon_min
        while lon <= bbox.lon_max:
            points.append((round(lat, 6), round(lon, 6)))
            lon += step
        lat += step
    return points


def _make_road_key(coordinates: list[dict]) -> str:
    """Create a deterministic dedup key from the first and last segment coordinate.

    Args:
        coordinates: List of dicts with 'latitude' and 'longitude' keys.

    Returns:
        String key of format "{first_lat:.5f},{first_lon:.5f}|{last_lat:.5f},{last_lon:.5f}"
    """
    first = coordinates[0]
    last = coordinates[-1]
    return (
        f"{first['latitude']:.5f},{first['longitude']:.5f}"
        f"|{last['latitude']:.5f},{last['longitude']:.5f}"
    )


def _congestion_level(ratio: float) -> str:
    """Map congestion ratio to level string.

    Args:
        ratio: currentSpeed / freeFlowSpeed (0.0 to 1.0+)

    Returns:
        'free' if >= 0.75, 'moderate' if 0.50-0.75, 'congested' if < 0.50
    """
    if ratio >= 0.75:
        return "free"
    elif ratio >= 0.50:
        return "moderate"
    else:
        return "congested"


class TomTomConnector(BaseConnector):
    """Fetches real-time traffic flow data from TomTom for auto-discovered road segments.

    On first run (or after cache expiry), scans the town's bounding box in a ~800m
    grid, queries TomTom Flow API at each probe point, filters to FRC0-FRC3 segments,
    deduplicates by first+last coordinate, and caches the result. Subsequent polling
    cycles use the cached segment list directly.

    Config keys (from ConnectorConfig.config dict):
        api_key: TomTom API key (required).
        attribution: Attribution string (optional).
    """

    # Class-level last run time for adaptive polling skip logic
    _last_run_time: float = 0.0

    def __init__(self, config: ConnectorConfig, town: Town) -> None:
        super().__init__(config, town)
        # Maps segment road_key -> features table UUID
        self._feature_ids: dict[str, str] = {}

    def _is_rush_hour(self) -> bool:
        """Check if current time in Europe/Berlin is during rush hours.

        Rush hours: 06:00-08:59 or 16:00-18:59.
        """
        now = _now_berlin()
        hour = now.hour
        return (6 <= hour <= 8) or (16 <= hour <= 18)

    def _get_poll_interval(self) -> int:
        """Return the effective poll interval in seconds.

        600s (10min) during rush hours, 1800s (30min) off-peak.
        """
        if self._is_rush_hour():
            return 600
        return 1800

    def _cache_path(self) -> Path:
        """Return the path to the segment cache file for this town."""
        return Path(f"/tmp/tomtom_segments_{self.town.id}.json")

    def _load_cache(self) -> list[dict] | None:
        """Load cached segment list from disk.

        Returns:
            List of segment dicts if cache exists and is fresh (< 7 days old),
            None otherwise.
        """
        path = self._cache_path()
        if not path.exists():
            return None
        age = time.time() - path.stat().st_mtime
        if age > _CACHE_TTL_SECONDS:
            logger.debug("TomTom segment cache expired (%.0f days old)", age / 86400)
            return None
        try:
            with path.open() as f:
                segments = json.load(f)
            logger.debug("Loaded %d cached TomTom segments from %s", len(segments), path)
            return segments
        except Exception as exc:
            logger.warning("TomTom cache read error: %s", exc)
            return None

    def _save_cache(self, segments: list[dict]) -> None:
        """Persist discovered segment list to disk cache."""
        path = self._cache_path()
        try:
            with path.open("w") as f:
                json.dump(segments, f)
            logger.debug("Saved %d TomTom segments to cache %s", len(segments), path)
        except Exception as exc:
            logger.warning("TomTom cache write error: %s", exc)

    async def _discover_segments(self) -> list[dict]:
        """Discover road segments by grid-scanning the town's bounding box.

        Generates a ~800m grid of probe points, queries each against TomTom Flow API,
        filters to FRC0-FRC3, and deduplicates by first+last coordinate key.

        Returns:
            List of segment dicts: {id, name, lat, lon, frc, road_key}.
            Also saves result to cache.
        """
        api_key = self.config.config["api_key"]
        grid_points = _generate_grid_points(self.town.bbox)
        logger.info(
            "TomTom discovery: scanning %d grid points for town %s",
            len(grid_points),
            self.town.id,
        )

        seen: dict[str, dict] = {}  # road_key -> segment_def

        async with httpx.AsyncClient(timeout=30.0) as client:
            for probe_lat, probe_lon in grid_points:
                url = (
                    f"{TOMTOM_FLOW_URL}"
                    f"?point={probe_lat},{probe_lon}"
                    f"&key={api_key}&unit=KMPH"
                )
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    data = response.json()
                except Exception as exc:
                    logger.debug(
                        "TomTom probe (%.5f,%.5f) failed: %s",
                        probe_lat, probe_lon, exc,
                    )
                    await asyncio.sleep(0.05)
                    continue

                flow_data = data.get("flowSegmentData", {})
                frc = flow_data.get("frc", "")
                if frc not in ALLOWED_FRC:
                    await asyncio.sleep(0.05)
                    continue

                coords = flow_data.get("coordinates", {}).get("coordinate", [])
                if len(coords) < 2:
                    await asyncio.sleep(0.05)
                    continue

                road_key = _make_road_key(coords)
                if road_key not in seen:
                    # Use midpoint of segment for reverse geocoding
                    mid_idx = len(coords) // 2
                    mid_lat = coords[mid_idx]["latitude"]
                    mid_lon = coords[mid_idx]["longitude"]
                    seen[road_key] = {
                        "id": road_key,
                        "name": frc,  # placeholder, resolved below
                        "lat": probe_lat,
                        "lon": probe_lon,
                        "frc": frc,
                        "road_key": road_key,
                        "mid_lat": mid_lat,
                        "mid_lon": mid_lon,
                    }

                await asyncio.sleep(0.05)

        # Reverse-geocode each segment to get actual street names
        logger.info("TomTom: reverse-geocoding %d segments for street names", len(seen))
        async with httpx.AsyncClient(timeout=15.0) as client:
            for seg in seen.values():
                try:
                    geo_url = (
                        f"https://api.tomtom.com/search/2/reverseGeocode/"
                        f"{seg['mid_lat']},{seg['mid_lon']}.json"
                        f"?key={api_key}"
                    )
                    resp = await client.get(geo_url)
                    resp.raise_for_status()
                    addresses = resp.json().get("addresses", [])
                    if addresses:
                        addr = addresses[0].get("address", {})
                        street = addr.get("streetName") or addr.get("freeformAddress") or seg["frc"]
                        seg["name"] = street
                except Exception:
                    pass  # keep FRC as fallback name
                await asyncio.sleep(0.05)

        segments = list(seen.values())

        # Log discovery stats
        frc_counts: dict[str, int] = {}
        for seg in segments:
            frc_counts[seg["frc"]] = frc_counts.get(seg["frc"], 0) + 1
        logger.info(
            "TomTom discovery complete: %d probes -> %d unique segments %s",
            len(grid_points),
            len(segments),
            frc_counts,
        )

        self._save_cache(segments)
        return segments

    async def fetch(self) -> list[tuple[dict, dict]]:
        """Fetch flow segment data from TomTom for each discovered/cached road segment.

        Loads segments from cache if available and fresh; otherwise triggers
        auto-discovery via grid scan.

        Returns:
            List of (segment_def, api_response_dict) tuples.
            Segments with API errors are skipped (logged as warning).
        """
        api_key = self.config.config["api_key"]

        # Load from cache or discover
        segments = self._load_cache()
        if segments is None:
            segments = await self._discover_segments()

        results: list[tuple[dict, dict]] = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            for segment in segments:
                url = (
                    f"{TOMTOM_FLOW_URL}"
                    f"?point={segment['lat']},{segment['lon']}"
                    f"&key={api_key}&unit=KMPH"
                )
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    data = response.json()
                    results.append((segment, data))
                except Exception as exc:
                    logger.warning(
                        "TomTom API error for segment %s: %s",
                        segment["id"],
                        exc,
                    )
                    continue

        return results

    def normalize(self, raw: Any) -> list[Observation]:
        """Transform TomTom API responses into Observations.

        Args:
            raw: List of (segment_def, api_response_dict) tuples from fetch().

        Returns:
            List of Observation objects with domain='traffic'.
        """
        observations: list[Observation] = []

        for segment_def, response_data in raw:
            flow_data = response_data.get("flowSegmentData", {})
            current_speed = flow_data.get("currentSpeed", 0)
            freeflow_speed = flow_data.get("freeFlowSpeed", 0)

            # Guard against division by zero
            if freeflow_speed > 0:
                congestion_ratio = current_speed / freeflow_speed
            else:
                congestion_ratio = 1.0

            level = _congestion_level(congestion_ratio)

            feature_id = self._feature_ids.get(segment_def["id"], "")

            observations.append(
                Observation(
                    feature_id=feature_id,
                    domain="traffic",
                    values={
                        "vehicle_count_total": None,
                        "vehicle_count_hgv": None,
                        "speed_avg_kmh": current_speed,
                        "congestion_level": level,
                    },
                    source_id=f"tomtom:{segment_def['id']}",
                )
            )

        return observations

    async def run(self) -> None:
        """Full pipeline: fetch, upsert features, normalize, persist, update staleness.

        Overrides BaseConnector.run() to:
        1. Check adaptive polling — skip off-peak if not enough time elapsed
        2. Fetch flow data from TomTom API (using cached or freshly discovered segments)
        3. Upsert each road segment as a spatial feature with LineString geometry
        4. Normalize into Observations
        5. Persist to traffic_readings
        6. Update staleness timestamp
        """
        # Adaptive polling: skip off-peak runs if less than 1800s since last run
        now_epoch = time.time()
        if not self._is_rush_hour():
            elapsed = now_epoch - TomTomConnector._last_run_time
            if TomTomConnector._last_run_time > 0 and elapsed < 300:
                logger.debug(
                    "TomTom off-peak skip: only %ds since last run (need 1800s)",
                    int(elapsed),
                )
                return

        attribution = self.config.config.get(
            "attribution", "TomTom Flow API"
        )

        # Step 1: fetch
        raw = await self.fetch()
        if not raw:
            logger.warning("TomTom: no segment data returned")
            return

        # Step 2: upsert features with LineString geometry
        for segment_def, response_data in raw:
            flow_data = response_data.get("flowSegmentData", {})
            coords = flow_data.get("coordinates", {}).get("coordinate", [])
            current_speed = flow_data.get("currentSpeed", 0)
            freeflow_speed = flow_data.get("freeFlowSpeed", 0)
            confidence = flow_data.get("confidence", 0)

            if freeflow_speed > 0:
                congestion_ratio = current_speed / freeflow_speed
            else:
                congestion_ratio = 1.0

            # Build WKT LINESTRING from coordinates
            if len(coords) >= 2:
                coord_pairs = [
                    f"{c['longitude']} {c['latitude']}" for c in coords
                ]
                geometry_wkt = f"LINESTRING({', '.join(coord_pairs)})"
            else:
                # Fallback to point if not enough coordinates
                geometry_wkt = f"POINT({segment_def['lon']} {segment_def['lat']})"

            feature_id = await self.upsert_feature(
                source_id=f"tomtom:{segment_def['id']}",
                domain="traffic",
                geometry_wkt=geometry_wkt,
                properties={
                    "road_name": segment_def["name"],
                    "segment_id": segment_def["id"],
                    "data_source": "TomTom",
                    "freeflow_kmh": freeflow_speed,
                    "congestion_ratio": round(congestion_ratio, 3),
                    "confidence": confidence,
                    "attribution": attribution,
                },
            )
            self._feature_ids[segment_def["id"]] = feature_id

        # Step 3-5: normalize -> persist -> update staleness
        observations = self.normalize(raw)
        await self.persist(observations)
        await self._update_staleness()

        # Record successful run time for adaptive polling
        TomTomConnector._last_run_time = time.time()
