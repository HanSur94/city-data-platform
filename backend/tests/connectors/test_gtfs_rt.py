"""GTFS-RT connector tests — uses fixture protobuf binary (no live feed required).

The live GTFS-RT URL for NVBW bwgesamt is unconfirmed (open question from RESEARCH.md).
Tests use a programmatically constructed minimal GTFS-RT feed to validate parsing logic.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.transit import gtfs_realtime_pb2
from app.connectors.gtfs_rt import GTFSRealtimeConnector, TRIP_UPDATE_SOURCE_ID
from app.config import ConnectorConfig


def make_test_feed() -> bytes:
    """Create a minimal GTFS-RT FeedMessage with one VehiclePosition."""
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = 1712345678
    entity = feed.entity.add()
    entity.id = "test-vehicle-1"
    entity.vehicle.trip.trip_id = "trip-123"
    entity.vehicle.trip.route_id = "route-456"
    entity.vehicle.position.latitude = 48.84
    entity.vehicle.position.longitude = 10.09
    return feed.SerializeToString()


def make_trip_update_feed() -> bytes:
    """Create a minimal GTFS-RT FeedMessage with one TripUpdate."""
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = 1712345678
    entity = feed.entity.add()
    entity.id = "test-trip-1"
    entity.trip_update.trip.trip_id = "trip-789"
    entity.trip_update.trip.route_id = "route-101"
    entity.trip_update.delay = 120  # 2 minutes late
    return feed.SerializeToString()


@pytest.fixture
def gtfs_rt_config_with_url():
    return ConnectorConfig(
        connector_class="GTFSRealtimeConnector",
        poll_interval_seconds=30,
        enabled=True,
        config={"gtfs_rt_url": "https://example.com/gtfs-rt"},
    )


@pytest.fixture
def gtfs_rt_config_no_url():
    return ConnectorConfig(
        connector_class="GTFSRealtimeConnector",
        poll_interval_seconds=30,
        enabled=True,
        config={"gtfs_rt_url": ""},  # empty = URL not configured
    )


@pytest.fixture
def connector(gtfs_rt_config_with_url, aalen_town):
    return GTFSRealtimeConnector(config=gtfs_rt_config_with_url, town=aalen_town)


def test_normalize_vehicle_position(connector):
    raw = make_test_feed()
    obs = connector.normalize(raw)
    assert len(obs) == 1
    assert obs[0].domain == "transit"
    assert obs[0].values["trip_id"] == "trip-123"
    assert obs[0].values["route_id"] == "route-456"
    assert abs(obs[0].values["lat"] - 48.84) < 0.001
    assert abs(obs[0].values["lon"] - 10.09) < 0.001


def test_normalize_trip_update(connector):
    raw = make_trip_update_feed()
    obs = connector.normalize(raw, relevant_trip_ids={"trip-789"})
    assert len(obs) == 1
    assert obs[0].values["trip_id"] == "trip-789"
    assert obs[0].values["delay_seconds"] == 120


def test_normalize_trip_update_irrelevant_dropped(connector):
    """Fail-closed: without relevance data a trip update is not stored."""
    obs = connector.normalize(make_trip_update_feed())
    assert obs == []


def test_normalize_drops_vehicle_outside_bbox(connector):
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    berlin = feed.entity.add()
    berlin.id = "berlin"
    berlin.vehicle.trip.trip_id = "t-berlin"
    berlin.vehicle.position.latitude = 52.52
    berlin.vehicle.position.longitude = 13.405
    nopos = feed.entity.add()
    nopos.id = "nopos"
    nopos.vehicle.trip.trip_id = "t-nopos"
    assert connector.normalize(feed.SerializeToString()) == []


def _mixed_feed() -> bytes:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"

    def vehicle(eid, trip, lat, lon):
        e = feed.entity.add()
        e.id = eid
        e.vehicle.trip.trip_id = trip
        e.vehicle.trip.route_id = "r1"
        e.vehicle.position.latitude = lat
        e.vehicle.position.longitude = lon

    def trip_update(eid, trip, delay, stop_id=None):
        e = feed.entity.add()
        e.id = eid
        e.trip_update.trip.trip_id = trip
        e.trip_update.trip.route_id = "r1"
        e.trip_update.delay = delay
        if stop_id:
            stu = e.trip_update.stop_time_update.add()
            stu.stop_id = stop_id

    vehicle("e1", "T-in", 48.84, 10.09)
    vehicle("e2", "T-out", 52.52, 13.405)
    trip_update("u-stop", "T-stop", 60, stop_id="S-aalen")
    trip_update("u-tracked", "T-tracked", 120)
    trip_update("u-in", "T-in", 30)
    trip_update("u-far", "T-far", 300, stop_id="S-elsewhere")
    trip_update("u-out", "T-out", 10)
    return feed.SerializeToString()


@pytest.mark.asyncio
async def test_run_filters_and_uses_single_placeholder(connector):
    raw = _mixed_feed()
    upserted: list[list] = []

    async def fake_batch(features):
        upserted.append(features)
        return {f[0]: "uuid-" + f[0] for f in features}

    with (
        patch.object(connector, "fetch", AsyncMock(return_value=raw)),
        patch.object(
            connector,
            "_load_relevance_sets",
            AsyncMock(return_value=({"S-aalen"}, {"T-tracked"})),
        ),
        patch.object(connector, "batch_upsert_features", AsyncMock(side_effect=fake_batch)),
        patch.object(connector, "upsert_feature", AsyncMock(return_value="uuid-placeholder")) as up,
        patch.object(connector, "persist", AsyncMock()) as persist,
        patch.object(connector, "_update_staleness", AsyncMock()) as stale,
    ):
        await connector.run()

    batch_ids = [f[0] for batch in upserted for f in batch]
    assert batch_ids == ["vehicle:e1"]
    assert not any(sid.startswith("trip:") for sid in batch_ids)

    up.assert_awaited_once()
    kwargs = up.await_args.kwargs
    assert kwargs["source_id"] == TRIP_UPDATE_SOURCE_ID
    assert kwargs["domain"] == "transit"
    assert kwargs["properties"]["feature_type"] == "trip_update"
    wkt = kwargs["geometry_wkt"]
    assert wkt.startswith("POINT(")
    lon, lat = (float(v) for v in wkt[len("POINT("):-1].split())
    bb = connector.town.bbox
    assert bb.lon_min <= lon <= bb.lon_max
    assert bb.lat_min <= lat <= bb.lat_max

    observations = persist.await_args.args[0]
    by_trip = {o.values["trip_id"]: o for o in observations}
    assert set(by_trip) == {"T-in", "T-stop", "T-tracked"}
    # T-in appears as vehicle observation (lat/lon) and as trip update
    assert sum(1 for o in observations if o.values["trip_id"] == "T-in") == 2
    vehicle_obs = [o for o in observations if o.values["lat"] is not None]
    assert len(vehicle_obs) == 1 and vehicle_obs[0].feature_id == "uuid-vehicle:e1"
    delays = {
        o.values["trip_id"]: o.values["delay_seconds"]
        for o in observations
        if o.values["lat"] is None
    }
    assert delays == {"T-stop": 60, "T-tracked": 120, "T-in": 30}
    assert all(
        o.feature_id == "uuid-placeholder" for o in observations if o.values["lat"] is None
    )
    stale.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_skips_trip_updates_without_relevance(connector):
    raw = make_trip_update_feed()
    with (
        patch.object(connector, "fetch", AsyncMock(return_value=raw)),
        patch.object(connector, "_load_relevance_sets", AsyncMock(return_value=(set(), set()))),
        patch.object(connector, "batch_upsert_features", AsyncMock(return_value={})),
        patch.object(connector, "upsert_feature", AsyncMock()) as up,
        patch.object(connector, "persist", AsyncMock()) as persist,
        patch.object(connector, "_update_staleness", AsyncMock()) as stale,
    ):
        await connector.run()

    up.assert_not_awaited()
    for call in persist.await_args_list:
        assert call.args[0] == []
    stale.assert_awaited_once()


def _session_local(rows=None, raises=False):
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    if raises:
        session.execute = AsyncMock(side_effect=RuntimeError("db down"))
    else:
        result = MagicMock()
        result.mappings.return_value.all.return_value = rows
        session.execute = AsyncMock(return_value=result)
    return MagicMock(return_value=session)


@pytest.mark.asyncio
async def test_load_relevance_sets(connector):
    rows = [
        {"source_id": "stop:de:08136:1", "trip_id": None},
        {"source_id": "bus-pos:T1", "trip_id": "T1"},
        {"source_id": "bus-pos:T2", "trip_id": None},
    ]
    with patch("app.db.AsyncSessionLocal", _session_local(rows)):
        result = await connector._load_relevance_sets()
    assert result == ({"de:08136:1"}, {"T1"})

    with patch("app.db.AsyncSessionLocal", _session_local(raises=True)):
        result = await connector._load_relevance_sets()
    assert result == (set(), set())


def test_normalize_empty_bytes_returns_empty(connector):
    # b"" (actual empty bytes, NOT serialized FeedMessage) must return []
    # This simulates fetch() returning b"" when URL is not configured.
    obs = connector.normalize(b"")
    assert obs == []


def test_empty_url_connector_normalize_returns_empty(gtfs_rt_config_no_url, aalen_town):
    connector = GTFSRealtimeConnector(config=gtfs_rt_config_no_url, town=aalen_town)
    # normalize() with empty feed message = no entities
    empty_feed = gtfs_realtime_pb2.FeedMessage()
    empty_feed.header.gtfs_realtime_version = "2.0"
    obs = connector.normalize(empty_feed.SerializeToString())
    assert obs == []


def test_connector_importable():
    from app.connectors.gtfs_rt import GTFSRealtimeConnector
    assert GTFSRealtimeConnector.__name__ == "GTFSRealtimeConnector"
