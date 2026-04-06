"""BusInterpolationConnector: interpolates bus positions from GTFS static + RT delays.

Stub — implementation follows in TDD GREEN phase.
"""
from __future__ import annotations

from app.connectors.base import BaseConnector
from app.models.bus_interpolation import ActiveTrip, BusPosition


def shape_walk(
    shape_coords: list[tuple[float, float]],
    progress: float,
) -> tuple[float, float, float]:
    """Walk along a LineString shape at the given progress fraction.

    Stub — not yet implemented.
    """
    raise NotImplementedError("shape_walk not yet implemented")


def interpolate_position(
    trip: ActiveTrip,
    now_seconds_since_midnight: int,
) -> BusPosition | None:
    """Calculate interpolated bus position for an active trip.

    Stub — not yet implemented.
    """
    raise NotImplementedError("interpolate_position not yet implemented")


class BusInterpolationConnector(BaseConnector):
    """Computation connector: interpolates bus positions from GTFS schedule + RT delay."""

    async def fetch(self):
        raise NotImplementedError

    def normalize(self, raw):
        raise NotImplementedError
