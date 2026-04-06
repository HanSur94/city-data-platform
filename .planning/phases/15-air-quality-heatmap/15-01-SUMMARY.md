---
phase: 15-air-quality-heatmap
plan: 01
subsystem: api
tags: [idw, interpolation, air-quality, geospatial, grid, fastapi]

requires:
  - phase: 04-air-quality
    provides: "air_quality_readings table, UBA + Sensor.community connectors, features table with air_quality domain"
provides:
  - "AirQualityGridConnector with IDW interpolation producing grid cell features"
  - "feature_type=air_grid filter on /layers/air_quality endpoint"
  - "Pure functions idw_interpolate() and generate_grid() for reuse"
affects: [15-air-quality-heatmap]

tech-stack:
  added: []
  patterns: ["computation connector pattern (override run(), no fetch/normalize)", "feature_type filtering on layers endpoint"]

key-files:
  created:
    - backend/app/connectors/air_quality_grid.py
    - backend/app/models/air_quality_grid.py
    - backend/tests/connectors/test_air_quality_grid.py
  modified:
    - backend/app/scheduler.py
    - backend/app/routers/layers.py
    - backend/app/schemas/geojson.py
    - towns/aalen.yaml

key-decisions:
  - "Pure function extraction for IDW and grid generation enables unit testing without database"
  - "feature_type filter on layers endpoint separates grid cells from sensor points without new endpoint"

patterns-established:
  - "feature_type property filtering: use properties->>'feature_type' to separate computed vs measured features within same domain"

requirements-completed: [REQ-AIR-01, REQ-AIR-06]

duration: 3min
completed: 2026-04-06
---

# Phase 15 Plan 01: Air Quality Grid Backend Summary

**IDW interpolation connector producing grid cell features with pm25/pm10/no2/o3 values from sensor readings, filterable via feature_type=air_grid on /layers/air_quality endpoint**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-06T21:56:52Z
- **Completed:** 2026-04-06T21:59:37Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- IDW interpolation algorithm with haversine distance, power=2 weighting, zero-distance safety
- AirQualityGridConnector as computation connector reading sensor data and producing grid cell features
- 9 unit tests covering IDW edge cases (single sensor, equidistant, close/far, zero distance, None handling)
- feature_type query parameter on /layers/{domain} endpoint filtering grid cells vs sensor points

## Task Commits

Each task was committed atomically:

1. **Task 1: AirQualityGridConnector with IDW computation** - `8706371` (feat, TDD)
2. **Task 2: Register connector and add grid layer filter** - `5baf842` (feat)

## Files Created/Modified
- `backend/app/connectors/air_quality_grid.py` - AirQualityGridConnector with IDW interpolation, haversine distance, grid generation
- `backend/app/models/air_quality_grid.py` - GridCell and SensorReading Pydantic models
- `backend/tests/connectors/test_air_quality_grid.py` - 9 unit tests for IDW algorithm and grid generation
- `backend/app/scheduler.py` - Added AirQualityGridConnector to _CONNECTOR_MODULES
- `backend/app/routers/layers.py` - Added feature_type query param with air_grid filtering
- `backend/app/schemas/geojson.py` - Added AirQualityGridConnector to CONNECTOR_ATTRIBUTION
- `towns/aalen.yaml` - Added AirQualityGridConnector at 300s interval

## Decisions Made
- Pure function extraction (idw_interpolate, generate_grid) for testability without database -- same pattern as bus_interpolation.py
- feature_type query parameter on existing /layers endpoint rather than new endpoint -- keeps API surface minimal
- Grid step configurable via config.grid_step_deg (default 0.005 deg ~ 500m) -- balances resolution vs cell count

## Deviations from Plan

None -- plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None -- no external service configuration required.

## Next Phase Readiness
- Grid connector ready to produce interpolated air quality surface
- Frontend heatmap layer can query /api/layers/air_quality?feature_type=air_grid to get grid cells
- Sensor point layer continues working unchanged (default feature_type excludes grid cells)

---
*Phase: 15-air-quality-heatmap*
*Completed: 2026-04-06*
