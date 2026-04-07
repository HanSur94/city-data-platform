"""Feature registry API endpoints.

- GET /api/features/search — search features by name, address, or ID
- GET /api/features/{feature_id}/data — per-feature data aggregation

Returns feature info (properties, geometry, semantic_id) plus the latest
observation from each domain that has data for this feature, queried from
the cross-domain feature_observations VIEW.

Accepts both UUID and semantic_id as the feature_id path parameter.
"""
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db import get_db
from app.dependencies import get_current_town
from app.config import Town

router = APIRouter(tags=["features"])


def _is_uuid(value: str) -> bool:
    """Check if a string looks like a UUID (36 chars with dashes)."""
    return len(value) == 36 and value.count("-") == 4


@router.get("/features/search")
async def search_features(
    q: str = Query(..., min_length=2),
    town: str = Query(...),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_town: Town = Depends(get_current_town),
) -> list[dict[str, Any]]:
    """Search features by name, address, semantic_id, or source_id.

    Returns an array of matching features with id, semantic_id, domain,
    name, and geometry coordinates.
    """
    if town != current_town.id:
        raise HTTPException(status_code=404, detail=f"Unknown town: {town!r}")

    pattern = f"%{q}%"
    result = await db.execute(
        text(
            "SELECT id::text, semantic_id, domain, source_id, "
            "ST_AsGeoJSON(geometry)::text AS geometry, "
            "properties "
            "FROM features "
            "WHERE town_id = :town_id "
            "AND ( "
            "  properties->>'name' ILIKE :q "
            "  OR properties->>'address' ILIKE :q "
            "  OR properties->>'stop_name' ILIKE :q "
            "  OR semantic_id ILIKE :q "
            "  OR source_id ILIKE :q "
            ") "
            "LIMIT :limit"
        ),
        {"town_id": current_town.id, "q": pattern, "limit": limit},
    )
    rows = result.mappings().all()

    results: list[dict[str, Any]] = []
    for row in rows:
        geom = row["geometry"]
        if isinstance(geom, str):
            geom = json.loads(geom)

        props = row["properties"]
        if isinstance(props, str):
            props = json.loads(props)
        props = props or {}

        # Extract name: try 'name', then 'stop_name', then source_id
        name = props.get("name") or props.get("stop_name") or row["source_id"] or "Unbekannt"

        # Extract centroid from geometry (Point -> direct, others -> first coordinate)
        lon, lat = 0.0, 0.0
        if geom:
            coords = geom.get("coordinates")
            if geom.get("type") == "Point" and coords:
                lon, lat = coords[0], coords[1]
            elif coords:
                # For LineString/Polygon, take the first coordinate
                flat = coords
                while isinstance(flat, list) and flat and isinstance(flat[0], list):
                    flat = flat[0]
                if flat and len(flat) >= 2:
                    lon, lat = flat[0], flat[1]

        results.append({
            "id": row["id"],
            "semantic_id": row["semantic_id"],
            "domain": row["domain"],
            "name": name,
            "longitude": lon,
            "latitude": lat,
        })

    return results


