# backend/app/routers/layers.py
"""GET /api/layers/{domain} — spatial feature layer endpoint.

Returns a GeoJSON FeatureCollection for a given domain and town.
Uses PostGIS ST_AsGeoJSON() for geometry serialization.
"""
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db import get_db
from app.dependencies import get_current_town
from app.config import Town
from app.schemas.geojson import (
    Attribution,
    LayerResponse,
    VALID_DOMAINS,
    CONNECTOR_ATTRIBUTION,
    eaqi_from_readings,
)

router = APIRouter(tags=["layers"])


@router.get("/layers/{domain}", response_model=None)
async def get_layer(
    domain: str,
    town: str = Query(...),
    at: datetime | None = Query(None, description="Historical snapshot timestamp (ISO 8601). If omitted, returns latest readings."),
    feature_type: str | None = Query(None, description="Filter by feature_type (e.g. 'air_grid' for grid cells, 'sensor' for sensor points)."),
    db: AsyncSession = Depends(get_db),
    current_town: Town = Depends(get_current_town),
) -> dict:
    """Return a GeoJSON FeatureCollection for the given domain and town."""
    # Town validation must be first
    if town != current_town.id:
        raise HTTPException(status_code=404, detail=f"Unknown town: {town!r}")
    # Domain validation
    if domain not in VALID_DOMAINS:
        raise HTTPException(status_code=404, detail=f"Unknown domain: {domain!r}")

    rows: list = []
    last_updated: datetime | None = None

    # Normalize at param to timezone-aware UTC if provided as naive datetime
    at_aware: datetime | None = None
    if at is not None:
        at_aware = at.replace(tzinfo=timezone.utc) if at.tzinfo is None else at

    if domain == "transit":
        result = await db.execute(
            text("""
                SELECT
                    f.id::text                     AS id,
                    ST_AsGeoJSON(f.geometry)::text AS geometry,
                    f.properties,
                    f.source_id,
                    s.connector_class,
                    MAX(f.created_at)              AS last_updated
                FROM features f
                LEFT JOIN sources s ON s.town_id = f.town_id AND s.domain = f.domain
                WHERE f.town_id = :town_id
                  AND f.domain   = 'transit'
                GROUP BY f.id, f.geometry, f.properties, f.source_id, s.connector_class
            """),
            {"town_id": current_town.id},
        )
        rows = result.mappings().all()
        # Get last_updated from transit rows (created_at grouped as last_updated)
        for row in rows:
            row_ts = row.get("last_updated")
            if row_ts is not None:
                if last_updated is None or row_ts > last_updated:
                    last_updated = row_ts

    elif domain == "air_quality":
        # feature_type filter: "air_grid" returns only grid cells,
        # None or "sensor" returns only non-grid features (sensors).
        if feature_type == "air_grid":
            ft_filter = "AND f.properties->>'feature_type' = 'air_grid'"
        else:
            ft_filter = "AND f.properties->>'feature_type' IS DISTINCT FROM 'air_grid'"

        result = await db.execute(
            text(f"""
                SELECT
                    f.id::text                     AS id,
                    ST_AsGeoJSON(f.geometry)::text AS geometry,
                    f.properties,
                    f.source_id,
                    s.connector_class,
                    r.pm25, r.pm10, r.no2, r.o3, r.aqi,
                    r.time                         AS reading_time
                FROM features f
                LEFT JOIN sources s ON s.town_id = f.town_id AND s.domain = f.domain
                LEFT JOIN LATERAL (
                    SELECT pm25, pm10, no2, o3, aqi, time
                    FROM air_quality_readings
                    WHERE feature_id = f.id
                      AND (:at IS NULL OR time <= :at)
                    ORDER BY time DESC
                    LIMIT 1
                ) r ON true
                WHERE f.town_id = :town_id
                  AND f.domain   = 'air_quality'
                  {ft_filter}
            """),
            {"town_id": current_town.id, "at": at_aware},
        )
        rows = result.mappings().all()
        # Get last_updated from reading_time
        for row in rows:
            row_ts = row.get("reading_time")
            if row_ts is not None:
                if last_updated is None or row_ts > last_updated:
                    last_updated = row_ts

    elif domain == "traffic":
        result = await db.execute(
            text("""
                SELECT
                    f.id::text                     AS id,
                    ST_AsGeoJSON(f.geometry)::text AS geometry,
                    f.properties,
                    f.source_id,
                    s.connector_class,
                    r.time                         AS reading_time,
                    r.vehicle_count_total, r.vehicle_count_hgv,
                    r.speed_avg_kmh, r.congestion_level
                FROM features f
                LEFT JOIN sources s ON s.town_id = f.town_id AND s.domain = f.domain
                LEFT JOIN LATERAL (
                    SELECT time, vehicle_count_total, vehicle_count_hgv,
                           speed_avg_kmh, congestion_level
                    FROM traffic_readings
                    WHERE feature_id = f.id
                      AND (:at IS NULL OR time <= :at)
                    ORDER BY time DESC
                    LIMIT 1
                ) r ON true
                WHERE f.town_id = :town_id
                  AND f.domain   = 'traffic'
            """),
            {"town_id": current_town.id, "at": at_aware},
        )
        rows = result.mappings().all()
        # Get last_updated from reading_time
        for row in rows:
            row_ts = row.get("reading_time")
            if row_ts is not None:
                if last_updated is None or row_ts > last_updated:
                    last_updated = row_ts

    elif domain == "energy":
        # Energy layer = MaStR installations (features only, no time-series join)
        result = await db.execute(
            text("""
                SELECT
                    f.id::text                     AS id,
                    ST_AsGeoJSON(f.geometry)::text AS geometry,
                    f.properties,
                    f.source_id,
                    s.connector_class
                FROM features f
                LEFT JOIN sources s ON s.town_id = f.town_id AND s.domain = f.domain
                WHERE f.town_id = :town_id
                  AND f.domain   = 'energy'
            """),
            {"town_id": current_town.id},
        )
        rows = result.mappings().all()

    elif domain == "demographics":
        # Demographics features with latest readings joined via LATERAL
        result = await db.execute(
            text("""
                SELECT
                    f.id::text                     AS id,
                    ST_AsGeoJSON(f.geometry)::text AS geometry,
                    f.properties,
                    f.source_id,
                    s.connector_class,
                    r.values                       AS reading_values,
                    r.time                         AS reading_time
                FROM features f
                LEFT JOIN sources s ON s.town_id = f.town_id AND s.domain = f.domain
                LEFT JOIN LATERAL (
                    SELECT values, time
                    FROM demographics_readings
                    WHERE feature_id = f.id
                      AND (:at IS NULL OR time <= :at)
                    ORDER BY time DESC
                    LIMIT 1
                ) r ON true
                WHERE f.town_id = :town_id
                  AND f.domain   = 'demographics'
            """),
            {"town_id": current_town.id, "at": at_aware},
        )
        rows = result.mappings().all()
        # Get last_updated from reading_time
        for row in rows:
            row_ts = row.get("reading_time")
            if row_ts is not None:
                if last_updated is None or row_ts > last_updated:
                    last_updated = row_ts

    elif domain in ("community", "infrastructure"):
        # Community POIs and infrastructure (roadworks) — features only, no time-series join
        result = await db.execute(
            text("""
                SELECT
                    f.id::text                     AS id,
                    ST_AsGeoJSON(f.geometry)::text AS geometry,
                    f.properties,
                    f.source_id,
                    s.connector_class
                FROM features f
                LEFT JOIN sources s ON s.town_id = f.town_id AND s.domain = f.domain
                WHERE f.town_id = :town_id
                  AND f.domain   = :domain
            """),
            {"town_id": current_town.id, "domain": domain},
        )
        rows = result.mappings().all()

    else:
        # Generic: weather, water — plain features, no reading join
        result = await db.execute(
            text("""
                SELECT
                    f.id::text                     AS id,
                    ST_AsGeoJSON(f.geometry)::text AS geometry,
                    f.properties,
                    f.source_id,
                    s.connector_class
                FROM features f
                LEFT JOIN sources s ON s.town_id = f.town_id AND s.domain = f.domain
                WHERE f.town_id = :town_id
                  AND f.domain   = :domain
            """),
            {"town_id": current_town.id, "domain": domain},
        )
        rows = result.mappings().all()

    # Build GeoJSON features list
    features: list[dict] = []
    for row in rows:
        # Parse geometry from JSON string
        geom_str = row.get("geometry")
        geometry = json.loads(geom_str) if geom_str else None

        # Copy properties dict; may already be a dict or a JSON string
        props = row.get("properties") or {}
        if isinstance(props, str):
            props = json.loads(props)
        else:
            props = dict(props)

        # Inject traffic reading fields into properties
        if domain == "traffic":
            for field in ("vehicle_count_total", "vehicle_count_hgv", "speed_avg_kmh", "congestion_level"):
                val = row.get(field)
                if val is not None:
                    props[field] = val

        # Inject demographics reading values into properties
        if domain == "demographics":
            reading_vals = row.get("reading_values")
            if reading_vals:
                if isinstance(reading_vals, str):
                    reading_vals = json.loads(reading_vals)
                if isinstance(reading_vals, dict):
                    for k, v in reading_vals.items():
                        if v is not None:
                            props[k] = v

        # Inject EEA EAQI tier data for air_quality domain
        if domain == "air_quality":
            tier_idx, tier_label, tier_color = eaqi_from_readings(
                pm25=row.get("pm25"),
                pm10=row.get("pm10"),
                no2=row.get("no2"),
                o3=row.get("o3"),
            )
            props["aqi_tier"] = tier_label
            props["aqi_tier_index"] = tier_idx
            props["aqi_color"] = tier_color
            # Also include raw readings in properties if available
            for field in ("pm25", "pm10", "no2", "o3", "aqi"):
                val = row.get(field)
                if val is not None:
                    props[field] = val

        feature: dict = {
            "type": "Feature",
            "id": row.get("id"),
            "geometry": geometry,
            "properties": props,
        }
        features.append(feature)

    # Collect unique connector_class values for attribution
    seen_classes: set[str] = set()
    for row in rows:
        cc = row.get("connector_class")
        if cc and cc in CONNECTOR_ATTRIBUTION:
            seen_classes.add(cc)

    attributions: list[Attribution] = [
        Attribution(**CONNECTOR_ATTRIBUTION[cc]) for cc in sorted(seen_classes)
    ]

    return LayerResponse(
        features=features,
        attribution=attributions,
        last_updated=last_updated,
        town=current_town.id,
        domain=domain,
    ).model_dump(by_alias=True)
