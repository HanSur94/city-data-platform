---
phase: 12-kocher-water-level
plan: 01
subsystem: api
tags: [lhpapi, water-level, kocher, pydantic, fastapi, timescaledb]

requires:
  - phase: 06-water-data
    provides: water_readings hypertable and BaseConnector water domain persist path
provides:
  - LhpConnector class polling Huttlingen/Kocher gauge via lhpapi
  - LhpGaugeReading Pydantic validation model
  - WaterKPI response model and /api/kpi water endpoint
  - WaterKPI TypeScript interface
affects: [12-kocher-water-level]

tech-stack:
  added: [lhpapi]
  patterns: [synchronous-api-via-asyncio-to-thread, trend-computation-from-hypertable]

key-files:
  created:
    - backend/app/connectors/lhp.py
    - backend/app/models/lhp.py
    - backend/tests/connectors/test_lhp.py
  modified:
    - backend/app/scheduler.py
    - towns/aalen.yaml
    - backend/app/schemas/responses.py
    - backend/app/routers/kpi.py
    - frontend/types/kpi.ts

key-decisions:
  - "Used asyncio.to_thread for lhpapi since it is synchronous/blocking"
  - "Trend computed from last 2 water_readings with 2cm threshold for rising/falling"
  - "Huttlingen gauge ident BW_13490006 stored as config parameter for override"

patterns-established:
  - "Synchronous third-party API wrapping: use asyncio.to_thread for blocking libraries"

requirements-completed: [REQ-KOCHER-01]

duration: 3min
completed: 2026-04-06
---

# Phase 12 Plan 01: LHP Connector and Water KPI Summary

**LHP connector polling Huttlingen/Kocher gauge via lhpapi with water KPI endpoint returning level, flow, stage, and trend**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-06T07:23:57Z
- **Completed:** 2026-04-06T07:26:44Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- LhpConnector fetches Kocher water level from LHP Huttlingen gauge via lhpapi library
- Water readings persisted to water_readings hypertable with level_cm and flow_m3s
- KPI endpoint returns WaterKPI with level, flow, warning stage (0-4), and trend
- 12 unit tests covering normalize, trend computation, and feature properties

## Task Commits

Each task was committed atomically:

1. **Task 1: Create LhpConnector with Pydantic model and tests** - `1a2dc52` (feat, TDD)
2. **Task 2: Register connector, add KPI water endpoint, update TypeScript types** - `6bb6ff8` (feat)

## Files Created/Modified
- `backend/app/connectors/lhp.py` - LhpConnector class polling Huttlingen gauge via lhpapi
- `backend/app/models/lhp.py` - LhpGaugeReading Pydantic model wrapping lhpapi attributes
- `backend/tests/connectors/test_lhp.py` - 12 unit tests for normalize, trend, properties
- `backend/app/scheduler.py` - Added LhpConnector to connector registry
- `towns/aalen.yaml` - Added LhpConnector config with 900s poll, BW_13490006 ident
- `backend/app/schemas/responses.py` - Added WaterKPI model, water field to KPIResponse
- `backend/app/routers/kpi.py` - Added water KPI query joining water_readings with lhp features
- `frontend/types/kpi.ts` - Added WaterKPI interface and water field to KPIResponse

## Decisions Made
- Used asyncio.to_thread for lhpapi since it is synchronous/blocking (no async support)
- Trend computed from last 2 water_readings with 2cm threshold for rising/falling classification
- Huttlingen gauge ident BW_13490006 stored as config parameter so it can be overridden

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required

None - lhpapi is a pip dependency with no API key required.

## Next Phase Readiness
- LHP connector and KPI backend ready for Plan 02 (frontend water layer on map + dashboard)
- No blockers

---
*Phase: 12-kocher-water-level*
*Completed: 2026-04-06*
