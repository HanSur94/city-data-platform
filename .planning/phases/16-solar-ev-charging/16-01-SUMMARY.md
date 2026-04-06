---
phase: 16-solar-ev-charging
plan: 01
subsystem: api
tags: [solar, ev-charging, bright-sky, ocpdb, irradiance, connectors]

requires:
  - phase: 08-community-infrastructure
    provides: LadesaeulenConnector pattern and BaseConnector infrastructure
  - phase: 07-traffic-energy
    provides: MaStR solar installations in features table
provides:
  - SolarProductionConnector computing live solar output from MaStR capacity x Bright Sky irradiance
  - EvChargingConnector fetching live charger status from OCPDB API
  - energy_readings with solar_production source_type
  - Infrastructure features with live EV charger status properties
affects: [16-solar-ev-charging-frontend, energy-dashboard, infrastructure-map-layer]

tech-stack:
  added: []
  patterns: [computation-connector, features-only-connector, pure-function-extraction]

key-files:
  created:
    - backend/app/connectors/solar_production.py
    - backend/app/connectors/ev_charging.py
    - backend/app/models/solar_production.py
    - backend/tests/connectors/test_solar_production.py
    - backend/tests/connectors/test_ev_charging.py
  modified:
    - backend/app/scheduler.py
    - backend/app/schemas/geojson.py
    - backend/app/routers/layers.py
    - towns/aalen.yaml

key-decisions:
  - "Used computation connector pattern (override run()) for SolarProductionConnector, same as AirQualityGridConnector"
  - "Exposed _parse_locations() as testable method on EvChargingConnector for normalize-like testing without DB"
  - "Added source query param to infrastructure layer endpoint for OCPDB vs BNetzA separation"
  - "Disabled LadesaeulenConnector in aalen.yaml since EvChargingConnector replaces it with live data"

patterns-established:
  - "Irradiance factor computation: solar_j_cm2 priority over cloud_cover, with 0.5 fallback"
  - "OCPDB status mapping: AVAILABLE/OCCUPIED/INOPERATIVE/UNKNOWN simplification"

requirements-completed: [REQ-SOLAR-01, REQ-EV-01, REQ-EV-02, REQ-EV-03]

duration: 4min
completed: 2026-04-06
---

# Phase 16 Plan 01: Solar Production + EV Charging Connectors Summary

**Solar production connector computing live kW output from MaStR capacity x Bright Sky irradiance, plus OCPDB live EV charger status connector replacing static BNetzA data**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-06T22:16:21Z
- **Completed:** 2026-04-06T22:20:34Z
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments
- SolarProductionConnector computes irradiance factor from Bright Sky weather (cloud_cover or solar J/cm2) and multiplies by MaStR installed capacity to produce per-installation solar output
- EvChargingConnector fetches live OCPDB charger data, maps OCPI status to AVAILABLE/OCCUPIED/INOPERATIVE, classifies power (ac_slow/ac_fast/dc_fast), and upserts infrastructure features
- Both connectors registered in scheduler (solar: 900s, EV: 300s) with full attribution metadata
- 22 unit tests passing across both connectors

## Task Commits

Each task was committed atomically:

1. **Task 1: SolarProductionConnector with irradiance computation** - `a3eb8a6` (test), `2caa535` (feat)
2. **Task 2: EvChargingConnector with OCPDB live status** - `b3a04ba` (test), `69eb86d` (feat)
3. **Task 3: Register both connectors and update config** - `767f663` (feat)

_Note: TDD tasks have separate test and implementation commits._

## Files Created/Modified
- `backend/app/connectors/solar_production.py` - Computation connector: irradiance factor x MaStR capacity = live solar output
- `backend/app/connectors/ev_charging.py` - Features-only connector: OCPDB live charger status with power classification
- `backend/app/models/solar_production.py` - IrradianceFactor and SolarInstallation Pydantic models
- `backend/tests/connectors/test_solar_production.py` - 8 tests for irradiance factor and solar output pure functions
- `backend/tests/connectors/test_ev_charging.py` - 14 tests for status mapping, power classification, normalize logic
- `backend/app/scheduler.py` - Added SolarProductionConnector and EvChargingConnector to registry
- `backend/app/schemas/geojson.py` - Added attribution metadata for both connectors
- `backend/app/routers/layers.py` - Added source query param for infrastructure domain filtering
- `towns/aalen.yaml` - Added solar (900s) and EV charging (300s) connectors, disabled LadesaeulenConnector

## Decisions Made
- Used computation connector pattern (override run()) for SolarProductionConnector, same as AirQualityGridConnector -- does not use fetch/normalize pipeline
- Exposed _parse_locations() as testable method on EvChargingConnector for normalize-like testing without database dependency
- Added source query param to infrastructure layer endpoint to separate live OCPDB chargers from static BNetzA data
- Disabled LadesaeulenConnector in aalen.yaml since EvChargingConnector replaces it with live data

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required. Both APIs (Bright Sky, OCPDB) are public and require no authentication.

## Next Phase Readiness
- Solar production data ready for frontend visualization (current_output_kw in feature properties)
- EV charger live status ready for map layer with AVAILABLE/OCCUPIED/INOPERATIVE color coding
- Infrastructure source filter enables separating OCPDB live data from BNetzA static data on frontend

---
*Phase: 16-solar-ev-charging*
*Completed: 2026-04-06*
