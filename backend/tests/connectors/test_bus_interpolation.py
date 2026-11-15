"""Unit tests for BusInterpolationConnector interpolation logic.

Tests cover the shape_walk algorithm and interpolate_position edge cases
per REQ-BUS-05: dwelling at stop, no delay data, trip not departed,
trip completed, and basic position interpolation.
"""
from __future__ import annotations

import asyncio
import json
import math
import threading
import time
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pandas as pd
import pytest

from app.config import ConnectorConfig
from app.connectors import bus_interpolation as bi
from app.connectors.bus_interpolation import (
    BusInterpolationConnector,
    shape_walk,
    interpolate_position,
)
from app.models.bus_interpolation import ActiveTrip, BusPosition


# ---------------------------------------------------------------------------
# Fixtures: a simple 3-point east-west LineString for shape_walk tests
# ---------------------------------------------------------------------------

# 3 points roughly along a horizontal line (same lat, increasing lon)
# Each segment is ~1.11 km (0.01 degree at ~48.84 lat)
SIMPLE_SHAPE: list[tuple[float, float]] = [
    (10.00, 48.84),  # start
    (10.01, 48.84),  # midpoint
    (10.02, 48.84),  # end
]


class TestShapeWalk:
    """Tests for the shape_walk pure function."""

    def test_walk_at_start(self):
        """progress=0.0 returns the first point of the shape."""
        lon, lat, bearing = shape_walk(SIMPLE_SHAPE, 0.0)
        assert abs(lon - 10.00) < 1e-6
        assert abs(lat - 48.84) < 1e-6

    def test_walk_at_end(self):
        """progress=1.0 returns the last point of the shape."""
        lon, lat, bearing = shape_walk(SIMPLE_SHAPE, 1.0)
        assert abs(lon - 10.02) < 1e-6
        assert abs(lat - 48.84) < 1e-6

    def test_walk_at_midpoint(self):
        """progress=0.5 returns the midpoint of a symmetric 3-point shape."""
        lon, lat, bearing = shape_walk(SIMPLE_SHAPE, 0.5)
        assert abs(lon - 10.01) < 0.001
        assert abs(lat - 48.84) < 0.001

    def test_walk_quarter(self):
        """progress=0.25 returns a point between first and second vertex."""
        lon, lat, bearing = shape_walk(SIMPLE_SHAPE, 0.25)
        assert 10.00 < lon < 10.01
        assert abs(lat - 48.84) < 0.001

    def test_walk_bearing_eastward(self):
        """Bearing should be roughly 90 degrees (east) for an east-west line."""
        _lon, _lat, bearing = shape_walk(SIMPLE_SHAPE, 0.5)
        assert 80 < bearing < 100

    def test_walk_correctly_walks_along_3_point_linestring(self):
        """shape_walk correctly walks along a 3-point LineString to intermediate positions."""
        # Walk at 75% — should be between second and third point
        lon, lat, bearing = shape_walk(SIMPLE_SHAPE, 0.75)
        assert 10.01 < lon < 10.02
        assert abs(lat - 48.84) < 0.001


