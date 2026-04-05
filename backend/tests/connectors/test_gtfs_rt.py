"""GTFS-RT connector tests — uses fixture protobuf binary (no live feed required).

The live GTFS-RT URL for NVBW bwgesamt is unconfirmed (open question from RESEARCH.md).
Tests use a programmatically constructed minimal GTFS-RT feed to validate parsing logic.
"""
import pytest
from google.transit import gtfs_realtime_pb2
from app.connectors.gtfs_rt import GTFSRealtimeConnector
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
    obs = connector.normalize(raw)
    assert len(obs) == 1
    assert obs[0].values["trip_id"] == "trip-789"
    assert obs[0].values["delay_seconds"] == 120


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
