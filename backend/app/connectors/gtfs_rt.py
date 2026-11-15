"""GTFSRealtimeConnector: fetches and parses GTFS-RT protobuf feeds.

Handles vehicle positions and trip updates. The feed is Germany-wide, so only
data relevant to the town is stored:

* Vehicle positions are kept only when inside the town bbox.
* Trip updates are kept only when relevant to the town: the trip belongs to an
  in-bbox vehicle of the same feed, to a trip tracked by bus interpolation
  (``bus-pos:*`` features), or one of its stop_time_updates references a town
  stop (``stop:*`` features). With no relevance data nothing else is stored.
* Trip-update delays attach to ONE per-town placeholder feature
  (feature_type ``trip_update``, located at the bbox centre); the trip is
  identified by transit_positions.trip_id, which is what bus interpolation reads.

Upserts features first to obtain valid UUIDs for feature_id in
transit_positions — prevents UUID cast errors.

Gracefully skips when gtfs_rt_url is empty (URL not yet configured).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from google.transit import gtfs_realtime_pb2

from app.connectors.base import BaseConnector, Observation

logger = logging.getLogger(__name__)

# One placeholder feature per town carries all trip-update delay observations.
# Explicit semantic id avoids the misleading "stop_" prefix of compute_semantic_id.
TRIP_UPDATE_SOURCE_ID = "gtfs-rt:trip-updates"
TRIP_UPDATE_SEMANTIC_ID = "gtfs_rt_trip_updates"


class GTFSRealtimeConnector(BaseConnector):
    """Fetches GTFS-RT protobuf feed, parses vehicle positions and trip updates.

    Config keys:
        gtfs_rt_url (str): URL of the GTFS-RT protobuf endpoint.
                           If empty, the connector logs a warning and skips.

    Overrides run() to upsert features first (to get valid UUIDs), then calls
    normalize() with the feature_ids mapping, then calls persist().

    The transit_positions table requires feature_id to be a valid UUID
    referencing features(id). Raw trip_id strings cannot be used as feature_id.
    Only in-bbox vehicles and town-relevant trip updates are stored.
    """

    async def fetch(self) -> bytes:
        """Fetch raw GTFS-RT protobuf bytes.

        Returns b"" (empty bytes) when gtfs_rt_url is not configured (empty string).
        This signals to run() to skip the run gracefully — no exception raised.

        Raises:
            httpx.HTTPError: On network failure or non-2xx response.
            ValueError: If the server returns HTTP 200 with empty content.
        """
        gtfs_rt_url = self.config.config.get("gtfs_rt_url", "")
        if not gtfs_rt_url:
            logger.warning(
                "GTFSRealtimeConnector: gtfs_rt_url is not configured in aalen.yaml. "
                "Skipping this run. Set gtfs_rt_url in the connector config to enable live data."
            )
            return b""

        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                gtfs_rt_url,
                headers={"Accept": "application/x-protobuf"},
            )
            r.raise_for_status()
            if not r.content:
                raise ValueError(
                    f"Empty GTFS-RT payload from {gtfs_rt_url} (HTTP 200 with no content)"
                )
            return r.content

    def _in_bbox(self, lat: float, lon: float) -> bool:
        """True when the point lies inside (inclusive) the town bbox."""
        bb = self.town.bbox
        return bb.lon_min <= lon <= bb.lon_max and bb.lat_min <= lat <= bb.lat_max

    def _town_centre_wkt(self) -> str:
        """WKT point at the centre of the town bbox."""
        bb = self.town.bbox
        lon = (bb.lon_min + bb.lon_max) / 2
        lat = (bb.lat_min + bb.lat_max) / 2
        return f"POINT({lon} {lat})"

    def _select_entities(
        self,
        feed_msg: Any,
        relevant_stop_ids: set[str] | None,
        relevant_trip_ids: set[str] | None,
    ) -> tuple[list, list]:
        """Pick the town-relevant parts of a feed.

        Returns (vehicle_entities, trip_update_entities). The vehicle and
        trip_update parts of one entity are judged independently.
        """
        stops = relevant_stop_ids or set()
        trips = relevant_trip_ids or set()

        vehicles = [
            e
            for e in feed_msg.entity
            if e.HasField("vehicle")
            and e.vehicle.HasField("position")
            and self._in_bbox(e.vehicle.position.latitude, e.vehicle.position.longitude)
        ]
        vehicle_trips = {e.vehicle.trip.trip_id for e in vehicles if e.vehicle.trip.trip_id}

        def relevant(tu: Any) -> bool:
            trip_id = tu.trip.trip_id
            if trip_id and (trip_id in trips or trip_id in vehicle_trips):
                return True
            return any(
                stu.stop_id and stu.stop_id in stops for stu in tu.stop_time_update
            )

        trip_updates = [
            e for e in feed_msg.entity if e.HasField("trip_update") and relevant(e.trip_update)
        ]
        return vehicles, trip_updates

    def normalize(
        self,
        raw: bytes,
        feature_ids: dict[str, str] | None = None,
        *,
        trip_update_feature_id: str | None = None,
        relevant_stop_ids: set[str] | None = None,
        relevant_trip_ids: set[str] | None = None,
    ) -> list[Observation]:
        """Parse GTFS-RT FeedMessage. Returns [] on empty input.

        Args:
            raw: Raw protobuf bytes from fetch().
            feature_ids: Mapping from entity.id to UUID string (from upsert_feature).
                         If None (e.g. in unit tests), falls back to entity.id as
                         placeholder feature_id.
            trip_update_feature_id: UUID of the per-town trip-update placeholder
                         feature. Falls back to the entity.id mapping when None.
            relevant_stop_ids: Town stop ids; trip updates touching them are kept.
            relevant_trip_ids: Tracked trip ids; their trip updates are kept.
                         With both sets None/empty, only trip updates for trips
                         of in-bbox vehicles in the same feed are kept (fail-closed).

        Returns:
            List of Observation objects for in-bbox vehicle positions and
            relevant trip updates.
            Returns [] if raw is empty bytes (graceful no-op for unconfigured URL).
        """
        if not raw:
            return []

        feed_msg = gtfs_realtime_pb2.FeedMessage()
        feed_msg.ParseFromString(raw)

        fids = feature_ids or {}
        observations: list[Observation] = []
        ts = datetime.now(timezone.utc)

        vehicles, trip_updates = self._select_entities(
            feed_msg, relevant_stop_ids, relevant_trip_ids
        )

        for entity in vehicles:
            vp = entity.vehicle
            observations.append(
                Observation(
                    feature_id=fids.get(entity.id, entity.id),  # fallback for unit tests
                    domain="transit",
                    values={
                        "lat": float(vp.position.latitude),
                        "lon": float(vp.position.longitude),
                        "trip_id": vp.trip.trip_id,
                        "route_id": vp.trip.route_id,
                        "delay_seconds": None,
                    },
                    timestamp=ts,
                    source_id=entity.id,
                )
            )

        for entity in trip_updates:
            tu = entity.trip_update
            observations.append(
                Observation(
                    feature_id=trip_update_feature_id or fids.get(entity.id, entity.id),
                    domain="transit",
                    values={
                        "lat": None,
                        "lon": None,
                        "trip_id": tu.trip.trip_id,
                        "route_id": tu.trip.route_id,
                        "delay_seconds": tu.delay if tu.HasField("delay") else None,
                    },
                    timestamp=ts,
                    source_id=entity.id,
                )
            )

        return observations

    async def _load_relevance_sets(self) -> tuple[set[str], set[str]]:
        """Load (town stop ids, tracked trip ids) from the features table.

        Stop ids come from GTFSConnector features (``stop:{stop_id}``); trip ids
        from BusInterpolationConnector features (``bus-pos:{trip_id}``). Returns
        empty sets when the lookup fails.
        """
        from app.db import AsyncSessionLocal
        from sqlalchemy import text

        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    text(
                        "SELECT source_id, properties->>'trip_id' AS trip_id "
                        "FROM features "
                        "WHERE town_id = :town_id AND domain = 'transit' "
                        "AND (source_id LIKE 'stop:%' OR source_id LIKE 'bus-pos:%')"
                    ),
                    {"town_id": self.town.id},
                )
                rows = result.mappings().all()
        except Exception as exc:
            logger.warning("GTFSRealtimeConnector: could not load relevance sets: %s", exc)
            return set(), set()

        stop_ids: set[str] = set()
        trip_ids: set[str] = set()
        for row in rows:
            source_id = row.get("source_id") or ""
            if source_id.startswith("stop:"):
                stop_ids.add(source_id[len("stop:"):])
            elif source_id.startswith("bus-pos:") and row.get("trip_id"):
                trip_ids.add(row["trip_id"])
        return stop_ids, trip_ids

    async def run(self) -> None:
        """Full pipeline: fetch -> filter -> upsert features -> normalize -> persist -> staleness.

        Overrides BaseConnector.run() to upsert vehicle features first,
        obtaining valid UUID feature_ids before writing to transit_positions.
        Only in-bbox vehicles get features; all relevant trip updates share one
        per-town placeholder feature.

        This prevents UUID cast errors: transit_positions.feature_id is UUID,
        not a string — raw trip_id values cannot be inserted directly.
        """
        raw = await self.fetch()
        if not raw:
            return  # empty URL or empty response — skip gracefully

        feed_msg = gtfs_realtime_pb2.FeedMessage()
        feed_msg.ParseFromString(raw)

        stop_ids, trip_ids = await self._load_relevance_sets()
        vehicles, trip_updates = self._select_entities(feed_msg, stop_ids, trip_ids)

        total_vehicles = sum(1 for e in feed_msg.entity if e.HasField("vehicle"))
        total_updates = sum(1 for e in feed_msg.entity if e.HasField("trip_update"))
        logger.info(
            "GTFSRealtimeConnector: kept %d/%d vehicles, %d/%d trip updates%s",
            len(vehicles), total_vehicles, len(trip_updates), total_updates,
            " (no town stops or tracked trips loaded yet: trip updates limited "
            "to in-bbox vehicle trips)" if not stop_ids and not trip_ids else "",
        )

        features_to_upsert: list[tuple[str, str, str, dict]] = []
        entity_source_ids: dict[str, str] = {}  # entity.id -> source_id
        for entity in vehicles:
            vp = entity.vehicle
            source_id = f"vehicle:{entity.id}"
            features_to_upsert.append((
                source_id,
                "transit",
                f"POINT({vp.position.longitude} {vp.position.latitude})",
                {
                    "feature_type": "bus_position",
                    "trip_id": vp.trip.trip_id,
                    "route_id": vp.trip.route_id,
                },
            ))
            entity_source_ids[entity.id] = source_id

        feature_ids: dict[str, str] = {}
        if features_to_upsert:
            feature_ids_map = await self.batch_upsert_features(features_to_upsert)
            feature_ids = {
                eid: feature_ids_map[src_id]
                for eid, src_id in entity_source_ids.items()
            }

        trip_update_feature_id: str | None = None
        if trip_updates:
            trip_update_feature_id = await self.upsert_feature(
                source_id=TRIP_UPDATE_SOURCE_ID,
                domain="transit",
                geometry_wkt=self._town_centre_wkt(),
                properties={"feature_type": "trip_update", "source": "gtfs-rt"},
                semantic_id=TRIP_UPDATE_SEMANTIC_ID,
            )

        observations = self.normalize(
            raw,
            feature_ids=feature_ids,
            trip_update_feature_id=trip_update_feature_id,
            relevant_stop_ids=stop_ids,
            relevant_trip_ids=trip_ids,
        )
        await self.persist(observations)
        await self._update_staleness()
