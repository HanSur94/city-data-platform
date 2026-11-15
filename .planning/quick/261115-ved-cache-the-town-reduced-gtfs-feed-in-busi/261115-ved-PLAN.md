---
phase: quick-261115-ved
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/connectors/bus_interpolation.py
  - backend/tests/connectors/test_bus_interpolation.py
autonomous: true
requirements: [VED-01, VED-02, VED-03, VED-04]

estimate:
  tokens: 70000
  raw_tokens: 70000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - "Two back-to-back BusInterpolationConnector.run() calls on two fresh connector instances (the way the scheduler calls it) with the same zip bytes call _parse_gtfs exactly once"
    - "_get_active_service_ids and _build_active_trips run in a worker thread, never on the event-loop thread, during run()"
    - "On the synthetic feed, _build_active_trips gives the same ActiveTrip list (model_dump plus _stop_shape_fracs) on reduce_feed_to_bbox(feed, bbox) as on the full feed"
    - "A different zip re-parses and replaces the single cache entry for that bbox; a failed parse (_parse_gtfs returns None) is not cached; two concurrent calls with the same zip parse once"
    - "If no town service runs today, run() still calls _cleanup_old_features(set()) and _update_staleness(), so stale bus-pos dots are removed as on the full-feed path"
    - "The bus-pos feature written for a running trip keeps the same source_id, domain and properties (line_name, destination, total_stops, shape_coords JSON)"
    - "Full backend suite (not slow): no failing or erroring test id outside the baseline recorded before the first edit; the 13 existing bus interpolation tests still pass"
  artifacts:
    - path: "backend/app/connectors/bus_interpolation.py"
      provides: "reduce_feed_to_bbox(), _REDUCED_FEED_CACHE, _REDUCED_FEED_LOCK, BusInterpolationConnector._parse_and_reduce / _get_reduced_feed, run() using both plus asyncio.to_thread for the per-run helpers"
      contains: "def reduce_feed_to_bbox"
    - path: "backend/tests/connectors/test_bus_interpolation.py"
      provides: "synthetic-feed tests for reduction, equivalence, optional tables, cache and run() wiring (no network, no DB)"
      contains: "reduce_feed_to_bbox"
  key_links:
    - from: "BusInterpolationConnector.run"
      to: "BusInterpolationConnector._get_reduced_feed"
      via: "awaited in place of the old asyncio.to_thread(self._parse_gtfs, zip_bytes) call"
      pattern: "await self._get_reduced_feed\\(zip_bytes\\)"
    - from: "BusInterpolationConnector._get_reduced_feed"
      to: "_parse_gtfs + reduce_feed_to_bbox"
      via: "one asyncio.to_thread(self._parse_and_reduce, ...) call inside async with _REDUCED_FEED_LOCK"
      pattern: "_parse_and_reduce"
    - from: "BusInterpolationConnector.run"
      to: "_get_active_service_ids / _build_active_trips"
      via: "asyncio.to_thread"
      pattern: "asyncio.to_thread\\(\\s*self._build_active_trips"
---

<objective>
Stop BusInterpolationConnector from parsing the whole statewide GTFS feed every 30 s. The feed should be parsed and cut down to the town bbox once per zip, and the remaining per-run pandas work should run off the event loop. Only backend/app/connectors/bus_interpolation.py changes in production code.

Purpose: live on the Docker stack, the 30 s job keeps the backend at about 100 % CPU, /api/kpi takes 47 s, /api/layers/transit takes more than 60 s, and APScheduler skips and misses jobs. The cause: the scheduler builds a new connector for every run (backend/app/scheduler.py line 134). So each run re-reads the 36.7 MB NVBW zip, runs gtfs_kit.read_feed on all of Baden-Wuerttemberg, and then runs _get_active_service_ids and _build_active_trips on the event loop over statewide tables.

