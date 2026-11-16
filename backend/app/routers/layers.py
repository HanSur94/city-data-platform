# backend/app/routers/layers.py
"""GET /api/layers/{domain} — spatial feature layer endpoint.

Returns a GeoJSON FeatureCollection for a given domain and town.
Uses PostGIS ST_AsGeoJSON() for geometry serialization.
"""
import json
from datetime import datetime, timezone
from collections.abc import Mapping, Sequence
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db import get_db
from app.dependencies import get_current_town
from app.config import Town, TownBbox
from app.schemas.geojson import (
    Attribution,
    LayerResponse,
    VALID_DOMAINS,
    CONNECTOR_ATTRIBUTION,
    eaqi_from_readings,
)

router = APIRouter(tags=["layers"])

# Transit line geometries (GTFS shapes) are clipped to the town bbox and
# simplified before they leave the database. ~0.00005 deg is about 4-5 m at
# 49 deg N, below what a map line can show at city zoom levels.
SHAPE_SIMPLIFY_TOLERANCE_DEG = 0.00005
# Decimal places of line coordinates in the GeoJSON output (~1 m).
SHAPE_COORD_PRECISION = 5


def build_transit_layer_query(
    town_id: str, bbox: TownBbox, feature_type: str | None
) -> tuple[str, dict[str, Any]]:
    """Build the SQL + bind parameters for the transit layer.

    Line geometries (dimension 1) are clipped to the town bbox, reduced to
    LineString/MultiLineString parts, simplified and serialised at reduced
    coordinate precision; lines that lie outside the bbox are dropped. All
    other geometries (stops, bus positions) are returned exactly as stored.
    Every request-derived value is a bind parameter; the only formatted value
    is the module constant SHAPE_COORD_PRECISION.
    """
    params: dict[str, Any] = {
        "town_id": town_id,
        "lon_min": float(bbox.lon_min),
        "lat_min": float(bbox.lat_min),
        "lon_max": float(bbox.lon_max),
        "lat_max": float(bbox.lat_max),
        "tolerance": SHAPE_SIMPLIFY_TOLERANCE_DEG,
    }
    ft_filter = ""
    if feature_type:
        ft_filter = "AND f.properties->>'feature_type' = :feature_type"
        params["feature_type"] = feature_type
    precision = int(SHAPE_COORD_PRECISION)
    sql = f"""
        SELECT
            id,
            properties,
            source_id,
            last_updated,
            is_line,
            CASE
                WHEN is_line THEN ST_AsGeoJSON(geom, {precision})
                ELSE ST_AsGeoJSON(geom)
            END::text AS geometry
        FROM (
            SELECT
                f.id::text                                AS id,
                f.properties                              AS properties,
                f.source_id                               AS source_id,
                f.created_at                              AS last_updated,
                COALESCE(ST_Dimension(f.geometry) = 1, false) AS is_line,
                CASE
                    WHEN ST_Dimension(f.geometry) = 1 THEN
                        ST_SimplifyPreserveTopology(
                            ST_CollectionExtract(
                                ST_Intersection(
                                    f.geometry,
                                    ST_MakeEnvelope(:lon_min, :lat_min, :lon_max, :lat_max, 4326)
                                ),
                                2
                            ),
                            :tolerance
                        )
                    ELSE f.geometry
                END                                       AS geom
            FROM features f
            WHERE f.town_id = :town_id
              AND f.domain   = 'transit'
              {ft_filter}
        ) t
        WHERE NOT is_line OR NOT ST_IsEmpty(geom)
    """
    return sql, params


