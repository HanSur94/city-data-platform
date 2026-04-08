"""BusInterpolationConnector: interpolates bus positions from GTFS static
schedule data + GTFS-RT delay offsets.

Computation connector — does NOT use the standard fetch/normalize/persist
pipeline. Instead, run() downloads/caches the GTFS zip, parses it with
gtfs_kit, determines active trips, queries delay data from the database,
and writes interpolated positions as transit domain features.

Shape-walking algorithm (shape_walk) and trip interpolation
(interpolate_position) are pure functions for easy unit testing.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.connectors.base import BaseConnector, Observation
from app.models.bus_interpolation import ActiveTrip, BusPosition

logger = logging.getLogger(__name__)

# Cache GTFS zip for 24 hours
_GTFS_CACHE_MAX_AGE = 604800  # 7 days — GTFS schedules update weekly


def _haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Haversine distance in metres between two WGS84 points."""
    R = 6_371_000.0
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _bearing(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Initial bearing in degrees (0-360) from point 1 to point 2."""
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlon) * math.cos(rlat2)
    y = math.cos(rlat1) * math.sin(rlat2) - math.sin(rlat1) * math.cos(rlat2) * math.cos(dlon)
    brng = math.degrees(math.atan2(x, y))
    return (brng + 360) % 360


def shape_walk(
    shape_coords: list[tuple[float, float]],
    progress: float,
) -> tuple[float, float, float]:
    """Walk along a LineString shape at the given progress fraction.

    Args:
        shape_coords: Ordered list of (lon, lat) tuples defining the route shape.
        progress: Fraction of total distance (0.0 = start, 1.0 = end).

    Returns:
        (lon, lat, bearing) at the interpolated position.
    """
    if not shape_coords:
        raise ValueError("shape_coords must not be empty")
    if len(shape_coords) == 1:
        lon, lat = shape_coords[0]
        return (lon, lat, 0.0)

    progress = max(0.0, min(1.0, progress))

    # Compute cumulative distances
    cum_dist = [0.0]
    for i in range(1, len(shape_coords)):
        lon1, lat1 = shape_coords[i - 1]
        lon2, lat2 = shape_coords[i]
        cum_dist.append(cum_dist[-1] + _haversine(lon1, lat1, lon2, lat2))

    total = cum_dist[-1]
    if total == 0.0:
        lon, lat = shape_coords[0]
        return (lon, lat, 0.0)

    target = progress * total

    # Find the segment
    for i in range(1, len(cum_dist)):
        if cum_dist[i] >= target:
            seg_start = cum_dist[i - 1]
            seg_len = cum_dist[i] - seg_start
            if seg_len == 0:
                frac = 0.0
            else:
                frac = (target - seg_start) / seg_len

            lon1, lat1 = shape_coords[i - 1]
            lon2, lat2 = shape_coords[i]
            lon = lon1 + frac * (lon2 - lon1)
            lat = lat1 + frac * (lat2 - lat1)
            brng = _bearing(lon1, lat1, lon2, lat2)
            return (lon, lat, brng)

    # Fallback: return last point
    lon, lat = shape_coords[-1]
    brng = _bearing(*shape_coords[-2], *shape_coords[-1]) if len(shape_coords) >= 2 else 0.0
    return (lon, lat, brng)


def interpolate_position(
    trip: ActiveTrip,
    now_seconds_since_midnight: int,
) -> BusPosition | None:
    """Calculate interpolated bus position for an active trip.

    Args:
        trip: ActiveTrip with stop_times, shape_coords, and delay.
        now_seconds_since_midnight: Current time as seconds since midnight.

    Returns:
        BusPosition if the trip is active, None if trip is completed.

    Edge cases handled per REQ-BUS-05:
        - Trip not departed: returns position at first stop, departed=False
        - Trip completed: returns None
        - Dwelling at stop: returns stop position exactly
        - No delay data: delay_seconds=0, pure schedule interpolation
    """
    if not trip.stop_times or not trip.shape_coords:
        return None

    delay = trip.delay_seconds

    # Effective times = scheduled + delay
    first_departure = trip.stop_times[0][2] + delay  # departure of first stop
    last_arrival = trip.stop_times[-1][1] + delay     # arrival at last stop

    now = now_seconds_since_midnight

    # Trip completed: current time > last arrival
    if now > last_arrival:
        return None

    # Trip not departed: current time < first departure
    if now < first_departure:
        lon, lat = trip.shape_coords[0]
        return BusPosition(
            trip_id=trip.trip_id,
            route_id=trip.route_id,
            line_name=trip.line_name,
            destination=trip.destination,
            next_stop=trip.stop_times[0][0],
            prev_stop="",
            lat=lat,
            lon=lon,
            bearing=0.0,
            delay_seconds=delay,
            progress=0.0,
            departed=False,
            route_type=trip.route_type,
        )

    # Find current segment between stops
    # Check if dwelling at a stop (between arrival and departure at same stop)
    for i, (stop_name, arr, dep) in enumerate(trip.stop_times):
        eff_arr = arr + delay
        eff_dep = dep + delay
        if eff_arr <= now <= eff_dep and eff_arr != eff_dep:
            # Dwelling at this stop — compute position from stop fraction
            # Stop i is at fraction i/(n-1) along the shape (approximate)
            n_stops = len(trip.stop_times)
            if n_stops <= 1:
                progress = 0.0
            else:
                progress = i / (n_stops - 1)
            lon, lat, brng = shape_walk(trip.shape_coords, progress)
            return BusPosition(
                trip_id=trip.trip_id,
                route_id=trip.route_id,
                line_name=trip.line_name,
                destination=trip.destination,
                next_stop=stop_name,
                prev_stop=trip.stop_times[i - 1][0] if i > 0 else "",
                lat=lat,
                lon=lon,
                bearing=brng,
                delay_seconds=delay,
                progress=progress,
                departed=True,
                route_type=trip.route_type,
            )

    # Find the segment: between which two stops is the bus now?
    for i in range(len(trip.stop_times) - 1):
        name_a, _arr_a, dep_a = trip.stop_times[i]
        name_b, arr_b, _dep_b = trip.stop_times[i + 1]
        eff_dep_a = dep_a + delay
        eff_arr_b = arr_b + delay

        if eff_dep_a <= now <= eff_arr_b:
            # Interpolate within this segment
            seg_duration = eff_arr_b - eff_dep_a
            if seg_duration <= 0:
                seg_frac = 1.0
            else:
                seg_frac = (now - eff_dep_a) / seg_duration

            # Map segment fraction to overall trip progress
            n_stops = len(trip.stop_times)
            stop_frac_a = i / (n_stops - 1) if n_stops > 1 else 0.0
            stop_frac_b = (i + 1) / (n_stops - 1) if n_stops > 1 else 1.0
            progress = stop_frac_a + seg_frac * (stop_frac_b - stop_frac_a)

            lon, lat, brng = shape_walk(trip.shape_coords, progress)
            return BusPosition(
                trip_id=trip.trip_id,
                route_id=trip.route_id,
                line_name=trip.line_name,
                destination=trip.destination,
                next_stop=name_b,
                prev_stop=name_a,
                lat=lat,
                lon=lon,
                bearing=brng,
                delay_seconds=delay,
                progress=progress,
                departed=True,
                route_type=trip.route_type,
            )

    # Fallback: past last computed segment — trip has effectively completed
    # Return None to let cleanup remove this bus from the map
    return None


class BusInterpolationConnector(BaseConnector):
    """Computation connector: interpolates bus positions from GTFS schedule + RT delay.

    Does NOT use the standard fetch/normalize/persist pipeline.
    run() orchestrates the full computation:
    1. Download/cache GTFS zip
    2. Parse with gtfs_kit (in thread — blocking)
    3. Determine active service_ids for today
    4. Find active trips
    5. Fetch GTFS-RT delays from DB
    6. Interpolate positions
    7. Upsert features + persist to transit_positions
    8. Clean up stale features
    """

    async def fetch(self) -> Any:
        """Not used — run() handles everything."""
        return None

    def normalize(self, raw: Any) -> list[Observation]:
        """Not used — run() handles everything."""
        return []

    async def run(self) -> None:
        """Full interpolation pipeline."""
        gtfs_url = self.config.config.get("gtfs_url", "")
        if not gtfs_url:
            # Default to NVBW Baden-Wuerttemberg GTFS for OstalbMobil coverage
            gtfs_url = "https://www.nvbw.de/fileadmin/nvbw/open-data/fahrplandaten_mit_liniennetz/bwgesamt.zip"
            logger.info("BusInterpolationConnector: using default NVBW GTFS URL")

        # 1. Download/cache GTFS
        zip_bytes = await self._download_cached_gtfs(gtfs_url)
        if not zip_bytes:
            return

        # 2. Parse GTFS (blocking, run in thread)
        feed = await asyncio.to_thread(self._parse_gtfs, zip_bytes)
        if feed is None:
            return

        # 3. Determine active services for today
        now_utc = datetime.now(timezone.utc)
        try:
            import zoneinfo
            tz = zoneinfo.ZoneInfo(self.town.timezone if hasattr(self.town, 'timezone') else "Europe/Berlin")
        except Exception:
            import zoneinfo
            tz = zoneinfo.ZoneInfo("Europe/Berlin")
        now_local = now_utc.astimezone(tz)
        today = now_local.date()
        now_secs = now_local.hour * 3600 + now_local.minute * 60 + now_local.second

        active_service_ids = self._get_active_service_ids(feed, today)
        if not active_service_ids:
            logger.info("No active services for %s — skipping interpolation.", today)
            await self._update_staleness()
            return

        # 4. Find active trips
        active_trips = self._build_active_trips(feed, active_service_ids, now_secs)
        logger.info("Found %d active trips for interpolation.", len(active_trips))

        # 5. Fetch delays from DB
        delays = await self._fetch_delays([t.trip_id for t in active_trips])

        # 6. Interpolate positions
        all_positions: list[tuple[ActiveTrip, BusPosition]] = []
        for trip in active_trips:
            trip.delay_seconds = delays.get(trip.trip_id, 0)
            pos = interpolate_position(trip, now_secs)
            if pos is None:
                continue
            all_positions.append((trip, pos))

        # 6a. Deduplicate: keep only 1 bus per route+direction
        # For each (route_id, destination), keep the trip with progress closest
        # to mid-route (most visible/useful position). This avoids showing 3-4
        # buses per line when the GTFS feed has overlapping 20-min frequency trips.
        best_per_route: dict[tuple[str, str], tuple[ActiveTrip, BusPosition]] = {}
        for trip, pos in all_positions:
            key = (pos.route_id, pos.destination)
            if key not in best_per_route:
                best_per_route[key] = (trip, pos)
            else:
                _, existing_pos = best_per_route[key]
                # Prefer the trip that is most actively in transit (closest to 0.5 progress)
                # Among departed trips, prefer the one furthest from endpoints
                existing_score = abs(existing_pos.progress - 0.5) if existing_pos.departed else 1.0
                new_score = abs(pos.progress - 0.5) if pos.departed else 1.0
                if new_score < existing_score:
                    best_per_route[key] = (trip, pos)

        logger.info(
            "Deduplicated %d positions to %d (1 per route+direction).",
            len(all_positions), len(best_per_route),
        )

        # 6b. Upsert deduplicated positions
        active_source_ids: set[str] = set()
        observations: list[Observation] = []

        for trip, pos in best_per_route.values():
            source_id = f"bus-pos:{trip.trip_id}"
            active_source_ids.add(source_id)
            wkt = f"POINT({pos.lon} {pos.lat})"
            # Include route shape coords so frontend can draw driven/remaining path
            import json as _json
            shape_coords_json = _json.dumps(trip.shape_coords) if trip.shape_coords else None

            # Format schedule times for frontend display
            def _fmt_time(secs: int) -> str:
                h, m = divmod(secs, 3600)
                m = m // 60
                return f"{h % 24:02d}:{m:02d}"

            first_dep = trip.stop_times[0][2] if trip.stop_times else 0
            last_arr = trip.stop_times[-1][1] if trip.stop_times else 0
            origin_stop = trip.stop_times[0][0] if trip.stop_times else ""
            total_stops = len(trip.stop_times)

            properties = {
                "feature_type": "bus_position",
                "trip_id": pos.trip_id,
                "route_id": pos.route_id,
                "line_name": pos.line_name,
                "destination": pos.destination,
                "next_stop": pos.next_stop,
                "prev_stop": pos.prev_stop,
                "delay_seconds": pos.delay_seconds,
                "bearing": pos.bearing,
                "progress": pos.progress,
                "departed": pos.departed,
                "route_type": pos.route_type,
                "shape_coords": shape_coords_json,
                "scheduled_departure": _fmt_time(first_dep),
                "scheduled_arrival": _fmt_time(last_arr),
                "origin_stop": origin_stop,
                "total_stops": total_stops,
            }

            feature_id = await self.upsert_feature(
                source_id=source_id,
                domain="transit",
                geometry_wkt=wkt,
                properties=properties,
            )

            observations.append(
                Observation(
                    feature_id=feature_id,
                    domain="transit",
                    values={
                        "trip_id": pos.trip_id,
                        "route_id": pos.route_id,
                        "delay_seconds": pos.delay_seconds,
                    },
                    timestamp=now_utc,
                    source_id=source_id,
                )
            )

        # 7. Persist to transit_positions
        if observations:
            await self.persist(observations)

        # 8. Clean up stale bus-pos features that are no longer active
        await self._cleanup_old_features(active_source_ids)

        await self._update_staleness()
        logger.info(
            "BusInterpolationConnector: interpolated %d bus positions.",
            len(observations),
        )

    async def _download_cached_gtfs(self, url: str) -> bytes | None:
        """Download GTFS zip, caching in /tmp for 24 hours.

        Tries the primary URL first. If it fails, tries the fallback URL from
        config (``gtfs_url_fallback``). Adds ``follow_redirects`` and a
        ``User-Agent`` header for resilience against server-side blocks.
        """
        # Use shared cache path with GTFSConnector
        cache_path = Path("/tmp/gtfs_cache.zip")

        if cache_path.exists():
            age = time.time() - cache_path.stat().st_mtime
            if age < _GTFS_CACHE_MAX_AGE:
                logger.debug("Using cached GTFS zip: %s (age=%ds)", cache_path, int(age))
                return cache_path.read_bytes()

        # Build list of URLs to try (primary + optional fallback)
        urls_to_try = [url]
        fallback = self.config.config.get("gtfs_url_fallback", "")
        if fallback and fallback != url:
            urls_to_try.append(fallback)

        import httpx

        headers = {"User-Agent": "CityDataPlatform/2.0"}

        for attempt_url in urls_to_try:
            try:
                async with httpx.AsyncClient(
                    timeout=600.0,
                    follow_redirects=True,
                    headers=headers,
                ) as client:
                    r = await client.get(attempt_url)
                    r.raise_for_status()
                    data = r.content

                if not data:
                    logger.error("Empty GTFS response from %s", attempt_url)
                    continue

                if len(data) < 1000:
                    logger.warning(
                        "GTFS response from %s is suspiciously small (%d bytes), "
                        "possibly an error page — trying next URL.",
                        attempt_url,
                        len(data),
                    )
                    continue

                logger.info("Successfully downloaded GTFS zip from %s (%d bytes)", attempt_url, len(data))
                cache_path.write_bytes(data)
                return data
            except Exception as exc:
                logger.warning("Failed to download GTFS zip from %s: %s", attempt_url, exc)
                continue

        # All URLs failed — fall back to stale cache if available
        if cache_path.exists():
            logger.warning("Using stale GTFS cache after all download attempts failed.")
            return cache_path.read_bytes()

        logger.error("Could not download GTFS zip from any URL and no cache available.")
        return None

    def _parse_gtfs(self, zip_bytes: bytes):
        """Parse GTFS zip bytes with gtfs_kit. Called in a thread."""
        import gtfs_kit
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp.write(zip_bytes)
            tmp_path = Path(tmp.name)
        try:
            return gtfs_kit.read_feed(tmp_path, dist_units="km")
        except Exception as exc:
            logger.error("Failed to parse GTFS feed: %s", exc)
            return None
        finally:
            tmp_path.unlink(missing_ok=True)

    def _get_active_service_ids(self, feed, today) -> set[str]:
        """Determine which service_ids are active for the given date."""
        active = set()
        weekday = today.strftime("%A").lower()  # monday, tuesday, etc.

        if hasattr(feed, "calendar") and feed.calendar is not None and not feed.calendar.empty:
            for row in feed.calendar.itertuples(index=False):
                start = getattr(row, "start_date", None)
                end = getattr(row, "end_date", None)
                if start and end:
                    # Parse dates if strings
                    if isinstance(start, str):
                        start = datetime.strptime(start, "%Y%m%d").date()
                    if isinstance(end, str):
                        end = datetime.strptime(end, "%Y%m%d").date()
                    if hasattr(start, 'date'):
                        start = start.date() if hasattr(start, 'date') else start
                    if hasattr(end, 'date'):
                        end = end.date() if hasattr(end, 'date') else end
                    if start <= today <= end:
                        if getattr(row, weekday, 0) == 1:
                            active.add(row.service_id)

        # calendar_dates overrides
        if hasattr(feed, "calendar_dates") and feed.calendar_dates is not None and not feed.calendar_dates.empty:
            for row in feed.calendar_dates.itertuples(index=False):
                d = row.date
                if isinstance(d, str):
                    d = datetime.strptime(d, "%Y%m%d").date()
                if hasattr(d, 'date'):
                    d = d.date() if callable(getattr(d, 'date', None)) else d
                if d == today:
                    if row.exception_type == 1:
                        active.add(row.service_id)
                    elif row.exception_type == 2:
                        active.discard(row.service_id)

        return active

    def _build_active_trips(
        self, feed, active_service_ids: set[str], now_secs: int,
    ) -> list[ActiveTrip]:
        """Build ActiveTrip objects for trips currently running."""
        bbox = self.town.bbox
        active_trips: list[ActiveTrip] = []

        if feed.trips is None or feed.trips.empty:
            return []
        if feed.stop_times is None or feed.stop_times.empty:
            return []

        def _safe_str(val: object) -> str:
            """Convert pandas value to str, handling NA/NaN/None."""
            if val is None:
                return ""
            s = str(val)
            if s in ("nan", "<NA>", "None", "NaT"):
                return ""
            return s

        # Build route lookup
        route_info: dict[str, tuple[str, str, int]] = {}  # route_id -> (short_name, long_name, route_type)
        if hasattr(feed, "routes") and feed.routes is not None and not feed.routes.empty:
            for row in feed.routes.itertuples(index=False):
                route_info[row.route_id] = (
                    _safe_str(getattr(row, "route_short_name", "")),
                    _safe_str(getattr(row, "route_long_name", "")),
                    int(getattr(row, "route_type", 3)),
                )

        # Build shapes lookup
        shape_coords_map: dict[str, list[tuple[float, float]]] = {}
        if hasattr(feed, "shapes") and feed.shapes is not None and not feed.shapes.empty:
            for shape_id, group in feed.shapes.groupby("shape_id"):
                pts = group.sort_values("shape_pt_sequence")
                coords = [
                    (float(r.shape_pt_lon), float(r.shape_pt_lat))
                    for r in pts.itertuples(index=False)
                ]
                # Filter: include if any point in bbox
                in_bbox = any(
                    bbox.lon_min <= lon <= bbox.lon_max and bbox.lat_min <= lat <= bbox.lat_max
                    for lon, lat in coords
                )
                if in_bbox:
                    shape_coords_map[shape_id] = coords

        # Build stop coordinate + name lookup FIRST (needed for pre-filter)
        stop_names: dict[str, str] = {}
        stop_coords: dict[str, tuple[float, float]] = {}
        if hasattr(feed, "stops") and feed.stops is not None and not feed.stops.empty:
            for row in feed.stops.itertuples(index=False):
                stop_names[row.stop_id] = getattr(row, "stop_name", row.stop_id)
                try:
                    stop_coords[row.stop_id] = (float(row.stop_lon), float(row.stop_lat))
                except (ValueError, TypeError):
                    pass

        # Pre-filter: find trip_ids that have at least one stop in Aalen bbox
        bbox_stop_ids = set()
        for sid, coord in stop_coords.items():
            if bbox.lon_min <= coord[0] <= bbox.lon_max and bbox.lat_min <= coord[1] <= bbox.lat_max:
                bbox_stop_ids.add(sid)
        logger.info("Stops in Aalen bbox: %d", len(bbox_stop_ids))

        # Find trip_ids that visit any bbox stop
        bbox_trip_ids = set()
        if bbox_stop_ids and feed.stop_times is not None:
            bbox_trip_ids = set(
                feed.stop_times[feed.stop_times.stop_id.isin(bbox_stop_ids)].trip_id.unique()
            )
        logger.info("Trips visiting Aalen stops: %d", len(bbox_trip_ids))

        # Filter to active services AND bbox trips only
        trips_df = feed.trips[
            feed.trips.service_id.isin(active_service_ids)
            & feed.trips.trip_id.isin(bbox_trip_ids)
        ]
        logger.info("Active trips in Aalen: %d", len(trips_df))

        has_shapes = bool(shape_coords_map)
        logger.info("Shape coords available: %s (%d shapes)", has_shapes, len(shape_coords_map))

        # Pre-group stop_times by trip_id for O(1) lookup (avoid O(N) scan per trip)
        aalen_trip_ids = set(trips_df.trip_id)
        st_filtered = feed.stop_times[feed.stop_times.trip_id.isin(aalen_trip_ids)].sort_values(
            ["trip_id", "stop_sequence"]
        )
        stop_times_by_trip: dict[str, list] = {}
        for row in st_filtered.itertuples(index=False):
            stop_times_by_trip.setdefault(row.trip_id, []).append(row)
        logger.info("Pre-grouped stop_times for %d trips", len(stop_times_by_trip))

        for trip_row in trips_df.itertuples(index=False):
            trip_id = trip_row.trip_id
            route_id = trip_row.route_id

            # Try to get shape coords
            shape_coords: list[tuple[float, float]] | None = None
            if has_shapes:
                raw_shape = getattr(trip_row, "shape_id", None)
                try:
                    shape_id = str(raw_shape) if raw_shape is not None and str(raw_shape) not in ("", "nan", "<NA>") else None
                except (ValueError, TypeError):
                    shape_id = None
                if shape_id and shape_id in shape_coords_map:
                    shape_coords = shape_coords_map[shape_id]

            # Get stop_times for this trip (from pre-grouped dict)
            trip_st_rows = stop_times_by_trip.get(trip_id, [])
            if not trip_st_rows:
                continue

            stop_time_list: list[tuple[str, int, int]] = []
            trip_stop_ids: list[str] = []
            for st_row in trip_st_rows:
                arr_str = getattr(st_row, "arrival_time", "00:00:00")
                dep_str = getattr(st_row, "departure_time", "00:00:00")
                arr_secs = self._time_str_to_seconds(arr_str)
                dep_secs = self._time_str_to_seconds(dep_str)
                stop_name = stop_names.get(st_row.stop_id, st_row.stop_id)
                stop_time_list.append((stop_name, arr_secs, dep_secs))
                trip_stop_ids.append(st_row.stop_id)

            if not stop_time_list:
                continue

            # If no shape, build coords from stop locations (straight-line between stops)
            if shape_coords is None:
                shape_coords = []
                for sid in trip_stop_ids:
                    if sid in stop_coords:
                        shape_coords.append(stop_coords[sid])
                if len(shape_coords) < 2:
                    continue

            first_dep = stop_time_list[0][2]
            last_arr = stop_time_list[-1][1]

            # Active if first departure <= now <= last arrival
            # Small pre-departure buffer (5 min) for showing buses about to depart,
            # minimal post-arrival buffer (60s) to avoid keeping completed trips visible
            if first_dep - 300 <= now_secs <= last_arr + 60:
                line_name, _, route_type = route_info.get(route_id, ("", "", 3))
                headsign = _safe_str(getattr(trip_row, "trip_headsign", ""))
                destination = headsign if headsign else stop_time_list[-1][0]

                active_trips.append(ActiveTrip(
                    trip_id=trip_id,
                    route_id=route_id,
                    line_name=line_name,
                    destination=destination,
                    stop_times=stop_time_list,
                    shape_coords=shape_coords,
                    delay_seconds=0,
                    route_type=route_type,
                ))

        return active_trips

    @staticmethod
    def _time_str_to_seconds(t: str) -> int:
        """Convert HH:MM:SS to seconds since midnight. Handles >24h GTFS times."""
        if not t or not isinstance(t, str):
            return 0
        parts = t.strip().split(":")
        if len(parts) != 3:
            return 0
        try:
            h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
            return h * 3600 + m * 60 + s
        except ValueError:
            return 0

    async def _fetch_delays(self, trip_ids: list[str]) -> dict[str, int]:
        """Query transit_positions for latest delay_seconds per trip_id."""
        if not trip_ids:
            return {}

        from app.db import AsyncSessionLocal
        from sqlalchemy import text

        delays: dict[str, int] = {}
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    text("""
                        SELECT DISTINCT ON (trip_id) trip_id, delay_seconds
                        FROM transit_positions
                        WHERE trip_id = ANY(:trip_ids)
                          AND delay_seconds IS NOT NULL
                          AND time > NOW() - INTERVAL '10 minutes'
                        ORDER BY trip_id, time DESC
                    """),
                    {"trip_ids": trip_ids},
                )
                for row in result.mappings():
                    delays[row["trip_id"]] = int(row["delay_seconds"])
        except Exception as exc:
            logger.warning("Could not fetch delays from DB: %s", exc)

        return delays

    async def _cleanup_old_features(self, active_source_ids: set[str]) -> None:
        """Remove bus-pos features whose trips are no longer active.

        Compares features in the DB with the current set of active source_ids.
        Any bus-pos feature NOT in the active set has its trip completed or
        route service ended — remove it so stale dots disappear from the map.
        """
        from app.db import AsyncSessionLocal
        from sqlalchemy import text

        if not active_source_ids:
            # No active buses — remove all bus-pos features for this town
            try:
                async with AsyncSessionLocal() as session:
                    result = await session.execute(
                        text(
                            "DELETE FROM features "
                            "WHERE town_id = :town_id "
                            "AND domain = 'transit' "
                            "AND source_id LIKE 'bus-pos:%'"
                        ),
                        {"town_id": self.town.id},
                    )
                    await session.commit()
                    deleted = result.rowcount
                    if deleted:
                        logger.info("Cleaned up all %d stale bus-pos features (no active trips).", deleted)
            except Exception as exc:
                logger.warning("Failed to clean up stale bus features: %s", exc)
            return

        try:
            async with AsyncSessionLocal() as session:
                # Get all current bus-pos source_ids for this town
                result = await session.execute(
                    text(
                        "SELECT source_id FROM features "
                        "WHERE town_id = :town_id "
                        "AND domain = 'transit' "
                        "AND source_id LIKE 'bus-pos:%'"
                    ),
                    {"town_id": self.town.id},
                )
                db_source_ids = {row[0] for row in result.fetchall()}

                # Find stale ones: in DB but not in current active set
                stale_ids = db_source_ids - active_source_ids
                if stale_ids:
                    await session.execute(
                        text(
                            "DELETE FROM features "
                            "WHERE town_id = :town_id "
                            "AND domain = 'transit' "
                            "AND source_id = ANY(:stale_ids)"
                        ),
                        {
                            "town_id": self.town.id,
                            "stale_ids": list(stale_ids),
                        },
                    )
                    await session.commit()
                    logger.info(
                        "Cleaned up %d stale bus-pos features (%d active remain).",
                        len(stale_ids), len(active_source_ids),
                    )
        except Exception as exc:
            logger.warning("Failed to clean up stale bus features: %s", exc)
