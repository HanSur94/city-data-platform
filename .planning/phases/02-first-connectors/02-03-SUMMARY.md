---
phase: 02-first-connectors
plan: "03"
subsystem: data-ingestion
tags: [weather, bright-sky, dwd, pydantic, httpx, timescaledb, hypertable]

# Dependency graph
requires:
  - phase: 02-01
    provides: BaseConnector with upsert_feature, persist (weather domain), _update_staleness
  - phase: 01-foundation
    provides: Observation dataclass, ConnectorConfig, Town models
provides:
  - WeatherConnector with current_weather (WAIR-01) and MOSMIX forecast (WAIR-02)
  - BrightSkyWeather and BrightSkyForecastEntry Pydantic models in app/models/weather.py
  - Integration tests calling live Bright Sky API (6 tests, all green)
affects: [02-04, 02-05, frontend map weather layer, Phase 04 dashboard]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_ensure_feature pattern: override run() to upsert_feature once, cache self._feature_id, then fetch/normalize/persist/_update_staleness"
    - "Pydantic model validation of external API responses before Observation creation"
    - "source_id_to_type lookup dict for filtering forecast entries by observation_type"
    - "All numeric weather fields typed as float | None to safely handle missing DWD data"

key-files:
  created:
    - backend/app/connectors/weather.py
    - backend/app/models/weather.py
    - backend/app/models/__init__.py
    - backend/tests/connectors/test_weather.py
  modified: []

key-decisions:
  - "lat/lon read from ConnectorConfig.config (default 48.84/10.09) — no Aalen hardcoding in connector class"
  - "Forecast filtered to MOSMIX-only entries via sources list lookup (observation_type=='forecast')"
  - "wind_direction typed as float|None in Pydantic model — API returns integer but float is correct DB type"
  - "app/models/ directory created for Pydantic API response models (separate from domain models)"

patterns-established:
  - "Pydantic models for external API responses live in app/models/ — named after the data source (e.g. weather.py)"
  - "_weather_values() static helper extracts dict from Pydantic model — keeps normalize() clean and testable"
  - "TDD cycle: RED (ImportError) -> commit test -> GREEN (all pass) -> commit implementation"

requirements-completed: [WAIR-01, WAIR-02]

# Metrics
duration: 8min
completed: 2026-04-05
---

# Phase 02 Plan 03: WeatherConnector Summary

**WeatherConnector writing current conditions and 48-hour MOSMIX forecast to weather_readings hypertable via Bright Sky API (DWD data, no auth required)**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-05T18:49:00Z
- **Completed:** 2026-04-05T18:57:00Z
- **Tasks:** 1 (TDD — 2 commits)
- **Files modified:** 4 created

## Accomplishments
- WeatherConnector fetches Aalen current weather (WAIR-01) and 48-hour MOSMIX forecast (WAIR-02) from Bright Sky API
- Both current and forecast Observations written to weather_readings hypertable via BaseConnector.persist()
- BrightSkyWeather and BrightSkyForecastEntry Pydantic models with all numeric fields typed float|None
- Integration tests call live Bright Sky API — 6/6 pass with real DWD data

## Task Commits

Each task was committed atomically (TDD cycle: test then implementation):

1. **Task 1 RED: failing test file** - `cc8dd4b` (test)
2. **Task 1 GREEN: WeatherConnector + models** - `71f325f` (feat)

**Plan metadata:** (docs commit — see below)

_Note: TDD task produced two commits per cycle (test RED → implementation GREEN)_

## Files Created/Modified
- `backend/app/connectors/weather.py` - WeatherConnector with fetch(), normalize(), run() override
- `backend/app/models/weather.py` - BrightSkyWeather and BrightSkyForecastEntry Pydantic models
- `backend/app/models/__init__.py` - Package init for models directory
- `backend/tests/connectors/test_weather.py` - 6 integration tests (WAIR-01, WAIR-02)

## Decisions Made
- lat/lon read from `ConnectorConfig.config` with defaults — connector works for any German town covered by DWD
- MOSMIX forecast entries identified by `sources[].observation_type == "forecast"` filter — excludes actual observation entries
- All numeric fields in Pydantic models typed `float | None` — Pydantic auto-coerces integer wind_direction to float
- Created `app/models/` directory for Pydantic API-response models (distinct from SQLAlchemy DB models)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — Bright Sky API responded correctly on first call, forecast response included MOSMIX entries as expected.

## User Setup Required

None - Bright Sky API is free with no authentication required. No environment variables needed for this connector.

## Next Phase Readiness
- WeatherConnector is ready for registration in the APScheduler via Plan 02-05 (connector registry)
- weather_readings hypertable and features table were created in Plan 02-01 — WeatherConnector.run() will write to them
- The `app/models/` pattern is established for air quality and transit connectors in Plans 02-04 and 02-05

---
*Phase: 02-first-connectors*
*Completed: 2026-04-05*
