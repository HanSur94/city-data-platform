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
from app.schemas.geojson import CONNECTOR_ATTRIBUTION, aqi_tier
from app.schemas.responses import (
    KPIResponse,
    AirQualityKPI,
    WeatherKPI,
    TransitKPI,
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

    tier, color = aqi_tier(aq_row["current_aqi"] if aq_row else None)

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

    # --- Overall last_updated: max of all domain timestamps ---
    candidate_times = [
        aq_row["last_updated"] if aq_row else None,
        wx_row["last_updated"] if wx_row else None,
        tr_row["last_updated"] if tr_row else None,
    ]
    last_updated: datetime | None = max(
        filter(None, candidate_times),
        default=None,
    )

    return KPIResponse(
        town=current_town.id,
        air_quality=AirQualityKPI(
            current_aqi=aq_row["current_aqi"] if aq_row else None,
            current_pm25=aq_row["current_pm25"] if aq_row else None,
            current_pm10=aq_row["current_pm10"] if aq_row else None,
            current_no2=aq_row["current_no2"] if aq_row else None,
            current_o3=aq_row["current_o3"] if aq_row else None,
            aqi_tier=tier,
            aqi_color=color,
            last_updated=aq_row["last_updated"] if aq_row else None,
        ),
        weather=WeatherKPI(
            temperature=wx_row["temperature"] if wx_row else None,
            condition=wx_row["condition"] if wx_row else None,
            wind_speed=wx_row["wind_speed"] if wx_row else None,
            icon=wx_row["icon"] if wx_row else None,
            last_updated=wx_row["last_updated"] if wx_row else None,
        ),
        transit=TransitKPI(
            stop_count=int(tr_row["stop_count"] or 0) if tr_row else 0,
            route_count=int(tr_row["route_count"] or 0) if tr_row else 0,
            last_updated=tr_row["last_updated"] if tr_row else None,
        ),
        attribution=attributions,
        last_updated=last_updated,
    )
