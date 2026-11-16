---
phase: quick-261116-eoz
plan: 01
subsystem: frontend-map
tags: [maplibre, fill-extrusion, 3d, air-quality, ev-charging, parking, heat-demand, traffic-flow]
requires: []
provides:
  - "3D-Daten switch (registry key data3d, group threeD, default on)"
  - "frontend/lib/extrude.ts pure geometry helpers"
  - "ColumnLayer: reusable fill-extrusion GeoJSON layer"
  - "3D forms of air quality, EV charging, parking, heat demand and traffic flow"
affects:
  - frontend/components/map/MapView.tsx
key-files:
  created:
    - frontend/lib/extrude.ts
    - frontend/components/map/ColumnLayer.tsx
  modified:
    - frontend/lib/layer-registry.ts
    - frontend/hooks/useUrlState.ts
    - frontend/app/page.tsx
    - frontend/components/sidebar/Sidebar.tsx
    - frontend/components/map/MapView.tsx
    - frontend/components/map/EvChargingLiveLayer.tsx
    - frontend/lib/map-styles.ts
    - frontend/components/map/AirQualityHeatmapLayer.tsx
    - frontend/components/map/ParkingLayer.tsx
    - frontend/components/map/HeatDemandLayer.tsx
    - frontend/components/map/TrafficFlowLayer.tsx
    - frontend/components/map/LegendOverlay.tsx
decisions:
  - "Air-grid cells are not clickable; clicks fall through to columns, buildings and other features beneath"
  - "Air cells are rectangles sized from the measured grid spacing x 0.92 (0.005 deg on both axes = about 366 m x 556 m)"
  - "EAQI bands mirrored from backend/app/schemas/geojson.py into map-styles.ts"
  - "In 3D mode the purple infrastructure EV clusters are hidden together with the flat EV circles"
status: complete
commits: 3
plan_head_before: d17e3baed5b3babeca2e665d5b159a22e5e3ca5a
plan_head_after: c8984256656a6a7e2901aeaad78fc8c575529b16
actuals:
  tokens: 8400
  tasks: 3
  commits: 3
metrics:
  completed: 2026-11-16
---

# Quick Task 261116-eoz: 3D data layers Summary

MapLibre fill-extrusion columns and cells (no deck.gl, no new dependency) lift air quality, EV charging, parking and heat demand into the 3D scene behind a default-on "3D-Daten" switch; traffic flow gets a congestion-coloured glow plus a moving ant-path dash. With the switch off every layer draws as on d17e3ba.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 (tracer) | 1e360fb | data3d switch end-to-end, extrude.ts, ColumnLayer, EV columns, popup wiring |
| 2 | bf529a6 | air-quality EAQI cells, parking columns with ring spread, heat-demand columns |
| 3 | c898425 | traffic glow + dash animation, 3D legend lines, traffic-flow prefix routing |

Three feat commits, 14 files, 874 insertions / 80 deletions. Nothing pushed. No package, backend or test-runner change.

## What was built

