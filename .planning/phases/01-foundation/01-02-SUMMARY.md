---
phase: 01-foundation
plan: 02
subsystem: database
tags: [alembic, timescaledb, postgis, geoalchemy2, postgresql, hypertables, migrations]

# Dependency graph
requires:
  - phase: 01-01
    provides: Docker Compose stack with TimescaleDB+PostGIS, Alembic env.py configured
provides:
  - Alembic migration 001 creating all 7 tables: towns, sources, features, air_quality_readings, transit_positions, water_readings, energy_readings
  - PostGIS spatial table (features) with GiST index on geometry column
  - Four TimescaleDB hypertables with retention policies
  - Migration test suite (8 tests) verifying complete schema
affects: [02-connectors, 03-api, all phases using database]

# Tech tracking
tech-stack:
  added: [geoalchemy2]
  patterns: [TDD migration — write tests first (RED), then migration (GREEN), spatial_index=False on GeoAlchemy2 columns when creating explicit named indexes]

key-files:
  created:
    - backend/alembic/versions/001_initial_schema.py
    - backend/tests/test_migrations.py
  modified: []

key-decisions:
  - "Set spatial_index=False on GeoAlchemy2 geometry columns when creating explicit named indexes to avoid duplicate index name collision"
  - "Hypertable chunk intervals: air_quality=1day, transit=1hour, water=1day, energy=1day"
  - "Retention policies: transit=90days, air_quality=2years, water=5years, energy=5years"

patterns-established:
  - "Pattern 1: GeoAlchemy2 spatial_index=False + explicit op.create_index with postgresql_using='gist' for named spatial indexes"
  - "Pattern 2: Extensions (PostGIS, TimescaleDB) created before any table DDL"
  - "Pattern 3: Hypertable creation via op.execute('SELECT create_hypertable(...)') with if_not_exists=TRUE"

requirements-completed: [PLAT-07, PLAT-08]

# Metrics
duration: 12min
completed: 2026-04-05
---

# Phase 01 Plan 02: Initial Database Schema Summary

**TimescaleDB schema with 4 hypertables, PostGIS spatial features table, and retention policies via Alembic migration 001**

## Performance

- **Duration:** 12 min
- **Started:** 2026-04-05T17:43:06Z
- **Completed:** 2026-04-05T17:55:00Z
- **Tasks:** 2 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments

- Created `backend/tests/test_migrations.py` with 8 tests covering all schema requirements (RED phase)
- Wrote `backend/alembic/versions/001_initial_schema.py` creating the complete schema
- All 8 migration tests pass; `alembic current` shows `001 (head)`
- Four hypertables with correct retention policies visible in `timescaledb_information.hypertables` and `timescaledb_information.jobs`

## Task Commits

Each task was committed atomically:

1. **Task 1: Write test_migrations.py (RED phase)** - `9a3710d` (test)
2. **Task 2: Write Alembic migration 001_initial_schema.py (GREEN phase)** - `f268333` (feat)

**Plan metadata:** (docs: see final commit below)

_Note: TDD tasks have separate test (RED) and feat (GREEN) commits_

## Files Created/Modified

- `backend/tests/test_migrations.py` - 8 pytest tests verifying schema structure, extensions, GiST index, retention policies
- `backend/alembic/versions/001_initial_schema.py` - Alembic migration creating all tables, hypertables, spatial indexes, and retention policies

## Decisions Made

- **spatial_index=False on GeoAlchemy2 columns:** GeoAlchemy2 defaults to `spatial_index=True`, which auto-creates a GiST index during `op.create_table`. When we also call `op.create_index(..., postgresql_using="gist")` for an explicit named index, Alembic raises `DuplicateTable` on the index name. Fix: `spatial_index=False` on geometry columns where we create named GiST indexes explicitly.
- **Retention durations:** transit=90d (high-frequency, large volume), air_quality=2yr (regulatory reference), water/energy=5yr (long-term trend analysis).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed GeoAlchemy2 duplicate spatial index name collision**
- **Found during:** Task 2 (migration run)
- **Issue:** GeoAlchemy2 `Geometry` column defaults to `spatial_index=True`, auto-creating a GiST index during table creation. The migration also called `op.create_index("idx_features_geometry", ..., postgresql_using="gist")`, causing a `DuplicateTable` error on index name.
- **Fix:** Added `spatial_index=False` to both `ga.Geometry()` column definitions (features.geometry and transit_positions.geometry) to suppress auto-creation, keeping the explicit named indexes.
- **Files modified:** `backend/alembic/versions/001_initial_schema.py`
- **Verification:** `alembic upgrade head` runs cleanly, all 8 tests pass
- **Committed in:** `f268333` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Fix was necessary for migration to run. No scope creep. Named GiST index `idx_features_geometry` provides predictable, queryable index name for spatial queries.

## Issues Encountered

GeoAlchemy2 auto-spatial-index behavior not documented in plan — discovered during first migration run. Root cause: GeoAlchemy2 `Geometry` type creates a GiST index by default as part of table creation DDL. Resolved cleanly via `spatial_index=False`.

## User Setup Required

None - no external service configuration required. Database runs in Docker Compose stack from Plan 01.

## Next Phase Readiness

- Complete schema is in place — all connector and API phases can proceed
- `alembic upgrade head` creates all required tables in one step
- Migration tests serve as regression guard for any future schema changes
- Concern: `geoalchemy2` package must be present in `pyproject.toml` for the migration to import correctly (verify in Plan 03 context if issues arise)

---
*Phase: 01-foundation*
*Completed: 2026-04-05*
