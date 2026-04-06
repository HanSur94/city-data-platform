---
phase: 17-static-layers
plan: 01
subsystem: connectors
tags: [overpass, osm, heat-demand, cycling, geojson, energy, infrastructure]

requires:
  - phase: 08-community-infra
    provides: OverpassCommunityConnector pattern for OSM Overpass queries
provides:
  - HeatDemandConnector with simulated KEA-BW building heat demand data
  - CyclingInfraConnector with OSM cycling infrastructure classification
  - CONNECTOR_ATTRIBUTION entries for both connectors
  - aalen.yaml registration for scheduler pickup
affects: [17-static-layers, frontend-layers]

tech-stack:
  added: []
  patterns: [simulated-data-connector, cycling-tag-classification]

key-files:
  created:
    - backend/app/connectors/heat_demand.py
    - backend/app/connectors/cycling.py
    - backend/tests/connectors/test_heat_demand.py
    - backend/tests/connectors/test_cycling.py
  modified:
    - towns/aalen.yaml
    - backend/app/schemas/geojson.py

key-decisions:
  - "Deterministic seed from town ID for reproducible simulated heat demand data"
  - "Residential roads without cycling tags are skipped (not classified as 'none')"

patterns-established:
  - "Simulated data connector: deterministic RNG from town ID for reproducible synthetic data"
  - "Cycling infra classification: 5-tier system (separated/lane/advisory/shared/none) from OSM tags"

requirements-completed: [REQ-HEAT-01, REQ-CYCLE-01]

duration: 3min
completed: 2026-04-06
---

# Phase 17 Plan 01: Heat Demand + Cycling Infrastructure Connectors Summary

**Simulated KEA-BW heat demand connector with 6-tier color classification and OSM Overpass cycling infrastructure connector with 5-category infra_type system**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-06T22:33:56Z
- **Completed:** 2026-04-06T22:36:54Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- HeatDemandConnector generates 50 simulated buildings with deterministic seed, classifying heat demand into 6 tiers (blue/light_blue/green/yellow/orange/red)
- CyclingInfraConnector queries OSM Overpass for cycling-tagged ways and classifies into 5 infra_types (separated/lane/advisory/shared/none)
- Both connectors registered in aalen.yaml with daily poll interval and CONNECTOR_ATTRIBUTION entries
- 24 unit tests covering all classification thresholds and edge cases

## Task Commits

Each task was committed atomically:

1. **Task 1: HeatDemandConnector + CyclingInfraConnector with tests** (TDD)
   - `e11c9e4` (test: failing tests for both connectors)
   - `477c9da` (feat: implement both connectors, 24 tests passing)
2. **Task 2: Register connectors in aalen.yaml and CONNECTOR_ATTRIBUTION** - `779a266` (chore)

## Files Created/Modified
- `backend/app/connectors/heat_demand.py` - HeatDemandConnector with simulated KEA-BW building data and 6-tier heat_class
- `backend/app/connectors/cycling.py` - CyclingInfraConnector via Overpass with 5-tier infra_type classification
- `backend/tests/connectors/test_heat_demand.py` - 12 tests: thresholds, boundaries, empty input, source field
- `backend/tests/connectors/test_cycling.py` - 12 tests: all infra_types, residential skip, empty input, source_id format
- `towns/aalen.yaml` - Added HeatDemandConnector and CyclingInfraConnector entries
- `backend/app/schemas/geojson.py` - Added CONNECTOR_ATTRIBUTION for both connectors

## Decisions Made
- Used deterministic RNG seeded from town ID (MD5 hash) for reproducible simulated heat demand data across runs
- Residential roads without cycling tags are skipped rather than classified as "none" -- only primary/secondary/tertiary get "none" to reduce noise
- Heat demand connector uses domain="energy" with feature_type="heat_demand" to distinguish from other energy features

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - both connectors are fully functional. Heat demand uses intentionally simulated data (documented in source and attribution) since KEA-BW GeoPackage is not publicly downloadable.

## Next Phase Readiness
- Both connectors produce GeoJSON features ready for Plan 03's frontend layers
- Heat demand features have heat_class property for choropleth coloring
- Cycling features have infra_type property for line color coding

---
*Phase: 17-static-layers*
*Completed: 2026-04-06*

## Self-Check: PASSED
