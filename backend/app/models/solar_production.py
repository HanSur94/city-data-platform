"""Pydantic models for solar production computation.

IrradianceFactor: computed irradiance multiplier from weather data.
SolarInstallation: MaStR solar installation with capacity and location.
"""
from pydantic import BaseModel


class IrradianceFactor(BaseModel):
    """Computed irradiance factor (0.0-1.0 multiplier) from weather data."""
    cloud_cover: float | None = None
    solar_j_cm2: float | None = None
    factor: float


class SolarInstallation(BaseModel):
    """A MaStR solar installation with capacity and coordinates."""
    feature_id: str
    capacity_kw: float
    lon: float
    lat: float