Output: a pure helper reduce_feed_to_bbox, a module-level cache with a lock, run() wired to both, and new synthetic-feed tests. Only the internals change: the same features, properties, /tmp/gtfs_cache.zip sharing with GTFSConnector and 7-day download TTL. Two documented log-count differences are listed under verification.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@backend/app/connectors/bus_interpolation.py
@backend/tests/connectors/test_bus_interpolation.py
@backend/tests/connectors/conftest.py

Facts checked live at planning time (HEAD 124a91f, branch fix/soupsieve-alerts):
- _get_active_service_ids(feed, today) reads only feed.calendar / feed.calendar_dates and datetime. _build_active_trips(feed, active_service_ids, now_secs) reads only feed tables, self.town.bbox, logger, the static _time_str_to_seconds and the pure _compute_stop_shape_fractions. Neither awaits, touches the DB, touches the loop, or mutates the feed, so both are safe to run in asyncio.to_thread.
- A scratch prototype of the reduction on the synthetic feed below gave identical _build_active_trips output (model_dump and _stop_shape_fracs [0.0, 0.184..., 1.0]) on the reduced and the full feed. The active service set was {SV1} on the reduced feed and {SV1, SV2} on the full feed. That shows why the no-active-services branch in Task 2 is needed.
- Venv: Python 3.11.5, pandas 3.0.2 (the default string dtype is "str"; ids compare fine with isin). gtfs-kit 12.0.3. pytest asyncio_mode=auto with session-scoped loops (backend/pyproject.toml).
- The scheduler job uses max_instances=1 (backend/app/scheduler.py line 163). backend/tests/connectors/conftest.py provides the aalen_town fixture, bbox lon 9.97..10.22, lat 48.76..48.90.
- Baselines: tests/connectors/test_bus_interpolation.py gives 13 passed. backend/app/connectors/bus_interpolation.py has 1 asyncio.to_thread call (line 330) and 0 occurrences of reduce_feed_to_bbox, _REDUCED_FEED, _get_reduced_feed or zlib.

Interfaces this plan creates (later tasks and tests use these exact names):
- reduce_feed_to_bbox(feed, bbox) -> types.SimpleNamespace. A module-level pure function. bbox is any object with lon_min, lat_min, lon_max and lat_max (app.config.TownBbox). The result has exactly the attributes calendar, calendar_dates, routes, trips, stop_times, stops and shapes.
- _REDUCED_FEED_CACHE: dict mapping bbox tuple (lon_min, lat_min, lon_max, lat_max) to (zip_key, reduced_feed), where zip_key = (len(zip_bytes), zlib.crc32(zip_bytes)).
- _REDUCED_FEED_LOCK: asyncio.Lock, module-level.
- BusInterpolationConnector._parse_and_reduce(self, zip_bytes, bbox): sync. Returns the reduced namespace, or None when parsing fails.
- BusInterpolationConnector._get_reduced_feed(self, zip_bytes) -> types.SimpleNamespace | None: async, cached.

