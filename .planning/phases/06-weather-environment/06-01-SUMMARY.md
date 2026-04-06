---
phase: 06-weather-environment
plan: 01
subsystem: api
tags: [pegelonline, water, timeseries, pydantic, fastapi, timescaledb, connector]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: base.py BaseConnector, Observation dataclass, persist() framework
  - phase: 02-first-connectors
    provides: UBAConnector pattern (fetch/normalize/run override)

provides:
  - PegelonlineConnector fetching Neckar water levels every 15 min
  - base.py persist() supporting domain="water" with INSERT INTO water_readings
  - PegelonlineStation/PegelonlineTimeseries/PegelonlineCurrentMeasurement Pydantic models
  - CONNECTOR_ATTRIBUTION["PegelonlineConnector"] in geojson.py

affects:
  - 06-weather-environment (subsequent plans using water domain)
  - future frontend water layer visualization

# Tech tracking
tech-stack:
  added: []
  patterns:
    - PegelonlineConnector follows UBAConnector pattern — fetch() then upsert_feature() per station in run() override
    - station_uuids: [] = dynamic all-stations fetch; non-empty = explicit UUID filter
    - Observations with level_cm=None are valid — hypertable accepts NULL for partial readings

key-files:
  created:
    - backend/app/models/pegelonline.py
    - backend/app/connectors/pegelonline.py
    - backend/tests/models/test_pegelonline.py
    - backend/tests/connectors/test_pegelonline.py
    - backend/tests/models/__init__.py
  modified:
    - backend/app/connectors/base.py
    - backend/app/schemas/geojson.py
    - backend/app/scheduler.py
    - towns/aalen.yaml

key-decisions:
  - "WATR-02 scope: Kocher is a state river (BW) — not in PEGELONLINE (federal only). HVZ BW has no public machine-readable API. WATR-02 fulfilled via Neckar federal stations."
  - "station_uuids: [] in aalen.yaml fetches all Neckar stations dynamically — avoids hardcoding station UUIDs that may change"
  - "run() fetches raw stations first, then upserts features (unlike UBAConnector which has fixed station config) — necessary because station set is dynamic"

patterns-established:
  - "Water domain: INSERT INTO water_readings (time, feature_id, level_cm, flow_m3s) via base.py persist() elif obs.domain == 'water'"
  - "Connector tests mock app.db.AsyncSessionLocal (not app.connectors.base.AsyncSessionLocal) — local import pattern requires patching source module"

requirements-completed:
  - WATR-01
  - WATR-02

# Metrics
duration: 4min
completed: 2026-04-06
---

# Phase 06 Plan 01: Water Domain + PegelonlineConnector Summary

**PEGELONLINE water level connector polling all Neckar stations every 15 minutes into water_readings hypertable via extended base.py persist() water branch**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-06T00:03:49Z
- **Completed:** 2026-04-06T00:07:34Z
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments

- Extended `base.py` persist() with `elif obs.domain == "water"` branch inserting into `water_readings` hypertable
- Implemented `PegelonlineConnector` following exact UBAConnector pattern — fetch/normalize/run() override with per-station feature upsert
- Created Pydantic models (`PegelonlineStation`, `PegelonlineTimeseries`, `PegelonlineCurrentMeasurement`, `PegelonlineWater`) validating PEGELONLINE REST API shapes
- Registered connector in scheduler `_CONNECTOR_MODULES` and `towns/aalen.yaml` with WATR-02 scope annotation
- 20 tests passing across models and connector (TDD red/green)

## Task Commits

Each task was committed atomically:

1. **Task 1: Pydantic models for PEGELONLINE response** - `53a7252` (feat)
2. **Task 2: base.py water branch + PegelonlineConnector** - `0be5b73` (feat)
3. **Task 3: Register connector in scheduler and aalen.yaml** - `c59ae7d` (feat)

**Plan metadata:** _(docs commit — see below)_

_Note: Tasks 1 and 2 followed TDD: failing test committed first (RED), then implementation (GREEN)._

## Files Created/Modified

- `backend/app/models/pegelonline.py` — Pydantic v2 models for PEGELONLINE REST API response
- `backend/app/connectors/pegelonline.py` — PegelonlineConnector: fetch/normalize/run() with station feature upsert
- `backend/app/connectors/base.py` — Added `elif obs.domain == "water"` branch to persist()
- `backend/app/schemas/geojson.py` — Added CONNECTOR_ATTRIBUTION["PegelonlineConnector"]
- `backend/app/scheduler.py` — Added "PegelonlineConnector" to _CONNECTOR_MODULES
- `towns/aalen.yaml` — Added PegelonlineConnector connector entry (900s interval, station_uuids: [])
- `backend/tests/models/test_pegelonline.py` — 11 model tests
- `backend/tests/connectors/test_pegelonline.py` — 9 connector tests
- `backend/tests/models/__init__.py` — Package init

## Decisions Made

- **WATR-02 scope:** Kocher is a Baden-Württemberg state river — not in PEGELONLINE (federal waterways only). HVZ BW has no public machine-readable API. WATR-02 is fulfilled by the closest available federal Neckar stations.
- **station_uuids: []** fetches all Neckar stations dynamically at runtime, avoiding hardcoded UUIDs that could become stale.
- **run() fetches raw before upsert:** Unlike UBAConnector (fixed config), stations are discovered dynamically — raw must be fetched first, then iterated to upsert each feature.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Mock patch target corrected from `app.connectors.base.AsyncSessionLocal` to `app.db.AsyncSessionLocal`**
- **Found during:** Task 2 (connector tests, GREEN phase)
- **Issue:** `base.py` uses local import pattern (`from app.db import AsyncSessionLocal` inside `persist()`). Patching `app.connectors.base.AsyncSessionLocal` fails — the name only exists in `app.db` module scope.
- **Fix:** Changed patch target to `app.db.AsyncSessionLocal` in both persist() test cases.
- **Files modified:** `backend/tests/connectors/test_pegelonline.py`
- **Verification:** All 9 connector tests pass after fix.
- **Committed in:** `0be5b73` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Necessary correction for test correctness. No scope creep.

## Issues Encountered

None beyond the mock patch target deviation documented above.

## Known Stubs

None — PegelonlineConnector is fully wired. `flow_m3s` is intentionally `None` (PEGELONLINE does not expose discharge Q measurements in this endpoint; Q requires a separate timeseries fetch).

## Next Phase Readiness

- Water domain backend is complete: hypertable writes, connector, scheduler registration
- Frontend water layer can now query `water_readings` for Neckar station levels
- `flow_m3s` always NULL — not a stub, PEGELONLINE discharge data requires separate API call (future enhancement)

---
*Phase: 06-weather-environment*
*Completed: 2026-04-06*
