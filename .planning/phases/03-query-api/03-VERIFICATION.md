---
phase: 03-query-api
verified: 2026-04-05T00:00:00Z
status: gaps_found
score: 4/5 must-haves verified
gaps:
  - truth: "GET /api/kpi?town=aalen returns current AQI, weather summary, and transit coverage metrics"
    status: failed
    reason: "test_kpi_fields fails at runtime: kpi.py line 60 calls aqi_tier(aq_row['current_aqi']) without guarding against a MagicMock return value. The conftest override_get_db autouse fixture provides a MagicMock session; mappings().first() returns a MagicMock (truthy), so aq_row is not None; aq_row['current_aqi'] returns another MagicMock; aqi_tier() receives it and crashes on 'MagicMock <= float'. The fix is to coerce the value: cast to float or guard with isinstance before calling aqi_tier."
    artifacts:
      - path: "backend/app/routers/kpi.py"
        issue: "Line 60: `aqi_tier(aq_row['current_aqi'] if aq_row else None)` — does not guard against aq_row being a truthy MagicMock with a non-float 'current_aqi'. Needs `aqi_tier(float(aq_row['current_aqi']) if (aq_row and aq_row['current_aqi'] is not None) else None)` or equivalent None-safe coercion."
    missing:
      - "Guard aqi_tier call in kpi.py so a None or non-numeric aq_row['current_aqi'] value does not reach the float comparison in aqi_tier(). One safe pattern: `_aqi_val = aq_row['current_aqi'] if aq_row else None; tier, color = aqi_tier(float(_aqi_val) if _aqi_val is not None else None)`"
human_verification:
  - test: "Run docker-compose up and hit GET http://localhost:8000/api/layers/transit?town=aalen"
    expected: "200 response with type=FeatureCollection; features list may be empty if Phase 2 GTFS connector has not run, but response shape must be valid GeoJSON"
    why_human: "Real PostGIS ST_AsGeoJSON geometry serialisation and GTFS feature data can only be confirmed with the full Docker stack running"
  - test: "Run docker-compose up, wait for GTFS connector to run, then GET /api/layers/air_quality?town=aalen"
    expected: "Features include aqi_tier and aqi_color properties populated by aqi_tier() function"
    why_human: "AQI tier injection requires live air_quality_readings in TimescaleDB from a connector run"
  - test: "GET /api/connectors/health?town=aalen after running docker-compose up"
    expected: "Connectors list is non-empty and each item has status one of 'ok', 'stale', 'never_fetched'"
    why_human: "Sources table is only populated after scheduler.start() runs connectors at least once"
---

# Phase 3: Query API Verification Report

**Phase Goal:** FastAPI exposes clean, town-scoped GeoJSON, time-series, and KPI endpoints that the frontend can consume without ever touching the database directly
**Verified:** 2026-04-05
**Status:** gaps_found — 1 test failing (test_kpi_fields), 4/5 truths verified
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | GET /api/layers/transit?town=aalen returns a valid GeoJSON FeatureCollection | ✓ VERIFIED | layers.py implements ST_AsGeoJSON query, response_model=None with model_dump(by_alias=True), test passes |
| 2 | GET /api/layers/air_quality?town=aalen returns GeoJSON with AQI tier color values | ✓ VERIFIED | LATERAL JOIN for latest reading, aqi_tier() injection into feature properties, test passes |
| 3 | GET /api/timeseries/air_quality returns time-ordered readings for the requested window | ✓ VERIFIED | timeseries.py queries air_quality_readings with start/end bounds, ORDER BY time ASC, 3/3 timeseries tests pass |
| 4 | GET /api/kpi?town=aalen returns current AQI, weather summary, transit metrics | ✗ FAILED | test_kpi_fields fails: MagicMock from conftest mock session flows into aqi_tier() which cannot compare MagicMock to float. 1/2 KPI tests pass (404 test passes). |
| 5 | Every endpoint response includes attribution and last_updated; unknown town returns 404 | ✓ VERIFIED | All routers validate town != current_town.id → 404; all schemas include attribution and last_updated fields; attribution tests pass |

**Score:** 4/5 truths verified

### Required Artifacts

