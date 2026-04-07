"""GET /api/features/{feature_id}/data — per-feature data aggregation endpoint.

Returns feature info (properties, geometry, semantic_id) plus the latest
observation from each domain that has data for this feature, queried from
the cross-domain feature_observations VIEW.

Accepts both UUID and semantic_id as the feature_id path parameter.
"""
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db import get_db

router = APIRouter(tags=["features"])


def _is_uuid(value: str) -> bool:
    """Check if a string looks like a UUID (36 chars with dashes)."""
    return len(value) == 36 and value.count("-") == 4


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
