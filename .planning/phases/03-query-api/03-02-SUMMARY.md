---
phase: 03-query-api
plan: "02"
subsystem: backend-api
tags: [fastapi, geojson, postgis, layers, connectors, spatial-queries]
dependency_graph:
  requires: [03-01]
  provides: [GET /api/layers/{domain}, GET /api/connectors/health]
  affects: [frontend map layer rendering (Phase 4), connector monitoring (PLAT-05)]
tech_stack:
  added: []
  patterns:
    - app.dependency_overrides pattern for FastAPI DB mocking in tests
    - ST_AsGeoJSON(geometry)::text cast for asyncpg WKB bypass
    - LATERAL JOIN for latest reading per feature in air_quality query
    - module-level STALE_THRESHOLD constant for connector health classification
key_files:
  created:
    - backend/app/routers/layers.py
    - backend/app/routers/connectors.py
  modified:
    - backend/app/main.py (added router mounts with /api prefix)
    - backend/pyproject.toml (asyncio_default_fixture_loop_scope=session)
    - backend/tests/conftest.py (override_get_db autouse fixture)
decisions:
  - Transit layer returns only static features (stops + route shapes) from features table — no transit_positions JOIN (per Phase 3 research scope decision)
  - Fixed 2-hour staleness threshold for connector health (poll_interval not in sources query scope)
  - response_model=None on layers endpoint to allow @context alias key in JSON output
  - override_get_db autouse fixture in conftest.py rather than per-test patch to fix event loop conflicts
metrics:
  duration_minutes: 4
  completed_date: "2026-04-05"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 3
---

# Phase 03 Plan 02: Layers and Connectors Routers Summary

One-liner: Spatial layer endpoint (GET /api/layers/{domain}) using PostGIS ST_AsGeoJSON with AQI tier injection, and connector health endpoint (GET /api/connectors/health) with staleness classification — 7 tests GREEN.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Implement layers router | c88b554 | layers.py, main.py, pyproject.toml, conftest.py |
| 2 | Implement connectors health router | 46dbeb8 | connectors.py |

## Files Created

- `backend/app/routers/layers.py` — GET /api/layers/{domain} with transit, air_quality, and generic domain queries
- `backend/app/routers/connectors.py` — GET /api/connectors/health with staleness status classification

## Files Modified

- `backend/app/main.py` — mounted `layers.router` and `connectors.router` with `/api` prefix
- `backend/pyproject.toml` — added `asyncio_default_fixture_loop_scope = "session"` to prevent event loop conflicts
- `backend/tests/conftest.py` — added `override_get_db` autouse fixture using `app.dependency_overrides`

## Key Implementation Decisions

1. **Transit layer: static features only** — The transit layer queries features + sources tables only. No JOIN to transit_positions. Consistent with Phase 3 research doc scope decision (static GTFS data for Phase 3, real-time positions for a later phase).

2. **AQI tier injection** — For air_quality domain, the LATERAL JOIN fetches the most recent reading per feature. `aqi_tier()` from `schemas/geojson.py` injects `aqi_tier` and `aqi_color` into feature properties before serialization.

3. **response_model=None on layers endpoint** — `LayerResponse` uses `Field(alias="@context")`. FastAPI's `response_model` validation would strip the `@context` key during serialization. Using `response_model=None` and returning `model.model_dump(by_alias=True)` preserves the NGSI-LD `@context` field.

4. **Fixed 2-hour staleness threshold** — The sources table does not contain `poll_interval`. A fixed `STALE_THRESHOLD = timedelta(hours=2)` is used; this can be made dynamic when poll_interval is added to the sources schema.

5. **Empty sources handled gracefully** — If no rows exist for a town, `GET /api/connectors/health` returns 200 with `connectors=[]` and a guidance message, not a 404. This matches the plan specification.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Event loop conflict: asyncpg pool bound to first test's event loop**
- **Found during:** Task 1 verification (running all 5 tests together)
- **Issue:** SQLAlchemy creates the async engine at module import time. When pytest-asyncio runs each test in a separate event loop (function scope), asyncpg's connection pool is attached to the first loop. Subsequent tests fail with `RuntimeError: Task got Future attached to a different loop`.
- **Fix 1:** Added `asyncio_default_fixture_loop_scope = "session"` to `pyproject.toml` so fixtures share one event loop.
- **Fix 2:** Added `override_get_db` autouse fixture in `conftest.py` that uses `app.dependency_overrides[get_db] = _mock_get_db` to bypass the real database entirely for all router tests. This replaces the `with patch("app.routers.layers.get_db", ...)` pattern in the test bodies, which was ineffective because FastAPI's `Depends(get_db)` captures the function object at router definition time (not via module namespace lookup).
- **Files modified:** `backend/pyproject.toml`, `backend/tests/conftest.py`
- **Commits:** c88b554

**2. [Rule 3 - Blocking] Both routers needed before first test could run**
- **Found during:** Task 1 — `main.py` imports both `layers` and `connectors` (added as part of mounting), so `connectors.py` had to exist before the layers tests could import `app.main`.
- **Fix:** Created `connectors.py` immediately after `layers.py` (before separate Task 2 commit).
- **Commits:** c88b554 (mount added), 46dbeb8 (connectors.py)

## Test Results

```
7 passed in 0.39s

tests/test_api_connectors.py::test_connector_health PASSED
tests/test_api_connectors.py::test_connector_health_unknown_town_404 PASSED
tests/test_api_layers.py::test_layers_transit_returns_geojson PASSED
tests/test_api_layers.py::test_layers_air_quality_properties PASSED
tests/test_api_layers.py::test_layer_attribution_present PASSED
tests/test_api_layers.py::test_unknown_town_404 PASSED
tests/test_api_layers.py::test_unknown_domain_404 PASSED
```

## Known Stubs

None — all response fields are wired to real data sources (or mocked empty in tests).

## Self-Check: PASSED
