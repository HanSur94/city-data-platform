"""Pydantic models for interpolated bus positions.

Used by BusInterpolationConnector to represent active trips and their
calculated positions along GTFS route shapes.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class BusPosition(BaseModel):
    """An interpolated bus position on a route shape.

    Fields:
        trip_id: GTFS trip identifier.
        route_id: GTFS route identifier.
        line_name: Short route name (e.g. "71").
        destination: Trip headsign or last stop name.
        next_stop: Name of the next upcoming stop.
        prev_stop: Name of the last departed stop (empty if bus hasn't departed yet).
        lat: Interpolated latitude (WGS 84).
        lon: Interpolated longitude (WGS 84).
        bearing: Heading in degrees (0-360, north=0).
        delay_seconds: Delay offset from GTFS-RT (0 if unknown).
        progress: Trip progress fraction (0.0 = at origin, 1.0 = at destination).
        departed: Whether the bus has departed from its first stop.
        route_type: GTFS route_type (0=tram, 1=subway, 2=rail, 3=bus, default 3).
    """

    trip_id: str
    route_id: str
    line_name: str = ""
    destination: str = ""
    next_stop: str = ""
    prev_stop: str = ""
    lat: float
    lon: float
    bearing: float = 0.0
    delay_seconds: int = 0
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    departed: bool = True
    route_type: int = 3


class ActiveTrip(BaseModel):
    """A currently active GTFS trip with schedule and shape data.

    Fields:
        trip_id: GTFS trip identifier.
        route_id: GTFS route identifier.
        line_name: Short route name from routes.route_short_name.
        destination: Trip headsign or name of the last stop.
        stop_times: Ordered list of (stop_name, arrival_secs, departure_secs)
                    where times are seconds since midnight.
        shape_coords: Ordered list of (lon, lat) tuples along the route shape.
        delay_seconds: Current delay in seconds (from GTFS-RT, default 0).
        route_type: GTFS route_type (0=tram, 1=subway, 2=rail, 3=bus, default 3).
    """

    trip_id: str
    route_id: str
    line_name: str = ""
    destination: str = ""
    stop_times: list[tuple[str, int, int]] = Field(default_factory=list)
    shape_coords: list[tuple[float, float]] = Field(default_factory=list)
    delay_seconds: int = 0
    route_type: int = 3
