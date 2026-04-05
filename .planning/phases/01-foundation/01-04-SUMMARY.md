---
phase: 01-foundation
plan: 04
subsystem: database
tags: [fastapi, geopandas, postgis, vg250, bkg, python, sqlalchemy, pytest]

# Dependency graph
requires:
  - phase: 01-02
    provides: features table with PostGIS geometry column (EPSG:4326)
  - phase: 01-03
    provides: load_town() function and Town model from config.py
provides:
  - FastAPI lifespan loading town from TOWN env var (fails fast on bad config)
  - /health endpoint returning {"status":"ok","town":"<town_id>"}
  - get_current_town() FastAPI dependency
  - scripts/load_vg250.py one-shot BKG VG250 boundary importer
  - Aalen administrative boundary in PostGIS features table (EPSG:4326, AGS=08136088)
  - 6 integration tests verifying geometry, SRID, coordinates, properties, source
affects: [all phases using FastAPI app startup, all phases querying features table]

# Tech tracking
tech-stack:
  added: [geopandas, httpx (download), zipfile (stdlib)]
  patterns: [lifespan-based config loading, sync SQLAlchemy for geopandas.to_postgis, JSONB serialization via json.dumps]

key-files:
  created:
    - backend/scripts/__init__.py
    - backend/scripts/load_vg250.py
    - backend/tests/test_boundaries.py
  modified:
    - backend/app/main.py

key-decisions:
  - "Use json.dumps() for JSONB properties — psycopg2 COPY protocol requires valid JSON strings, not Python dict repr"
  - "VG250 download cached in /tmp/vg250 — skip re-download if zip already exists"
  - "Auto-insert towns row if missing — prevents FK constraint failure for first-time runs"

patterns-established:
  - "Pattern: Sync SQLAlchemy engine for geopandas.to_postgis() — async engines not supported"
  - "Pattern: AGS must be matched as STRING — leading zero (08136088) is significant, integer cast would fail"
  - "Pattern: Always reproject to EPSG:4326 before inserting — VG250 ships in UTM32s (EPSG:25832)"

requirements-completed: [GEO-06]

# Metrics
duration: 3min
completed: 2026-04-05
---

# Phase 01 Plan 04: FastAPI Lifespan + VG250 Boundary Import Summary

**FastAPI lifespan validates town config from TOWN env var on startup, and BKG VG250 importer loads Aalen's administrative boundary into PostGIS as EPSG:4326 MultiPolygon (AGS=08136088, source=bkg_vg250)**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-05T18:07:40Z
- **Completed:** 2026-04-05T18:10:46Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Replaced FastAPI stub with town-config-aware lifespan loading `TOWN` env var at startup
- Created `load_vg250.py` one-shot script: downloads BKG VG250 GeoPackage (~200MB, cached), filters to AGS, reprojects UTM32s -> WGS84, inserts into `features` table
- Successfully imported Aalen boundary (1 MultiPolygon feature) into PostGIS
- 6 integration tests verify geometry correctness (SRID, coordinates in BW, AGS, source_id, geom type)
- Full test suite: 28 tests pass (migrations + config + connector + boundaries)

## Task Commits

Each task was committed atomically:

1. **Task 1: FastAPI lifespan + VG250 import script** - `29e9eae` (feat)
2. **Task 2: Run VG250 import + boundary integration tests** - `c7886c2` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `backend/app/main.py` - FastAPI app with lifespan loading TOWN env var, /health endpoint, get_current_town() dependency
- `backend/scripts/__init__.py` - Package marker (empty)
- `backend/scripts/load_vg250.py` - One-shot VG250 boundary importer with download, filter, reproject, insert
- `backend/tests/test_boundaries.py` - 6 integration tests verifying Aalen boundary in PostGIS

## Decisions Made
- Used `json.dumps()` for JSONB properties column — psycopg2's COPY protocol requires valid JSON strings (double-quotes), not Python dict `repr()` (single-quotes). Without this the import crashes with "invalid input syntax for type json".
- VG250 download cached in `/tmp/vg250` to avoid re-downloading 200MB on subsequent runs.
- Script auto-inserts the `towns` row if missing to prevent FK constraint failure for fresh database runs.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed JSONB serialization for properties column**
- **Found during:** Task 2 (Run VG250 import)
- **Issue:** The plan's lambda produced a Python dict (`{'gen': 'Aalen', ...}`) but psycopg2's COPY protocol expected valid JSON (`{"gen": "Aalen", ...}`). Single quotes caused `invalid input syntax for type json`.
- **Fix:** Changed lambda to use `json.dumps(...)` to produce valid JSON strings before passing to `to_postgis()`.
- **Files modified:** `backend/scripts/load_vg250.py`
- **Verification:** Import ran successfully, all 6 boundary tests pass including `test_aalen_boundary_properties_contain_ags`.
- **Committed in:** `c7886c2` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Essential correctness fix. No scope creep. Import would have failed without it.

## Issues Encountered
- Port 5432 already in use by existing PostgreSQL instance outside Docker — this was actually the correct running database, so the import succeeded without needing Docker.

## User Setup Required
None - no external service configuration required beyond running the database.

## Next Phase Readiness
- Phase 1 complete: FastAPI starts with validated town config, PostGIS has Aalen administrative boundary
- Phase 2 can use `get_current_town()` dependency and query `features WHERE domain='administrative'`
- `load_vg250.py` can be run for other towns by passing `<town_id> <ags>` arguments

---
*Phase: 01-foundation*
*Completed: 2026-04-05*
