# backend/app/routers/admin.py
"""Admin health router: GET /api/admin/health, GET /api/admin/monitor

Returns per-connector health with domain-specific staleness thresholds
(green/yellow/red) for the operator dashboard (PLAT-09).
Comprehensive monitoring endpoint aggregating hypertable stats, connector
health, feature registry counts, and system info.
"""
import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Town
from app.db import get_db
from app.dependencies import get_current_town
from app.schemas.responses import (
    AdminHealthItem,
    AdminHealthResponse,
    AdminMonitorResponse,
    ConnectorHealthInfo,
    FeatureDomainCount,
    HypertableStats,
    SystemInfo,
)

logger = logging.getLogger(__name__)

# Module-level start time to approximate server uptime
_server_start_time = time.time()

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


# ── Known hypertables ────────────────────────────────────────────────

HYPERTABLES = [
    "air_quality_readings",
    "weather_readings",
    "transit_positions",
    "water_readings",
    "energy_readings",
    "traffic_readings",
    "demographics_readings",
]


async def _query_system_info(db: AsyncSession) -> SystemInfo:
    """Gather database system information."""
    try:
        ts_version = None
        postgis_version = None
        size_bytes = 0
        size_pretty = "0 bytes"
        uptime_seconds = 0.0

        # TimescaleDB version
        row = (await db.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'")
        )).first()
        if row:
            ts_version = row[0]

        # PostGIS version
        row = (await db.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'postgis'")
        )).first()
        if row:
            postgis_version = row[0]

        # Total DB size
        row = (await db.execute(
            text("SELECT pg_database_size(current_database()) as size_bytes")
        )).first()
        if row:
            size_bytes = int(row[0])

        # Human-readable size
        row = (await db.execute(
            text("SELECT pg_size_pretty(pg_database_size(current_database()))")
        )).first()
        if row:
            size_pretty = row[0]

        # Server uptime
        row = (await db.execute(
            text("SELECT extract(epoch from (now() - pg_postmaster_start_time())) as uptime_seconds")
        )).first()
        if row:
            uptime_seconds = float(row[0])

        return SystemInfo(
            db_ok=True,
            timescaledb_version=ts_version,
            postgis_version=postgis_version,
            total_db_size=size_pretty,
            total_db_size_bytes=size_bytes,
            server_uptime_seconds=uptime_seconds,
        )
    except Exception:
        logger.exception("Failed to query system info")
        return SystemInfo(
            db_ok=False,
            timescaledb_version=None,
            postgis_version=None,
            total_db_size="unknown",
            total_db_size_bytes=0,
            server_uptime_seconds=time.time() - _server_start_time,
        )


async def _query_hypertable_stats(db: AsyncSession) -> list[HypertableStats]:
    """Gather per-hypertable statistics."""
    stats: list[HypertableStats] = []

    for table_name in HYPERTABLES:
        try:
            # Chunk count and size from timescaledb catalog
            chunk_count = 0
            disk_size_bytes = 0
            try:
                row = (await db.execute(
                    text("""
                        SELECT num_chunks,
                               hypertable_size(format('%I', hypertable_name)) as size_bytes
                        FROM timescaledb_information.hypertables
                        WHERE hypertable_schema = 'public'
                          AND hypertable_name = :ht
                    """),
                    {"ht": table_name},
                )).first()
                if row:
                    chunk_count = int(row[0]) if row[0] else 0
                    disk_size_bytes = int(row[1]) if row[1] else 0
            except Exception:
                logger.debug("Could not query hypertable info for %s", table_name)

            # Row count and time range
            row_count = 0
            oldest_ts = None
            newest_ts = None
            try:
                row = (await db.execute(
                    text(f"SELECT count(*), min(time), max(time) FROM {table_name}")  # noqa: S608
                )).first()
                if row:
                    row_count = int(row[0]) if row[0] else 0
                    oldest_ts = row[1]
                    newest_ts = row[2]
            except Exception:
                logger.debug("Could not query row count for %s", table_name)

            # Compression ratio (may not be enabled)
            compression_ratio = None
            try:
                row = (await db.execute(
                    text("""
                        SELECT CASE WHEN after_compression_total_bytes > 0
                                    THEN before_compression_total_bytes::float / after_compression_total_bytes
                                    ELSE NULL END as ratio
                        FROM hypertable_compression_stats(:ht_regclass)
                    """),
                    {"ht_regclass": table_name},
                )).first()
                if row and row[0] is not None:
                    compression_ratio = round(float(row[0]), 2)
            except Exception:
                pass  # Compression not enabled for this table

            # Retention policy
            retention_policy = None
            try:
                row = (await db.execute(
                    text("""
                        SELECT config::json->>'drop_after' as drop_after
                        FROM timescaledb_information.jobs
                        WHERE proc_name = 'policy_retention'
                          AND hypertable_schema = 'public'
                          AND hypertable_name = :ht
                    """),
                    {"ht": table_name},
                )).first()
                if row and row[0]:
                    retention_policy = row[0]
            except Exception:
                pass

            stats.append(HypertableStats(
                table_name=table_name,
                row_count=row_count,
                disk_size_bytes=disk_size_bytes,
                chunk_count=chunk_count,
                compression_ratio=compression_ratio,
                oldest_timestamp=oldest_ts,
                newest_timestamp=newest_ts,
                retention_policy=retention_policy,
            ))
        except Exception:
            logger.exception("Failed to query stats for %s", table_name)
            stats.append(HypertableStats(
                table_name=table_name,
                row_count=0,
                disk_size_bytes=0,
                chunk_count=0,
                compression_ratio=None,
                oldest_timestamp=None,
                newest_timestamp=None,
                retention_policy=None,
            ))

    return stats


