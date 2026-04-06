# backend/app/schemas/responses.py
"""Response schemas for timeseries, KPI, and connector health endpoints."""
from datetime import datetime
from typing import Any
from pydantic import BaseModel


class TimeseriesPoint(BaseModel):
    time: datetime
    feature_id: str
    values: dict[str, Any]


class TimeseriesResponse(BaseModel):
    domain: str
    town: str
    start: datetime
    end: datetime
    count: int
    points: list[TimeseriesPoint]
    attribution: list[dict[str, str]]
    last_updated: datetime | None


class AirQualityKPI(BaseModel):
    current_aqi: float | None
    current_pm25: float | None
    current_pm10: float | None
    current_no2: float | None
    current_o3: float | None
    aqi_tier: str | None
    aqi_color: str | None
    last_updated: datetime | None


class WeatherKPI(BaseModel):
    temperature: float | None
    condition: str | None
    wind_speed: float | None
    icon: str | None
    last_updated: datetime | None


class TransitKPI(BaseModel):
    stop_count: int
    route_count: int
    last_updated: datetime | None


class TrafficKPI(BaseModel):
    active_roadworks: int
    flow_status: str | None  # "normal" | "elevated" | "congested" | None
    last_updated: datetime | None


class EnergyKPI(BaseModel):
    renewable_percent: float | None
    generation_mix: dict[str, float]  # source -> MW
    wholesale_price_eur_mwh: float | None
    last_updated: datetime | None


class DemographicsKPI(BaseModel):
    population: int | None
    population_year: int | None
    age_under_18_pct: float | None
    age_over_65_pct: float | None
    unemployment_rate: float | None
    last_updated: datetime | None


class WaterKPI(BaseModel):
    level_cm: float | None
    flow_m3s: float | None
    stage: int | None  # 0-4 warning stage
    trend: str | None  # "rising" | "falling" | "stable"
    gauge_name: str | None
    last_updated: datetime | None


class ParkingKPI(BaseModel):
    total_free: int | None          # sum of free_spots across all garages
    total_capacity: int | None      # sum of total_spots across all garages
    garage_count: int               # number of parking garages
    availability_pct: float | None  # (total_free / total_capacity) * 100
    last_updated: datetime | None


class KPIResponse(BaseModel):
    town: str
    air_quality: AirQualityKPI
    weather: WeatherKPI
    transit: TransitKPI
    traffic: TrafficKPI | None = None
    energy: EnergyKPI | None = None
    demographics: DemographicsKPI | None = None
    water: WaterKPI | None = None
    parking: ParkingKPI | None = None
    attribution: list[dict[str, str]]
    last_updated: datetime | None


class ConnectorHealthItem(BaseModel):
    id: str
    domain: str
    connector_class: str
    last_successful_fetch: datetime | None
    validation_error_count: int
    status: str  # "ok", "stale", "never_fetched"


class ConnectorHealthResponse(BaseModel):
    town: str
    connectors: list[ConnectorHealthItem]
    message: str | None = None


class AdminHealthItem(BaseModel):
    id: str
    domain: str
    connector_class: str
    last_successful_fetch: datetime | None
    validation_error_count: int
    status: str         # "green", "yellow", "red", "never_fetched"
    staleness_seconds: float | None  # seconds since last fetch
    poll_interval: int | None        # configured poll interval
    threshold_yellow: int
    threshold_red: int


class AdminHealthResponse(BaseModel):
    town: str
    town_display_name: str
    checked_at: datetime
    summary: dict[str, int]  # {"green": N, "yellow": N, "red": N, "never_fetched": N}
    connectors: list[AdminHealthItem]