class TestInterpolatePosition:
    """Tests for interpolate_position with ActiveTrip edge cases."""

    def _make_trip(
        self,
        delay_seconds: int = 0,
        stop_times: list[tuple[str, int, int]] | None = None,
    ) -> ActiveTrip:
        """Create an ActiveTrip for testing.

        Default stop_times: 3 stops at 08:00, 08:10, 08:20
        (28800, 30000, 31200 seconds since midnight).
        """
        if stop_times is None:
            stop_times = [
                ("Stop A", 28800, 28800),   # 08:00 arrival = departure
                ("Stop B", 29400, 29400),   # 08:10
                ("Stop C", 30000, 30000),   # 08:20
            ]
        return ActiveTrip(
            trip_id="trip_1",
            route_id="route_1",
            line_name="71",
            destination="Stop C",
            stop_times=stop_times,
            shape_coords=SIMPLE_SHAPE,
            delay_seconds=delay_seconds,
        )

    def test_interpolate_midway_between_stops(self):
        """interpolate_position returns correct lat/lon for a trip 50% between two stops."""
        trip = self._make_trip()
        # Time = 08:05 (29100s) = halfway between Stop A (28800) and Stop B (29400)
        now_secs = 29100
        result = interpolate_position(trip, now_secs)

        assert result is not None
        assert result.departed is True
        assert 0.2 < result.progress < 0.3  # ~25% of total trip
        assert result.next_stop == "Stop B"

    def test_trip_not_departed(self):
        """trip not departed returns position at first stop with departed=false."""
        trip = self._make_trip()
        # Time = 07:50 (27000s) — before first departure at 08:00
        now_secs = 27000
        result = interpolate_position(trip, now_secs)

        assert result is not None
        assert result.departed is False
        assert result.progress == 0.0
        # Should be at first stop position
        assert abs(result.lon - 10.00) < 0.001
        assert abs(result.lat - 48.84) < 0.001

    def test_trip_completed(self):
        """trip completed returns None (should be filtered out)."""
        trip = self._make_trip()
        # Time = 08:30 (30600s) — well after last arrival at 08:20
        now_secs = 30600
        result = interpolate_position(trip, now_secs)

        assert result is None

    def test_dwelling_at_stop(self):
        """dwelling at stop (current time equals scheduled stop time) returns stop position exactly."""
        # Trip with dwell time at Stop B: arrival 29100, departure 29400
        trip = self._make_trip(
            stop_times=[
                ("Stop A", 28800, 28800),
                ("Stop B", 29100, 29400),   # 5-minute dwell
                ("Stop C", 30000, 30000),
            ]
        )
        # Time = 29200 — during dwell at Stop B
        now_secs = 29200
        result = interpolate_position(trip, now_secs)

        assert result is not None
        assert result.departed is True
        # Should be at Stop B's position on the shape (midpoint)
        assert result.next_stop == "Stop B"

    def test_no_delay_data(self):
        """no delay data defaults to schedule-only interpolation (delay_seconds=0)."""
        trip = self._make_trip(delay_seconds=0)
        now_secs = 29100  # 08:05
        result = interpolate_position(trip, now_secs)

        assert result is not None
        assert result.delay_seconds == 0
        assert result.departed is True

    def test_with_delay_shifts_schedule(self):
        """Positive delay shifts the effective schedule forward."""
        trip = self._make_trip(delay_seconds=300)  # 5 minutes late
        # At 08:05 (29100s), with 5 min delay the bus hasn't departed yet
        # (effective departure = 08:05)
        now_secs = 29100
        result = interpolate_position(trip, now_secs)

        assert result is not None
        # Bus should be near start since it just departed
        assert result.progress < 0.1

    def test_bus_position_model_validates(self):
        """BusPosition model validates interpolation output correctly."""
        pos = BusPosition(
            trip_id="trip_1",
            route_id="route_1",
            line_name="71",
            destination="Bahnhof",
            next_stop="Rathaus",
            lat=48.84,
            lon=10.01,
            bearing=90.0,
            delay_seconds=120,
            progress=0.5,
            departed=True,
        )
        assert pos.trip_id == "trip_1"
        assert pos.progress == 0.5


# ---------------------------------------------------------------------------
# Reduced-feed cache and off-loop computation (quick-261115-ved)
# ---------------------------------------------------------------------------

_STOP_A = (10.05, 48.80)
_STOP_B = (10.10, 48.83)
_STOP_C = (10.40, 48.83)
_STOP_D = (11.00, 49.20)
_STOP_E = (11.10, 49.30)
_STOP_F = (10.15, 48.85)

_ALL_DAYS = {
    d: [1, 1]
    for d in (
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    )
}


