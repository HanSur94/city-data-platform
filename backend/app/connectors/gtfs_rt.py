"""GTFSRealtimeConnector: fetches and parses GTFS-RT protobuf feeds.

Handles vehicle positions and trip updates. Upserts features first to obtain
valid UUIDs for feature_id in transit_positions — prevents UUID cast errors.

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


class GTFSRealtimeConnector(BaseConnector):
    """Fetches GTFS-RT protobuf feed, parses vehicle positions and trip updates.

    Config keys:
        gtfs_rt_url (str): URL of the GTFS-RT protobuf endpoint.
                           If empty, the connector logs a warning and skips.

    Overrides run() to upsert features first (to get valid UUIDs), then calls
    normalize() with the feature_ids mapping, then calls persist().

    The transit_positions table requires feature_id to be a valid UUID
    referencing features(id). Raw trip_id strings cannot be used as feature_id.
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

    def normalize(
        self,
        raw: bytes,
        feature_ids: dict[str, str] | None = None,
    ) -> list[Observation]:
        """Parse GTFS-RT FeedMessage. Returns [] on empty input.

        Args:
            raw: Raw protobuf bytes from fetch().
            feature_ids: Mapping from entity.id to UUID string (from upsert_feature).
                         If None (e.g. in unit tests), falls back to entity.id as
                         placeholder feature_id.

        Returns:
            List of Observation objects for vehicle positions and trip updates.
            Returns [] if raw is empty bytes (graceful no-op for unconfigured URL).
        """
        if not raw:
            return []

        feed_msg = gtfs_realtime_pb2.FeedMessage()
        feed_msg.ParseFromString(raw)

        fids = feature_ids or {}
        observations: list[Observation] = []
        ts = datetime.now(timezone.utc)

        for entity in feed_msg.entity:
            fid = fids.get(entity.id, entity.id)  # fallback to entity.id for unit tests

            if entity.HasField("vehicle"):
                vp = entity.vehicle
                observations.append(
                    Observation(
                        feature_id=fid,
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

            if entity.HasField("trip_update"):
                tu = entity.trip_update
                observations.append(
                    Observation(
                        feature_id=fid,
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

    async def run(self) -> None:
        """Full pipeline: fetch -> upsert features -> normalize with UUIDs -> persist -> staleness.

        Overrides BaseConnector.run() to upsert vehicle/trip features first,
        obtaining valid UUID feature_ids before writing to transit_positions.

        This prevents UUID cast errors: transit_positions.feature_id is UUID,
        not a string — raw trip_id values cannot be inserted directly.
        """
        raw = await self.fetch()
        if not raw:
            return  # empty URL or empty response — skip gracefully

        # Parse protobuf to extract vehicle/trip entities
        feed_msg = gtfs_realtime_pb2.FeedMessage()
        feed_msg.ParseFromString(raw)

        # Upsert a feature for each unique vehicle/trip entity, get UUID
        feature_ids: dict[str, str] = {}  # entity.id -> UUID

        for entity in feed_msg.entity:
            if entity.HasField("vehicle"):
                vp = entity.vehicle
                lat = vp.position.latitude
                lon = vp.position.longitude
                source_id = f"vehicle:{entity.id}"
                feature_id = await self.upsert_feature(
                    source_id=source_id,
                    domain="transit",
                    geometry_wkt=f"POINT({lon} {lat})",
                    properties={
                        "feature_type": "bus_position",
                        "trip_id": vp.trip.trip_id,
                        "route_id": vp.trip.route_id,
                    },
                )
                feature_ids[entity.id] = feature_id

            elif entity.HasField("trip_update"):
                # TripUpdates don't have a position; upsert a placeholder feature
                source_id = f"trip:{entity.trip_update.trip.trip_id}"
                feature_id = await self.upsert_feature(
                    source_id=source_id,
                    domain="transit",
                    geometry_wkt="POINT(0 0)",  # no position for trip updates
                    properties={
                        "feature_type": "trip_update",
                        "trip_id": entity.trip_update.trip.trip_id,
                    },
                )
                feature_ids[entity.id] = feature_id

        # Normalize with real feature UUIDs
        observations = self.normalize(raw, feature_ids=feature_ids)
        await self.persist(observations)
        await self._update_staleness()
