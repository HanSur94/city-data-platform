---
phase: quick-261115-ved
plan: 01
subsystem: backend/connectors
tags: [gtfs, bus-interpolation, performance, asyncio, pandas, cache]
requires: []
provides:
  - reduce_feed_to_bbox (pure, vectorised GTFS town reduction)
  - module-level reduced-feed cache with lock in bus_interpolation.py
affects: [backend/app/connectors/bus_interpolation.py]
tech-stack:
  added: []
  patterns: ["module-level cache because the scheduler builds a new connector per run", "CPU-bound pandas work in asyncio.to_thread"]
key-files:
  created: []
  modified:
    - backend/app/connectors/bus_interpolation.py
    - backend/tests/connectors/test_bus_interpolation.py
decisions:
  - "Cache key is the town bbox tuple; value is ((len, crc32) of zip, reduced namespace); one entry per bbox, replaced when the zip changes"
  - "No-active-services branch in run() now calls _cleanup_old_features(set()) to keep stale-dot removal after the calendar was reduced to town services"
metrics:
  duration: "about 25 minutes"
  completed: "2026-11-15"
status: complete
actuals:
  tokens: 4950
  tasks: 2
  commits: 4
plan_head_before: 124a91fe748c2ffae1807d40f7cc61cd6c3f2ec6
plan_head_after: 5fe724a73f04e10a94408d8b7684823e383167c9
---

# Phase quick-261115-ved Plan 01: Cache the town-reduced GTFS feed in BusInterpolationConnector Summary

BusInterpolationConnector now parses the statewide NVBW GTFS zip once per distinct zip and town bbox, keeps only the town-touching trips in a module-level cache, and runs the remaining per-run pandas work in worker threads instead of on the event loop.

## What changed

Only `backend/app/connectors/bus_interpolation.py` changed in production code:

- `reduce_feed_to_bbox(feed, bbox)`: pure, vectorised helper. Keeps whole trips (all stop_times, including out-of-bbox stops) that touch the bbox, plus the referenced stops, routes, shapes, calendar and calendar_dates rows. Missing or empty tables are returned unchanged and never raise. The result never references the statewide feed.
- `_REDUCED_FEED_CACHE` / `_REDUCED_FEED_LOCK` (module level): one entry per bbox, keyed to `(len(zip_bytes), crc32)`. A different zip replaces the entry, a failed parse is never cached, concurrent calls parse once. Parse and reduce share one `asyncio.to_thread` call; the crc32 is also computed in a thread.
- `BusInterpolationConnector._parse_and_reduce` / `_get_reduced_feed`: used by `run()` in place of the old per-run `to_thread(self._parse_gtfs, ...)`.
- `run()`: `_get_active_service_ids` and `_build_active_trips` now go through `asyncio.to_thread`.
- `run()` no-active-services branch: added `await self._cleanup_old_features(set())` before `_update_staleness()` (see Task 2 below).

## Commits

| Commit | Subject |
| --- | --- |
| e225c32 | test(quick-261115-ved): reduced GTFS feed cache and off-loop interpolation (RED) |
| 9463dcd | fix(quick-261115-ved): parse the statewide GTFS feed once per zip, reduce it to the town bbox and keep per-run work off the event loop |
| d82178d | test(quick-261115-ved): equivalence, optional-table, cache and no-service cleanup tests (RED) |
| 5fe724a | fix(quick-261115-ved): keep removing stale bus-pos features when no town service runs today |

Each commit touches exactly one file. No push, no branch change, no Docker interaction.

## Baseline (before changes)

Command: full suite, `-m "not slow" -p no:cacheprovider -rfE`, HEAD 124a91f.