Executor ground rules (from the orchestrator):
- Stay on branch fix/soupsieve-alerts. Do not create or switch branches. Never push.
- Do not touch GTFSConnector, backend/app/scheduler.py, the layers router or any frontend code.
- Do not rebuild or restart Docker containers.
- Never read, print or edit dotenv files, and do not name them in shell commands.
- Stage files by explicit path only, never with add -A or add . (the untracked files under .planning/ and docs/ stay uncommitted).
- Never create backend/.venv. Always set UV_PROJECT_ENVIRONMENT as in the verify commands.
- A PostgreSQL with live app data is reachable on localhost:5432. The new tests must mock every DB-touching method. Apart from the two full-suite runs this plan prescribes, which match the orchestrator's baseline command, run only tests/connectors/test_bus_interpolation.py.
- Commit subjects use type(quick-261115-ved): ... and every commit message ends with the trailer line Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>
</context>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Tracer: fresh connector instances share one parsed, town-reduced feed, and per-run work leaves the event loop</name>
  <files>backend/tests/connectors/test_bus_interpolation.py, backend/app/connectors/bus_interpolation.py</files>
  <behavior>
    - reduce_feed_to_bbox on the synthetic feed keeps trip T1 (touches the bbox and continues outside it) with all 3 of its stop_times, including the one at out-of-bbox stop C. It keeps stops {A, B, C}, shape S1 (3 points), route R1, and calendar and calendar_dates rows only for SV1. It drops trip T2, its stop_times, stops D and E, the unreferenced in-bbox stop F, shape S2, route R2, and every SV2 row.
    - Two run() calls on two fresh connector instances with the same zip bytes call _parse_gtfs once.
    - During those runs, every call of _get_active_service_ids and _build_active_trips happens off the main (event-loop) thread.
    - The second run upserts exactly one feature: source_id "bus-pos:T1", domain "transit", line_name "71", destination "Outside C", total_stops 3, and shape_coords JSON equal to the three S1 points as [lon, lat] pairs. _cleanup_old_features is awaited with {"bus-pos:T1"}.
  </behavior>
  <action>
Implements VED-01, VED-02, VED-03 and the "same features" half of VED-04. These are orchestrator design items 1-3, which are settled; do not redesign them.

Step 0, baseline (BEFORE editing any file). From the repo root, run the full suite command from this plan's verification section, adding the flag -rfE. Write the summary line (passed / skipped / failed / errors) and the sorted list of FAILED and ERROR test ids into the SUMMARY draft at .planning/quick/261115-ved-cache-the-town-reduced-gtfs-feed-in-busi/261115-ved-SUMMARY.md, under a "Baseline (before changes)" heading. The orchestrator's last count was 306 passed, 1 skipped, 4 failed, 20 errors. It may differ now because a PostgreSQL is reachable, so record what you actually see. This list is the comparison set for Task 2.

Step 1, RED tests. Append to backend/tests/connectors/test_bus_interpolation.py and keep every existing test and import unchanged.
- Add these imports: asyncio, json, threading, time, datetime.date, types.SimpleNamespace, unittest.mock.AsyncMock, pandas as pd, app.config.ConnectorConfig, and the module object itself as "from app.connectors import bus_interpolation as bi".
- Reach every new symbol through bi at call time (bi.reduce_feed_to_bbox, bi._REDUCED_FEED_CACHE). That way the RED run fails only the new tests with AttributeError, and the 13 existing tests keep passing.
- Add a builder function _synthetic_feed(**overrides) that returns a SimpleNamespace of pandas DataFrames, with every id and date as a string. Overrides replace whole tables. The data:
  - stops (stop_id, stop_name, stop_lon, stop_lat): A "Inside A" 10.05/48.80; B "Inside B" 10.10/48.83; C "Outside C" 10.40/48.83; D "Far D" 11.00/49.20; E "Far E" 11.10/49.30; F "Unused F" 10.15/48.85. F lies inside the bbox but no trip serves it.
  - trips (route_id, service_id, trip_id, trip_headsign, shape_id): R1/SV1/T1/"Outside C"/S1 and R2/SV2/T2/"Far E"/S2.
  - stop_times (trip_id, arrival_time, departure_time, stop_id, stop_sequence): T1 A 00:00:00, T1 B 12:00:00, T1 C 23:59:59, T2 D 05:00:00, T2 E 07:00:00, with the same arrival and departure time on each row and sequences 1..n per trip. T1 therefore counts as active at any wall-clock time, so the run() tests do not depend on the time of day.
  - shapes (shape_id, shape_pt_lat, shape_pt_lon, shape_pt_sequence): S1 through the A, B and C coordinates, and S2 through the D and E coordinates.
  - routes (route_id, route_short_name, route_long_name, route_type): R1 "71" "" 3 and R2 "99" "" 3.
  - calendar: SV1 and SV2 with all seven weekday columns set to 1, start_date "20000101" and end_date "20991231".
  - calendar_dates (service_id, date, exception_type): SV1 "19990101" 2 (a date outside the calendar range, so it never changes activity) and SV2 "20261116" 1.