| Artifact | Provides | Status | Details |
|----------|---------|--------|---------|
| `backend/app/dependencies.py` | get_current_town() / set_current_town() | ✓ VERIFIED | Exists, 22 lines, exports both functions, no circular import |
| `backend/app/schemas/geojson.py` | Attribution, LayerResponse, VALID_DOMAINS, CONNECTOR_ATTRIBUTION, aqi_tier | ✓ VERIFIED | All symbols present, aqi_tier(25.0) returns ("moderate", "#ffeb3b") |
| `backend/app/schemas/responses.py` | TimeseriesResponse, KPIResponse, ConnectorHealthResponse, ConnectorHealthItem | ✓ VERIFIED | All classes present with correct fields |
| `backend/app/routers/layers.py` | GET /api/layers/{domain} | ✓ VERIFIED | 175 lines, real PostGIS query with ST_AsGeoJSON, AQI injection, exports router |
| `backend/app/routers/connectors.py` | GET /api/connectors/health | ✓ VERIFIED | 83 lines, sources table query with staleness classification |
| `backend/app/routers/timeseries.py` | GET /api/timeseries/{domain} | ✓ VERIFIED | 161 lines, air_quality and weather queries with time-range validation |
| `backend/app/routers/kpi.py` | GET /api/kpi | ⚠️ PARTIAL | 164 lines, real TimescaleDB last() aggregate queries, but aqi_tier call fails under mock (see gap) |
| `backend/app/main.py` | All four routers mounted under /api prefix | ✓ VERIFIED | All five required routes registered: /api/layers/{domain}, /api/timeseries/{domain}, /api/kpi, /api/connectors/health, /health |
| `backend/tests/test_api_layers.py` | 5 layer tests | ✓ VERIFIED | 5/5 passing |
| `backend/tests/test_api_timeseries.py` | 3 timeseries tests | ✓ VERIFIED | 3/3 passing |
| `backend/tests/test_api_kpi.py` | 2 KPI tests | ✗ PARTIAL | 1/2 passing; test_kpi_fields fails |
| `backend/tests/test_api_connectors.py` | 2 connector health tests | ✓ VERIFIED | 2/2 passing |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| backend/app/main.py | backend/app/dependencies.py | `from app.dependencies import set_current_town, get_current_town` | ✓ WIRED | Confirmed in main.py line 14 |
| backend/app/routers/layers.py | backend/app/dependencies.py | `from app.dependencies import get_current_town` | ✓ WIRED | Confirmed in layers.py line 14 |
| backend/app/routers/layers.py | PostGIS features table | `ST_AsGeoJSON(f.geometry)::text` in SQL | ✓ WIRED | Pattern found at line 50 |
| backend/app/routers/connectors.py | sources table | `FROM sources WHERE town_id = :town_id` | ✓ WIRED | Confirmed at connectors.py line 41 |
| backend/app/routers/timeseries.py | air_quality_readings hypertable | `FROM air_quality_readings` with time range | ✓ WIRED | Confirmed in timeseries.py line 56 |
| backend/app/routers/kpi.py | air_quality_readings, weather_readings, features | `last(aqi, time)` TimescaleDB aggregate | ✓ WIRED | SQL at kpi.py lines 43-56, 66-79, 88-100 |
| backend/app/main.py | app.routers.* | `app.include_router(router, prefix='/api')` | ✓ WIRED | Four include_router calls at main.py lines 50-53 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| routers/layers.py | `rows` (features list) | `SELECT ... FROM features JOIN sources` with `ST_AsGeoJSON` | Yes — real SQL with PostGIS | ✓ FLOWING |
| routers/connectors.py | `items` (connector list) | `SELECT ... FROM sources WHERE town_id` | Yes — real SQL | ✓ FLOWING |
| routers/timeseries.py | `points` (TimeseriesPoint list) | `SELECT ... FROM air_quality_readings JOIN features` | Yes — real SQL with time bounds | ✓ FLOWING |
| routers/kpi.py | `aq_row`, `wx_row`, `tr_row` | TimescaleDB `last()` aggregates | Yes — real SQL, but aqi_tier() call crashes under mock | ⚠️ PARTIAL |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All schemas importable | `python -c "from app.schemas.geojson import ...; from app.schemas.responses import ..."` | All imports OK | ✓ PASS |
| aqi_tier(25.0) returns correct tier | `python -c "...; assert tier == 'moderate'"` | ("moderate", "#ffeb3b") | ✓ PASS |
| All routers importable | `python -c "from app.routers.layers import router as lr; ..."` | All router imports OK | ✓ PASS |
| All required endpoints registered | `python -c "from app.main import app; ..."` | All 5 routes present | ✓ PASS |
| 12 API tests run | `pytest test_api_layers.py test_api_timeseries.py test_api_kpi.py test_api_connectors.py` | 11 passed, 1 failed | ✗ FAIL — test_kpi_fields |
| geojson-pydantic installed | `grep geojson-pydantic pyproject.toml` | `geojson-pydantic==2.1.0` | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|------------|------------|-------------|--------|---------|
| PLAT-03 | 03-01, 03-02, 03-03 | NGSI-LD compatible API layer (Smart Data Models schemas) | ✓ SATISFIED | LayerResponse uses @context = NGSI FIWARE URL; GeoJSON FeatureCollection structure; all four endpoint types implemented |
| PLAT-04 | 03-01, 03-02, 03-03 | Data source attribution display (Datenlizenz Deutschland compliance) | ✓ SATISFIED | CONNECTOR_ATTRIBUTION dict maps connector classes to DL-DE-BY-2.0 metadata; attribution field present in LayerResponse, TimeseriesResponse, KPIResponse |
| PLAT-05 | 03-01, 03-02 | Connector health monitoring — staleness detection, last-update timestamps | ✓ SATISFIED | connectors.py queries sources table, classifies "ok"/"stale"/"never_fetched" with 2-hour threshold; 2/2 connector tests pass |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|---------|--------|
| backend/app/routers/kpi.py | 60 | `aqi_tier(aq_row["current_aqi"] if aq_row else None)` — no type guard on the value | ✗ BLOCKER | Causes TypeError in test environment (and in production when DB returns NULL-typed row object); test_kpi_fields fails |
| backend/app/routers/connectors.py | 74 | `except Exception: items = []` — bare exception swallows all errors | ⚠️ WARNING | Silent failure: any bug in the DB query is hidden; returns empty connectors list rather than surfacing the error |
| backend/app/routers/timeseries.py | 124-144 | `except Exception: attributions = []` — bare exception on attribution query | ⚠️ WARNING | Attribution silently disappears on any DB error |
| backend/app/routers/kpi.py | 39-58, 64-80, 87-101, 107-124 | Four separate `try/except Exception` blocks swallowing all errors | ⚠️ WARNING | All KPI domain queries degrade silently to None; production errors are invisible |