@router.get("/features/at")
async def get_feature_at_point(
    lng: float = Query(...),
    lat: float = Query(...),
    town: str = Query(...),
    radius_m: float = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_town: Town = Depends(get_current_town),
) -> dict[str, Any] | None:
    """Find the nearest feature to a point (lng, lat) within radius_m meters.

    Used for reverse-lookup when clicking a building on the map (vector tile
    features don't carry our semantic_id). Returns the same shape as
    /features/{feature_id}/data, or null if no feature found.
    """
    if town != current_town.id:
        raise HTTPException(status_code=404, detail=f"Unknown town: {town!r}")

    result = await db.execute(
        text(
            "SELECT id::text, domain, semantic_id, source_id, properties, "
            "ST_AsGeoJSON(geometry)::text AS geometry "
            "FROM features "
            "WHERE town_id = :town_id "
            "AND ST_DWithin(geometry::geography, "
            "  ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, :radius) "
            "ORDER BY geometry::geography <-> "
            "  ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography "
            "LIMIT 1"
        ),
        {"town_id": current_town.id, "lng": lng, "lat": lat, "radius": radius_m},
    )
    row = result.mappings().first()

    if row is None:
        return None

    feature_uuid = row["id"]

    # Get latest observation per domain
    obs_result = await db.execute(
        text(
            "SELECT DISTINCT ON (domain) domain, timestamp, values "
            "FROM feature_observations "
            "WHERE feature_id = CAST(:fid AS uuid) "
            "ORDER BY domain, timestamp DESC"
        ),
        {"fid": feature_uuid},
    )
    obs_rows = obs_result.mappings().all()

    observations: dict[str, Any] = {}
    for obs in obs_rows:
        values = obs["values"]
        if isinstance(values, str):
            values = json.loads(values)
        observations[obs["domain"]] = {
            "timestamp": obs["timestamp"].isoformat() if obs["timestamp"] else None,
            "values": values,
        }

    geometry = row["geometry"]
    if isinstance(geometry, str):
        geometry = json.loads(geometry)

    properties = row["properties"]
    if isinstance(properties, str):
        properties = json.loads(properties)

    return {
        "feature_id": feature_uuid,
        "semantic_id": row["semantic_id"],
        "domain": row["domain"],
        "properties": properties or {},
        "geometry": geometry,
        "observations": observations,
    }


@router.get("/features/{feature_id}/data")
async def get_feature_data(
    feature_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return feature info + latest observation per domain.

    The feature_id can be either a UUID string or a semantic_id string.
    Returns 404 if the feature is not found.

    Response shape:
        {
            "feature_id": "uuid-here",
            "semantic_id": "bldg_DEBWAL330000aBcD",
            "domain": "buildings",
            "properties": { ... },
            "geometry": { GeoJSON },
            "observations": {
                "energy": { "timestamp": "...", "values": { ... } },
                "air_quality": { "timestamp": "...", "values": { ... } }
            }
        }
    """
    # Resolve feature by UUID or semantic_id
    if _is_uuid(feature_id):
        query = text(
            "SELECT id, domain, semantic_id, properties, "
            "ST_AsGeoJSON(geometry)::json AS geometry "
            "FROM features WHERE id = CAST(:fid AS uuid)"
        )
    else:
        query = text(
            "SELECT id, domain, semantic_id, properties, "
            "ST_AsGeoJSON(geometry)::json AS geometry "
            "FROM features WHERE semantic_id = :fid"
        )

    result = await db.execute(query, {"fid": feature_id})
    row = result.mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Feature not found")

    feature_uuid = str(row["id"])

    # Get latest observation per domain using DISTINCT ON
    obs_result = await db.execute(
        text(
            "SELECT DISTINCT ON (domain) domain, timestamp, values "
            "FROM feature_observations "
            "WHERE feature_id = CAST(:fid AS uuid) "
            "ORDER BY domain, timestamp DESC"
        ),
        {"fid": feature_uuid},
    )
    obs_rows = obs_result.mappings().all()

    observations: dict[str, Any] = {}
    for obs in obs_rows:
        values = obs["values"]
        # Handle case where values might be a string (JSON) rather than dict
        if isinstance(values, str):
            values = json.loads(values)
        observations[obs["domain"]] = {
            "timestamp": obs["timestamp"].isoformat() if obs["timestamp"] else None,
            "values": values,
        }

    # Build geometry dict
    geometry = row["geometry"]
    if isinstance(geometry, str):
        geometry = json.loads(geometry)

    # Build properties dict
    properties = row["properties"]
    if isinstance(properties, str):
        properties = json.loads(properties)

    return {
        "feature_id": feature_uuid,
        "semantic_id": row["semantic_id"],
        "domain": row["domain"],
        "properties": properties or {},
        "geometry": geometry,
        "observations": observations,
    }
