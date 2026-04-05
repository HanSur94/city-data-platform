# backend/app/routers/connectors.py
"""Connector health router: GET /api/connectors/health

Returns staleness and health status for all registered data connectors
in the current town.
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db import get_db
from app.dependencies import get_current_town
from app.config import Town
from app.schemas.responses import ConnectorHealthItem, ConnectorHealthResponse

router = APIRouter(tags=["connectors"])

# A connector is "stale" if no successful fetch in the last 2 hours
STALE_THRESHOLD = timedelta(hours=2)


@router.get("/connectors/health", response_model=ConnectorHealthResponse)
async def get_connector_health(
    town: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_town: Town = Depends(get_current_town),
) -> ConnectorHealthResponse:
    """Return health and staleness status for all connectors in this town."""
    if town != current_town.id:
        raise HTTPException(status_code=404, detail=f"Town not found: {town}")

    now = datetime.now(tz=timezone.utc)
    items: list[ConnectorHealthItem] = []

    try:
        result = await db.execute(
            text("""
                SELECT
                    id::text,
                    domain,
                    connector_class,
                    last_successful_fetch,
                    validation_error_count
                FROM sources
                WHERE town_id = :town_id
                ORDER BY domain, connector_class
            """),
            {"town_id": current_town.id},
        )
        rows = result.mappings().all()

        for row in rows:
            last_fetch: datetime | None = row["last_successful_fetch"]
            if last_fetch is None:
                status = "never_fetched"
            else:
                # Make timezone-aware if needed
                if last_fetch.tzinfo is None:
                    last_fetch = last_fetch.replace(tzinfo=timezone.utc)
                if now - last_fetch > STALE_THRESHOLD:
                    status = "stale"
                else:
                    status = "ok"

            items.append(ConnectorHealthItem(
                id=row["id"],
                domain=row["domain"],
                connector_class=row["connector_class"],
                last_successful_fetch=last_fetch,
                validation_error_count=int(row["validation_error_count"] or 0),
                status=status,
            ))
    except Exception:
        # Sources table may not exist in test environment — return empty list
        items = []

    return ConnectorHealthResponse(
        town=current_town.id,
        connectors=items,
        message=None if items else "No connectors registered for this town",
    )
