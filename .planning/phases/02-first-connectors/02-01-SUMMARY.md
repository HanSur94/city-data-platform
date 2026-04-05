---
phase: 02-first-connectors
plan: "01"
subsystem: backend-connectors
tags: [connectors, scheduler, migrations, timescaledb, apscheduler]
dependency_graph:
  requires: [01-foundation/01-04-PLAN.md]
  provides: [weather_readings hypertable, BaseConnector.persist(), staleness tracking, APScheduler, connector test scaffolding]
  affects: [02-02-PLAN.md, 02-03-PLAN.md, 02-04-PLAN.md, 02-05-PLAN.md]
tech_stack:
  added: [gtfs-kit==12.0.3, gtfs-realtime-bindings==2.0.0, apscheduler==3.11.2]
  patterns: [fresh-session-per-job-run, staleness-tracking, ON-CONFLICT-upsert, APScheduler-AsyncIOScheduler]
key_files:
  created:
    - backend/alembic/versions/002_schema_additions.py
    - backend/app/scheduler.py
    - backend/tests/connectors/__init__.py
    - backend/tests/connectors/conftest.py
  modified:
    - backend/app/connectors/base.py
    - backend/pyproject.toml
    - backend/uv.lock
decisions:
  - "Fresh AsyncSession per persist()/upsert_feature()/_update_staleness() call — sessions never held at class level (Pitfall 8 pattern)"
  - "run() explicitly calls _update_staleness() so staleness is always updated after successful pipeline"
  - "upsert_feature() uses ON CONFLICT (town_id, domain, source_id) — requires migration 002 unique constraint"
  - "scheduler._resolve_connector() uses explicit registry dict (not dynamic discovery) for safety"
metrics:
  duration_minutes: 15
  completed_date: "2026-04-05"
  tasks_completed: 2
  files_changed: 7
---

# Phase 02 Plan 01: Install Packages + Schema Migration + BaseConnector Upgrade Summary

**One-liner:** Alembic migration 002 (weather hypertable, staleness columns, features unique constraint), BaseConnector upgraded from no-op to real DB writes with APScheduler integration and test scaffolding.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Install packages + Alembic migration 002 | f72d2fb | 002_schema_additions.py, pyproject.toml, uv.lock |
| 2 | Upgrade BaseConnector + scheduler.py + test scaffolding | 5f7b9ad | base.py, scheduler.py, tests/connectors/conftest.py |

## What Was Built

### Task 1: Packages + Migration

- Installed `gtfs-kit==12.0.3`, `gtfs-realtime-bindings==2.0.0`, `apscheduler==3.11.2` via `uv add`
- Created `backend/alembic/versions/002_schema_additions.py` with:
  - `weather_readings` TimescaleDB hypertable (14 columns: time, feature_id, temperature, dew_point, pressure_msl, wind_speed, wind_direction, cloud_cover, condition, icon, precipitation_10, precipitation_30, precipitation_60, observation_type)
  - 1-year retention policy on weather_readings
  - `uq_features_town_domain_source` unique constraint on `features(town_id, domain, source_id)`
  - `sources.last_successful_fetch` TIMESTAMPTZ column
  - `sources.validation_error_count` INTEGER DEFAULT 0 column
- Migration runs without error (`alembic upgrade head` exits 0)

### Task 2: BaseConnector + Scheduler + Tests

- Upgraded `BaseConnector.persist()` from `pass` to real async INSERT statements:
  - `air_quality_readings`: pm25, pm10, no2, o3, aqi
  - `weather_readings`: all 12 weather columns + observation_type
  - `transit_positions`: trip_id, route_id, delay_seconds
- Added `BaseConnector.upsert_feature()`: ON CONFLICT upsert to features table, returns UUID string
- Upgraded `BaseConnector.run()`: now calls `await self._update_staleness()` after persist()
- Added `BaseConnector._update_staleness()`: issues `UPDATE sources SET last_successful_fetch = :now WHERE town_id = :town_id AND connector_class = :connector_class`
- Created `backend/app/scheduler.py`:
  - `AsyncIOScheduler` instance at module level
  - `_CONNECTOR_MODULES` registry mapping class names to module paths
  - `_resolve_connector(connector_class)` dynamic class loader
  - `setup_scheduler(town)` registers APScheduler jobs for all enabled connectors
  - `_run_connector()` async job handler with error logging
- Created `backend/tests/connectors/__init__.py` (empty package init)
- Created `backend/tests/connectors/conftest.py` with `aalen_town` and `stub_connector_config` fixtures

## Decisions Made

1. **Fresh session per call**: `persist()`, `upsert_feature()`, and `_update_staleness()` each open their own `AsyncSessionLocal()` context manager. Sessions are never held at class level. This prevents session lifetime issues with APScheduler job re-entrancy.

2. **Staleness always via `_update_staleness()`**: `run()` explicitly calls `_update_staleness()`. Subclasses that override `run()` must call `await self._update_staleness()` at the end of their implementation — documented in docstring.

3. **ON CONFLICT upsert requires unique constraint**: `upsert_feature()` relies on `uq_features_town_domain_source` from migration 002. This is a hard dependency — the method will fail without the constraint.

4. **Explicit connector registry**: `_CONNECTOR_MODULES` in scheduler.py lists all known connectors explicitly. Unknown connector class names raise `ValueError` immediately, preventing silent failures from typos.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all functionality is wired. `persist()` writes to real DB tables. `_update_staleness()` writes to real `sources` table.

## Self-Check: PASSED

Files created:
- backend/alembic/versions/002_schema_additions.py: FOUND
- backend/app/scheduler.py: FOUND
- backend/tests/connectors/__init__.py: FOUND
- backend/tests/connectors/conftest.py: FOUND

Commits:
- f72d2fb: FOUND (feat(02-01): install packages + alembic migration 002)
- 5f7b9ad: FOUND (feat(02-01): upgrade BaseConnector, create scheduler.py, test scaffolding)

DB schema verified:
- weather_readings hypertable: 14 columns confirmed
- uq_features_town_domain_source constraint: confirmed
- sources.last_successful_fetch column: confirmed
- sources.validation_error_count column: confirmed