def dedupe_shape_rows(rows: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Collapse identical line rows (same route, colour and geometry).

    After clipping and simplification many trip-pattern shapes of one line are
    byte-identical. Each group keeps its smallest id (string comparison) at the
    position where the group first appeared. Rows without a truthy ``is_line``
    pass through unchanged and are never merged.
    """
    out: list[Mapping[str, Any]] = []
    group_pos: dict[tuple[Any, Any, Any], int] = {}
    for row in rows:
        if not row.get("is_line"):
            out.append(row)
            continue
        props = row.get("properties") or {}
        if isinstance(props, str):
            props = json.loads(props)
        key = (
            props.get("route_short_name"),
            props.get("route_type_color"),
            row.get("geometry"),
        )
        pos = group_pos.get(key)
        if pos is None:
            group_pos[key] = len(out)
            out.append(row)
        elif str(row.get("id")) < str(out[pos].get("id")):
            out[pos] = row
    return out


async def _fetch_attribution(
    db: AsyncSession, town_id: str, domain: str
) -> list[Attribution]:
    """Attribution list for the connectors registered for a town + domain.

    Kept separate from the feature queries so rows are never multiplied by the
    number of sources rows. Must be the last DB call of the request.
    """
    try:
        result = await db.execute(
            text(
                "SELECT DISTINCT connector_class FROM sources "
                "WHERE town_id = :town_id AND domain = :domain"
            ),
            {"town_id": town_id, "domain": domain},
        )
        classes = {
            row.get("connector_class") for row in result.mappings().all()
        }
        return [
            Attribution(**CONNECTOR_ATTRIBUTION[cc])
            for cc in sorted(c for c in classes if c in CONNECTOR_ATTRIBUTION)
        ]
    except Exception:
        # Sources table may not exist / be reachable; attribution is best-effort.
        return []


@router.get("/layers/{domain}", response_model=None)
async def get_layer(
    domain: str,
    town: str = Query(...),
    at: datetime | None = Query(None, description="Historical snapshot timestamp (ISO 8601). If omitted, returns latest readings."),
    feature_type: str | None = Query(None, description="Filter by feature_type (e.g. 'air_grid' for grid cells, 'sensor' for sensor points)."),
    source: str | None = Query(None, description="Filter infrastructure features by source (e.g. 'ocpdb' for live OCPDB chargers)."),
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
        transit_sql, transit_params = build_transit_layer_query(
            current_town.id, current_town.bbox, feature_type
        )
        result = await db.execute(text(transit_sql), transit_params)
        rows = result.mappings().all()
        # last_updated is the newest created_at over all rows (before de-duplication)
        for row in rows:
            row_ts = row.get("last_updated")
            if row_ts is not None:
                if last_updated is None or row_ts > last_updated:
                    last_updated = row_ts
        rows = dedupe_shape_rows(rows)

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
                    r.pm25, r.pm10, r.no2, r.o3, r.aqi,
                    r.time                         AS reading_time
                FROM features f
                LEFT JOIN LATERAL (
                    SELECT pm25, pm10, no2, o3, aqi, time
                    FROM air_quality_readings
                    WHERE feature_id = f.id
                      AND (CAST(:at AS timestamptz) IS NULL OR time <= CAST(:at AS timestamptz))
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
                    r.time                         AS reading_time,
                    r.vehicle_count_total, r.vehicle_count_hgv,
                    r.speed_avg_kmh, r.congestion_level
                FROM features f
                LEFT JOIN LATERAL (
                    SELECT time, vehicle_count_total, vehicle_count_hgv,
                           speed_avg_kmh, congestion_level
                    FROM traffic_readings
                    WHERE feature_id = f.id
                      AND (CAST(:at AS timestamptz) IS NULL OR time <= CAST(:at AS timestamptz))
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
                    f.source_id
                FROM features f
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
                    r.values                       AS reading_values,
                    r.time                         AS reading_time
                FROM features f
                LEFT JOIN LATERAL (
                    SELECT values, time
                    FROM demographics_readings
                    WHERE feature_id = f.id
                      AND (CAST(:at AS timestamptz) IS NULL OR time <= CAST(:at AS timestamptz))
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
        # Community POIs and infrastructure (roadworks, EV chargers) — features only
        # Optional source filter for infrastructure: e.g. source=ocpdb for live OCPDB chargers
        source_filter = ""
        params: dict[str, Any] = {"town_id": current_town.id, "domain": domain}
        if domain == "infrastructure" and source:
            # Match the explicit "source" property (e.g. 'ocpdb') or, for connectors
            # that only tag their features with a feature_type (cycling), that type.
            source_filter = (
                "AND (f.properties->>'source' = :source "
                "OR f.properties->>'feature_type' = :source)"
            )
            params["source"] = source
        result = await db.execute(
            text(f"""
                SELECT
                    f.id::text                     AS id,
                    ST_AsGeoJSON(f.geometry)::text AS geometry,
                    f.properties,
                    f.source_id
                FROM features f
                WHERE f.town_id = :town_id
                  AND f.domain   = :domain
                  {source_filter}
            """),
            params,
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
                    f.source_id
                FROM features f
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

    # Attribution: one separate query, executed last (a failure must not
    # abort the transaction before the feature query).
    attributions = await _fetch_attribution(db, current_town.id, domain)

    return LayerResponse(
        features=features,
        attribution=attributions,
        last_updated=last_updated,
        town=current_town.id,
        domain=domain,
    ).model_dump(by_alias=True)