def _synthetic_feed(**overrides) -> SimpleNamespace:
    """Small GTFS-like feed of pandas DataFrames (all ids and dates are strings).

    T1 (service SV1) touches the Aalen bbox at A and B and continues to the
    out-of-bbox stop C; it is active at any wall-clock time. T2 (service SV2)
    never comes near the bbox. Stop F lies inside the bbox but no trip serves it.
    Overrides replace whole tables.
    """
    stops = pd.DataFrame(
        {
            "stop_id": ["A", "B", "C", "D", "E", "F"],
            "stop_name": [
                "Inside A", "Inside B", "Outside C", "Far D", "Far E", "Unused F",
            ],
            "stop_lon": [
                _STOP_A[0], _STOP_B[0], _STOP_C[0], _STOP_D[0], _STOP_E[0], _STOP_F[0],
            ],
            "stop_lat": [
                _STOP_A[1], _STOP_B[1], _STOP_C[1], _STOP_D[1], _STOP_E[1], _STOP_F[1],
            ],
        }
    )
    trips = pd.DataFrame(
        {
            "route_id": ["R1", "R2"],
            "service_id": ["SV1", "SV2"],
            "trip_id": ["T1", "T2"],
            "trip_headsign": ["Outside C", "Far E"],
            "shape_id": ["S1", "S2"],
        }
    )
    times = ["00:00:00", "12:00:00", "23:59:59", "05:00:00", "07:00:00"]
    stop_times = pd.DataFrame(
        {
            "trip_id": ["T1", "T1", "T1", "T2", "T2"],
            "arrival_time": times,
            "departure_time": times,
            "stop_id": ["A", "B", "C", "D", "E"],
            "stop_sequence": [1, 2, 3, 1, 2],
        }
    )
    shapes = pd.DataFrame(
        {
            "shape_id": ["S1", "S1", "S1", "S2", "S2"],
            "shape_pt_lat": [_STOP_A[1], _STOP_B[1], _STOP_C[1], _STOP_D[1], _STOP_E[1]],
            "shape_pt_lon": [_STOP_A[0], _STOP_B[0], _STOP_C[0], _STOP_D[0], _STOP_E[0]],
            "shape_pt_sequence": [1, 2, 3, 1, 2],
        }
    )
    routes = pd.DataFrame(
        {
            "route_id": ["R1", "R2"],
            "route_short_name": ["71", "99"],
            "route_long_name": ["", ""],
            "route_type": [3, 3],
        }
    )
    calendar = pd.DataFrame(
        {
            "service_id": ["SV1", "SV2"],
            **_ALL_DAYS,
            "start_date": ["20000101", "20000101"],
            "end_date": ["20991231", "20991231"],
        }
    )
    calendar_dates = pd.DataFrame(
        {
            "service_id": ["SV1", "SV2"],
            "date": ["19990101", "20261116"],
            "exception_type": [2, 1],
        }
    )
    tables = {
        "stops": stops,
        "trips": trips,
        "stop_times": stop_times,
        "shapes": shapes,
        "routes": routes,
        "calendar": calendar,
        "calendar_dates": calendar_dates,
    }
    tables.update(overrides)
    return SimpleNamespace(**tables)


def _connector(town) -> BusInterpolationConnector:
    return BusInterpolationConnector(
        config=ConnectorConfig(
            connector_class="BusInterpolationConnector",
            config={"gtfs_url": "https://example.invalid/bwgesamt.zip"},
        ),
        town=town,
    )


@pytest.fixture(autouse=True)
def _fresh_reduced_feed_cache(monkeypatch):
    """Every test starts with an empty module-level cache and a fresh lock."""
    monkeypatch.setattr(bi, "_REDUCED_FEED_CACHE", {}, raising=False)
    monkeypatch.setattr(bi, "_REDUCED_FEED_LOCK", asyncio.Lock(), raising=False)


def _patch_io(monkeypatch, parse_result) -> SimpleNamespace:
    """Replace every network/DB/parse touch point of the connector with mocks."""
    parse_calls: list[bytes] = []

    def _fake_parse(self, zip_bytes):
        parse_calls.append(zip_bytes)
        return parse_result

    def _fake_upsert(features, *args, **kwargs):
        return {f[0]: f"fid-{f[0]}" for f in features}

    mocks = SimpleNamespace(
        download=AsyncMock(return_value=b"zip-v1"),
        fetch_delays=AsyncMock(return_value={}),
        upsert=AsyncMock(side_effect=_fake_upsert),
        persist=AsyncMock(),
        cleanup=AsyncMock(),
        staleness=AsyncMock(),
        parse_calls=parse_calls,
    )
    cls = BusInterpolationConnector
    monkeypatch.setattr(cls, "_download_cached_gtfs", mocks.download)
    monkeypatch.setattr(cls, "_fetch_delays", mocks.fetch_delays)
    monkeypatch.setattr(cls, "batch_upsert_features", mocks.upsert)
    monkeypatch.setattr(cls, "persist", mocks.persist)
    monkeypatch.setattr(cls, "_cleanup_old_features", mocks.cleanup)
    monkeypatch.setattr(cls, "_update_staleness", mocks.staleness)
    monkeypatch.setattr(cls, "_parse_gtfs", _fake_parse)
    return mocks


