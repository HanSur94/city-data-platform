"""Pydantic models for the PEGELONLINE REST API response.

PEGELONLINE is the German federal water level service (WSV/BfG).
License: Datenlizenz Deutschland – Zero – Version 2.0

API endpoint:
    GET https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations.json
        ?waters=NECKAR&includeTimeseries=true&includeCurrentMeasurement=true
"""
from __future__ import annotations

from pydantic import BaseModel


class PegelonlineCurrentMeasurement(BaseModel):
    """Represents the current measurement for a single timeseries."""

    timestamp: str  # ISO 8601 string from API, e.g. "2026-04-06T01:30:00+02:00"
    value: float | None = None


class PegelonlineTimeseries(BaseModel):
    """A single timeseries for a station (e.g. W=water level, Q=discharge)."""

    shortname: str  # "W" = water level in cm, "Q" = discharge in m3/s
    unit: str       # "cm" for W
    currentMeasurement: PegelonlineCurrentMeasurement | None = None


class PegelonlineWater(BaseModel):
    """Water body information for a station."""

    longname: str  # e.g. "NECKAR"


class PegelonlineStation(BaseModel):
    """A single PEGELONLINE gauging station with its timeseries data."""

    uuid: str
    shortname: str
    water: PegelonlineWater
    latitude: float
    longitude: float
    timeseries: list[PegelonlineTimeseries] = []

    def current_level_cm(self) -> float | None:
        """Return current water level in cm, or None if unavailable.

        Looks for the first timeseries with shortname="W" and a non-None
        currentMeasurement. Returns None if not found.
        """
        for ts in self.timeseries:
            if ts.shortname == "W" and ts.currentMeasurement is not None:
                return ts.currentMeasurement.value
        return None

    def current_timestamp(self) -> str | None:
        """Return the ISO timestamp string of the current W measurement, or None."""
        for ts in self.timeseries:
            if ts.shortname == "W" and ts.currentMeasurement is not None:
                return ts.currentMeasurement.timestamp
        return None
