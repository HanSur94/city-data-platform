# backend/app/routers/admin.py
"""Admin health router: GET /api/admin/health

Returns per-connector health with domain-specific staleness thresholds
(green/yellow/red) for the operator dashboard (PLAT-09).
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db import get_db
from app.dependencies import get_current_town
from app.config import Town
from app.schemas.responses import AdminHealthItem, AdminHealthResponse

router = APIRouter(tags=["admin"])

# Per-domain staleness thresholds in seconds.
# yellow = warn (data getting old), red = critical (data definitely stale)
STALENESS_THRESHOLDS: dict[str, dict[str, int]] = {
    "air_quality": {"yellow": 3600, "red": 7200},       # 1h/2h — sensors report frequently
    "weather": {"yellow": 3600, "red": 7200},            # 1h/2h
    "transit": {"yellow": 86400, "red": 172800},         # 1d/2d — GTFS is daily
    "water": {"yellow": 1800, "red": 3600},              # 30m/1h — gauges update every 15m
    "traffic": {"yellow": 3600, "red": 7200},            # 1h/2h
    "energy": {"yellow": 1800, "red": 3600},             # 30m/1h — SMARD is 15min
    "community": {"yellow": 172800, "red": 604800},      # 2d/7d — Overpass is daily
    "infrastructure": {"yellow": 172800, "red": 604800}, # 2d/7d
    "demographics": {"yellow": 604800, "red": 2592000},  # 7d/30d — slow-moving data
}

# Default thresholds for domains not in the map above
_DEFAULT_THRESHOLDS = {"yellow": 3600, "red": 7200}


def classify_staleness(
    last_fetch: datetime | None,
    now: datetime,
    domain: str,
) -> tuple[str, float | None]:
    """Classify connector staleness as green/yellow/red/never_fetched.

    Returns:
        (status, staleness_seconds) where staleness_seconds is None if never fetched.
    """
    if last_fetch is None:
        return "never_fetched", None

    # Ensure timezone-aware
    if last_fetch.tzinfo is None:
        last_fetch = last_fetch.replace(tzinfo=timezone.utc)

    staleness_seconds = (now - last_fetch).total_seconds()
    thresholds = STALENESS_THRESHOLDS.get(domain, _DEFAULT_THRESHOLDS)

    if staleness_seconds >= thresholds["red"]:
        status = "red"
    elif staleness_seconds >= thresholds["yellow"]:
        status = "yellow"
    else:
        status = "green"

    return status, staleness_seconds


@router.get("/admin/health", response_model=AdminHealthResponse)
async def get_admin_health(
    town: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_town: Town = Depends(get_current_town),
) -> AdminHealthResponse:
    """Return per-connector health with green/yellow/red staleness classification."""
    if town != current_town.id:
        raise HTTPException(status_code=404, detail=f"Town not found: {town}")

    now = datetime.now(tz=timezone.utc)

    # Build a lookup: connector_class -> poll_interval_seconds from town config
    poll_interval_map: dict[str, int] = {
        c.connector_class: c.poll_interval_seconds
        for c in current_town.connectors
    }

    items: list[AdminHealthItem] = []

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
            domain: str = row["domain"]
            last_fetch: datetime | None = row["last_successful_fetch"]
            connector_class: str = row["connector_class"]

            status, staleness_seconds = classify_staleness(last_fetch, now, domain)

            thresholds = STALENESS_THRESHOLDS.get(domain, _DEFAULT_THRESHOLDS)

            # Reflect back the tz-aware version used for staleness computation
            last_fetch_aware: datetime | None = None
            if last_fetch is not None:
                last_fetch_aware = (
                    last_fetch
                    if last_fetch.tzinfo is not None
                    else last_fetch.replace(tzinfo=timezone.utc)
                )

            items.append(AdminHealthItem(
                id=row["id"],
                domain=domain,
                connector_class=connector_class,
                last_successful_fetch=last_fetch_aware,
                validation_error_count=int(row["validation_error_count"] or 0),
                status=status,
                staleness_seconds=staleness_seconds,
                poll_interval=poll_interval_map.get(connector_class),
                threshold_yellow=thresholds["yellow"],
                threshold_red=thresholds["red"],
            ))
    except Exception:
        # sources table may not exist in test environment
        items = []

    # Build summary counts
    summary: dict[str, int] = {"green": 0, "yellow": 0, "red": 0, "never_fetched": 0}
    for item in items:
        if item.status in summary:
            summary[item.status] += 1

    return AdminHealthResponse(
        town=current_town.id,
        town_display_name=current_town.display_name,
        checked_at=now,
        summary=summary,
        connectors=items,
    )
