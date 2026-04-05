"""Pydantic models for Bright Sky weather API responses.

BrightSkyWeather: current_weather endpoint response weather object.
BrightSkyForecastEntry: weather (forecast) endpoint response weather entry.

All numeric fields are float | None to safely handle missing data from DWD/Bright Sky.
wind_direction is typed as float | None (API returns integer degrees; cast is safe).
"""
from datetime import datetime
from pydantic import BaseModel


class BrightSkyWeather(BaseModel):
    """Current weather observation from Bright Sky current_weather endpoint."""
    timestamp: datetime
    temperature: float | None = None
    dew_point: float | None = None
    pressure_msl: float | None = None
    wind_speed: float | None = None
    wind_direction: float | None = None
    cloud_cover: float | None = None
    condition: str | None = None
    icon: str | None = None
    precipitation_10: float | None = None
    precipitation_30: float | None = None
    precipitation_60: float | None = None
    relative_humidity: float | None = None


class BrightSkyForecastEntry(BaseModel):
    """MOSMIX forecast entry from Bright Sky weather endpoint."""
    timestamp: datetime
    source_id: int
    temperature: float | None = None
    dew_point: float | None = None
    pressure_msl: float | None = None
    wind_speed: float | None = None
    wind_direction: float | None = None
    cloud_cover: float | None = None
    condition: str | None = None
    icon: str | None = None
    precipitation_10: float | None = None
    precipitation_30: float | None = None
    precipitation_60: float | None = None
    relative_humidity: float | None = None
