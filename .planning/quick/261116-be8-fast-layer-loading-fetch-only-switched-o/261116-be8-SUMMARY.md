---
phase: quick-261116-be8
plan: 01
subsystem: layers-api, frontend-data-loading
tags: [performance, postgis, transit, hooks, request-sharing]
status: complete
requirements: [quick-261116-be8]
key-files:
  modified:
    - backend/app/routers/layers.py
    - backend/tests/test_api_layers.py
    - frontend/hooks/useLayerData.ts
    - frontend/hooks/useGridLayerData.ts
    - frontend/hooks/useLayerMetadata.ts
    - frontend/lib/api.ts
    - frontend/app/page.tsx
    - frontend/components/map/BusRouteLayer.tsx
    - frontend/components/map/BusStopLayer.tsx
    - frontend/components/map/CommunityLayer.tsx
    - frontend/components/map/InfrastructureLayer.tsx
    - frontend/components/sidebar/Sidebar.tsx
actuals:
  tasks: 3
  commits: 3
plan_head_before: b365190fadae9bb766e59f7d11b4d48d27ae02f9
plan_head_after: aabf221b2a77a7680ef1213516f215a9d1c795dc
commits: 3
---

# Quick 261116-be8: Fast layer loading — fetch only what is switched on

One-liner: layer data is fetched only while a consuming layer is on, the transit shapes endpoint clips lines to the town bbox, simplifies, reduces precision and de-duplicates them in SQL, layer metadata comes from the API origin, and identical concurrent GETs share one request.

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | c9a9a99 | perf: serve transit shapes clipped, simplified and de-duplicated; fetch bus routes and stops only while visible |
| 2 | e96044b | perf: fetch page-level and always-mounted layer data only while a consuming layer is on |
| 3 | aabf221 | fix: load layer metadata from the API origin and share identical in-flight requests |

## What changed

- **Backend** (`layers.py`): `build_transit_layer_query` (pure; bbox, tolerance, town and feature type are all bind parameters; only the module int `SHAPE_COORD_PRECISION` is formatted in), `dedupe_shape_rows` (pure), constants `SHAPE_SIMPLIFY_TOLERANCE_DEG = 0.00005`, `SHAPE_COORD_PRECISION = 5`. Line geometries (`ST_Dimension = 1`) are clipped with `ST_Intersection` against `ST_MakeEnvelope`, reduced to line parts with `ST_CollectionExtract(..., 2)`, simplified with `ST_SimplifyPreserveTopology`, serialised at 5 decimals; empty lines dropped; points untouched. The old `MAX(created_at) ... GROUP BY` was removed (`f.id` is the primary key, so the group was one row per feature). Response schema and `at` handling are unchanged.
- **Hooks**: `useLayerData` and `useGridLayerData` take `{ enabled }` (default true; no fetch, no interval while false; immediate fetch when it flips on).
- **page.tsx**: transit fetches only `feature_type=stop`, gated by transit; air quality and grid gated by `airQuality`; water gated by `water || kocher`; the page-level traffic and energy hooks are removed.
- **Always-mounted layers**: BusRouteLayer / BusStopLayer gated by `visible`; CommunityLayer by any of its four switches; InfrastructureLayer by `evCharging || roadworks`.
- **Metadata**: `useLayerMetadata` uses new `fetchLayerMetadata` (API_BASE) instead of the relative URL that 404ed on the Next.js origin; Sidebar now passes its `town` (it previously always used 'aalen').
- **In-flight sharing** (`lib/api.ts` `getJsonShared`): layer, grid, KPI and metadata GETs with the same URL in flight share one promise of parsed JSON; the entry is deleted on settle (not a cache).

## Verification (executor, all automated)

- Backend pytest `-m "not slow"`:
  - before: `10 failed, 324 passed, 1 skipped, 4 deselected, 1 warning, 6 errors`
  - after: `10 failed, 329 passed, 1 skipped, 4 deselected, 1 warning, 6 errors` (+5 new tests)
  - failing/error ids: `diff failing-before.txt failing-after.txt` is empty (identical; the pre-existing failures are environment/config related: test_boundaries, test_config, test_multi_town, test_connector, test_ladesaeulen).
  - `test_layers_transit_returns_geojson` passed before and after (it runs the real SQL against the live PostGIS).
- Additional read-only live SQL check against the running database (SELECT only, rolled back), with the new builder and dedupe:
  - stops: 571 rows -> 571, Point only, 0.20 s, ~30 KB geometry.
  - shapes: 1537 rows -> 930 after clipping+dedupe, geometry types only LineString / MultiLineString, 1.29 s query, ~3.6 MB geometry text. This is above the 2 MB target (the target is measured by the orchestrator on the rebuilt stack; note it before assuming the target is met). ST_ClipByBox2D remains the known faster follow-up for the time side.
- Frontend: `npx tsc --noEmit` 0 errors; `npm run lint` before 23 problems (10 errors, 13 warnings), after 23 problems (10 errors, 13 warnings); `eslint` output on the ten touched frontend files identical before/after; `npm run build` passes.
- Static gates: `git grep -F "useLayerData('transit', town, historicalTimestamp)" -- frontend` no match (was 1); ``git grep -F 'fetch(`/api/metadata' -- frontend`` no match (was 1).
- `frontend/package.json`, `frontend/package-lock.json`, `backend/pyproject.toml`, `backend/uv.lock` unchanged vs b365190. No push.
- Baseline artefacts: SCRATCH/be8/{pytest-before,pytest-after,failing-before,failing-after,eslint-files-before,eslint-files-after,eslint-total-before}.txt and live_check.py under the scratchpad directory.

