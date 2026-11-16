"""Pydantic model for parking garage occupancy data.

Validates scraped parking data from Stadtwerke Aalen before connector processing.
"""
from __future__ import annotations

from pydantic import BaseModel, field_validator


class ParkingGarage(BaseModel):
    """Validated parking garage occupancy data.

    The Stadtwerke page publishes free spaces and an open state only; capacity
    (total_spots) and occupancy_pct are filled in when a capacity is known.
    """

    name: str
    free_spots: int
    total_spots: int | None = None
    occupancy_pct: float | None = None  # computed: (total - free) / total * 100
    is_open: bool | None = None
    status_text: str | None = None

    @field_validator("free_spots")
    @classmethod
    def free_spots_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("free_spots must be >= 0")
        return v

    @field_validator("total_spots")
    @classmethod
    def total_spots_positive(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("total_spots must be > 0")
        return v