- Add a connector factory _connector(town) that returns BusInterpolationConnector(config=ConnectorConfig(connector_class="BusInterpolationConnector", config={"gtfs_url": "https://example.invalid/bwgesamt.zip"}), town=town).
- Add an autouse fixture that resets the cache for every test: monkeypatch.setattr(bi, "_REDUCED_FEED_CACHE", {}, raising=False) and monkeypatch.setattr(bi, "_REDUCED_FEED_LOCK", asyncio.Lock(), raising=False).
- Add a helper _patch_io(monkeypatch, parse_result). It sets class attributes on BusInterpolationConnector:
  - _download_cached_gtfs = AsyncMock(return_value=b"zip-v1")
  - _fetch_delays = AsyncMock(return_value={})
  - batch_upsert_features = AsyncMock whose side_effect maps each feature tuple's source_id to a fake id
  - persist, _cleanup_old_features and _update_staleness = plain AsyncMocks
  - _parse_gtfs = a plain function (self, zip_bytes) that records zip_bytes in a list and returns parse_result
  The helper returns a namespace holding those mocks and the call list. No new test may reach app.db, the network or /tmp/gtfs_cache.zip.
- Test test_reduce_keeps_touching_trip_and_drops_outside_trip (sync, uses the aalen_town fixture): assert the keep/drop sets from the behavior block, and assert that all seven attribute names exist on the result.
- Test test_two_fresh_instances_parse_once_and_compute_off_loop (async, aalen_town):
  - Wrap the original _get_active_service_ids and _build_active_trips with monkeypatch class-level wrappers. Each wrapper records whether threading.current_thread() is threading.main_thread() and then delegates.
  - Await _connector(aalen_town).run() twice, using two separate instances.
  - Assert: one _parse_gtfs call; each wrapper called twice and never on the main thread; batch_upsert_features awaited twice, and its last call is the single bus-pos:T1 feature with the properties from the behavior block (parse shape_coords with json.loads); _cleanup_old_features last awaited with {"bus-pos:T1"}.
- Run the target file. The two new tests must fail and the 13 existing tests must pass. Commit only the test file with subject "test(quick-261115-ved): reduced GTFS feed cache and off-loop interpolation (RED)".

Step 2, GREEN, in backend/app/connectors/bus_interpolation.py.
- Add import zlib and import types. Import pandas lazily inside reduce_feed_to_bbox; this follows the Phase 14 lazy-import decision in STATE.md that keeps test collection fast.
- Below _GTFS_CACHE_MAX_AGE, add _REDUCED_FEED_CACHE (empty dict) and _REDUCED_FEED_LOCK (asyncio.Lock()). Comment that they live at module level because the scheduler builds a new connector per run.
- Add module-level reduce_feed_to_bbox(feed, bbox) above the class, with a docstring.
  - Read each table with getattr(feed, name, None). Treat a table as present only when it is not None and not empty, the same rule as the existing guards. Return a table that is not present unchanged (None stays None, an empty DataFrame stays as it is).
  - Use vectorised pandas only, no Python loops over rows:
    - bbox stop ids: pd.to_numeric(stop_lon / stop_lat, errors="coerce") with Series.between on the bbox bounds, inclusive on both ends like the current <= comparisons. NaN coordinates fall out, matching the float() try/except in _build_active_trips.
    - town trip ids: trip_id values of stop_times rows whose stop_id isin the bbox stop ids.
    - trips: rows whose trip_id isin the town trip ids.
    - stop_times: ALL rows whose trip_id isin the reduced trips' trip_id, including out-of-bbox stops, because interpolation needs the whole trip.
    - stops: rows whose stop_id isin the reduced stop_times' stop_id.
    - routes: rows whose route_id isin the reduced trips' route_id.
    - shapes: rows whose shape_id isin the reduced trips' shape_id. Use an empty set when trips has no shape_id column.
    - calendar and calendar_dates: rows whose service_id isin the reduced trips' service_id.
  - A missing upstream table yields empty id sets, so downstream tables filter to zero rows instead of raising.
  - Build the SimpleNamespace from the filtered frames only. Never store the original feed on it, so the statewide feed can be garbage-collected.
  - Log one info line with the reduced trip, stop_time, stop and shape-row counts.