Result: 10 failed, 314 passed, 1 skipped, 4 deselected, 6 errors. (The orchestrator's earlier count was 306 passed, 1 skipped, 4 failed, 20 errors; it differs because the real PostgreSQL is reachable now and `TOMTOM_API_KEY` is not set in this shell.)

FAILED:
- tests/connectors/test_ladesaeulen.py::test_run_max_power_calculation (float assertion, unrelated)
- tests/test_boundaries.py::test_aalen_boundary_coordinates_in_bw, test_aalen_boundary_exists, test_aalen_boundary_geometry_is_wgs84, test_aalen_boundary_is_multipolygon, test_aalen_boundary_properties_contain_ags, test_aalen_boundary_source_id (the DB is reachable but has 0 administrative features for aalen)
- tests/test_config.py::test_aalen_bbox, test_load_aalen (KeyError: TOMTOM_API_KEY not set)
- tests/test_multi_town.py::test_load_aalen_regression (same KeyError)

ERROR (same KeyError at fixture setup):
- tests/test_connector.py::test_abstract_cannot_instantiate, test_stub_fetch_returns_dict, test_stub_has_fetch, test_stub_has_normalize, test_stub_normalize_returns_empty_list, test_stub_run_completes

Note on the database: the boundary tests now do connect to the live PostgreSQL via `db_conn`. I checked: they only run read-only `SELECT` queries (and `test_migrations.py` / `test_sources_registration.py` do no writes either), so nothing was migrated, truncated or seeded. I therefore ran the plan's second full-suite run as prescribed. No test I added touches the DB, network or `/tmp/gtfs_cache.zip`.

## After (final full suite)

10 failed, 324 passed, 1 skipped, 4 deselected, 6 errors. The sorted list of FAILED and ERROR ids is identical to the baseline (no new ids). Passed went from 314 to 324 = 10 new tests (2 in Task 1, 8 in Task 2 counting the 3 parametrized cases individually). The target file runs 23 passed (13 original + 10 new).

## Task notes

**Task 1 (tracer).** RED run: both new tests failed, the 13 existing tests passed. The off-main-thread and feature-property assertions were reached and only the parse-count assertion failed, which confirms that `run()` itself works with the mocks. GREEN: 15 passed. Tracer gate: the verify is automated only, so the passing re-run of the target file counts as the end-to-end re-verification before expansion.

**Task 2.** RED run: only `test_no_active_town_service_still_removes_stale_bus_features` failed. The guard tests (`test_reduced_feed_yields_same_active_trips_as_full_feed`, the three `test_missing_optional_tables_do_not_raise` variants, `test_different_zip_reparses_and_keeps_one_entry_per_bbox`, `test_parse_failure_is_not_cached`, `test_concurrent_calls_parse_once`) already passed against Task 1's code, so no Task 1 defect surfaced. The one-line fix then turned the remaining test green.

## Intended log-count differences (message text unchanged)

- "Stops in Aalen bbox: %d" now counts only bbox stops that some town trip serves.
- "Shape coords available: %s (%d shapes)" now counts only shapes of town trips.
- In the rare no-town-service case, `run()` logs "No active services ..." instead of reaching the zero-trip log lines.
- New info line "Reduced GTFS feed to town bbox: ..." appears once per zip, not every run.

## Deviations from Plan

None - plan executed as written.

Minor process notes (not behaviour deviations): the new Task 2 tests were appended to the test file with a shell append rather than the Edit tool, and the `bus_interpolation.py` edits for Task 1 were applied with a short scripted string replacement. The resulting diffs are exactly the planned changes.

## Not verified here

The real-world effect (CPU use, `/api/kpi` and `/api/layers/transit` latency, scheduler skips) was not measured. The plan leaves that to the orchestrator after rebuilding the backend image. The reduction was only exercised on the synthetic feed, not on the real 36.7 MB NVBW zip.

## Known Stubs

None.

## Threat Flags

None. No new endpoints, auth paths or schema changes. T-261115-ved-01, -02 and -04 mitigations are implemented and covered by the tests named above.

## Self-Check: PASSED

- backend/app/connectors/bus_interpolation.py contains `def reduce_feed_to_bbox`: found.
- backend/tests/connectors/test_bus_interpolation.py: found, 23 tests pass.
- Commits e225c32, 9463dcd, d82178d, 5fe724a: all ancestors of HEAD.
- `git rev-list --count 124a91f..HEAD` = 4, matching `commits: 4`.
- `git status` shows no modified tracked files; the pre-existing untracked `.planning/` and `docs/` entries are untouched (SUMMARY.md is new and left uncommitted for the orchestrator).

## Orchestrator verification on the running Docker stack (2026-11-15)

Backend image rebuilt with these commits and restarted; database, frontend and real NVBW feed unchanged.

- Latency, sampled every ~8 s for 3.5 minutes while the 30 s job ran: `/api/kpi` 0.04–0.4 s (one 7.2 s and one 1.2 s sample during the first parse after the restart), `/api/layers/transit?feature_type=stop` 0.05–0.44 s, `/api/layers/water` 0.006–0.13 s. Before the fix the same endpoints took 15–47 s whenever the job was running.
- Backend container CPU 2 % at the end of the sampling window (about 100 % before). No "maximum number of running instances" or "was missed" scheduler warnings in the last 2 minutes of the window (17 during the startup parse).
- The job keeps running: `sources.last_successful_fetch` for BusInterpolationConnector was 4 s old, 13 `bus-pos:*` features present.
- Real-feed equivalence, run inside the backend container on `/tmp/gtfs_cache.zip`: full feed 9,737 trips / 149,750 stop_times / 3,131,241 shape rows; reduced 4,009 / 63,075 / 1,248,471. `_get_active_service_ids` + `_build_active_trips` returned identical trips (trip id, route id, stop_time count, shape point count) on both for three times of day: now (13 trips), 08:00 (11), 17:30 (27).
- Still open: the per-run `_build_active_trips` on the reduced feed takes 3.5–6.8 s (measured standalone next to the running app; 9.5–16.8 s on the full feed). It now runs in a worker thread, but it rebuilds the shape lookup from 1.25 M rows every 30 s. Caching that lookup with the reduced feed would be the next step.
