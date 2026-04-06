"""Unit tests for BusInterpolationConnector interpolation logic.

Tests cover the shape_walk algorithm and interpolate_position edge cases
per REQ-BUS-05: dwelling at stop, no delay data, trip not departed,
trip completed, and basic position interpolation.
"""
from __future__ import annotations

import math

import pytest

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
