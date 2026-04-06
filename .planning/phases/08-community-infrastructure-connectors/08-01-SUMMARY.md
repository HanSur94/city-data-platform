---
phase: 08-community-infrastructure-connectors
plan: "01"
subsystem: api
tags: [overpass, openstreetmap, osm, community, infrastructure, roadworks, connectors, geojson]

# Dependency graph
requires:
  - phase: 07-traffic-energy-connectors
    provides: BaseConnector with upsert_feature(), features-only connector pattern established

provides:
  - OverpassCommunityConnector: community POIs (school, healthcare, park, waste) from OSM Overpass API
  - OverpassRoadworksConnector: highway=construction roadworks from OSM Overpass API
  - community and infrastructure domains registered in VALID_DOMAINS
  - /api/layers/community and /api/layers/infrastructure endpoints active

affects:
  - 08-community-infrastructure-connectors (plans 02+, frontend visualization)
  - future phases needing community or infrastructure layer data

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Overpass API POI connector using consolidated single-query for all category variants
    - features-only connector pattern: fetch + upsert_feature + _update_staleness (no time-series)
    - Category mapping dict for OSM tag values to domain categories
    - Coordinate extraction: node (lat/lon top-level) vs way (center.lat/lon) elements

key-files:
  created:
    - backend/app/connectors/overpass_community.py
    - backend/app/connectors/overpass_roadworks.py
    - backend/tests/connectors/test_overpass_community.py
    - backend/tests/connectors/test_overpass_roadworks.py
  modified:
    - backend/app/schemas/geojson.py
    - backend/app/routers/layers.py
    - backend/app/connectors/__init__.py

key-decisions:
  - "Consolidated single Overpass query for all community POI types (school, healthcare, park, waste) minimizes API requests"
  - "OverpassCommunityConnector._extract_mappings() is public for testability without DB mocking"
  - "__init__.py kept as empty comment-only file to avoid eager import failures (gtfs_kit not installed in test env)"

patterns-established:
  - "Overpass community connector pattern: _extract_mappings() returns plain dicts, run() calls upsert_feature()"
  - "Coordinate extraction: lat = element.get('lat') or (element.get('center') or {}).get('lat')"
  - "source_id format for OSM data: osm:{type}:{id}"

requirements-completed: [COMM-01, COMM-02, COMM-03, COMM-04, INFR-01]

# Metrics
duration: 4min
completed: 2026-04-06
---

# Phase 8 Plan 01: Backend Foundation — Community + Infrastructure Connectors Summary

**Overpass API connectors for community POIs (school/healthcare/park/waste) and highway=construction roadworks with domain registration and 16 unit tests**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-06T18:49:31Z
- **Completed:** 2026-04-06T18:53:18Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Registered `community` and `infrastructure` domains in `VALID_DOMAINS` — `/api/layers/community` and `/api/layers/infrastructure` now return 200 with GeoJSON FeatureCollection
- Created `OverpassCommunityConnector` with consolidated single Overpass query covering all 4 community categories: school (school, kindergarten), healthcare (pharmacy, hospital, doctors, clinic, dentist), park (park, playground, sports_centre, pitch), waste (recycling, waste_disposal)
- Created `OverpassRoadworksConnector` fetching `highway=construction` elements with domain=infrastructure, category=roadwork — handles empty results gracefully
- Added `CONNECTOR_ATTRIBUTION` entries for all 4 Phase 8 connector classes (OverpassCommunity, OverpassRoadworks, Ladesaeulen, SolarPotential)
- 16 unit tests covering all category mappings, coordinate extraction (node vs way), missing coordinate skipping, source_id format, and empty result handling

## Task Commits

Each task was committed atomically:

1. **TDD RED: Failing tests for OverpassCommunityConnector** - `a4e20bf` (test)
2. **Task 1: Domain registration + OverpassCommunityConnector + tests** - `8ecce6b` (feat)
3. **Task 2: OverpassRoadworksConnector + tests** - `5773dee` (feat)

_Note: TDD tasks — RED commit (a4e20bf) followed by GREEN implementation commit (8ecce6b)_

## Files Created/Modified

- `backend/app/connectors/overpass_community.py` - OverpassCommunityConnector: consolidated Overpass query for community POIs
- `backend/app/connectors/overpass_roadworks.py` - OverpassRoadworksConnector: highway=construction roadworks connector
- `backend/app/schemas/geojson.py` - Added community/infrastructure to VALID_DOMAINS, 4 new CONNECTOR_ATTRIBUTION entries
- `backend/app/routers/layers.py` - Added community/infrastructure query branch (features-only, no time-series join)
- `backend/app/connectors/__init__.py` - Kept as comment-only stub (eager imports break test env without gtfs_kit)
- `backend/tests/connectors/test_overpass_community.py` - 9 unit tests for OverpassCommunityConnector
- `backend/tests/connectors/test_overpass_roadworks.py` - 7 unit tests for OverpassRoadworksConnector

## Decisions Made

- **Consolidated Overpass query:** One POST request fetching all community POI types avoids rate limiting and simplifies the connector. The Overpass `~"school|kindergarten|..."` regex union works efficiently.
- **`_extract_mappings()` extracted as public method:** Enables clean unit testing without database mocking. Tests call `_extract_mappings()` directly with fixture data.
- **`__init__.py` kept minimal:** Eager imports of all connectors (including GTFSConnector which requires `gtfs_kit`) break the test environment. The scheduler loads connectors by class name dynamically, so the `__init__.py` doesn't need to enumerate them.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Kept __init__.py as comment stub instead of full connector registry**
- **Found during:** Task 1 (GREEN phase, running tests)
- **Issue:** Plan spec called for registering OverpassCommunityConnector in `__init__.py` imports. Adding all connector imports caused `ModuleNotFoundError: No module named 'gtfs_kit'` in the test environment.
- **Fix:** Reverted `__init__.py` to a single comment line — connectors are loaded by name at runtime by APScheduler, not via `__init__.py` eager imports.
- **Files modified:** `backend/app/connectors/__init__.py`
- **Verification:** All 16 tests pass with the minimal `__init__.py`
- **Committed in:** `8ecce6b` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Fix was necessary for tests to run. No scope creep. Connector registry behavior unchanged — schedulers use class name strings from YAML config, not `__init__.py` imports.

## Issues Encountered

None beyond the deviation above.

## User Setup Required

None — no external service configuration required for this plan. Connectors are ready to be added to town YAML config.

## Next Phase Readiness

- Community and infrastructure domains are registered and query-ready
- Both connectors can be added to `towns/aalen.yaml` with appropriate poll intervals
- Phase 8 Plan 02+ can add frontend visualization for community and infrastructure layers
- No blockers — all 16 tests green, all acceptance criteria met

---
*Phase: 08-community-infrastructure-connectors*
*Completed: 2026-04-06*
