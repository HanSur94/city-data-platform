"""Pydantic model for parking garage occupancy data.

Validates scraped parking data from Stadtwerke Aalen before connector processing.
"""
from __future__ import annotations

from pydantic import BaseModel, field_validator


class ParkingGarage(BaseModel):
    """Validated parking garage occupancy data."""

    name: str
    free_spots: int
    total_spots: int
    occupancy_pct: float  # computed: (total - free) / total * 100

    @field_validator("free_spots")
    @classmethod
    def free_spots_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("free_spots must be >= 0")
        return v

    @field_validator("total_spots")
    @classmethod
    def total_spots_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("total_spots must be > 0")
        return v
