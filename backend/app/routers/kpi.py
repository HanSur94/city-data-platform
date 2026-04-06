# backend/app/routers/kpi.py
"""KPI router: GET /api/kpi

Returns current KPI summary for a town including air quality, weather, and
transit indicators. Uses TimescaleDB last() aggregate for efficient current-value
queries.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db import get_db
from app.dependencies import get_current_town
from app.config import Town
from app.schemas.geojson import CONNECTOR_ATTRIBUTION, eaqi_from_readings
from app.schemas.responses import (
    KPIResponse,
    AirQualityKPI,
    WeatherKPI,
    TransitKPI,
    TrafficKPI,
    EnergyKPI,
    DemographicsKPI,
    WaterKPI,
)

router = APIRouter(tags=["kpi"])


@router.get("/kpi", response_model=KPIResponse)
async def get_kpi(
    town: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_town: Town = Depends(get_current_town),
) -> KPIResponse:
    """Return current KPI summary for the given town."""
    if town != current_town.id:
        raise HTTPException(status_code=404, detail=f"Town not found: {town}")

    # --- Air quality KPI ---
    aq_row = None
    try:
        aq_result = await db.execute(
            text("""
                SELECT
                    last(aqi,  time) AS current_aqi,
                    last(pm25, time) AS current_pm25,
                    last(pm10, time) AS current_pm10,
                    last(no2,  time) AS current_no2,
                    last(o3,   time) AS current_o3,
                    MAX(time)        AS last_updated
                FROM air_quality_readings r
                JOIN features f ON r.feature_id = f.id
                WHERE f.town_id = :town_id
                  AND r.time > NOW() - INTERVAL '24 hours'
            """),
            {"town_id": current_town.id},
        )
        aq_row = aq_result.mappings().first()
    except Exception:
        aq_row = None

    def _to_float(val: object) -> float | None:
        """Convert a DB value to float, returning None for non-numeric types."""
        if val is None:
            return None
        try:
            return float(val)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None

    _tier_idx, tier, color = eaqi_from_readings(
        pm25=_to_float(aq_row["current_pm25"] if aq_row else None),
        pm10=_to_float(aq_row["current_pm10"] if aq_row else None),
        no2=_to_float(aq_row["current_no2"] if aq_row else None),
        o3=_to_float(aq_row["current_o3"] if aq_row else None),
    )

    # --- Weather KPI ---
    wx_row = None
    try:
        wx_result = await db.execute(
            text("""
                SELECT
                    last(temperature, time) AS temperature,
                    last(condition,   time) AS condition,
                    last(wind_speed,  time) AS wind_speed,
                    last(icon,        time) AS icon,
                    MAX(time)               AS last_updated
                FROM weather_readings r
                JOIN features f ON r.feature_id = f.id
                WHERE f.town_id    = :town_id
                  AND r.observation_type = 'current'
                  AND r.time > NOW() - INTERVAL '48 hours'
            """),
            {"town_id": current_town.id},
        )
        wx_row = wx_result.mappings().first()
    except Exception:
        wx_row = None

    # --- Transit KPI ---
    tr_row = None
    try:
        tr_result = await db.execute(
            text("""
                SELECT
                    COUNT(*) FILTER (WHERE source_id LIKE 'stop:%') AS stop_count,
                    COUNT(*) FILTER (WHERE source_id LIKE 'shape:%') AS route_count,
                    MAX(created_at) AS last_updated
                FROM features
                WHERE town_id = :town_id
                  AND domain  = 'transit'
            """),
            {"town_id": current_town.id},
        )
        tr_row = tr_result.mappings().first()
    except Exception:
        tr_row = None

    # --- Traffic KPI ---
    traffic_kpi: TrafficKPI
    try:
        # Count active roadworks (Autobahn features with type="roadwork" or type="closure")
        roadworks_result = await db.execute(
            text("""
                SELECT COUNT(*) FROM features
                WHERE domain = 'traffic'
                  AND town_id = :town_id
                  AND properties->>'type' IN ('roadwork', 'closure')
            """),
            {"town_id": current_town.id},
        )
        active_roadworks = roadworks_result.scalar() or 0

        # Flow status: most common congestion level in last hour's readings
        flow_result = await db.execute(
            text("""
                SELECT r.congestion_level, COUNT(*) AS cnt
                FROM traffic_readings r
                INNER JOIN features f ON f.id = r.feature_id
                WHERE f.domain = 'traffic'
                  AND f.town_id = :town_id
                  AND r.time > NOW() - INTERVAL '1 hour'
                GROUP BY r.congestion_level
                ORDER BY cnt DESC
                LIMIT 1
            """),
            {"town_id": current_town.id},
        )
        flow_row = flow_result.first()
        flow_status_map = {"free": "normal", "moderate": "elevated", "congested": "congested"}
        flow_status = flow_status_map.get(flow_row[0]) if flow_row else None

        # Last updated from traffic_readings
        traffic_ts_result = await db.execute(
            text("""
                SELECT MAX(r.time)
                FROM traffic_readings r
                INNER JOIN features f ON f.id = r.feature_id
                WHERE f.domain = 'traffic' AND f.town_id = :town_id
            """),
            {"town_id": current_town.id},
        )
        traffic_last_updated = traffic_ts_result.scalar()
        traffic_kpi = TrafficKPI(
            active_roadworks=int(active_roadworks),
            flow_status=flow_status,
            last_updated=traffic_last_updated,
        )
    except Exception:
        traffic_kpi = TrafficKPI(active_roadworks=0, flow_status=None, last_updated=None)

    # --- Energy KPI ---
    energy_kpi: EnergyKPI
    try:
        # Latest generation mix from energy_readings (one row per source_type)
        mix_result = await db.execute(
            text("""
                SELECT DISTINCT ON (source_type) source_type, value_kw, time
                FROM energy_readings
                WHERE time > NOW() - INTERVAL '1 hour'
                ORDER BY source_type, time DESC
            """),
        )
        mix_rows = mix_result.fetchall()
        generation_mix = {
            row.source_type: row.value_kw / 1000
            for row in mix_rows
            if row.source_type != "price"
        }
        # Wholesale price stored as EUR/MWh in value_kw
        price_row = next((r for r in mix_rows if r.source_type == "price"), None)
        wholesale_price = price_row.value_kw if price_row else None
        # Renewable percent
        renewable_sources = {"solar", "wind_onshore", "wind_offshore", "hydro", "biomass"}
        total = sum(generation_mix.values()) if generation_mix else 0
        renewable = sum(v for k, v in generation_mix.items() if k in renewable_sources)
        renewable_pct: float | None = (renewable / total * 100) if total > 0 else None

        # Last updated
        energy_last_updated = max((r.time for r in mix_rows), default=None)
        energy_kpi = EnergyKPI(
            renewable_percent=renewable_pct,
            generation_mix=generation_mix,
            wholesale_price_eur_mwh=wholesale_price,
            last_updated=energy_last_updated,
        )
    except Exception:
        energy_kpi = EnergyKPI(
            renewable_percent=None,
            generation_mix={},
            wholesale_price_eur_mwh=None,
            last_updated=None,
        )

    # --- Demographics KPI ---
    demographics_kpi: DemographicsKPI | None = None
    try:
        # Query latest demographics_readings for each key indicator
        # Uses demographics_readings JSONB values column
        demo_result = await db.execute(
            text("""
                SELECT
                    dr.values,
                    dr.time AS reading_time
                FROM demographics_readings dr
                JOIN features f ON dr.feature_id = f.id
                WHERE f.town_id = :town_id
                  AND f.domain = 'demographics'
                  AND dr.time > NOW() - INTERVAL '8 days'
                ORDER BY dr.time DESC
                LIMIT 20
            """),
            {"town_id": current_town.id},
        )
        demo_rows = demo_result.fetchall()

        if demo_rows:
            # Merge all latest readings into a single values dict
            merged: dict = {}
            last_demo_time: datetime | None = None
            for row in demo_rows:
                vals = row.values if isinstance(row.values, dict) else {}
                for k, v in vals.items():
                    if k not in merged and v is not None:
                        merged[k] = v
                if last_demo_time is None and row.reading_time is not None:
                    last_demo_time = row.reading_time

            def _to_int(v: object) -> int | None:
                if v is None:
                    return None
                try:
                    return int(float(str(v)))
                except (TypeError, ValueError):
                    return None

            demographics_kpi = DemographicsKPI(
                population=_to_int(merged.get("population")),
                population_year=_to_int(merged.get("population_year")),
                age_under_18_pct=_to_float(merged.get("age_under_18_pct")),
                age_over_65_pct=_to_float(merged.get("age_over_65_pct")),
                unemployment_rate=_to_float(merged.get("unemployment_rate")),
                last_updated=last_demo_time,
            )
    except Exception:
        demographics_kpi = DemographicsKPI(
            population=None,
            population_year=None,
            age_under_18_pct=None,
            age_over_65_pct=None,
            unemployment_rate=None,
            last_updated=None,
        )

    # --- Water KPI ---
    water_kpi: WaterKPI | None = None
    try:
        water_result = await db.execute(
            text("""
                SELECT
                    last(r.level_cm, r.time) AS level_cm,
                    last(r.flow_m3s, r.time) AS flow_m3s,
                    MAX(r.time) AS last_updated,
                    f.properties
                FROM water_readings r
                JOIN features f ON r.feature_id = f.id
                WHERE f.town_id = :town_id
                  AND f.source_id LIKE 'lhp:%'
                  AND r.time > NOW() - INTERVAL '24 hours'
                GROUP BY f.id
                LIMIT 1
            """),
            {"town_id": current_town.id},
        )
        water_row = water_result.mappings().first()
        if water_row:
            props = water_row["properties"] if isinstance(water_row["properties"], dict) else {}
            water_kpi = WaterKPI(
                level_cm=_to_float(water_row["level_cm"]),
                flow_m3s=_to_float(water_row["flow_m3s"]),
                stage=props.get("stage"),
                trend=props.get("trend"),
                gauge_name=props.get("station_name"),
                last_updated=_to_datetime(water_row["last_updated"]),
            )
    except Exception:
        water_kpi = WaterKPI(
            level_cm=None, flow_m3s=None, stage=None,
            trend=None, gauge_name=None, last_updated=None,
        )

    # --- Attribution ---
    attributions: list[dict[str, str]] = []
    try:
        attr_result = await db.execute(
            text("""
                SELECT DISTINCT connector_class
                FROM sources
                WHERE town_id = :town_id
                ORDER BY connector_class
            """),
            {"town_id": current_town.id},
        )
        attr_rows = attr_result.mappings().all()
        seen: set[str] = set()
        for attr_row in attr_rows:
            cls = attr_row["connector_class"]
            if cls in CONNECTOR_ATTRIBUTION and cls not in seen:
                attributions.append(CONNECTOR_ATTRIBUTION[cls])
                seen.add(cls)
    except Exception:
        attributions = []

    def _to_datetime(val: object) -> datetime | None:
        """Return val if it's a datetime, else None."""
        return val if isinstance(val, datetime) else None  # type: ignore[return-value]

    # --- Overall last_updated: max of all domain timestamps ---
    candidate_times = [
        _to_datetime(aq_row["last_updated"]) if aq_row else None,
        _to_datetime(wx_row["last_updated"]) if wx_row else None,
        _to_datetime(tr_row["last_updated"]) if tr_row else None,
        traffic_kpi.last_updated,
        energy_kpi.last_updated,
        demographics_kpi.last_updated if demographics_kpi else None,
        water_kpi.last_updated if water_kpi else None,
    ]
    last_updated: datetime | None = max(
        filter(None, candidate_times),
        default=None,
    )

    try:
        air_quality_kpi = AirQualityKPI(
            current_aqi=_to_float(aq_row["current_aqi"] if aq_row else None),
            current_pm25=_to_float(aq_row["current_pm25"] if aq_row else None),
            current_pm10=_to_float(aq_row["current_pm10"] if aq_row else None),
            current_no2=_to_float(aq_row["current_no2"] if aq_row else None),
            current_o3=_to_float(aq_row["current_o3"] if aq_row else None),
            aqi_tier=tier,
            aqi_color=color,
            last_updated=_to_datetime(aq_row["last_updated"] if aq_row else None),
        )
    except Exception:
        air_quality_kpi = AirQualityKPI(
            current_aqi=None, current_pm25=None, current_pm10=None,
            current_no2=None, current_o3=None, aqi_tier=None, aqi_color=None,
            last_updated=None,
        )

    try:
        weather_kpi = WeatherKPI(
            temperature=_to_float(wx_row["temperature"] if wx_row else None),
            condition=wx_row["condition"] if wx_row and isinstance(wx_row["condition"], (str, type(None))) else None,
            wind_speed=_to_float(wx_row["wind_speed"] if wx_row else None),
            icon=wx_row["icon"] if wx_row and isinstance(wx_row["icon"], (str, type(None))) else None,
            last_updated=_to_datetime(wx_row["last_updated"] if wx_row else None),
        )
    except Exception:
        weather_kpi = WeatherKPI(
            temperature=None, condition=None, wind_speed=None,
            icon=None, last_updated=None,
        )

    try:
        transit_kpi = TransitKPI(
            stop_count=int(tr_row["stop_count"] or 0) if tr_row else 0,
            route_count=int(tr_row["route_count"] or 0) if tr_row else 0,
            last_updated=_to_datetime(tr_row["last_updated"] if tr_row else None),
        )
    except Exception:
        transit_kpi = TransitKPI(stop_count=0, route_count=0, last_updated=None)

    return KPIResponse(
        town=current_town.id,
        air_quality=air_quality_kpi,
        weather=weather_kpi,
        transit=transit_kpi,
        traffic=traffic_kpi,
        energy=energy_kpi,
        demographics=demographics_kpi,
        water=water_kpi,
        attribution=attributions,
        last_updated=last_updated,
    )