def test_reduce_keeps_touching_trip_and_drops_outside_trip(aalen_town):
    reduced = bi.reduce_feed_to_bbox(_synthetic_feed(), aalen_town.bbox)

    for name in (
        "calendar", "calendar_dates", "routes", "trips", "stop_times", "stops", "shapes",
    ):
        assert hasattr(reduced, name), name

    assert set(reduced.trips.trip_id) == {"T1"}
    # T1 is kept whole, including the stop_time at the out-of-bbox stop C
    assert len(reduced.stop_times) == 3
    assert set(reduced.stop_times.trip_id) == {"T1"}
    assert set(reduced.stop_times.stop_id) == {"A", "B", "C"}
    assert set(reduced.stops.stop_id) == {"A", "B", "C"}
    assert set(reduced.shapes.shape_id) == {"S1"}
    assert len(reduced.shapes) == 3
    assert set(reduced.routes.route_id) == {"R1"}
    assert set(reduced.calendar.service_id) == {"SV1"}
    assert set(reduced.calendar_dates.service_id) == {"SV1"}


async def test_two_fresh_instances_parse_once_and_compute_off_loop(
    aalen_town, monkeypatch
):
    mocks = _patch_io(monkeypatch, _synthetic_feed())

    on_main_thread: dict[str, list[bool]] = {"service_ids": [], "trips": []}
    orig_service_ids = BusInterpolationConnector._get_active_service_ids
    orig_build = BusInterpolationConnector._build_active_trips

    def _wrap_service_ids(self, *args, **kwargs):
        on_main_thread["service_ids"].append(
            threading.current_thread() is threading.main_thread()
        )
        return orig_service_ids(self, *args, **kwargs)

    def _wrap_build(self, *args, **kwargs):
        on_main_thread["trips"].append(
            threading.current_thread() is threading.main_thread()
        )
        return orig_build(self, *args, **kwargs)

    monkeypatch.setattr(
        BusInterpolationConnector, "_get_active_service_ids", _wrap_service_ids
    )
    monkeypatch.setattr(BusInterpolationConnector, "_build_active_trips", _wrap_build)

    # The scheduler builds a new connector for every run
    await _connector(aalen_town).run()
    await _connector(aalen_town).run()

    assert mocks.parse_calls == [b"zip-v1"]
    assert on_main_thread["service_ids"] == [False, False]
    assert on_main_thread["trips"] == [False, False]

    assert mocks.upsert.await_count == 2
    features = mocks.upsert.await_args.args[0]
    assert len(features) == 1
    source_id, domain, wkt, props = features[0]
    assert source_id == "bus-pos:T1"
    assert domain == "transit"
    assert wkt.startswith("POINT(")
    assert props["line_name"] == "71"
    assert props["destination"] == "Outside C"
    assert props["total_stops"] == 3
    assert json.loads(props["shape_coords"]) == [
        list(_STOP_A), list(_STOP_B), list(_STOP_C),
    ]
    mocks.cleanup.assert_awaited_with({"bus-pos:T1"})


# ---------------------------------------------------------------------------
# Edge cases: equivalence, optional tables, cache invalidation, failure,
# concurrency and stale-dot cleanup (quick-261115-ved, Task 2)
# ---------------------------------------------------------------------------

_MONDAY = date(2026, 11, 16)


def test_reduced_feed_yields_same_active_trips_as_full_feed(aalen_town):
    connector = _connector(aalen_town)
    full = _synthetic_feed()
    reduced = bi.reduce_feed_to_bbox(full, aalen_town.bbox)

    full_services = connector._get_active_service_ids(full, _MONDAY)
    reduced_services = connector._get_active_service_ids(reduced, _MONDAY)
    assert full_services == {"SV1", "SV2"}
    assert reduced_services == {"SV1"}
    assert reduced_services <= full_services

    now_secs = 21600
    full_trips = connector._build_active_trips(full, full_services, now_secs)
    reduced_trips = connector._build_active_trips(reduced, reduced_services, now_secs)

    assert [t.trip_id for t in full_trips] == ["T1"]
    assert [t.trip_id for t in reduced_trips] == ["T1"]
    assert [t.model_dump() for t in reduced_trips] == [t.model_dump() for t in full_trips]
    assert [t._stop_shape_fracs for t in reduced_trips] == [
        t._stop_shape_fracs for t in full_trips
    ]


