---
phase: 01-foundation
plan: "01"
subsystem: infra
tags: [docker, timescaledb, postgis, fastapi, alembic, sqlalchemy, uv, pytest]

requires: []

provides:
  - "Running TimescaleDB 2.x + PostGIS on PostgreSQL 17 via Docker Compose (port 5432)"
  - "FastAPI backend service definition in Docker Compose (port 8000)"
  - "uv-managed Python project with all Phase 1 dependencies locked"
  - "Alembic migration infrastructure with include_object filter for TimescaleDB safety"
  - "pytest conftest with db_url, db_engine, db_conn session-scoped fixtures"

affects: [01-02, 01-03, 01-04, all-future-plans]

tech-stack:
  added:
    - "timescale/timescaledb-ha:pg17 (Docker image — bundles TimescaleDB 2.x + PostGIS)"
    - "FastAPI 0.135.3"
    - "SQLAlchemy 2.0.49 (async engine)"
    - "asyncpg 0.31.0"
    - "psycopg2-binary 2.9.11"
    - "Alembic 1.18.4"
    - "geopandas 1.1.3"
    - "GeoAlchemy2 0.18.4"
    - "httpx 0.28.1"
    - "pytest 9.0.2 + pytest-asyncio 1.3.0"
    - "uv (Python package manager)"
  patterns:
    - "DATABASE_URL env var with +asyncpg for FastAPI, stripped to plain postgresql:// for Alembic/sync"
    - "include_object filter in alembic/env.py to skip _hyper_* indexes and _timescaledb_internal schema"
    - "Session-scoped pytest fixtures for database connections"

key-files:
  created:
    - "docker-compose.yml"
    - "backend/Dockerfile"
    - "backend/pyproject.toml"
    - "backend/app/__init__.py"
    - "backend/app/main.py"
    - "backend/app/db.py"
    - "backend/alembic.ini"
    - "backend/alembic/env.py"
    - "backend/tests/conftest.py"
    - ".gitignore"
  modified: []

key-decisions:
  - "Use timescale/timescaledb-ha:pg17 image (not deprecated timescale/timescaledb-postgis) — bundles both extensions"
  - "Alembic uses sync psycopg2 URL; FastAPI uses asyncpg URL — both sourced from DATABASE_URL env var with +asyncpg stripped"
  - "include_object filter excludes _hyper_* indexes from Alembic autogenerate to prevent spurious DROP INDEX migrations"

patterns-established:
  - "Pattern 1: DATABASE_URL dual-mode — asyncpg for runtime, sync for migrations (strip +asyncpg)"
  - "Pattern 2: TimescaleDB Alembic safety — include_object filter is mandatory in all env.py files"
  - "Pattern 3: uv for all Python dependency management — no pip/poetry"

requirements-completed: [PLAT-02]

duration: 9min
completed: 2026-04-05
---

# Phase 1 Plan 01: Foundation Summary

**TimescaleDB-ha + PostGIS on Docker Compose, uv-managed FastAPI backend with Alembic migration infrastructure and pytest fixture scaffold**

## Performance

- **Duration:** 9 min
- **Started:** 2026-04-05T17:50:51Z
- **Completed:** 2026-04-05T18:00:09Z
- **Tasks:** 2
- **Files modified:** 12

## Accomplishments
- Docker Compose with `timescale/timescaledb-ha:pg17` starts a healthy container verified via `pg_isready` healthcheck
- FastAPI app with `/health` endpoint and async SQLAlchemy engine wired via `DATABASE_URL` env var
- Alembic initialized with `include_object` filter preventing TimescaleDB internal indexes from being dropped on autogenerate
- pytest `conftest.py` with session-scoped `db_url`, `db_engine`, `db_conn` fixtures ready for all future test plans

## Task Commits

Each task was committed atomically:

1. **Task 1: Docker Compose + project directory layout** - `19ab0c8` (feat)
2. **Task 2: Alembic scaffold + pytest conftest** - `3c7aa5e` (feat)
3. **Chore: .gitignore** - `552d22c` (chore)

**Plan metadata:** (docs commit to follow)

## Files Created/Modified
- `docker-compose.yml` - Service definitions for db (TimescaleDB-ha) and backend (FastAPI); healthcheck on db
- `backend/Dockerfile` - python:3.12-slim + GDAL + uv; copies pyproject.toml for layer caching
- `backend/pyproject.toml` - city-data-platform-backend; all Phase 1 deps locked with uv
- `backend/app/main.py` - FastAPI app factory with lifespan and /health endpoint
- `backend/app/db.py` - Async SQLAlchemy engine + session factory + get_db() dependency
- `backend/alembic.ini` - Sync postgresql:// URL for Alembic
- `backend/alembic/env.py` - Migration environment with include_object filter for TimescaleDB
- `backend/tests/conftest.py` - Session-scoped db_url, db_engine, db_conn fixtures
- `.gitignore` - Python/__pycache__/Node/data file exclusions

## Decisions Made
- Used `timescale/timescaledb-ha:pg17` (not deprecated `timescale/timescaledb-postgis`) — ha image bundles both extensions
- Alembic env.py strips `+asyncpg` from DATABASE_URL to get sync psycopg2 URL — no separate env var needed
- `include_object` filter is installed from day one — prevents a class of Alembic bugs that would corrupt TimescaleDB hypertable indexes

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed auto-generated stub main.py from uv init**
- **Found during:** Task 2 (cleanup after alembic init)
- **Issue:** `uv init` generated a `backend/main.py` stub that would conflict with `backend/app/main.py`
- **Fix:** Deleted `backend/main.py` stub; the real application entry point is `backend/app/main.py`
- **Files modified:** `backend/main.py` (deleted)
- **Verification:** No conflicts; pytest collects 0 items cleanly
- **Committed in:** `3c7aa5e` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking/cleanup)
**Impact on plan:** Minor cleanup. No scope creep.

## Issues Encountered
- `docker compose` `version:` key generates a deprecation warning (obsolete in Compose v5). Kept for compatibility — not an error, just cosmetic.

## User Setup Required
None - no external service configuration required. Docker Compose handles everything.

## Next Phase Readiness
- TimescaleDB + PostGIS container running and healthy on port 5432
- Alembic connected and ready to run migrations (Plan 01-02)
- pytest test infrastructure ready for fixture use
- `uv.lock` committed — deterministic builds for all subsequent plans

---
*Phase: 01-foundation*
*Completed: 2026-04-05*
