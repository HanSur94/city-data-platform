---
phase: 02-first-connectors
plan: "05"
subsystem: ingestion
tags: [gtfs-rt, protobuf, apscheduler, fastapi, transit, connectors]

# Dependency graph
requires:
  - phase: 02-first-connectors/02-04
    provides: GTFSConnector, upsert_feature pattern, BaseConnector.run() override pattern
  - phase: 02-first-connectors/02-01
    provides: APScheduler setup_scheduler() in scheduler.py
  - phase: 01-foundation
    provides: FastAPI lifespan, BaseConnector ABC, Observation dataclass

provides:
  - GTFSRealtimeConnector with protobuf parsing (vehicle positions + trip updates)
  - Feature-first pattern for transit connectors (upsert UUID before persist)
  - APScheduler wired into FastAPI lifespan (startup/shutdown)
  - aalen.yaml with all 5 connectors configured (UBA, SensorCommunity, Weather, GTFS, GTFSRealtime)

affects: [03-api-layer, 04-frontend, all phases needing transit live data]

# Tech tracking
tech-stack:
  added: [gtfs-realtime-bindings (google.transit.gtfs_realtime_pb2)]
  patterns:
    - "Override run() to upsert features first when feature_id must be a valid UUID"
    - "fetch() returns b'' for unconfigured URL — normalize(b'') returns [] — graceful skip"
    - "APScheduler.start() called in FastAPI lifespan after town config loaded"
    - "Separate upsert_feature() calls before normalize() to resolve entity.id -> UUID mapping"

key-files:
  created:
    - backend/app/connectors/gtfs_rt.py
    - backend/tests/connectors/test_gtfs_rt.py
  modified:
    - backend/app/main.py
    - towns/aalen.yaml

key-decisions:
  - "GTFSRealtimeConnector overrides run() to upsert features before normalize() — transit_positions.feature_id must be UUID, not trip_id string"
  - "gtfs_rt_url empty string = graceful skip with log warning (NVBW GTFS-RT URL unconfirmed)"
  - "normalize() accepts optional feature_ids kwarg — fallback to entity.id for unit tests without DB"

patterns-established:
  - "Feature-first run() pattern: parse proto -> upsert_feature() -> normalize(raw, feature_ids=...) -> persist()"
  - "Empty-URL graceful skip: fetch() returns b'', run() returns early, no exception"

requirements-completed: [TRAF-02]

# Metrics
duration: 8min
completed: 2026-04-05
---

# Phase 02 Plan 05: GTFSRealtimeConnector + APScheduler Wiring Summary

**GTFSRealtimeConnector parsing GTFS-RT protobuf (vehicle positions + trip updates) with UUID feature_id resolution, and APScheduler wired into FastAPI lifespan with all 5 connectors in aalen.yaml**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-05T19:02:57Z
- **Completed:** 2026-04-05T19:11:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- GTFSRealtimeConnector parses GTFS-RT protobuf binary (vehicle positions and trip updates) using the google.transit library
- Feature-first run() pattern: upserts vehicle/trip features to get UUID feature_ids before calling persist() — prevents UUID cast errors in transit_positions table
- Graceful skip when gtfs_rt_url is empty: fetch() returns b"", normalize(b"") returns [], run() returns early
- APScheduler wired into FastAPI lifespan — scheduler.start() after town config loaded, scheduler.shutdown(wait=False) on shutdown
- aalen.yaml updated from 1 StubConnector to all 5 real connectors with correct config keys
- All 23 connector tests pass (5 new GTFS-RT tests)

## Task Commits

1. **Task 1: GTFSRealtimeConnector + unit tests** - `86938ee` (feat — TDD green phase)
2. **Task 2: Wire APScheduler + update aalen.yaml** - `84484d1` (feat)

**Plan metadata:** (docs commit hash — added after state updates)

## Files Created/Modified

- `backend/app/connectors/gtfs_rt.py` — GTFSRealtimeConnector: fetch(), normalize(), run() with feature-first UUID pattern
- `backend/tests/connectors/test_gtfs_rt.py` — 5 unit tests using fixture protobuf binary (no live feed required)
- `backend/app/main.py` — Lifespan updated with setup_scheduler() + scheduler.start()/shutdown()
- `towns/aalen.yaml` — All 5 connectors: UBA, SensorCommunity, Weather, GTFSConnector, GTFSRealtimeConnector

## Decisions Made

- **GTFSRealtimeConnector overrides run()**: transit_positions.feature_id is a UUID FK to features(id); raw trip_id strings cannot be used. The run() override upserts features first, builds entity.id -> UUID map, then calls normalize(raw, feature_ids=...) with real UUIDs.
- **Empty URL = graceful skip**: NVBW GTFS-RT URL is unconfirmed (open question from RESEARCH.md). gtfs_rt_url set to empty string; fetch() logs warning and returns b""; run() returns early. This prevents crashes while the URL is unknown.
- **normalize() feature_ids kwarg optional**: Allows unit tests to call normalize() without a DB connection — entity.id is used as placeholder feature_id in test context, which is fine for parsing validation.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — the TDD cycle was clean. RED (ImportError) confirmed before GREEN implementation. All 5 tests pass on first implementation attempt.

## User Setup Required

None — GTFSRealtimeConnector skips gracefully when gtfs_rt_url is empty. Once the NVBW GTFS-RT feed URL is confirmed, update `towns/aalen.yaml` under `GTFSRealtimeConnector.config.gtfs_rt_url`.

## Next Phase Readiness

- All 5 connectors are implemented and scheduled: docker-compose up now starts all connectors polling automatically
- Phase 02 is complete — all planned connectors (UBA, SensorCommunity, Weather, GTFS, GTFSRealtime) are wired
- Phase 03 (API layer) can read from all populated tables: air_quality_readings, weather_readings, transit_positions, features
- Remaining open item: NVBW GTFS-RT feed URL — update aalen.yaml when confirmed

---
*Phase: 02-first-connectors*
*Completed: 2026-04-05*

## Self-Check: PASSED

- backend/app/connectors/gtfs_rt.py: FOUND
- backend/tests/connectors/test_gtfs_rt.py: FOUND
- backend/app/main.py: FOUND
- towns/aalen.yaml: FOUND
- .planning/phases/02-first-connectors/02-05-SUMMARY.md: FOUND
- Commit 86938ee: FOUND
- Commit 84484d1: FOUND
