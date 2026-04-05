"""Pydantic model for UBA air quality measurement data.

Validates individual time-series measurements returned by the UBA API.
Negative readings are rejected (set to None) since negative pollutant
concentrations are physically impossible and indicate sensor/API errors.
"""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, field_validator


class UBAMeasurement(BaseModel):
    """A single UBA measurement for one component at one timestamp.

    Fields:
        station_id: UBA station identifier (e.g. 238 for Aalen DEBW029)
        component_id: UBA component identifier (1=PM10, 3=O3, 5=NO2, 9=PM2.5, etc.)
        date_end: End timestamp of the measurement interval
        value: Measured concentration (float) or None if missing/invalid
        index: UBA air quality index value (1-6) or None
    """
    station_id: int
    component_id: int
    date_end: datetime
    value: float | None
    index: int | None

    @field_validator("value", mode="before")
    @classmethod
    def reject_negative(cls, v: object) -> float | None:
        """Reject negative readings — physically impossible concentrations."""
        if v is None:
            return None
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        if f < 0:
            return None
        return f