- **Switch:** registry entry `data3d` (url key `data3d`, label "3D-Daten", group `threeD`, no metadataKey), default URL layers `transit,aqi,buildings3d,terrain3d,data3d`, Sidebar `LayerToggle`, `data3dVisible` prop page -> MapView (default false). The master data switch ignores it (group is not a data group).
- **extrude.ts:** `offsetLngLat`, `regularPolygon` (CCW, closed), `cellFromPoint`, `gridSpacing`, `spreadApproximate`, `columnsFromPoints` (plus an exported `haversineM` helper). Only a type import from `geojson`.
- **ColumnLayer:** Source `${id}-source` + fill-extrusion Layer, base 0 (keeps MapLibre's terrain basement), vertical gradient, paint memoised, `beforeId` = first label layer, optional children share the source.
- **EV:** 6-sided columns, status colours via the shared `EV_STATUS_COLOR`. InfrastructureLayer receives `evChargingVisible && !data3dVisible`, so the purple clusters/points disappear in 3D.
- **Air quality:** cells memoised on `[extruded, data]` only; heights for all four pollutants precomputed as `height_pm25|pm10|no2|o3`; the active pollutant only changes `fill-extrusion-height` (`height_<pollutant>`) and the colour expression. Heatmap hidden while extruded. Sensor layer untouched.
- **Parking:** garages with `location_approximate` sharing a position are placed on a ring (min 75 m apart) sorted by `garage_code|name`; free-spot labels via child layer `parking-labels-3d`.
- **Heat demand:** axis-aligned square columns.
- **Traffic flow:** glow layer (beneath `traffic-flow-lines`) and dash layer on top; animation is a rAF loop in a `useEffect` calling `setPaintProperty` at most every 80 ms; stops on 3D off / unmount, hidden tab, prefers-reduced-motion; never in React state. The TomTom-filtered collection is now memoised (it was a new object on every render before).
- **Popups:** new layer ids are in `interactiveLayerIds` and the layer-id chain; `traffic-flow` prefix routes to `trafficFlow` before the generic `traffic` prefix. Column features carry `_center_lng/_center_lat`; the popup anchors there. A pick step prefers the first non-`buildings-3d` interactive hit.
- **Legend:** "3D-Daten" block with one line per active 3D layer; air line names the active pollutant (PM2.5 / PM10 / NO₂ / O₃).

## Decision: air-cell clicks

A click on an air cell opens no popup. The existing air-quality popup is a sensor popup (title "Luftqualitätssensor", "Kein aktueller Messwert" because cells carry no `aqi`, unrounded concentrations, badge `unknown`, sensor-chart lookup without a `feature_id`), which does not fit a grid cell. Implementation: `AIR_QUALITY_CELLS_LAYER_ID` is not in `interactiveLayerIds`, and its hits are also filtered out of the 10 px fallback results, so a click falls through to columns, buildings or other features at that spot; if nothing remains, no popup. The explanatory comment sits next to that filter in MapView's onClick.

## Tuning constants (for the orchestrator's visual pass)

| Layer | Constants |
|-------|-----------|
| Air cells (AirQualityHeatmapLayer.tsx) | `AIR_CELL_INSET` 0.92, `AIR_CELL_BASE_M` 20, `AIR_CELL_MODERATE_TOP_M` 500, `AIR_CELL_MAX_M` 1500, `AIR_CELL_OPACITY` 0.6; EAQI bands in map-styles.ts `EAQI_BREAKPOINTS` (moderate tops: pm25 25, pm10 50, no2 50, o3 130) |
| EV (EvChargingLiveLayer.tsx) | `EV_COLUMN_RADIUS_M` 22, `EV_COLUMN_SIDES` 6, `EV_COLUMN_BASE_M` 30, `EV_COLUMN_M_PER_SQRT_KW` 45, `EV_COLUMN_MAX_M` 600, `EV_COLUMN_OPACITY` 0.9 |
| Parking (ParkingLayer.tsx) | `PARKING_COLUMN_RADIUS_M` 30, `PARKING_COLUMN_SIDES` 16, `PARKING_MIN_SEPARATION_M` 75, `PARKING_COLUMN_BASE_M` 20, `PARKING_COLUMN_M_PER_SPOT` 2, `PARKING_COLUMN_MAX_M` 300, `PARKING_COLUMN_OPACITY` 0.85 |
| Heat demand (HeatDemandLayer.tsx) | `HEAT_COLUMN_MIN_RADIUS_M` 8, `HEAT_COLUMN_MAX_RADIUS_M` 25 (radius = sqrt(area_m2 / 2)), `HEAT_COLUMN_M_PER_KWH` 0.6, `HEAT_COLUMN_MIN_M` 5, `HEAT_COLUMN_MAX_M` 400, `HEAT_COLUMN_OPACITY` 0.85 |
| Traffic (TrafficFlowLayer.tsx) | `DASH_STEP_MS` 80, `ANT_PATH_SEQUENCE` (14 steps), glow width 12/24/36 and blur 6/12/18 at zoom 10/14/18, glow opacity 0.35, dash width 1.5/3/4.5, dash opacity 0.85 |

## Verification results

- Geometry check (`eoz-extrude-check.mts`): PASS (a) to (f); (g) PASS against the live backend (spacing 0.005 / 0.005, 1,400 cells). Runner: `node --experimental-strip-types` (Node v22.23.1); jiti was not needed. Node prints a harmless MODULE_TYPELESS_PACKAGE_JSON warning.
- Static check stages 1, 2 and 3: PASS.
- Extra check: the EAQI colour expression and the parking colour expression validated with `@maplibre/maplibre-gl-style-spec` createExpression and evaluated on sample values (pm25 3 -> good, 30 -> poor, 100 -> extremely poor, null/missing -> grey; parking occupancy / closed / open all as intended).
- `npx tsc --noEmit`: 0 errors.
- `npm run lint`: before 20 problems (10 errors, 10 warnings); after 20 problems (10 errors, 10 warnings). Not worse.
- eslint on the touched files: before 3 problems (2 errors, 1 warning) in MapView.tsx; after the same 3 (react-hooks/immutability at the `setPopupInfo` effect, exhaustive-deps on the bus-tracking effect, `no-explicit-any` at the bbox fallback), only shifted by line number. extrude.ts and ColumnLayer.tsx are clean.
- `npm run build`: passes.
- `git diff --quiet` on frontend/package.json and frontend/package-lock.json: unchanged.
- Commits contain only files_modified; unrelated untracked `.planning/` and `docs/` files left uncommitted.
- Measured commit count (ledger-based): 3; `actuals.tokens` is chars/4 over the added diff lines (33,717 chars).

## Deviations from Plan

None - plan executed as written. Small additions inside plan scope: `haversineM` is exported from extrude.ts (used by the check script's reasoning, harmless), `Data3dLayers` type is exported from LegendOverlay.tsx, and the dash `setPaintProperty` call is wrapped in try/catch so a base-map style swap cannot throw inside the animation loop.

## Known Stubs

None.

## Threat Flags

None. No new endpoints, auth paths or schema changes; all heights are capped and non-finite inputs are skipped (T-261116-eoz-01), the animation is throttled and stoppable (T-261116-eoz-02), air cells are memoised and not rebuilt on pollutant switches (T-261116-eoz-03).

## PENDING - orchestrator (browser)

1. data3d on (default URL): air-quality cells stand on the terrain (not below it, not floating; note any edge float/sink on slopes), cover the town bbox with small even gaps, opacity lets the city show through.
2. Switching the pollutant (PM2.5 / PM10 / NO2 / O3) changes cell heights and colours with no visible rebuild pause.
3. EV, parking and heat columns stand at their locations, colours match the flat layers, and clicking each opens its usual popup at the column.
4. The four approximate parking garages (P1 Kubus, P1 Rathaus, P6 Bahnhof, P3 Spritzenhausplatz) stand separately on a ring; free-spot numbers visible.
5. Traffic-flow lines glow and the white dash moves along them; it stops with reduced motion enabled and resumes after a hidden tab returns.
6. Clicking an air cell opens nothing; clicking a building or column inside the air field still opens its popup.
7. Switching data3d off restores today's flat layers exactly (air heatmap, EV status circles plus purple infrastructure clusters, parking circles plus labels, heat circles, plain traffic lines).
8. Legend panel shows the 3D lines for the layers that are on, with the active pollutant name.
9. No new console errors (in particular no 'Cannot add layer before non-existing layer').

Additional notes for the browser pass: the dash layer has no `beforeId`, so it draws above labels; `line-dasharray-transition` is set to duration 0 (accepted by tsc, behaviour untested); parking label placement on polygons (`parking-labels-3d`) is untested visually; reduced-motion leaves the dash static at its first step rather than hiding it.

## Self-Check: PASSED

- FOUND: frontend/lib/extrude.ts, frontend/components/map/ColumnLayer.tsx
- FOUND commits: 1e360fb, bf529a6, c898425 (all ancestors of HEAD)

## Orchestrator browser verification and tuning (2026-11-16)

Checked on a local production build against the running backend (dark base, noon via `?ts=`).

Verified:
- All 3D layers stand on the terrain: air-quality bars, EV, parking and heat columns; `traffic-flow-glow` and `traffic-flow-dash` draw with the moving dash.
- Column popup: a click on an EV column standing on a traffic line opens the EV popup (after the fix below).
- The six parking columns are at six distinct positions (four flagged `location_approximate`).
- Legend panel shows the five explanation lines.
- Switching "3D-Daten" off removes every 3D layer and brings back `ev-charging-live-points`, `parking-points`, `heat-demand-points` and the plain traffic line; switching it on again restores the 3D forms.

Tuned in commit after the executor's three (constants in the layer files):
- Air: `AIR_CELL_INSET` 0.92 -> 0.3, base 20 -> 10 m, opacity 0.6 -> 0.75. At 0.92 the cells formed a solid teal slab over the whole city.
- EV: 30 m + 45*sqrt(kW), max 600 -> 15 m + 12*sqrt(kW), max 250 (22 kW = 71 m).
- Parking: 20 m + 2 m/spot, max 300 -> 15 m + 1.2 m/spot, max 200.
- Heat: 0.6 -> 0.3 m per kWh/m2a, max 400 -> 200.
- Click selection: features on `*-columns-3d` / `bus-position-3d` win over flat features under the cursor.

Not verified:
- Switching the pollutant in 3D mode (heights and colours should change without a rebuild pause) was not exercised.
- Heat-demand and parking popups were not clicked individually; they use the same mapping as EV.
- Reduced-motion behaviour, and how the bars look on steep slopes at close range.
- All timing: the test browser pane was hidden, which throttles rendering.

Open:
- With today's clean air (PM2.5 around 1-8 ug/m3) all bars are short and the same colour; the field only becomes expressive with higher values.
- EV status is `UNKNOWN`/`STATIC` for most stations, so most EV columns are grey.