- Add sync method _parse_and_reduce(self, zip_bytes, bbox): call self._parse_gtfs(zip_bytes); return None if that returns None, otherwise return reduce_feed_to_bbox(feed, bbox).
- Add async method _get_reduced_feed(self, zip_bytes):
  - Build the bbox tuple from self.town.bbox.
  - Inside async with _REDUCED_FEED_LOCK:
    - compute zip_key = (len(zip_bytes), await asyncio.to_thread(zlib.crc32, zip_bytes));
    - if the entry for the bbox has an equal zip_key, log at debug and return the cached namespace;
    - otherwise await asyncio.to_thread(self._parse_and_reduce, zip_bytes, self.town.bbox), so parsing and reduction happen in one thread call;
    - if the result is None, return None without storing it and leave any existing entry alone;
    - if not, write _REDUCED_FEED_CACHE[bbox_key] = (zip_key, reduced), replacing the previous entry for that bbox, and return it.
  - Refer to both globals by plain name at call time, mutate the dict in place, and do not bind them as defaults or class attributes. The test fixture swaps them.
- In run():
  - Replace the step-2 line feed = await asyncio.to_thread(self._parse_gtfs, zip_bytes) with feed = await self._get_reduced_feed(zip_bytes). Keep the following if feed is None: return.
  - Change step 3 to active_service_ids = await asyncio.to_thread(self._get_active_service_ids, feed, today).
  - Change step 4 to active_trips = await asyncio.to_thread(self._build_active_trips, feed, active_service_ids, now_secs).
  - Leave everything else in run() unchanged, including the "No active services" branch (Task 2 handles it).
- Update the class docstring step list to read "parse + reduce to town bbox (cached per zip, in thread)" and note that steps 3-4 run in a thread.
- Do NOT change the bodies of _parse_gtfs, _download_cached_gtfs, _get_active_service_ids, _build_active_trips, interpolate_position or the feature property construction.