### Human Verification Required

#### 1. Live GeoJSON Layer Response

**Test:** Run `docker-compose up`, wait for startup, then `curl "http://localhost:8000/api/layers/transit?town=aalen"`
**Expected:** 200 response with `type=FeatureCollection`, `@context` key present, `attribution` list, `last_updated` field; `features` may be empty if GTFS connector has not run yet but structure must be valid
**Why human:** Full PostGIS ST_AsGeoJSON geometry serialisation and response shape with real data requires the Docker stack

#### 2. AQI Tier Injection in Live Data

**Test:** After air quality connector has run at least once, `curl "http://localhost:8000/api/layers/air_quality?town=aalen"`
**Expected:** Feature properties include `aqi_tier` (one of "good", "moderate", "poor", "bad", "very_bad") and `aqi_color` hex string
**Why human:** aqi_tier injection requires live readings in TimescaleDB

#### 3. Connector Health With Live Data

**Test:** After scheduler has run connectors, `curl "http://localhost:8000/api/connectors/health?town=aalen"`
**Expected:** `connectors` list is non-empty; each entry has `status` one of "ok", "stale", "never_fetched"; `last_successful_fetch` is a valid ISO timestamp or null
**Why human:** Sources table only has rows after connectors have registered themselves via the scheduler

### Gaps Summary

**One gap blocking full goal achievement:** `test_kpi_fields` fails because `kpi.py` does not defend against a truthy-but-non-numeric mock row value flowing into `aqi_tier()`. The bug is in `kpi.py` line 60: the guard `if aq_row else None` only checks truthiness of the row object; it does not guard against `aq_row["current_aqi"]` being a non-float value (MagicMock in test, potentially NULL-coerced object in certain database driver states). The fix is a one-line change to coerce the value safely before passing to aqi_tier:

```python
_aqi_val = aq_row["current_aqi"] if aq_row else None
tier, color = aqi_tier(float(_aqi_val) if isinstance(_aqi_val, (int, float)) else None)
```

This gap is isolated to kpi.py line 60 — no other files need changes. The other three bare `except Exception` blocks are warnings, not blockers (they have no failing tests), but they represent technical debt that should be addressed before Phase 4 integration.

**Note on ROADMAP.md vs actual state:** The ROADMAP.md progress table shows Plan 02 as unchecked (`[ ]`) while Plans 01 and 03 are checked. The 03-02-SUMMARY.md and actual codebase show layers.py and connectors.py are fully implemented and all 7 Plan 02 tests pass. The ROADMAP.md checkbox should be updated to `[x]` for 03-02.

---

_Verified: 2026-04-05_
_Verifier: Claude (gsd-verifier)_
