---
phase: 11-traffic-flow
plan: 01
subsystem: api
tags: [tomtom, traffic, httpx, congestion, adaptive-polling]

requires:
  - phase: 07-traffic-energy
    provides: BaseConnector, traffic_readings hypertable, BastConnector pattern
provides:
  - TomTomConnector class for real-time traffic flow data
  - 35 Aalen road segment sample points (B29, B19, Friedrichstr., Gmunder Str.)
  - Adaptive rush/off-peak polling logic
affects: [11-traffic-flow, frontend-traffic-layer]

tech-stack:
  added: []
  patterns: [adaptive-polling-skip-logic, linestring-geometry-upsert]

key-files:
  created:
    - backend/app/connectors/tomtom.py
    - backend/tests/connectors/test_tomtom.py
  modified:
    - backend/app/scheduler.py
    - towns/aalen.yaml

key-decisions:
  - "Adaptive polling via skip logic: scheduler runs at 600s always, connector skips off-peak if <1800s elapsed"
  - "congestion_ratio stored in feature properties, speed_avg_kmh in traffic_readings for schema compatibility"

patterns-established:
  - "Adaptive polling: class-level _last_run_time with skip logic in run() for variable poll intervals"
  - "LineString geometry upsert from API coordinate arrays"

requirements-completed: [REQ-TRAFFIC-01, REQ-TRAFFIC-03, REQ-TRAFFIC-04]

duration: 3min
completed: 2026-04-06
---

# Phase 11 Plan 01: TomTom Traffic Flow Connector Summary

**TomTom Flow Segment Data connector polling 35 Aalen road segments with congestion ratio computation and adaptive 10min/30min rush/off-peak polling**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-06T20:44:44Z
- **Completed:** 2026-04-06T20:47:29Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- TomTomConnector fetching real-time speed/freeflow data from TomTom Flow Segment Data API for 35 Aalen road segments
- Congestion ratio (currentSpeed/freeFlowSpeed) computed with level mapping: free/moderate/congested
- Adaptive polling: 10min during rush hours (06-09, 16-19 Europe/Berlin), 30min off-peak via skip logic
- LineString geometry upserted from TomTom API coordinate responses
- 13 unit tests covering normalize, congestion levels, rush hour detection, poll intervals, fetch URL

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Add failing tests for TomTomConnector** - `964886f` (test)
2. **Task 1 (GREEN): Implement TomTomConnector** - `8df7c2c` (feat)
3. **Task 2: Register in scheduler and aalen.yaml** - `ce59339` (feat)

## Files Created/Modified
- `backend/app/connectors/tomtom.py` - TomTomConnector with 35 road segment definitions, fetch/normalize/run, adaptive polling
- `backend/tests/connectors/test_tomtom.py` - 13 unit tests for TomTom connector
- `backend/app/scheduler.py` - Added TomTomConnector to _CONNECTOR_MODULES registry
- `towns/aalen.yaml` - Added TomTomConnector config with 600s interval and API key placeholder

## Decisions Made
- Adaptive polling implemented via skip logic in run() rather than dynamic APScheduler intervals (APScheduler 3.x IntervalTrigger doesn't support dynamic intervals natively)
- congestion_ratio stored in feature properties; speed_avg_kmh and congestion_level stored in traffic_readings to match existing schema
- poll_interval_seconds set to 600 (rush-hour rate); off-peak skipping handled by connector itself

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

TomTom API key required. Set `TOMTOM_API_KEY` environment variable before running the connector. A free TomTom developer account provides 2,500 daily API transactions.

## Next Phase Readiness
- TomTom connector ready for production use once API key is configured
- Traffic flow data will appear in traffic_readings hypertable alongside BASt data
- Frontend traffic layer can consume both BASt and TomTom features via the existing features/traffic API

---
*Phase: 11-traffic-flow*
*Completed: 2026-04-06*
