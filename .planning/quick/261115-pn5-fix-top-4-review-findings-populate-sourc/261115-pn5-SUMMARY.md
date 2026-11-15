---
phase: quick-261115-pn5
plan: 01
subsystem: backend
tags: [sources, attribution, scheduler, gtfs-rt, demographics]
requires: []
provides:
  - sources table populated at startup (register_sources)
  - de-duplicated /api/layers features with separate attribution query
  - demographics connectors scheduled
  - bbox- and relevance-filtered GTFS-RT ingestion
affects: [backend/app/scheduler.py, backend/app/main.py, backend/app/routers/layers.py, backend/app/routers/admin.py, backend/app/connectors/gtfs_rt.py]
tech-stack:
  added: []
  patterns: [domain map next to connector registry, fail-closed relevance filter]
key-files:
  created:
    - backend/tests/test_sources_registration.py
    - backend/tests/test_connector_registry.py
  modified:
    - backend/app/scheduler.py
    - backend/app/main.py
    - backend/app/routers/layers.py
    - backend/app/routers/admin.py
    - backend/app/connectors/gtfs_rt.py
    - backend/scripts/cleanup_stale_transit.sql
    - backend/tests/test_api_layers.py
    - backend/tests/connectors/test_gtfs_rt.py
decisions:
  - "Connector domains live in one CONNECTOR_DOMAINS map next to _CONNECTOR_MODULES instead of class attributes on about 30 connector files"
  - "GTFS-RT trip updates are stored only when relevant; with no relevance data only trips of in-bbox vehicles qualify (fail-closed)"
status: complete
commits: 5
plan_head_before: 93021106e7d3b947fcae7211d5ee4c1f11c6cb79
plan_head_after: cf2fba8f99a2601c31df4856e73cce9ca2544b0a
actuals:
  tokens: 12000
  tasks: 3
  commits: 5
completed: 2026-11-15
---

# Phase quick-261115-pn5 Plan 01: Fix top 4 review findings Summary

Populated the `sources` table at startup (idempotent, no config stored), removed the sources join that would have multiplied layer features, registered the four demographics connectors, and bbox/relevance-filtered the GTFS-RT connector onto a single per-town trip-update placeholder.

## Tasks and commits

| Task | Name | Commit |
|------|------|--------|
| 1 | F1 + F2: register_sources, lifespan hook, layers attribution query (one commit) | 34ac38a |
| 2 | F3: RED registry tests | 7578e88 |
| 2 | F3: register 4 demographics connectors + buildings/police staleness thresholds | bf7fbc5 |
| 3 | F4: RED GTFS-RT tests | 9bc5e38 |
| 3 | F4: GTFS-RT bbox + relevance filter, single placeholder, cleanup SQL | cf2fba8 |

## What was built

- **F1** `scheduler.register_sources(town)`: one parameterised `INSERT ... ON CONFLICT (id) DO UPDATE` per enabled, registered connector, id `{town_id}:{connector_class}`. The statement never names `config`, `last_successful_fetch` or `validation_error_count`, so the TomTom API key never reaches the DB and restarts do not reset health counters. `main.lifespan` awaits it after the towns upsert inside try/except and continues on failure.
- **F2** `layers.py`: the sources left join and `s.connector_class` column are gone from all seven feature queries (and the transit GROUP BY). `_fetch_attribution(db, town_id, domain)` runs one `SELECT DISTINCT connector_class FROM sources ...` as the last DB call, returns `[]` on any exception. Response keys unchanged.
- **F3** Four demographics connectors added to `_CONNECTOR_MODULES` and `CONNECTOR_DOMAINS`; `test_connector_registry.py` locks YAML classes, concrete connector classes and domain consistency (VALID_DOMAINS, STALENESS_THRESHOLDS). Added `buildings` and `police` thresholds to `admin.STALENESS_THRESHOLDS`.
- **F4** `gtfs_rt.py`: vehicles kept only inside the town bbox; trip updates kept only when relevant; all delays attach to one placeholder feature (`gtfs-rt:trip-updates`, `feature_type: trip_update`, at bbox centre). The `POINT(0 0)` / per-trip `trip:{id}` placeholders are gone. `cleanup_stale_transit.sql` gained two commented, manual-only statements (legacy `trip:%` features; out-of-bbox `vehicle:%` features). The script was not run.

## Design notes

- **Domain mapping design choice:** a single `CONNECTOR_DOMAINS` dict beside the registry (27 entries plus 4 demographics = 31, StubConnector excluded). It touches one file and is checked against the registry by test.
- **GTFS-RT relevance rule:** a trip update is stored when its trip_id is in the tracked `bus-pos:*` trip ids, OR is the trip of an in-bbox vehicle in the same feed, OR any `stop_time_update.stop_id` is a town `stop:*` feature id. Empty ids never match. If the relevance lookup fails or returns nothing, only in-bbox vehicle trips qualify; with no vehicles, nothing is stored.

## Deviations from Plan

None. Plan executed as written. (In the `run()` skip test, persist may be called with an empty list or not at all; the test accepts both, since `persist` returns early on an empty list.)

## Known limitations

- GTFS-RT stop/trip ids from realtime.gtfs.de may not match NVBW static GTFS ids (`stop:*`, `bus-pos:*` features). If they do not, only in-bbox vehicle trips will qualify until the feeds are aligned. Not verifiable without live data.
- The cleanup SQL statements are commented out and must be reviewed and run manually; no live DB was available here, and none of the SQL (register_sources, attribution, relevance query, cleanup) was run against PostgreSQL. Only mocked tests cover it.

## Verification

- Final full-suite line: `4 failed, 306 passed, 1 skipped, 4 deselected, 20 errors in 8.98s` (baseline 292 passed). The gate script passed: all failed/errored node ids are in the baseline allowlist.
- `backend/uv.lock` still ` M` (unstaged); no commit of this task touched it.

## Known Stubs

None.

## Threat Flags

None. No new endpoints or trust boundaries beyond the plan's threat model.

## Self-Check: PASSED

All five commits (34ac38a, 7578e88, bf7fbc5, 9bc5e38, cf2fba8) are ancestors of HEAD; created test files exist.
