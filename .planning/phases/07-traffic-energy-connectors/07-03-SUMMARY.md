---
phase: 07-traffic-energy-connectors
plan: 03
subsystem: connectors
tags: [smard, mastr, energy, open-mastr, httpx, pandas, sqlite, timeseries, spatial]

# Dependency graph
requires:
  - phase: 07-01
    provides: BaseConnector, Observation, persist(), upsert_feature(), energy domain schema

provides:
  - SmardConnector: two-step SMARD fetch, 9 generation sources + price, null filtering, renewable %, energy_readings persistence
  - MastrConnector: open-mastr bulk download, Ostalbkreis filter, Lage classification, feature upserts
  - energy branch in BaseConnector.persist() for energy_readings hypertable

affects:
  - 07-scheduler (registers connectors for APScheduler jobs)
  - 07-api (energy domain queries)
  - frontend energy layer

# Tech tracking
tech-stack:
  added:
    - open-mastr (bulk MaStR download via SQLite)
  patterns:
    - Two-step API fetch (index -> data chunk) for SMARD
    - 24h cache freshness check before bulk download (open-mastr)
    - features-only connector (no persist() call, only upsert_feature())
    - Synthetic national feature for national-grid data without coordinates

key-files:
  created:
    - backend/app/connectors/smard.py
    - backend/app/connectors/mastr.py
    - backend/tests/connectors/test_smard.py
    - backend/tests/connectors/test_mastr.py
  modified:
    - backend/app/connectors/base.py (added energy branch to persist())
    - backend/pyproject.toml (open-mastr dependency)
    - backend/uv.lock

key-decisions:
  - "SmardConnector uses synthetic national feature (source_id=smard:national, POINT(10.45 51.16)) to satisfy energy_readings FK without map coordinates"
  - "MastrConnector checks rooftop keywords (bauliche/aufdach/hausdach) BEFORE freifl to correctly handle Bauliche Anlagen (Hausdach, Gebaeude und Freiflaechenanlagen)"
  - "open-mastr download cached for 24h via SQLite mtime check to avoid repeated multi-minute bulk downloads"
  - "MastrConnector.normalize() returns empty list (features-only) — no time-series observations"

patterns-established:
  - "Energy branch in BaseConnector.persist(): INSERT INTO energy_readings (time, feature_id, value_kw, source_type)"
  - "classify_installation() module-level function for testability without connector instantiation"
  - "_filter_by_landkreis() helper on connector for DataFrame filtering testability"

requirements-completed:
  - ENRG-01
  - ENRG-02
  - ENRG-03

# Metrics
duration: 3min
completed: 2026-04-06
---

# Phase 07 Plan 03: Energy Connectors (SMARD + MaStR) Summary

**SMARD two-step connector persists 9 electricity generation sources + wholesale price to energy_readings; MaStR connector downloads bulk registry, filters to Ostalbkreis, classifies solar_rooftop/solar_ground/wind/battery, upserts spatial features**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-06T17:44:13Z
- **Completed:** 2026-04-06T17:47:30Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- SmardConnector implements SMARD two-step fetch (index -> data chunk), filters null values, computes renewable %, persists generation mix + price to energy_readings hypertable
- MastrConnector downloads bulk MaStR data via open-mastr (with 24h cache), filters to Ostalbkreis, classifies each installation, upserts spatial features
- Added energy branch to BaseConnector.persist() for energy_readings hypertable writes
- 10 tests GREEN (6 SMARD + 4 MaStR)

## Task Commits

Each task was committed atomically:

1. **Task 1: SMARD electricity generation mix + wholesale price connector** - `21b7035` (feat)
2. **Task 2: MaStR renewable energy installations connector** - `93f15a2` (feat)

**Plan metadata:** (docs commit below)

_Note: TDD tasks — tests written first in RED state, then implementation brought them GREEN_

## Files Created/Modified

- `backend/app/connectors/smard.py` - SmardConnector with two-step fetch, null filtering, renewable %, synthetic national feature
- `backend/app/connectors/mastr.py` - MastrConnector with open-mastr integration, Ostalbkreis filter, Lage classification
- `backend/app/connectors/base.py` - Added energy branch to persist() for energy_readings hypertable
- `backend/tests/connectors/test_smard.py` - 6 tests: two-step fetch, null filtering, renewable %, zero total, filter count, price filter value
- `backend/tests/connectors/test_mastr.py` - 4 tests: Landkreis filter, Lage field mapping, normalize returns empty, constant value
- `backend/pyproject.toml` - Added open-mastr dependency
- `backend/uv.lock` - Updated lockfile

## Decisions Made

- Used synthetic national feature (POINT(10.45 51.16) center of Germany) for SMARD data to satisfy energy_readings foreign key without geographic coordinates
- Checked rooftop keywords before "freifl" in _classify_installation to correctly handle the canonical Lage value "Bauliche Anlagen (Hausdach, Gebaeude und Freiflaechenanlagen)" which contains "freiflaechenanlagen" but is rooftop
- 24h cache freshness check on open-mastr SQLite DB to avoid repeated multi-minute bulk downloads during normal polling

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added energy branch to BaseConnector.persist()**
- **Found during:** Task 1 (SMARD connector implementation)
- **Issue:** base.py persist() had no "energy" domain branch — SMARD observations would be silently dropped
- **Fix:** Added elif obs.domain == "energy" branch with INSERT INTO energy_readings (time, feature_id, value_kw, source_type)
- **Files modified:** backend/app/connectors/base.py
- **Verification:** SmardConnector tests pass, energy observations would reach DB
- **Committed in:** 21b7035 (Task 1 commit)

**2. [Rule 1 - Bug] Fixed Lage classification order in _classify_installation**
- **Found during:** Task 2 (MaStR test run)
- **Issue:** "Bauliche Anlagen (Hausdach, Gebaeude und Freiflaechenanlagen)" was classified as "solar_ground" because "freifl" check fired before "bauliche"/"hausdach" check
- **Fix:** Moved rooftop keyword check before ground-mounted check in _classify_installation
- **Files modified:** backend/app/connectors/mastr.py
- **Verification:** test_mastr_lage_field_mapping passes with all 5 classification cases correct
- **Committed in:** 93f15a2 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 missing critical, 1 bug)
**Impact on plan:** Both auto-fixes necessary for correctness. No scope creep.

## Issues Encountered

- open-mastr adds ~750 transitive dependencies (pandas, geopandas, lxml, etc.) — install took ~60s but is a one-time cost

## User Setup Required

None — connectors will run automatically via APScheduler when registered. open-mastr downloads data from BNetzA open API requiring no credentials.

## Next Phase Readiness

- Both energy connectors implemented and tested GREEN
- energy_readings hypertable write path verified via persist() energy branch
- SmardConnector and MastrConnector importable and ready for APScheduler registration in Phase 07 scheduler plan
- MaStR bulk download will trigger on first run (~5-10 minutes); subsequent runs use 24h cache

---
*Phase: 07-traffic-energy-connectors*
*Completed: 2026-04-06*

## Self-Check: PASSED

- FOUND: backend/app/connectors/smard.py
- FOUND: backend/app/connectors/mastr.py
- FOUND: backend/tests/connectors/test_smard.py
- FOUND: backend/tests/connectors/test_mastr.py
- FOUND: .planning/phases/07-traffic-energy-connectors/07-03-SUMMARY.md
- FOUND commit: 21b7035 (feat: SMARD connector)
- FOUND commit: 93f15a2 (feat: MaStR connector)