async def _query_connector_health(
    db: AsyncSession, current_town: Town,
) -> list[ConnectorHealthInfo]:
    """Gather connector health using the existing staleness classification."""
    now = datetime.now(tz=timezone.utc)
    poll_interval_map: dict[str, int] = {
        c.connector_class: c.poll_interval_seconds
        for c in current_town.connectors
    }

    items: list[ConnectorHealthInfo] = []
    try:
        result = await db.execute(
            text("""
                SELECT domain, connector_class, last_successful_fetch, validation_error_count
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

            status, _ = classify_staleness(last_fetch, now, domain)

            last_fetch_aware: datetime | None = None
            if last_fetch is not None:
                last_fetch_aware = (
                    last_fetch if last_fetch.tzinfo is not None
                    else last_fetch.replace(tzinfo=timezone.utc)
                )

            items.append(ConnectorHealthInfo(
                connector_class=connector_class,
                domain=domain,
                status=status,
                last_successful_fetch=last_fetch_aware,
                poll_interval_seconds=poll_interval_map.get(connector_class),
                validation_error_count=int(row["validation_error_count"] or 0),
            ))
    except Exception:
        logger.exception("Failed to query connector health")

    return items


async def _query_feature_registry(
    db: AsyncSession, town_id: str,
) -> list[FeatureDomainCount]:
    """Gather per-domain feature counts."""
    items: list[FeatureDomainCount] = []
    try:
        result = await db.execute(
            text("""
                SELECT
                    domain,
                    count(*) as total_features,
                    count(semantic_id) as with_semantic_id
                FROM features
                WHERE town_id = :town_id
                GROUP BY domain
                ORDER BY domain
            """),
            {"town_id": town_id},
        )
        rows = result.mappings().all()
        for row in rows:
            items.append(FeatureDomainCount(
                domain=row["domain"],
                total_features=int(row["total_features"]),
                with_semantic_id=int(row["with_semantic_id"]),
            ))
    except Exception:
        logger.exception("Failed to query feature registry")

    return items


@router.get("/admin/monitor", response_model=AdminMonitorResponse)
async def get_admin_monitor(
    town: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_town: Town = Depends(get_current_town),
) -> AdminMonitorResponse:
    """Comprehensive monitoring endpoint aggregating all admin data sections.

    Returns hypertable stats, connector health, feature registry counts, and
    system info in a single response. Each section is independently resilient
    -- partial failures return defaults, not 500 errors.
    """
    if town != current_town.id:
        raise HTTPException(status_code=404, detail=f"Town not found: {town}")

    now = datetime.now(tz=timezone.utc)

    system_info = await _query_system_info(db)
    hypertable_stats = await _query_hypertable_stats(db)
    connector_health = await _query_connector_health(db, current_town)
    feature_registry = await _query_feature_registry(db, current_town.id)

    return AdminMonitorResponse(
        town=current_town.id,
        checked_at=now,
        system_info=system_info,
        hypertable_stats=hypertable_stats,
        connector_health=connector_health,
        feature_registry=feature_registry,
    )