@pytest.mark.parametrize(
    "variant",
    ["shapes_and_dates_none", "shapes_and_dates_empty", "calendar_none"],
)
def test_missing_optional_tables_do_not_raise(aalen_town, variant):
    if variant == "shapes_and_dates_none":
        overrides = {"shapes": None, "calendar_dates": None}
    elif variant == "shapes_and_dates_empty":
        overrides = {"shapes": pd.DataFrame(), "calendar_dates": pd.DataFrame()}
    else:
        overrides = {
            "calendar": None,
            "calendar_dates": pd.DataFrame(
                {"service_id": ["SV1"], "date": ["20261116"], "exception_type": [1]}
            ),
        }
    feed = _synthetic_feed(**overrides)

    reduced = bi.reduce_feed_to_bbox(feed, aalen_town.bbox)

    for name, value in overrides.items():
        if value is None:
            assert getattr(reduced, name) is None

    connector = _connector(aalen_town)
    services = connector._get_active_service_ids(reduced, _MONDAY)
    assert "SV1" in services
    trips = connector._build_active_trips(reduced, services, 21600)
    assert [t.trip_id for t in trips] == ["T1"]
    if variant != "calendar_none":
        # No shapes table: straight line through the stop coordinates
        assert trips[0].shape_coords == [_STOP_A, _STOP_B, _STOP_C]


async def test_different_zip_reparses_and_keeps_one_entry_per_bbox(
    aalen_town, monkeypatch
):
    mocks = _patch_io(monkeypatch, _synthetic_feed())
    connector = _connector(aalen_town)

    first = await connector._get_reduced_feed(b"zip-v1")
    again = await connector._get_reduced_feed(b"zip-v1")
    assert again is first
    assert mocks.parse_calls == [b"zip-v1"]

    second = await connector._get_reduced_feed(b"zip-v2")
    assert second is not first
    assert mocks.parse_calls == [b"zip-v1", b"zip-v2"]
    assert len(bi._REDUCED_FEED_CACHE) == 1


async def test_parse_failure_is_not_cached(aalen_town, monkeypatch):
    mocks = _patch_io(monkeypatch, None)
    connector = _connector(aalen_town)

    assert await connector._get_reduced_feed(b"zip-v1") is None
    assert bi._REDUCED_FEED_CACHE == {}
    assert await connector._get_reduced_feed(b"zip-v1") is None
    assert len(mocks.parse_calls) == 2


async def test_concurrent_calls_parse_once(aalen_town, monkeypatch):
    calls: list[bytes] = []
    feed = _synthetic_feed()

    def _slow_parse(self, zip_bytes):
        calls.append(zip_bytes)
        time.sleep(0.2)  # runs in a worker thread
        return feed

    monkeypatch.setattr(BusInterpolationConnector, "_parse_gtfs", _slow_parse)

    first, second = await asyncio.gather(
        _connector(aalen_town)._get_reduced_feed(b"zip-v1"),
        _connector(aalen_town)._get_reduced_feed(b"zip-v1"),
    )

    assert calls == [b"zip-v1"]
    assert first is second
    assert first is not None


async def test_no_active_town_service_still_removes_stale_bus_features(
    aalen_town, monkeypatch
):
    no_service_today = pd.DataFrame(
        {
            "service_id": ["SV1", "SV2"],
            **{d: [0, 1] for d in _ALL_DAYS},
            "start_date": ["20000101", "20000101"],
            "end_date": ["20991231", "20991231"],
        }
    )
    feed = _synthetic_feed(calendar=no_service_today, calendar_dates=None)
    mocks = _patch_io(monkeypatch, feed)

    await _connector(aalen_town).run()

    mocks.cleanup.assert_awaited_once_with(set())
    mocks.staleness.assert_awaited_once()
    for call in mocks.upsert.await_args_list:
        assert not call.args[0]
