"""Models for air quality grid interpolation."""
from pydantic import BaseModel


class GridCell(BaseModel):
    """A single grid cell with interpolated pollutant values."""
    lon: float
    lat: float
    pm25: float | None = None
    pm10: float | None = None
    no2: float | None = None
    o3: float | None = None


class SensorReading(BaseModel):
    """A sensor reading with location and pollutant values."""
    feature_id: str
    lon: float
    lat: float
    pm25: float | None = None
    pm10: float | None = None
    no2: float | None = None
    o3: float | None = None
