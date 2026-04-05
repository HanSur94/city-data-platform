---
phase: 05-dashboard
plan: "01"
subsystem: api
tags: [fastapi, sql, timescaledb, historical, time-series, layers, air-quality]

requires:
  - phase: 03-query-api
    provides: layers endpoint GET /api/layers/{domain} with LATERAL join for air_quality readings
  - phase: 04-map-frontend
    provides: frontend consuming GET /api/layers/{domain} for map data

provides:
  - "Optional ?at=ISO8601 query param on GET /api/layers/{domain}"
  - "Air quality LATERAL join filters time <= :at when at is provided"
  - "Timezone normalization for naive datetime inputs (UTC)"
  - "Contract tests for at param HTTP behavior"

affects: [05-dashboard, frontend-time-slider, MAP-06]

tech-stack:
  added: []
  patterns:
    - "at_aware timezone normalization: at.replace(tzinfo=timezone.utc) if at.tzinfo is None else at"
    - "Conditional SQL filter: AND (:at IS NULL OR time <= :at) for optional timestamp gates"

key-files:
  created:
    - backend/tests/test_layers_at_param.py
  modified:
    - backend/app/routers/layers.py

key-decisions:
  - "at param placed after town and before db in signature — keeps dependency params last"
  - "at_aware computed before domain branch — available to all future domains if needed"
  - "Timezone normalization applied to naive datetimes (UTC assumed) — avoids DB comparison failures"
  - "Transit and generic domain branches intentionally unchanged — only air_quality has time-series readings at this phase"

patterns-established:
  - "Conditional SQL: use :param IS NULL OR col <= :param pattern for optional filter params"
  - "at_aware: always normalize naive datetimes to UTC before passing to DB"

requirements-completed: [MAP-06]

duration: 2min
completed: 2026-04-05
---

# Phase 05 Plan 01: Dashboard At-Param Summary

**Optional `?at=ISO8601` timestamp param wired into air quality LATERAL join via `AND (:at IS NULL OR time <= :at)`, enabling historical map snapshots for the time slider**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-05T22:52:00Z
- **Completed:** 2026-04-05T22:54:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `at: datetime | None = Query(None)` to `get_layer()` signature with ISO 8601 description
- Modified air quality LATERAL subquery: `AND (:at IS NULL OR time <= :at)` for historical filtering
- Added `at_aware` timezone normalization (naive datetimes coerced to UTC) before DB query
- Created `test_layers_at_param.py` with 4 contract tests covering no-at, valid-at, transit-at, invalid-at scenarios
- All 4 tests pass; transit and generic domain branches remain unchanged

## Task Commits

1. **Task 1: Add ?at= param to layers router air_quality LATERAL join** - `ca20b15` (feat)
2. **Task 2: Test ?at= param behaviour** - `7942c5f` (test)

## Files Created/Modified

- `backend/app/routers/layers.py` - Added `at` param, `at_aware` normalization, LATERAL join conditional filter, `timezone` import
- `backend/tests/test_layers_at_param.py` - 4 contract tests for the at param HTTP behavior

## Decisions Made

- `at_aware` computed before the domain branch (not inside it) — available if future domains add time-series
- Timezone normalization assumes UTC for naive datetimes — consistent with TimescaleDB storage convention
- Transit domain intentionally does not use `at` — no time-series readings at this phase
- Tests use `in (200, 404)` assertions rather than fixed 200 — tests run without a real DB (mock returns empty results which still yield 200 FeatureCollection)

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- Plan's automated verification command pointed at `/Users/hannessuhr/Projects/city-data-platform/backend` (main repo path) rather than the worktree. The worktree path was correct and all checks passed when run from the worktree directory. No code change needed.

## Known Stubs

None — the `at` parameter is fully wired to the SQL filter. No hardcoded empty values or placeholder behavior introduced.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `GET /api/layers/air_quality?town=aalen&at=2026-01-01T00:00:00Z` now returns readings at or before the given timestamp
- Frontend time slider (MAP-06) can call this endpoint with ISO 8601 timestamps from the slider value
- All existing callers without `?at=` continue to receive latest readings (backward compatible)

---
*Phase: 05-dashboard*
*Completed: 2026-04-05*