Step 3: run the target file until everything passes. Then commit only backend/app/connectors/bus_interpolation.py with subject "fix(quick-261115-ved): parse the statewide GTFS feed once per zip, reduce it to the town bbox and keep per-run work off the event loop".
  </action>
  <verify>
    <automated>cd backend && UV_PROJECT_ENVIRONMENT="/private/tmp/claude-501/-Users-hannessuhr-Library-Application-Support-Claude-scratch-workspaces-917fe486-0d98-4ede-ac88-e647c09dcb55-4c52147a-b177-4f3c-8801-8ef7ea1c9bce-scratch-2026-11-15-7357de/2d37f251-3d2e-41ee-ae9f-b74e9b5a9365/scratchpad/venv" uv run --frozen pytest -q -m "not slow" -p no:cacheprovider tests/connectors/test_bus_interpolation.py</automated>
    <automated>git --no-pager log -2 --name-only --format='%s'</automated>
  </verify>
  <done>
    - The target file passes: the 13 original tests plus the 2 new ones.
    - The last two commits are the RED test commit (touching only backend/tests/connectors/test_bus_interpolation.py) and the GREEN fix commit (touching only backend/app/connectors/bus_interpolation.py). Both end with the Co-Authored-By trailer.
    - The baseline list of failing and erroring ids is in the SUMMARY draft.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Edge cases (equivalence, optional tables, cache invalidation, failure, concurrency) and stale-dot cleanup when no town service runs today</name>
  <files>backend/tests/connectors/test_bus_interpolation.py, backend/app/connectors/bus_interpolation.py</files>
  <behavior>
    - Equivalence on a fixed date (date(2026, 11, 16), a Monday) at now_secs = 21600:
      - _get_active_service_ids gives {"SV1", "SV2"} on the full feed and {"SV1"} on the reduced feed; assert reduced is a subset of full and contains SV1.
      - _build_active_trips with each feed's own active set returns exactly one trip (T1) on both. model_dump() lists and _stop_shape_fracs values are equal.
    - Optional tables, parametrized over three variants:
      - (a) shapes=None and calendar_dates=None;
      - (b) shapes=pd.DataFrame() and calendar_dates=pd.DataFrame();
      - (c) calendar=None with calendar_dates holding only SV1 "20261116" 1.
      - In every variant, reduce_feed_to_bbox does not raise, and the None tables stay None in (a) and (c).
      - SV1 is active on 2026-11-16, and _build_active_trips returns exactly T1. In (a) and (b) T1's shape_coords are the three stop coordinates A, B, C (straight-line fallback).
    - Cache: the same zip twice calls _parse_gtfs once and returns the identical object. A different zip (b"zip-v2") parses again, returns a new object, and leaves exactly one cache entry.
    - Parse failure: a fake _parse_gtfs returning None makes _get_reduced_feed return None with an empty cache, and the next call parses again (2 calls).
    - Concurrency: asyncio.gather of _get_reduced_feed(b"zip-v1") on two instances parses once and both get the same object. The fake parse sleeps 0.2 s in its worker thread.
    - No town service today: calendar with SV1 weekday flags all 0 and SV2 all 1 (2000-2099) and calendar_dates=None. run() awaits _cleanup_old_features exactly once with set(), awaits _update_staleness once, and upserts no feature (batch_upsert_features is never awaited with a non-empty list). The result does not depend on the date.
  </behavior>
  <action>
Implements the rest of VED-04: same public behaviour and the full test list in the orchestrator's brief. It also covers the edge cases of VED-01 and VED-02.

Step 1, tests. Append the tests from the behavior block to backend/tests/connectors/test_bus_interpolation.py, reusing _synthetic_feed, _connector, _patch_io and the autouse cache fixture from Task 1.
- For the cache tests, call await connector._get_reduced_feed(...) directly, with _parse_gtfs replaced by a counting fake at class level via monkeypatch. Inspect bi._REDUCED_FEED_CACHE.
- For the no-town-service test, use _patch_io with the overridden calendar and run one fresh connector's run().
- Name the tests test_reduced_feed_yields_same_active_trips_as_full_feed, test_missing_optional_tables_do_not_raise (parametrized), test_different_zip_reparses_and_keeps_one_entry_per_bbox, test_parse_failure_is_not_cached, test_concurrent_calls_parse_once and test_no_active_town_service_still_removes_stale_bus_features.
- Run the target file. Expect test_no_active_town_service_still_removes_stale_bus_features to fail. The others guard Task 1 behaviour and should already pass; note in the SUMMARY which ones did.
- If any guard test fails, that is a Task 1 defect: fix it in Step 2, inside backend/app/connectors/bus_interpolation.py only.
- Commit only the test file with subject "test(quick-261115-ved): equivalence, optional-table, cache and no-service cleanup tests (RED)".

Step 2, fix. In run()'s "No active services for %s — skipping interpolation." branch, add await self._cleanup_old_features(set()) between the existing log line and the existing await self._update_staleness(). Keep the log text and the early return.

Add a short comment explaining why the call is needed. The reduced calendar covers only town services, so an empty set now means no bus runs in the town today. On the old full-feed path that case never reached this branch, because statewide services are always active. It went on to _build_active_trips, which returned [], and then to _cleanup_old_features(set()), which removed all bus-pos dots. This call keeps that result.

