# backend/app/routers/timeseries.py
"""Timeseries router: GET /api/timeseries/{domain}

Returns time-ordered readings for a given domain and town within a date range.
Supports air_quality and weather domains. Other valid domains return empty results.
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db import get_db
from app.dependencies import get_current_town
from app.config import Town
from app.schemas.geojson import VALID_DOMAINS, CONNECTOR_ATTRIBUTION
from app.schemas.responses import TimeseriesResponse, TimeseriesPoint

router = APIRouter(tags=["timeseries"])

MAX_RANGE = timedelta(days=90)


@router.get("/timeseries/{domain}", response_model=TimeseriesResponse)
async def get_timeseries(
    domain: str,
    town: str = Query(...),
    start: datetime = Query(...),
    end: datetime = Query(...),
    db: AsyncSession = Depends(get_db),
    current_town: Town = Depends(get_current_town),
) -> TimeseriesResponse:
    """Return time-ordered timeseries readings for the given domain and town."""
    # Validation order per plan spec
    if town != current_town.id:
        raise HTTPException(status_code=404, detail=f"Town not found: {town}")

    if domain not in VALID_DOMAINS:
        raise HTTPException(status_code=404, detail=f"Unknown domain: {domain}")

    # Ensure datetimes are comparable (make both timezone-aware if needed)
    start_aware = start if start.tzinfo is not None else start.replace(tzinfo=timezone.utc)
    end_aware = end if end.tzinfo is not None else end.replace(tzinfo=timezone.utc)

    if end_aware - start_aware > MAX_RANGE:
        raise HTTPException(status_code=400, detail="Time range exceeds 90-day maximum")

    if start_aware >= end_aware:
        raise HTTPException(status_code=400, detail="start must be before end")

    points: list[TimeseriesPoint] = []

    if domain == "air_quality":
        result = await db.execute(
            text("""
                SELECT
                    r.time          AS time,
                    r.feature_id::text AS feature_id,
                    r.pm25, r.pm10, r.no2, r.o3, r.aqi
                FROM air_quality_readings r
                JOIN features f ON r.feature_id = f.id
                WHERE f.town_id = :town_id
                  AND r.time >= :start
                  AND r.time <  :end
                ORDER BY r.time ASC
                LIMIT 10000
            """),
            {"town_id": current_town.id, "start": start_aware, "end": end_aware},
        )
        rows = result.mappings().all()
        for row in rows:
            values = {
                k: v for k, v in {
                    "pm25": row["pm25"],
                    "pm10": row["pm10"],
                    "no2": row["no2"],
                    "o3": row["o3"],
                    "aqi": row["aqi"],
                }.items() if v is not None
            }
            points.append(TimeseriesPoint(
                time=row["time"],
                feature_id=row["feature_id"],
                values=values,
            ))

    elif domain == "weather":
        result = await db.execute(
            text("""
                SELECT
                    r.time, r.feature_id::text AS feature_id,
                    r.temperature, r.wind_speed, r.condition, r.icon,
                    r.observation_type
                FROM weather_readings r
                JOIN features f ON r.feature_id = f.id
                WHERE f.town_id = :town_id
                  AND r.time >= :start
                  AND r.time <  :end
                ORDER BY r.time ASC
                LIMIT 10000
            """),
            {"town_id": current_town.id, "start": start_aware, "end": end_aware},
        )
        rows = result.mappings().all()
        for row in rows:
            values = {
                k: v for k, v in {
                    "temperature": row["temperature"],
                    "wind_speed": row["wind_speed"],
                    "condition": row["condition"],
                    "icon": row["icon"],
                    "observation_type": row["observation_type"],
                }.items() if v is not None
            }
            points.append(TimeseriesPoint(
                time=row["time"],
                feature_id=row["feature_id"],
                values=values,
            ))

    elif domain == "traffic":
        result = await db.execute(
            text("""
                SELECT
                    r.time, r.feature_id::text AS feature_id,
                    r.vehicle_count_total, r.vehicle_count_hgv,
                    r.speed_avg_kmh, r.congestion_level
                FROM traffic_readings r
                JOIN features f ON r.feature_id = f.id
                WHERE f.town_id = :town_id
                  AND r.time >= :start
                  AND r.time <  :end
                ORDER BY r.time ASC
                LIMIT 10000
            """),
            {"town_id": current_town.id, "start": start_aware, "end": end_aware},
        )
        rows = result.mappings().all()
        for row in rows:
            values = {
                k: v for k, v in {
                    "vehicle_count_total": row["vehicle_count_total"],
                    "vehicle_count_hgv": row["vehicle_count_hgv"],
                    "speed_avg_kmh": row["speed_avg_kmh"],
                    "congestion_level": row["congestion_level"],
                }.items() if v is not None
            }
            points.append(TimeseriesPoint(
                time=row["time"],
                feature_id=row["feature_id"],
                values=values,
            ))

    elif domain == "energy":
        result = await db.execute(
            text("""
                SELECT
                    r.time, r.feature_id::text AS feature_id,
                    r.value_kw, r.source_type
                FROM energy_readings r
                WHERE r.time >= :start
                  AND r.time <  :end
                ORDER BY r.time ASC
                LIMIT 10000
            """),
            {"town_id": current_town.id, "start": start_aware, "end": end_aware},
        )
        rows = result.mappings().all()
        for row in rows:
            values = {
                k: v for k, v in {
                    "value_kw": row["value_kw"],
                    "source_type": row["source_type"],
                }.items() if v is not None
            }
            points.append(TimeseriesPoint(
                time=row["time"],
                feature_id=row["feature_id"],
                values=values,
            ))

    # Other domains (transit, water) — tables may be empty in Phase 3
    # Return empty response, no error.

    # Attribution: query sources table for this town+domain
    try:
        attr_result = await db.execute(
            text("""
                SELECT connector_class
                FROM sources
                WHERE town_id = :town_id
                  AND domain = :domain
            """),
            {"town_id": current_town.id, "domain": domain},
        )
        attr_rows = attr_result.mappings().all()
        attributions: list[dict[str, str]] = []
        seen: set[str] = set()
        for attr_row in attr_rows:
            cls = attr_row["connector_class"]
            if cls in CONNECTOR_ATTRIBUTION and cls not in seen:
                attributions.append(CONNECTOR_ATTRIBUTION[cls])
                seen.add(cls)
    except Exception:
        # Sources table may not exist in test environment
        attributions = []

    # last_updated: MAX time from result rows, or None if empty
    last_updated: datetime | None = None
    if points:
        last_updated = max(p.time for p in points)

    return TimeseriesResponse(
        domain=domain,
        town=current_town.id,
        start=start_aware,
        end=end_aware,
        count=len(points),
        points=points,
        attribution=attributions,
        last_updated=last_updated,
    )
