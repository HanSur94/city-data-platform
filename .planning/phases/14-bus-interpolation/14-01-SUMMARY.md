---
phase: 14-bus-interpolation
plan: 01
subsystem: api
tags: [gtfs, interpolation, transit, bus, haversine, geojson]

requires:
  - phase: 05-transit
    provides: "GTFS static connector, transit_positions hypertable, transit features"
  - phase: 05-transit
    provides: "GTFSRealtimeConnector writing delay data to transit_positions"
provides:
  - "BusInterpolationConnector computing interpolated bus positions from GTFS schedule + RT delay"
  - "shape_walk pure function for LineString geometry walking with haversine distances"
  - "interpolate_position pure function handling all edge cases per REQ-BUS-05"
  - "BusPosition and ActiveTrip Pydantic models"
affects: [15-bus-frontend, transit-layer]

tech-stack:
  added: []
  patterns: ["Computation connector pattern: run() orchestrates without fetch/normalize pipeline", "Lazy imports for heavy dependencies (gtfs_kit) to keep test imports fast", "Pure function extraction for testable algorithms (shape_walk, interpolate_position)"]

key-files:
  created:
    - backend/app/connectors/bus_interpolation.py
    - backend/app/models/bus_interpolation.py
    - backend/tests/connectors/test_bus_interpolation.py
  modified:
    - backend/app/scheduler.py
    - backend/app/schemas/geojson.py
    - towns/aalen.yaml

key-decisions:
  - "Lazy import of gtfs_kit and httpx inside methods to avoid blocking test collection"
  - "Pure functions shape_walk and interpolate_position extracted from connector for direct unit testing"
  - "Stop-fraction-based progress mapping (stop i at i/(n-1) along shape) for simplicity"

patterns-established:
  - "Computation connector: overrides run() entirely, skips fetch/normalize/persist pipeline"
  - "Pure function extraction for testable algorithms alongside connector class"

requirements-completed: [REQ-BUS-01, REQ-BUS-05]

duration: 4min
completed: 2026-04-06
---

# Phase 14 Plan 01: Bus Interpolation Engine Summary

**GTFS shape-walking interpolation engine with haversine distance computation, 5 edge cases handled, and 13 unit tests**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-06T21:38:24Z
- **Completed:** 2026-04-06T21:42:51Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- BusInterpolationConnector reads GTFS static + RT delay data, produces interpolated bus positions
- shape_walk algorithm correctly walks along LineString geometry using haversine distances
- All 5 edge cases from REQ-BUS-05 handled: dwelling at stop, no delay, not departed, completed, multiple buses
- Connector registered in scheduler at 30s interval, attribution added, aalen.yaml configured

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Failing tests for interpolation** - `f86544c` (test)
2. **Task 1 (GREEN): Implement shape_walk + interpolate_position** - `05a0e25` (feat)
3. **Task 2: Register connector, config, attribution** - `d07bfca` (feat)

## Files Created/Modified
- `backend/app/connectors/bus_interpolation.py` - BusInterpolationConnector with shape_walk and interpolate_position
- `backend/app/models/bus_interpolation.py` - BusPosition and ActiveTrip Pydantic models
- `backend/tests/connectors/test_bus_interpolation.py` - 13 unit tests covering all edge cases
- `backend/app/scheduler.py` - Added BusInterpolationConnector to _CONNECTOR_MODULES
- `backend/app/schemas/geojson.py` - Added NVBW GTFS interpolation attribution
- `towns/aalen.yaml` - Added BusInterpolationConnector with 30s poll interval

## Decisions Made
- Lazy import of gtfs_kit and httpx inside connector methods to avoid blocking test collection (gtfs_kit not available in test environment by default)
- Pure functions shape_walk and interpolate_position extracted as module-level functions for easy unit testing without DB mocking
- Stop-fraction-based progress mapping: stop i positioned at fraction i/(n-1) along the shape for simple linear mapping

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Made gtfs_kit and httpx imports lazy**
- **Found during:** Task 1 (TDD GREEN phase)
- **Issue:** Top-level `import gtfs_kit` caused ModuleNotFoundError during test collection
- **Fix:** Moved gtfs_kit import into _parse_gtfs() and httpx import into _download_cached_gtfs()
- **Files modified:** backend/app/connectors/bus_interpolation.py
- **Verification:** Tests collect and pass without gtfs_kit at import time
- **Committed in:** 05a0e25

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential for test execution. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Bus interpolation engine complete, ready for frontend visualization (Phase 14 Plan 02)
- Bus positions served via existing /api/layers/transit endpoint as feature_type="bus_position"
- Frontend needs to filter transit features by feature_type and render bus icons

## Known Stubs
None - all functions are fully implemented with real logic.

---
*Phase: 14-bus-interpolation*
*Completed: 2026-04-06*
