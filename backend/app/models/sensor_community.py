"""Pydantic model for Sensor.community air quality readings.

Validates sensor readings from the Sensor.community API, extracting
PM10 (P1) and PM2.5 (P2) from the sensordatavalues array.
"""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, model_validator


class SensorReading(BaseModel):
    """A validated sensor reading from the Sensor.community API.

    Fields:
        sensor_id: Unique sensor identifier from sensor.community
        sensor_type: Sensor model name (e.g. "SDS011", "SPS30")
        lat: Latitude of the sensor location
        lon: Longitude of the sensor location
        pm10: PM10 concentration in µg/m³ (P1 value) or None if unavailable
        pm25: PM2.5 concentration in µg/m³ (P2 value) or None if unavailable
    """
    sensor_id: int
    sensor_type: str
    lat: float
    lon: float
    pm10: float | None = None
    pm25: float | None = None

    @model_validator(mode="before")
    @classmethod
    def parse_sensor_entry(cls, data: Any) -> dict:
        """Parse a raw Sensor.community API entry into model fields.

        Extracts P1 (PM10) and P2 (PM2.5) from the sensordatavalues array.
        Missing or non-parseable values become None.
        """
        if not isinstance(data, dict):
            return data

        sensor = data.get("sensor", {})
        sensor_type_obj = sensor.get("sensor_type", {})
        location = data.get("location", {})

        pm10: float | None = None
        pm25: float | None = None
        for entry in data.get("sensordatavalues", []):
            vtype = entry.get("value_type", "")
            raw_val = entry.get("value")
            try:
                val = float(raw_val) if raw_val is not None else None
            except (TypeError, ValueError):
                val = None
            if vtype == "P1":
                pm10 = val
            elif vtype == "P2":
                pm25 = val

        try:
            lat = float(location.get("latitude", 0))
            lon = float(location.get("longitude", 0))
        except (TypeError, ValueError):
            lat = 0.0
            lon = 0.0

        return {
            "sensor_id": sensor.get("id"),
            "sensor_type": sensor_type_obj.get("name", ""),
            "lat": lat,
            "lon": lon,
            "pm10": pm10,
            "pm25": pm25,
        }