This is a deliberate one-line addition to keep public behaviour (the features on the map) unchanged. Without it, stale dots would stay all day once the cache path is in place. Make no other run() changes. Run the target file until green, then commit only backend/app/connectors/bus_interpolation.py with subject "fix(quick-261115-ved): keep removing stale bus-pos features when no town service runs today".

Step 3, regression. Run the full suite command from the verification section with -rfE. The command exits non-zero because of the baseline failures, so judge it by comparing ids, not by its exit status. Compare the FAILED and ERROR ids with the Task 1 baseline list. The goal: no id that is not in the baseline, and passed = baseline passed + the number of new tests (count parametrized cases individually).
- If a non-baseline failure appears, decide whether it is caused by this change: run that single test id alone and check whether it imports bus_interpolation. Fix it only if it is.
- Record the before/after counts and the comparison in the SUMMARY. Also record the two log-count differences listed in this plan's verification section.
  </action>
  <verify>
    <automated>cd backend && UV_PROJECT_ENVIRONMENT="/private/tmp/claude-501/-Users-hannessuhr-Library-Application-Support-Claude-scratch-workspaces-917fe486-0d98-4ede-ac88-e647c09dcb55-4c52147a-b177-4f3c-8801-8ef7ea1c9bce-scratch-2026-11-15-7357de/2d37f251-3d2e-41ee-ae9f-b74e9b5a9365/scratchpad/venv" uv run --frozen pytest -q -m "not slow" -p no:cacheprovider tests/connectors/test_bus_interpolation.py</automated>
    <automated>cd backend && UV_PROJECT_ENVIRONMENT="/private/tmp/claude-501/-Users-hannessuhr-Library-Application-Support-Claude-scratch-workspaces-917fe486-0d98-4ede-ac88-e647c09dcb55-4c52147a-b177-4f3c-8801-8ef7ea1c9bce-scratch-2026-11-15-7357de/2d37f251-3d2e-41ee-ae9f-b74e9b5a9365/scratchpad/venv" uv run --frozen pytest -q -m "not slow" -p no:cacheprovider -rfE</automated>
    <automated>git status --short</automated>
  </verify>
  <done>
    - The target file passes: 13 original tests, 2 from Task 1, and all Task 2 tests including each parametrized case.
    - The full suite shows no failing or erroring id outside the baseline.
    - The git status still lists the pre-existing untracked .planning/ and docs/ files, and no modified tracked files remain.
    - Task 2 added two commits (RED test, then fix), each touching only its one file and ending with the Co-Authored-By trailer.
  </done>
</task>

</tasks>

<source_audit>
| Source | Item | Covered by |
|---|---|---|
| GOAL | Parse the statewide feed once per zip instead of every 30 s; per-run pandas work off the event loop | Task 1 (tracer), Task 2 |
| REQ VED-01 | reduce_feed_to_bbox: a pure, vectorised helper; keeps whole touching trips; tolerates missing optional tables (orchestrator design item 1) | Task 1 Step 2, tests in Task 1 and Task 2 (keep/drop, equivalence, optional tables) |
| REQ VED-02 | Module-level cache keyed by (len, crc32, bbox), latest entry per bbox, asyncio.Lock, parse and reduce in one to_thread call, failures not cached (design item 2) | Task 1 Step 2, Task 2 cache, failure and concurrency tests |
| REQ VED-03 | _get_active_service_ids and _build_active_trips via asyncio.to_thread; checked at planning time that they touch no DB or loop (design item 3) | Task 1 Step 2 and its off-main-thread test |
| REQ VED-04 | Public behaviour unchanged: features, properties, logging text, /tmp/gtfs_cache.zip sharing, 7-day TTL; GTFSConnector, scheduler, layers router and frontend untouched (design item 4) | Task 1 feature-property assertions, Task 2 no-service cleanup and full-suite regression |
| RESEARCH | none (no research phase) | n/a |
| CONTEXT | no CONTEXT.md; the orchestrator's settled design items 1-4 are treated as locked | as above |
</source_audit>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| NVBW GTFS zip -> parser | The statewide zip in /tmp/gtfs_cache.zip is untrusted external open data, parsed by gtfs_kit and pandas |
| Background job -> event loop | CPU-bound pandas work shares the uvicorn event loop with all API endpoints |