## Decisions and findings

- **Traffic/energy error flags dropped.** The page-level traffic and energy hooks only fed the red fetch-error dot (`trafficError`, `energyError` on Sidebar); their `.data` was never used. TrafficLayer, TrafficFlowLayer, AutobahnLayer, EnergyLayer, SolarGlowLayer and HeatDemandLayer fetch their own data when mounted, and the stale indicator from layer metadata (working again after the URL fix) remains. A fetch error cannot be derived without a fetch, so the two flags are no longer passed; Sidebar's optional props were left as is (no dot when undefined).
- **Transit cluster-count side effect.** The page-level transit data is now stops only (`feature_type=stop`), so the transit cluster bubbles at zoom 13 and below count only stops; before, bus_position and trip_update points of the unfiltered domain were clustered into them.
- **Double-request investigation (static only).** (a) Not a remount: HomeInner sits in a single Suspense boundary without a key, MapView is one `dynamic()` instance, no code navigates on mount. (b) Hook effect deps are primitive strings (ISO strings), so recreated `dateRange` / Date objects do not re-run them. (c) Real duplicates in our code existed: `/api/kpi` (page.tsx and DashboardPanel), `/api/metadata/layers` (Sidebar and DashboardPanel, and Sidebar used a hardcoded 'aalen'), identical traffic/energy/infrastructure URLs from several mounted layer components, and transit stop from page.tsx plus BusStopLayer when both are on; all collapsed by the in-flight sharing when they start together. (d) In development React StrictMode (no `reactStrictMode: false` in the Next config, so default on in the App Router) double-invokes effects; collapsed by the sharing too. (e) Every polled endpoint refetches after 60 s; with the old ~30 s transit response and ~50 s blank map, a resource list read after the first minute shows each polled URL twice, which is expected polling, not a bug. No further clear bug found.
- Shape de-duplication keys on (route_short_name, route_type_color, geometry text) and keeps the smallest id; the frontend does not depend on shape ids (MapLibre drops non-numeric ids anyway) and renders MultiLineString natively.

## Deviations from Plan

None - plan executed as written. (One addition: the extra read-only live SQL check above.)

## Known Stubs

None.

## PENDING — orchestrator (after rebuilding the backend image and running a production frontend build; not claimed here)

1. GET /api/layers/transit?town=aalen&feature_type=shape: payload size and time against the target of at most 2 MB and at most 2 s. The executor's read-only live run of the same SQL measured ~3.6 MB geometry text and 1.29 s DB time (930 shapes after dedupe), so the size target may be missed; if the time misses, ST_ClipByBox2D is the known faster drop-in for rectangular clipping of lines (a follow-up decision, not part of this plan).
2. Page load with layers=buildings3d,terrain3d makes NO /api/layers/* request.
3. Switching transit on fetches only /api/layers/transit?town=aalen&feature_type=stop.
4. Switching bus positions on fetches shape, stop and bus_position once each.
5. No request is issued twice on load — compare startTime of same-URL resource entries: pairs about 60 s apart are the scheduled poll, pairs within milliseconds are duplicates.
6. /api/metadata/layers answers 200 from the backend origin and the sidebar/dashboard freshness indicators populate.
7. Bus routes still draw correctly: clipped lines, no gaps at the bbox edge beyond the bbox itself, MultiLineString parts render; transit stops (clusters count stops only), bus popups and KPI tiles still work.

## Self-Check: PASSED

- Commits c9a9a99, e96044b, aabf221 exist on feat/layer-loading-and-registry (3 commits since b365190, measured via ledger).
- All twelve files_modified paths modified in those commits; no files outside the plan staged.

## Orchestrator live verification (2026-11-16)

Backend image rebuilt with these commits; frontend checked as a local production build against it.

Measured:
- Transit shapes (`/api/layers/transit?feature_type=shape`): 31.6 MB / 1,547 features / 1,353,202 coordinates before; 2.3 MB / 840 features / 107,725 coordinates after (LineString 293, MultiLineString 547, 80 route names). With gzip (commit added by the orchestrator, `GZipMiddleware` in backend/app/main.py) 0.22 MB on the wire.
- Response time for shapes: 2.7-4.0 s once the backend has finished starting (1.7-4.1 s before gzip; up to 30 s before this task). The 2 MB size target is met; the 2 s time target is NOT met. The clip and simplify run on every request and the bus layer re-polls every 60 s; caching the result (shapes change weekly) is the open follow-up.
- Page load with only `buildings3d,terrain3d`: no `/api/layers/*` request. Requests made: `/api/metadata/layers` (200, from the backend origin), `/api/kpi`, `/api/timeseries/air_quality`, once each.
- Switching transit on: exactly one request, `transit?feature_type=stop`, 0.4 s.
- Switching bus positions on: `shape`, `stop` and `bus_position` once each, 3.4-3.8 s.
- Bus routes draw in their line colours, clipped at the town bbox; stops, stop clusters, the bus line list and KPI tiles render.
- Backend tests after the gzip commit: 329 passed, 10 failed, 6 errors (same failing ids as the baseline).

Correction to an earlier measurement: the "map stays blank for about 50 s" observation was made in a browser pane that was hidden at the time, which throttles rendering. The download sizes and API response times above were measured with curl and are not affected, but on-screen render times from that pane are unreliable and were not re-measured.
