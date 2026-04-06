---
phase: 06-weather-environment
plan: 03
subsystem: api
tags: [lubw, wfs, geojson, shapely, environmental-zones, water, connector]

# Dependency graph
requires:
  - phase: 06-weather-environment/06-01
    provides: base connector infrastructure, features table, upsert_feature()

provides:
  - LubwWfsConnector fetching Naturschutzgebiet + Wasserschutzgebiet polygons into features table
  - Pydantic models for LUBW WFS GeoJSON response validation
  - CONNECTOR_ATTRIBUTION entry for LUBW in geojson.py
  - LubwWfsConnector registered in scheduler and aalen.yaml (86400s daily poll)

affects:
  - 06-weather-environment
  - frontend map layers (water domain)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "WFS polygon connector: fetch full FC dict → validate via Pydantic → centroid via shapely → upsert_feature(domain='water')"
    - "Shapely-first with ring-average fallback for centroid computation"

key-files:
  created:
    - backend/app/connectors/lubw_wfs.py
    - backend/app/models/lubw_wfs.py
    - backend/tests/connectors/test_lubw_wfs.py
  modified:
    - backend/app/schemas/geojson.py
    - backend/app/scheduler.py
    - towns/aalen.yaml

key-decisions:
  - "LubwWfsConnector.fetch() returns full FeatureCollection dicts (not lists) to allow LubwWfsFeatureCollection.model_validate() in run()"
  - "Centroid approach used for polygon features: shapely.centroid first, ring-average fallback — avoids storing full polygon WKT while enabling map display"
  - "Empty WFS response (0 features in bbox) is valid success — run() completes and calls _update_staleness()"

patterns-established:
  - "WFS polygon connector pattern: override run(), fetch FC dicts per endpoint, validate with Pydantic, compute centroid WKT, upsert as domain features"

requirements-completed:
  - WATR-05

# Metrics
duration: 4min
completed: 2026-04-06
---

# Phase 06 Plan 03: LUBW WFS Environmental Connector Summary

**LUBW WFS connector fetching Naturschutzgebiet and Wasserschutzgebiet polygon centroids into features table via daily poll, using shapely for centroid computation**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-06T00:09:57Z
- **Completed:** 2026-04-06T00:13:14Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- LubwWfsConnector fetches two LUBW WFS endpoints (Naturschutzgebiet + Wasserschutzgebiet) with bbox from town config
- Features stored via upsert_feature(domain="water") with centroid point geometry computed via shapely
- Empty WFS response (no zones in bbox) handled gracefully — connector completes without error
- Registered in scheduler._CONNECTOR_MODULES and aalen.yaml with 86400s poll interval

## Task Commits

Each task was committed atomically:

1. **RED phase: failing tests** - `4ac9e46` (test)
2. **Task 1: Pydantic models + LubwWfsConnector** - `576f609` (feat)
3. **Task 2: Register in scheduler + aalen.yaml** - `b405327` (feat)

## Files Created/Modified
- `backend/app/models/lubw_wfs.py` - Pydantic models: LubwWfsFeatureCollection, LubwWfsFeature, LubwWfsGeometry
- `backend/app/connectors/lubw_wfs.py` - LubwWfsConnector fetching both WFS endpoints, centroid extraction, upsert_feature()
- `backend/tests/connectors/test_lubw_wfs.py` - 9 tests covering run() behavior, empty FC, model validation, source_id format
- `backend/app/schemas/geojson.py` - Added LubwWfsConnector attribution (LUBW, DL-DE-BY-2.0)
- `backend/app/scheduler.py` - Added "LubwWfsConnector": "app.connectors.lubw_wfs" to _CONNECTOR_MODULES
- `towns/aalen.yaml` - Added LubwWfsConnector entry with poll_interval_seconds=86400

## Decisions Made
- `fetch()` returns full FeatureCollection dicts (not lists) to cleanly hand off to `LubwWfsFeatureCollection.model_validate()` — the mock in tests matched this shape which exposed an initial type mismatch (auto-fixed inline)
- Centroid approach for polygon storage: stores a POINT in features table from shapely centroid (with ring-average fallback). Full polygon shape for WMS overlay is deferred to Plan 04 as stated in the plan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed fetch() return type mismatch in run()**
- **Found during:** Task 1 GREEN phase (first test run)
- **Issue:** Initial implementation had `fetch()` returning `dict[str, list[dict]]` (list of feature dicts) but `run()` tried to validate it as a full FC dict. Tests correctly caught this with a Pydantic ValidationError.
- **Fix:** Changed `fetch()` to return `dict[str, dict]` (full FC dicts) and `run()` to call `model_validate(fc_dict)` directly.
- **Files modified:** backend/app/connectors/lubw_wfs.py
- **Verification:** All 9 tests pass after fix
- **Committed in:** 576f609 (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug)
**Impact on plan:** Minor type contract fix, no scope change.

## Issues Encountered
None beyond the type mismatch auto-fixed above.

## User Setup Required
None - no external service configuration required. LUBW WFS is a public endpoint requiring no API key.

## Next Phase Readiness
- LubwWfsConnector is live and registered — will upsert environmental zone features on next scheduler run
- Water layer endpoint (/api/layers/water?town=aalen) will return Naturschutzgebiet and Wasserschutzgebiet features with their properties
- Plan 04 (WMS overlay) can use these features as anchors for polygon display

## Known Stubs
None - connector is fully wired. Polygon centroids are intentional per plan design (full polygon shape via WMS in Plan 04).

---
*Phase: 06-weather-environment*
*Completed: 2026-04-06*
