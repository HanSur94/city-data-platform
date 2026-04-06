---
phase: 10-operator-multi-town
plan: "02"
subsystem: api
tags: [fastapi, pydantic, yaml, admin, health, multi-town, staleness]

requires:
  - phase: 01-foundation
    provides: load_town() config loader, Town/ConnectorConfig Pydantic models
  - phase: 02-first-connectors
    provides: connector patterns, sources table schema
  - phase: 10-01
    provides: operator dashboard plan context, PLAT-09 requirement

provides:
  - GET /api/admin/health endpoint with per-connector green/yellow/red staleness
  - STALENESS_THRESHOLDS dict covering 9 domains with domain-specific timings
  - classify_staleness() utility function (pure function, easily testable)
  - AdminHealthItem and AdminHealthResponse Pydantic models
  - towns/ulm.yaml stub proving zero-code-change multi-town architecture
  - 18 tests covering admin health endpoint and multi-town loading

affects:
  - operator dashboard frontend (future plan consuming /api/admin/health)
  - any German town wanting to onboard (just add a YAML file)

tech-stack:
  added: []
  patterns:
    - STALENESS_THRESHOLDS dict for domain-specific time budgets (different domains have very different update cadences)
    - classify_staleness() pure function for deterministic threshold classification
    - towns/{id}.yaml pattern validated as zero-code-change multi-town mechanism

key-files:
  created:
    - backend/app/routers/admin.py
    - backend/tests/test_api_admin.py
    - backend/tests/test_multi_town.py
    - towns/ulm.yaml
  modified:
    - backend/app/schemas/responses.py
    - backend/app/main.py

key-decisions:
  - "Per-domain staleness thresholds vary by 200x: demographics (7d/30d) vs water (30m/1h) — one-size-fits-all stale threshold would give misleading red for transit during normal operation"
  - "classify_staleness() is a pure function (not method) for easy unit testing without DB fixture"
  - "Ulm uses NVBW BW-wide GTFS (same URL as Aalen) — BW-gesamt feed covers the whole state"
  - "UBA station 320 is Ulm/Eselsberg air quality station"

patterns-established:
  - "Admin health extends connector health pattern (same DB query, richer response)"
  - "Domain-specific thresholds via lookup dict with _DEFAULT_THRESHOLDS fallback for unknown domains"
  - "Multi-town via YAML-only — no code changes, just drop a new file in towns/"

requirements-completed:
  - PLAT-09

duration: 12min
completed: 2026-04-06
---

# Phase 10 Plan 02: Admin Health API + Ulm Multi-Town Validation Summary

**Operator health API with per-domain green/yellow/red staleness (9 domain-specific thresholds), plus Ulm YAML stub proving zero-code-change multi-town architecture**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-04-06T19:35:00Z
- **Completed:** 2026-04-06T19:47:00Z
- **Tasks:** 2
- **Files modified:** 6 (4 created, 2 modified)

## Accomplishments

- Admin health router at GET /api/admin/health with domain-specific green/yellow/red staleness classification (9 domains, thresholds ranging from 30m/1h for water to 7d/30d for demographics)
- AdminHealthItem and AdminHealthResponse Pydantic models with staleness_seconds, poll_interval, threshold fields for rich operator diagnostics
- towns/ulm.yaml with WeatherConnector, UBAConnector (station 320/Eselsberg), and GTFSConnector — loads via load_town("ulm") with zero code changes
- 18 tests: 11 for admin health endpoint (unit + integration), 7 for multi-town config loading

## Task Commits

1. **Task 1: Admin health router with per-domain staleness thresholds** - `116afda` (feat)
2. **Task 2: Ulm stub town config + multi-town validation test** - `646be78` (feat)

## Files Created/Modified

- `backend/app/routers/admin.py` - GET /api/admin/health router with STALENESS_THRESHOLDS and classify_staleness()
- `backend/app/schemas/responses.py` - Added AdminHealthItem and AdminHealthResponse models
- `backend/app/main.py` - Registered admin router
- `backend/tests/test_api_admin.py` - 11 tests: endpoint structure, HTTP codes, staleness unit tests
- `backend/tests/test_multi_town.py` - 7 tests: Ulm config loading, bbox validation, connector count, Aalen regression
- `towns/ulm.yaml` - Ulm town config: bbox 9.90-10.06/48.35-48.44, 3 connectors

## Decisions Made

- Per-domain staleness thresholds vary by 200x between domains: water sensors at 30m/1h vs demographics at 7d/30d. Using one threshold would produce false red alerts for transit during normal GTFS daily-update cycles.
- classify_staleness() implemented as a pure function (not a class method) to enable direct unit testing without DB fixtures or async setup.
- Ulm uses the NVBW BW-gesamt GTFS feed (same URL as Aalen) — the feed covers all of Baden-Württemberg.
- UBA station 320 is the Ulm/Eselsberg air quality monitoring station (confirmed from UBA station list).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Admin health API is ready for frontend integration (operator dashboard UI in next plan)
- towns/ulm.yaml proves multi-town architecture works — any German town can onboard by dropping a YAML file in towns/
- classify_staleness() is exported and usable by future operator dashboard aggregation logic

---
*Phase: 10-operator-multi-town*
*Completed: 2026-04-06*
