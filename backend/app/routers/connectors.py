# backend/app/routers/connectors.py
"""GET /api/connectors/health — connector staleness health endpoint.

Returns staleness data (last_successful_fetch, validation_error_count, status)
for all sources registered for the current town.
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db import get_db
from app.dependencies import get_current_town
from app.config import Town
from app.schemas.responses import ConnectorHealthItem, ConnectorHealthResponse

router = APIRouter(tags=["connectors"])

STALE_THRESHOLD = timedelta(hours=2)


def _classify_status(last_fetch: datetime | None) -> str:
    """Classify connector staleness based on last successful fetch time."""
    if last_fetch is None:
        return "never_fetched"
    age = datetime.now(timezone.utc) - last_fetch
    return "stale" if age > STALE_THRESHOLD else "ok"


@router.get("/connectors/health", response_model=ConnectorHealthResponse)
async def get_connector_health(
    town: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_town: Town = Depends(get_current_town),
) -> ConnectorHealthResponse:
    """Return connector health/staleness data for the given town."""
    if town != current_town.id:
        raise HTTPException(status_code=404, detail=f"Unknown town: {town!r}")

    result = await db.execute(
        text("""
            SELECT id, domain, connector_class,
                   last_successful_fetch, validation_error_count
            FROM sources
            WHERE town_id = :town_id
            ORDER BY domain, connector_class
        """),
        {"town_id": current_town.id},
    )
    rows = result.mappings().all()

    if not rows:
        return ConnectorHealthResponse(
            town=current_town.id,
            connectors=[],
            message="No connector source rows found. Run the scheduler at least once.",
        )

    items = [
        ConnectorHealthItem(
            id=row["id"],
            domain=row["domain"],
            connector_class=row["connector_class"],
            last_successful_fetch=row["last_successful_fetch"],
            validation_error_count=row["validation_error_count"] or 0,
            status=_classify_status(row["last_successful_fetch"]),
        )
        for row in rows
    ]

    return ConnectorHealthResponse(town=current_town.id, connectors=items)
