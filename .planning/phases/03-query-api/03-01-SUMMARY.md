---
phase: 03-query-api
plan: "01"
subsystem: backend-api
tags: [schemas, dependencies, tdd, geojson, pydantic]
dependency_graph:
  requires: []
  provides:
    - app.dependencies.get_current_town
    - app.dependencies.set_current_town
    - app.schemas.geojson.LayerResponse
    - app.schemas.geojson.Attribution
    - app.schemas.geojson.CONNECTOR_ATTRIBUTION
    - app.schemas.geojson.VALID_DOMAINS
    - app.schemas.geojson.aqi_tier
    - app.schemas.responses.TimeseriesResponse
    - app.schemas.responses.KPIResponse
    - app.schemas.responses.ConnectorHealthResponse
    - app.schemas.responses.ConnectorHealthItem
  affects:
    - backend/app/main.py (refactored to use dependencies.py)
tech_stack:
  added:
    - geojson-pydantic==2.1.0
  patterns:
    - FastAPI dependency injection via dependencies.py module
    - TDD RED phase — test stubs written before router implementation
    - Pydantic v2 response schemas with model_config and Field aliases
key_files:
  created:
    - backend/app/dependencies.py
    - backend/app/schemas/__init__.py
    - backend/app/schemas/geojson.py
    - backend/app/schemas/responses.py
    - backend/app/routers/__init__.py
    - backend/tests/test_api_layers.py
    - backend/tests/test_api_timeseries.py
    - backend/tests/test_api_kpi.py
    - backend/tests/test_api_connectors.py
  modified:
    - backend/app/main.py (extracted get_current_town/set_current_town to dependencies.py)
    - backend/pyproject.toml (added geojson-pydantic==2.1.0)
decisions:
  - "get_current_town moved to dependencies.py to prevent circular imports when routers import it"
  - "TownBbox used in MOCK_TOWN fixtures (not flat list) — matches actual Town model from config.py"
  - "asyncio_mode=auto in pyproject.toml means @pytest.mark.asyncio marks are redundant but kept for clarity"
metrics:
  duration_seconds: 210
  completed_date: "2026-04-05"
  tasks_completed: 2
  files_created: 9
  files_modified: 2
---

# Phase 03 Plan 01: Foundation — Dependencies, Schemas, Test Stubs Summary

**One-liner:** Created dependencies.py with get_current_town/set_current_town, full schema package (geojson + responses), routers package, and 12 RED failing test stubs across 4 test files.

## What Was Built

### geojson-pydantic Installation
- Added `geojson-pydantic==2.1.0` to backend/pyproject.toml via `uv add`
- Installed and importable in the backend virtualenv

### backend/app/dependencies.py
- Extracted `_current_town` module-level state and `get_current_town()` from main.py
- Added `set_current_town()` setter called by main.py lifespan on startup
- Eliminates circular import: routers can import `get_current_town` without importing `main.py`

### backend/app/main.py (refactored)
- Removed local `_current_town` variable and `get_current_town()` definition
- Added `from app.dependencies import set_current_town, get_current_town`
- Lifespan now calls `set_current_town(town)` instead of direct assignment
- `/health` endpoint uses imported `get_current_town()` with try/except

### backend/app/schemas/geojson.py
Exports:
- `NGSI_CONTEXT` — FIWARE context URL
- `CONNECTOR_ATTRIBUTION` — dict mapping connector class names to DL-DE-BY-2.0 metadata
- `VALID_DOMAINS` — frozenset of valid domain path parameters
- `AQI_TIERS` — WHO/UBA health tier thresholds
- `aqi_tier(value)` — function returning (tier_label, hex_color) tuple
- `Attribution` — Pydantic model for data attribution metadata
- `LayerResponse` — GeoJSON FeatureCollection response schema with @context alias

### backend/app/schemas/responses.py
Exports:
- `TimeseriesPoint`, `TimeseriesResponse` — time-series reading schemas
- `AirQualityKPI`, `WeatherKPI`, `TransitKPI`, `KPIResponse` — dashboard KPI schemas
- `ConnectorHealthItem`, `ConnectorHealthResponse` — connector staleness schemas