## STRIDE Threat Register (ASVS L1, block on high)

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-261115-ved-01 | Denial of Service | BusInterpolationConnector.run every 30 s (event loop starvation, /api/kpi at 47 s) | high | mitigate | Parse and reduce once per zip inside one asyncio.to_thread under _REDUCED_FEED_LOCK; per-run _get_active_service_ids and _build_active_trips in asyncio.to_thread; crc32 also in a thread. Proven by the parse-count, concurrency and off-main-thread tests. |
| T-261115-ved-02 | Denial of Service (memory) | _REDUCED_FEED_CACHE | medium | mitigate | One entry per bbox, replaced on a zip change; the reduced namespace holds only filtered frames and no reference to the statewide feed. Checked by the single-entry assertion in test_different_zip_reparses_and_keeps_one_entry_per_bbox. |
| T-261115-ved-03 | Tampering | Corrupt or replaced GTFS zip | low | accept | The trust model is unchanged from today. A parse failure returns None and is never cached, so a fixed zip is picked up on the next run. crc32 only detects changes and makes no integrity claim. |
| T-261115-ved-04 | Tampering (stale state) | Stale bus-pos features when no town service runs today | medium | mitigate | _cleanup_old_features(set()) in the no-active-services branch (Task 2), proven by test_no_active_town_service_still_removes_stale_bus_features. |
| T-261115-ved-SC | Tampering | npm/pip/cargo installs | low | accept | This plan installs no packages; uv runs with --frozen against the existing lock. |
</threat_model>

<verification>
Full-suite command (run from the repo root; the same command the orchestrator used for its baseline):
cd backend && UV_PROJECT_ENVIRONMENT="/private/tmp/claude-501/-Users-hannessuhr-Library-Application-Support-Claude-scratch-workspaces-917fe486-0d98-4ede-ac88-e647c09dcb55-4c52147a-b177-4f3c-8801-8ef7ea1c9bce-scratch-2026-11-15-7357de/2d37f251-3d2e-41ee-ae9f-b74e9b5a9365/scratchpad/venv" uv run --frozen pytest -q -m "not slow" -p no:cacheprovider

Checks:
- The target test file is fully green.
- The full suite has no failing or erroring id outside the baseline recorded in Task 1 Step 0.
- git log shows four commits for quick-261115-ved (RED, fix, RED, fix), each touching only its listed file.
- No push, no branch change, no Docker rebuild. The orchestrator measures endpoint latency after rebuilding the backend image.

Known, intended log-count differences (the message text is unchanged; record these in the SUMMARY):
- "Stops in Aalen bbox: %d" now counts only bbox stops that some trip serves.
- "Shape coords available: %s (%d shapes)" now counts only shapes of town trips.
- In the rare no-town-service case, run() logs "No active services ..." instead of reaching the zero-trip log lines.
</verification>

<success_criteria>
- A scheduler-style sequence of runs parses the statewide NVBW feed once per distinct zip and bbox, not every 30 s.
- No pandas work from BusInterpolationConnector runs on the event-loop thread.
- The same bus-pos features and properties are produced. Stale bus-pos features are still removed when no town trip runs.
- No DB, network or Docker interaction from the new tests. Production code changes are limited to backend/app/connectors/bus_interpolation.py.
</success_criteria>

<output>
Create `.planning/quick/261115-ved-cache-the-town-reduced-gtfs-feed-in-busi/261115-ved-SUMMARY.md` when done
</output>
