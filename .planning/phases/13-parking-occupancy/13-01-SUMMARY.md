---
phase: 13-parking-occupancy
plan: 01
subsystem: api
tags: [beautifulsoup4, scraping, parking, pydantic, kpi, infrastructure]

# Dependency graph
requires: []
provides:
  - ParkingConnector scraping Stadtwerke Aalen parking page
  - ParkingGarage Pydantic model with validation
  - ParkingKPI aggregation endpoint via existing KPI route
  - ParkingKPI TypeScript interface for frontend consumption
affects: [13-parking-occupancy]

# Tech tracking
tech-stack:
  added: [beautifulsoup4]
  patterns: [feature-properties-only connector (no hypertable), HTML scraping connector]

key-files:
  created:
    - backend/app/connectors/parking.py
    - backend/app/models/parking.py
    - backend/tests/connectors/test_parking.py
  modified:
    - backend/app/scheduler.py
    - towns/aalen.yaml
    - backend/app/schemas/responses.py
    - backend/app/routers/kpi.py
    - backend/app/schemas/geojson.py
    - frontend/types/kpi.ts

key-decisions:
  - "Feature-properties-only pattern: parking uses infrastructure domain features with no hypertable writes"
  - "Hardcoded garage coordinates from OSM since scraped page has no geo data"

patterns-established:
  - "HTML scraping connector: fetch HTML via httpx, parse with BeautifulSoup4, upsert as infrastructure features"
  - "geschlossen handling: treat closed/unparseable free spots as 0"

requirements-completed: [REQ-PARKING-01, REQ-PARKING-02, REQ-PARKING-04]

# Metrics
duration: 4min
completed: 2026-04-06
---

# Phase 13 Plan 01: Parking Backend Summary

**ParkingConnector scrapes Stadtwerke Aalen garage occupancy via BeautifulSoup4, upserts infrastructure features, and exposes ParkingKPI aggregate endpoint**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-06T21:21:27Z
- **Completed:** 2026-04-06T21:25:11Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- ParkingConnector scrapes HTML from sw-aalen.de and extracts garage name, free spots, total capacity
- Scraper creates/updates infrastructure domain features with parking category and occupancy properties
- KPI endpoint returns parking availability summary (total free / total capacity)
- Connector registered in scheduler and aalen.yaml with 5-minute poll interval
- 5 unit tests passing with mock HTML fixtures

## Task Commits

Each task was committed atomically:

1. **Task 1: ParkingConnector with HTML scraper and Pydantic model** - `a453075` (feat+test, TDD)
2. **Task 2: ParkingKPI endpoint and TypeScript types** - `a8093bc` (feat)

## Files Created/Modified
- `backend/app/connectors/parking.py` - ParkingConnector scraping Stadtwerke Aalen parking page
- `backend/app/models/parking.py` - ParkingGarage Pydantic model with validation
- `backend/tests/connectors/test_parking.py` - 5 unit tests with mock HTML
- `backend/app/scheduler.py` - ParkingConnector registered in _CONNECTOR_MODULES
- `towns/aalen.yaml` - ParkingConnector config with 300s poll interval
- `backend/app/schemas/responses.py` - ParkingKPI model and parking field in KPIResponse
- `backend/app/routers/kpi.py` - Parking KPI query section aggregating from features table
- `backend/app/schemas/geojson.py` - ParkingConnector attribution entry
- `frontend/types/kpi.ts` - ParkingKPI interface and parking field in KPIResponse

## Decisions Made
- Feature-properties-only pattern: parking data stored as infrastructure domain feature properties, no hypertable writes needed
- Hardcoded approximate garage coordinates from OSM since the scraped page provides no geographic data
- "geschlossen" (closed) garages treated as 0 free spots for graceful degradation

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed _to_datetime forward reference in kpi.py**
- **Found during:** Task 2 (ParkingKPI endpoint)
- **Issue:** _to_datetime helper function defined after parking KPI section would cause NameError at runtime
- **Fix:** Inlined datetime type check instead of calling _to_datetime in parking section
- **Files modified:** backend/app/routers/kpi.py
- **Verification:** Import succeeds, no runtime error
- **Committed in:** a8093bc (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary fix for runtime correctness. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all data paths are wired to live scraping.

## Next Phase Readiness
- Backend parking data pipeline complete
- ParkingKPI available via /api/kpi endpoint
- TypeScript types ready for frontend dashboard tile (Plan 02)

---
*Phase: 13-parking-occupancy*
*Completed: 2026-04-06*