### backend/app/routers/__init__.py
- Empty package placeholder — routers (layers, timeseries, kpi, connectors) to be implemented in Plans 02 and 03

### Test Stubs (RED State)
All 12 tests fail with `AttributeError: module 'app.routers' has no attribute 'layers'` (or similar for other routers) because the router modules do not exist yet. This is the expected RED state.

| Test File | Tests | Covers |
|-----------|-------|--------|
| test_api_layers.py | 5 | PLAT-03 (GeoJSON layers), PLAT-04 (attribution) |
| test_api_timeseries.py | 3 | PLAT-03 (timeseries), PLAT-04 (last_updated) |
| test_api_kpi.py | 2 | PLAT-03 (KPI fields + unknown town 404) |
| test_api_connectors.py | 2 | PLAT-05 (connector health + unknown town 404) |

## Key Contracts for Plans 02 and 03

### Town Model Fields (confirmed from config.py)
```python
Town(
    id="aalen",                    # str slug
    display_name="Aalen",          # str
    country="DE",                  # str (default "DE")
    timezone="Europe/Berlin",      # str (default "Europe/Berlin")
    bbox=TownBbox(                 # TownBbox object (NOT flat list)
        lon_min=9.9,
        lat_min=48.7,
        lon_max=10.2,
        lat_max=48.9,
    ),
    connectors=[],                 # list[ConnectorConfig]
)
```

### Import Paths
```python
from app.dependencies import get_current_town, set_current_town
from app.schemas.geojson import LayerResponse, Attribution, CONNECTOR_ATTRIBUTION, VALID_DOMAINS, aqi_tier
from app.schemas.responses import TimeseriesResponse, KPIResponse, ConnectorHealthResponse, ConnectorHealthItem
```

### CONNECTOR_ATTRIBUTION Keys
- `"UBAConnector"` — Umweltbundesamt air quality
- `"SensorCommunityConnector"` — Sensor.Community citizen sensors
- `"GTFSConnector"` — MobiData BW / NVBW GTFS
- `"GTFSRealtimeConnector"` — MobiData BW / NVBW GTFS-RT
- `"WeatherConnector"` — DWD via Bright Sky

### aqi_tier() Function
```python
aqi_tier(25.0)  # → ("moderate", "#ffeb3b")
aqi_tier(None)  # → ("unknown", "#9e9e9e")
aqi_tier(0.0)   # → ("good", "#00c853")  (≤20.0)
```

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | a928e1d | feat(03-01): install geojson-pydantic, create dependencies/schemas/routers packages |
| Task 2 | 9a6c46b | test(03-01): write failing test stubs for all API routers (RED state) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed MOCK_TOWN constructor in test stubs**
- **Found during:** Task 2
- **Issue:** Plan showed `bbox=[9.9, 48.7, 10.2, 48.9]` (flat list) but `Town.bbox` requires a `TownBbox` object with named fields `lon_min`, `lat_min`, `lon_max`, `lat_max`
- **Fix:** Used `bbox=TownBbox(lon_min=9.9, lat_min=48.7, lon_max=10.2, lat_max=48.9)` in all four test files
- **Files modified:** test_api_layers.py, test_api_timeseries.py, test_api_kpi.py, test_api_connectors.py
- **Commit:** 9a6c46b

**2. [Rule 1 - Bug] Changed @pytest.mark.anyio to @pytest.mark.asyncio**
- **Found during:** Task 2
- **Issue:** Plan specified `@pytest.mark.anyio` but project uses `pytest-asyncio` (not `pytest-anyio`); `asyncio_mode = "auto"` in pyproject.toml handles async fixtures automatically
- **Fix:** Used `@pytest.mark.asyncio` markers to match the project's existing test toolchain
- **Files modified:** All four test files
- **Commit:** 9a6c46b

## Known Stubs

None — this plan creates schemas and test stubs, not feature implementations. All "empty" structures (empty routers package, empty schemas/__init__.py) are intentional package placeholders, not data stubs.

## Self-Check: PASSED
