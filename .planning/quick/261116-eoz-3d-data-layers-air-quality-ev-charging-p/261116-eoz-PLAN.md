---
phase: quick-261116-eoz
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/lib/extrude.ts
  - frontend/components/map/ColumnLayer.tsx
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
autonomous: true
requirements:
  - quick-261116-eoz

estimate:
  tokens: 160000
  raw_tokens: 160000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "The 3D group of the sidebar has a third switch '3D-Daten' (registry key data3d, url key data3d, group threeD, no metadataKey); a URL without a layers parameter has it on (default 'transit,aqi,buildings3d,terrain3d,data3d'); the master data switch does not touch it"
    - "With data3d on and the layer's own switch on, EV charging stations stand as 6-sided columns (radius 22 m, height 30 m + 45 m x sqrt(power_kw), capped at 600 m, colour by status like the flat circles), parking garages as 16-sided columns (radius 30 m, height 20 m + 2 m x free_spots, capped at 300 m, occupancy colours when occupancy_pct exists, else blue open / grey closed, free-spot number still shown), heat-demand points as axis-aligned squares (radius sqrt(area_m2 / 2) clamped to 8..25 m, height 0.6 m per kWh/m2a, capped at 400 m, colour by heat_class like the flat circles); the flat circles of these three layers, including the purple infrastructure-ev clusters and points, are not drawn"
    - "With data3d and air quality on, the air grid is drawn as rectangular cells (cell size = grid spacing measured from the data x 0.92) at opacity 0.6 whose height (20 m base, 500 m at the top of the EAQI 'moderate' band, capped at 1500 m) and EAQI colour come from the active pollutant; switching the pollutant changes only paint properties (no new GeoJSON is built); the air-grid heatmap is not drawn; the sensor layer (AQILayer) is unchanged"
    - "Parking features flagged location_approximate that share one position stand on a ring around that position, every pair at least 75 m apart, with the same garage at the same spot on every poll; the flag stays in their properties"
    - "With data3d and traffic flow on, every TomTom segment has a wide blurred glow in its congestion colour beneath the existing line and a white dash on top that moves along the line about 12 times per second; the animation does not run when 3D mode or the traffic-flow layer is off, while the tab is hidden, or when prefers-reduced-motion is set, and it never goes through React state"
    - "Clicking an EV, parking or heat-demand column, or a traffic glow/dash, opens the same popup component with the same properties as the flat counterpart, anchored at the column centre; clicking an air cell opens no popup and the click falls through to columns, buildings or other interactive features at that spot"
    - "With data3d off, every layer draws exactly as on d17e3ba (same layers, ids, paint, visibility)"
    - "The legend panel shows one short line per 3D layer that is on (air: 'Höhe = <pollutant>-Konzentration', EV, parking, heat, traffic)"
    - "cd frontend && npx tsc --noEmit reports 0 errors; npm run lint is not worse than the baseline recorded before the first edit and eslint on the touched files shows nothing new; npm run build passes; frontend/package.json and frontend/package-lock.json are unchanged"
  artifacts:
    - path: "frontend/lib/extrude.ts"
      provides: "Pure geometry helpers, no React/MapLibre runtime imports, runnable by Node type stripping"
      exports: ["offsetLngLat", "regularPolygon", "cellFromPoint", "gridSpacing", "spreadApproximate", "columnsFromPoints"]
    - path: "frontend/components/map/ColumnLayer.tsx"
      provides: "Reusable GeoJSON Source + fill-extrusion layer (vertical gradient, beneath the first label layer)"
      exports: ["default ColumnLayer"]
    - path: "frontend/lib/map-styles.ts"
      provides: "Per-pollutant EAQI breakpoints mirrored from backend/app/schemas/geojson.py and an EAQI colour step expression"
      exports: ["EAQI_BREAKPOINTS", "eaqiColorExpression"]
    - path: "frontend/components/map/TrafficFlowLayer.tsx"
      provides: "Glow + ant-path dash layers and the throttled dash animation"
      exports: ["TRAFFIC_FLOW_GLOW_LAYER_ID", "TRAFFIC_FLOW_DASH_LAYER_ID"]
  key_links:
    - from: "frontend/app/page.tsx layerVisibility.data3d"
      to: "frontend/components/map/MapView.tsx data3dVisible"
      via: "data3dVisible prop -> extruded prop of AirQualityHeatmapLayer, EvChargingLiveLayer, ParkingLayer, HeatDemandLayer, TrafficFlowLayer; InfrastructureLayer gets evChargingVisible && !data3dVisible"
    - from: "MapView interactiveLayerIds + onClick layer-id chain"
      to: "EvChargingPopup / ParkingPopup / HeatDemandPopup / TrafficFlowPopup"
      via: "EV_CHARGING_COLUMNS_LAYER_ID, PARKING_COLUMNS_LAYER_ID, HEAT_DEMAND_COLUMNS_LAYER_ID, traffic-flow prefix; AIR_QUALITY_CELLS_LAYER_ID removed from click candidates"
    - from: "AirQualityHeatmapLayer activePollutant"
      to: "ColumnLayer paint"
      via: "heightProperty 'height_' + pollutant and eaqiColorExpression(pollutant); geometry memo keyed on data only"
    - from: "TrafficFlowLayer animation effect"
      to: "MapLibre layer traffic-flow-dash"
      via: "map.setPaintProperty(TRAFFIC_FLOW_DASH_LAYER_ID, 'line-dasharray', sequence[step]) from a throttled requestAnimationFrame loop"
---

<objective>
Lift the city's public data into the existing 3D scene: a "3D-Daten" rendering-mode switch that, when on, draws air quality (grid cells), EV charging, parking and heat demand as extruded columns standing on the MapLibre terrain, and gives traffic flow a glow plus a moving dash. When the switch is off every layer draws exactly as today.

Purpose: the user wants "a really cool 3D version of the city with all public data shown in the graphics"; the basemap, terrain, sky and 3D buildings exist, but all data is still flat.
Output: frontend/lib/extrude.ts (pure geometry), frontend/components/map/ColumnLayer.tsx, a data3d registry entry, 3D forms in five layer components, popup and legend wiring in MapView/LegendOverlay. MapLibre layer types only: no deck.gl, no three.js, no new dependency (frontend/package.json and package-lock.json stay byte-identical), no backend change.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@frontend/AGENTS.md

Settled design (from the orchestrator; implement it, do not redesign it). Rendering uses MapLibre fill-extrusion only because extrusions stand on MapLibre terrain natively (buildings-3d and bus-position-3d already do).

Wiring facts observed at planning time (d17e3ba, branch feat/3d-data-layers):
- frontend/lib/layer-registry.ts: REGISTRY entries end with buildings3d and terrain3d in group threeD (isDataGroup false, so the master switch ignores it). LayerKey, LayerVisibility, visibilityFromUrl and the sidebar group header all derive from REGISTRY.
- frontend/hooks/useUrlState.ts line 40: default layers string 'transit,aqi,buildings3d,terrain3d'.
- frontend/components/sidebar/Sidebar.tsx lines 275-279: the 3D group renders LayerToggle explicitly per key (toggleProps('buildings3d'), toggleProps('terrain3d')); a new key needs its own LayerToggle line.
- frontend/app/page.tsx passes each visibility to MapView as a named prop (buildings3dVisible={layerVisibility.buildings3d}, ...). MapView's own layerVisibility prop type is narrow; use a new named prop data3dVisible.
- frontend/components/map/MapView.tsx: labelBeforeId = firstSymbolLayerId(mapStyle) (BuildingsLayer uses it as beforeId). EvChargingLiveLayer, ParkingLayer, HeatDemandLayer and TrafficFlowLayer are mounted only while their switch is on and fetch their own data with useLayerData; AirQualityHeatmapLayer gets airQualityGridData and activePollutant from MapView. InfrastructureLayer ALSO draws the same 83 EV stations (category ev_charging, all source ocpdb) as purple clusters/points (infrastructure-ev-*) whenever evChargingVisible is true.
- MapView onClick: features = e.features (interactive layers only); when empty it falls back to map.queryRenderedFeatures over a 10 px box across ALL layers. feature = features[0]; a ternary chain maps layer id -> PopupInfo domain; prefix branches exist for 'kocher', 'aqi', 'water', 'traffic', 'autobahn', 'energy', 'community-', and the default is 'transit'. Any new id starting with 'traffic' would fall into the BASt 'traffic' branch unless mapped before it.
- Popups (EvChargingPopup, ParkingPopup, HeatDemandPopup, TrafficFlowPopup) read only feature.properties, never geometry, so Polygon features with copied properties render the same content.
- MapLibre GeoJSON sources drop non-numeric feature ids; the live features have UUID string ids, so popups already rely on properties (same for flat and 3D).
- MapLibre (maplibre-gl ^6.18) fill-extrusion on terrain lifts each polygon by the terrain elevation at its centroid and adds a 10 m basement when fill-extrusion-base is 0. Keep base 0 everywhere. Large air cells on slopes may therefore show a little float/sink at their edges; the orchestrator judges this in the browser.
- line-dasharray is a transitionable cross-faded property in this style spec; setPaintProperty with a constant array works.

Live data measured at planning time (read-only curl against :8000):
- Air grid: 1,400 Points, exactly 50 unique longitudes x 28 unique latitudes, spacing 0.005 deg on both axes (about 366 m east-west x 556 m north-south at lat 48.84, so cells are rectangles, not squares: use cellFromPoint, not a 4-sided regular polygon). Properties pm25 (0.01..3.1), pm10 (0.13..49.6), no2 (0.4), o3 (1.98), aqi_tier 'unknown'. No feature_id property.
- EV: 83 Points, all source 'ocpdb'; status UNKNOWN 47 / AVAILABLE 26 / OCCUPIED 8 / INOPERATIVE 2; power_kw 11..400.
- Parking: 6 Points; P1 Kubus, P1 Rathaus, P6 Bahnhof, P3 Spritzenhausplatz all at [10.0935, 48.836] with location_approximate true (garage_code P1 occurs twice); P5 and P2 have location_approximate null; occupancy_pct and capacity are null for all.
- Heat demand: 50 Points; heat_demand_kwh_m2_y 33.9..342.7; area_m2 92.2..499.2; heat_class red 18 / orange 11 / green 9 / yellow 8 / light_blue 3 / blue 1.
- Backend EAQI bands (backend/app/schemas/geojson.py EAQI_BREAKPOINTS, citing airindex.eea.europa.eu, upper bounds of good, fair, moderate, poor, very_poor): pm25 5, 15, 25, 50, 75; pm10 10, 20, 50, 100, 150; no2 10, 20, 50, 100, 200; o3 50, 100, 130, 240, 380. The frontend mirrors these so cells and sensor badges agree.

Environment rules for the executor:
- Repo root is the cwd of every command below. Sequential execution on this working tree; frontend/node_modules is installed. Never push.
- Do not touch frontend/package.json or frontend/package-lock.json; no backend change; do not add a test runner.
- Docker stack is running (backend :8000, frontend :4000 built from an image, no bind mount, so a local next build is safe). Read-only curl is fine; do not rebuild/restart/stop containers and do not start a dev server.
- Never read, print or modify any dotenv file of the repo and do not name such paths in shell commands.
- Stage files explicitly by path (never git add -A or git add .). Untracked files under .planning/ and docs/ that are not this task's stay uncommitted. Never commit node_modules or .next.
- Commit messages: type(quick-261116-eoz): description, ending with the trailer line Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>
- frontend/AGENTS.md: this Next.js has breaking changes. These edits are client components using React hooks and react-map-gl only; if you touch any Next.js API, read the matching guide under frontend/node_modules/next/dist/docs/ first.
- SCRATCH = /private/tmp/claude-501/-Users-hannessuhr-Library-Application-Support-Claude-scratch-workspaces-917fe486-0d98-4ede-ac88-e647c09dcb55-4c52147a-b177-4f3c-8801-8ef7ea1c9bce-scratch-2026-11-15-7357de/2d37f251-3d2e-41ee-ae9f-b74e9b5a9365/scratchpad (the session scratchpad, outside the repo; the one-off check scripts live here and are never committed). If that directory does not exist for you, use your own session scratchpad and say so in the SUMMARY.

Source coverage audit (quick task: the orchestrator design items are the source):
| Item | Covered by |
|---|---|
| 1 data3d switch, threeD group, on by default | Task 1 |
| 2 pure geometry helper (regularPolygon, columnsFromPoints, cell helper) | Task 1 |
| 3 reusable ColumnLayer beneath first label layer | Task 1 |
| 4 EV columns | Task 1 |
| 4 air grid cells, EAQI per-pollutant bands, height constants | Task 2 |
| 4 parking columns + approximate-position ring | Task 2 |
| 4 heat-demand columns | Task 2 |
| 4 traffic glow + ant-path dash, stop rules | Task 3 |
| 4 flat and 3D never visible together | Tasks 1-3 (per layer) |
| 5 popups for every new layer id, air-cell click decision | Tasks 1-3 |
| 6 legend lines | Task 3 |
| 7 useMemo, pollutant switch without rebuild | Tasks 1-2 |
| Verification list incl. PENDING browser list | Tasks 1-3, verification section |
Out of scope and not planned: buildings coloured by data, bus/train 3D models, time animation of data, deck.gl, backend changes, new data sources, sidebar restyling.
</context>

<tasks>

<task type="tracer">
  <name>Task 1: Tracer - 3D-Daten switch end-to-end with EV charging columns (geometry helper, ColumnLayer, registry, URL default, sidebar, page, MapView, popup)</name>
  <files>frontend/lib/extrude.ts, frontend/components/map/ColumnLayer.tsx, frontend/lib/layer-registry.ts, frontend/hooks/useUrlState.ts, frontend/app/page.tsx, frontend/components/sidebar/Sidebar.tsx, frontend/components/map/MapView.tsx, frontend/components/map/EvChargingLiveLayer.tsx</files>
  <read_first>frontend/components/map/MapView.tsx, frontend/components/map/EvChargingLiveLayer.tsx, frontend/components/map/BuildingsLayer.tsx, frontend/lib/layer-registry.ts, frontend/hooks/useUrlState.ts, frontend/components/sidebar/Sidebar.tsx (lines 75-110 and 270-280), frontend/app/page.tsx (lines 225-271)</read_first>
  <action>
Step 0 - baselines before any edit. Run cd frontend and npm run lint, and save the final problems summary line (expected around 10 errors / 10 warnings) to SCRATCH/eoz-lint-baseline.txt. Also run npx eslint on the 14 files listed in files_modified that already exist at HEAD (12 of them; extrude.ts and ColumnLayer.tsx are new) and save the full output to the same scratch folder as eoz-eslint-touched-baseline.txt. These two files are what Task 3 compares against.

Step 1 - frontend/lib/extrude.ts (new, design item 2). Pure TypeScript: the only import allowed is a whole-statement type import from 'geojson' (import type { ... } from 'geojson'); no runtime imports, no '@/' aliases, no enums, namespaces or parameter properties, so Node 22 type stripping can execute the file directly. Constants: EARTH_RADIUS_M = 6371008.8 and METERS_PER_DEGREE = PI x EARTH_RADIUS_M / 180. Exports:
- offsetLngLat(lng, lat, dxMeters, dyMeters) returns [lng, lat] moved dx east and dy north: dLat = dy / METERS_PER_DEGREE, dLng = dx / (METERS_PER_DEGREE x cos(lat in radians)).
- regularPolygon(lng, lat, radiusMeters, sides, rotationDeg = 0) returns a closed ring (sides + 1 positions, last equals first) whose vertex k sits at angle rotationDeg + 360 x k / sides, measured counter-clockwise from east, at radiusMeters from the centre via offsetLngLat (round on the ground thanks to the cos(lat) factor). Counter-clockwise order (RFC 7946 exterior winding, matches building tiles so wall lighting is not inverted). rotationDeg 45 with 4 sides gives an axis-aligned square.
- cellFromPoint(lng, lat, widthDeg, heightDeg) returns the closed 5-position counter-clockwise rectangle centred on the point (SW, SE, NE, NW, SW).
- gridSpacing(points) takes Point features and returns { dLng, dLat } or null: per axis, round coordinates to 1e-7, take unique sorted values, spacing = smallest positive difference. If one axis has fewer than two unique values, use the other axis's spacing; if neither has, return null. No town-specific defaults (CLAUDE.md: no Aalen hardcoding).
- spreadApproximate(features, { flagProperty, minSeparationMeters, sortKey }) returns new features: features whose flagProperty is truthy are grouped by coordinate (rounded to 1e-6); groups of n of at least 2 move onto a ring of radius minSeparationMeters / (2 x sin(PI / n)) around the shared point, member k (after sorting the group by sortKey(properties), ties by original index) at bearing 360 x k / n clockwise from north. Unflagged features and single flagged features keep their coordinates. Properties (including the flag) and id are copied; input is not mutated.
- columnsFromPoints(features, options) returns a FeatureCollection of Polygons. Options: footprint either { radiusMeters: number or (props) => number, sides, rotationDeg? } or a function (lng, lat, props) => ring; height(props) => number; extra?(props) => record of extra properties. For each Point feature with finite coordinates and a finite height: Polygon from the footprint, id copied when defined, properties = original properties + extra + height_m + _center_lng and _center_lat (the point used as centre). Non-Point features and non-finite values are skipped.

Step 2 - geometry check script SCRATCH/eoz-extrude-check.mts (never committed). It takes the repo-relative path of extrude.ts as argv[2], imports it via pathToFileURL(path.resolve(...)), and asserts with node:assert, printing one PASS line per check and exiting non-zero on failure:
(a) regularPolygon at (10.0918, 48.84) for (22 m, 6), (30 m, 16), (15 m, 4, rotation 45): ring length sides + 1, first equals last, every vertex within 1 % of radiusMeters by haversine distance (R = 6371008.8), signed area positive (counter-clockwise).
(b) cellFromPoint: 5 positions, closed, east-west extent equals widthDeg and north-south extent equals heightDeg within 1e-12.
(c) gridSpacing on a synthetic 50 x 28 grid built as 9.97 + 0.005 x i and 48.76 + 0.005 x j (float noise included) returns 0.005 on both axes within 1e-9; on a single point returns null.
(d) tiling: 3 x 3 synthetic grid at lat 48.84, spacing 0.005, inset 0.92 via cellFromPoint: horizontally and vertically neighbouring cells do not overlap and the gap between them equals 0.005 x (1 - 0.92) within 1e-9 deg (never more than the configured inset gap).
(e) spreadApproximate: four flagged features at one point plus one unflagged at the same point plus one flagged alone elsewhere, minSeparationMeters 75: the four are pairwise at least 74.25 m apart (haversine), the unflagged and the lone flagged feature are unchanged, the flag is kept, and shuffling the input order gives each named feature the same position.
(f) columnsFromPoints: skips a LineString and a Point with NaN coordinate, keeps id and properties, adds numeric height_m, _center_lng, _center_lat and the extra properties.
(g) optional, only if http://localhost:8000/api/layers/air_quality?town=aalen&feature_type=air_grid answers within 5 s: gridSpacing returns 0.005 / 0.005 and columnsFromPoints with the cell footprint yields 1,400 polygons; print SKIP when the backend does not answer.
Run it with node --experimental-strip-types; if Node refuses to load the TypeScript module, run the same script with frontend/node_modules/.bin/jiti and note that in the SUMMARY.

Step 3 - frontend/components/map/ColumnLayer.tsx (new, 'use client', design item 3). Props: id, data (Polygon FeatureCollection or null), heightProperty (default 'height_m'), colorExpression (ExpressionSpecification or a colour string), opacity (default 0.85), beforeId, visible, children (optional ReactNode, rendered inside the Source after the extrusion layer so extra layers such as labels share the source). Renders null without data; otherwise a react-map-gl Source type geojson with id = id + '-source' and a Layer with the given id, type fill-extrusion, paint fill-extrusion-color = colorExpression, fill-extrusion-height = get heightProperty, fill-extrusion-base 0 (keeps MapLibre's terrain basement), fill-extrusion-opacity = opacity, fill-extrusion-vertical-gradient true; layout visibility from visible; beforeId passed through. Paint object memoised on heightProperty, colorExpression and opacity so React re-renders do not re-apply paint. Follow the typing pattern of BuildingsLayer.tsx (FillExtrusionLayerSpecification paint, ExpressionSpecification from maplibre-gl).

Step 4 - switch wiring (design item 1). layer-registry.ts: append { key: 'data3d', urlKey: 'data3d', label: '3D-Daten', group: 'threeD' } directly after terrain3d (no metadataKey, no externalWms). useUrlState.ts: default layers string becomes 'transit,aqi,buildings3d,terrain3d,data3d'. Sidebar.tsx: add a LayerToggle for 'data3d' after the terrain3d one inside the 3D group (no other sidebar change). page.tsx: pass data3dVisible={layerVisibility.data3d} to MapView next to terrain3dVisible. MapView: new optional prop data3dVisible (default false, so an absent prop means today's flat drawing).

Step 5 - EV columns (design item 4, EV). EvChargingLiveLayer.tsx: new optional props extruded and beforeId. Export EV_CHARGING_COLUMNS_LAYER_ID = 'ev-charging-columns-3d'. Move the status match expression into a module constant (EV_STATUS_COLOR) used by both the flat circle layer and the columns, so colours are identical. Memoise the ocpdb-filtered collection on data (useMemo) and, only while extruded, the columns: 6 sides, radius EV_COLUMN_RADIUS_M = 22, height = min(EV_COLUMN_MAX_M = 600, EV_COLUMN_BASE_M = 30 + EV_COLUMN_M_PER_SQRT_KW = 45 x sqrt(power_kw)), with power_kw missing, non-finite or negative giving the base height; opacity 0.9. All hooks run before any early return. Render the ColumnLayer (id EV_CHARGING_COLUMNS_LAYER_ID, beforeId) when extruded, otherwise exactly today's circle Source/Layer. Keep EV_CHARGING_LIVE_INTERACTIVE_LAYER_IDS as is.

Step 6 - MapView wiring for the tracer (design items 4 and 5). Pass extruded={data3dVisible} and beforeId={labelBeforeId} to EvChargingLiveLayer. Pass evChargingVisible={evChargingVisible && !data3dVisible} to InfrastructureLayer so its purple EV clusters/points are not drawn in 3D mode (roadworks and solar potential unaffected; the flat and 3D EV forms are never visible together). Add EV_CHARGING_COLUMNS_LAYER_ID to interactiveLayerIds and map it to 'evCharging' in the layer-id chain. Replace the bare features[0] pick with a small pick step: from the interactive results (e.features) prefer the first feature whose layer id is not 'buildings-3d', falling back to the first feature (columns are drawn beneath the labels next to the buildings, and a column click must not open the building popup; flat point layers already sort above buildings, so their behaviour is unchanged); the 10 px fallback query keeps today's first-feature behaviour. When the picked feature has numeric _center_lng and _center_lat properties, use them for the popup longitude/latitude instead of e.lngLat (a click high on a tall column hits the terrain far behind it). Do not change any other branch.

Step 7 - static check script SCRATCH/eoz-static-check.mjs (never committed), run from the repo root with a stage argument 1, 2 or 3; each stage includes the earlier ones. It reads files as text and asserts:
stage 1: layer-registry.ts has an entry with key 'data3d', urlKey 'data3d', label '3D-Daten', group 'threeD'; useUrlState.ts contains 'transit,aqi,buildings3d,terrain3d,data3d'; Sidebar.tsx contains toggleProps('data3d'); page.tsx contains data3dVisible={layerVisibility.data3d}; EvChargingLiveLayer.tsx defines EV_CHARGING_COLUMNS_LAYER_ID as 'ev-charging-columns-3d'; in MapView.tsx the text between 'interactiveLayerIds={[' and the next ']}' contains EV_CHARGING_COLUMNS_LAYER_ID, and the text of the onClick handler (from 'onClick={(e) =>' to 'setPopupInfo({') contains it as well; git diff --quiet on frontend/package.json and frontend/package-lock.json succeeds.
stage 2 (extended in Task 2): AIR_QUALITY_CELLS_LAYER_ID = 'air-quality-cells-3d', PARKING_COLUMNS_LAYER_ID = 'parking-columns-3d', HEAT_DEMAND_COLUMNS_LAYER_ID = 'heat-demand-columns-3d' are defined in their layer files; parking and heat ids are inside the interactiveLayerIds region and inside the onClick region; the air id is inside the onClick region but NOT inside the interactiveLayerIds region; map-styles.ts exports EAQI_BREAKPOINTS and eaqiColorExpression.
stage 3 (extended in Task 3): TrafficFlowLayer.tsx defines TRAFFIC_FLOW_GLOW_LAYER_ID = 'traffic-flow-glow' and TRAFFIC_FLOW_DASH_LAYER_ID = 'traffic-flow-dash'; both are inside the interactiveLayerIds region; the onClick region maps the 'traffic-flow' prefix to 'trafficFlow' before the generic 'traffic' prefix branch; TrafficFlowLayer.tsx contains prefers-reduced-motion, visibilitychange, requestAnimationFrame and cancelAnimationFrame; LegendOverlay.tsx contains 'Höhe'.
Write all three stages now (stage 2 and 3 fail until their tasks are done; that is expected).

Commit (explicit paths: the 8 files of this task): feat(quick-261116-eoz): 3D-Daten switch with extruded EV charging columns, plus the trailer.
  </action>
  <verify>
    <automated>S=/private/tmp/claude-501/-Users-hannessuhr-Library-Application-Support-Claude-scratch-workspaces-917fe486-0d98-4ede-ac88-e647c09dcb55-4c52147a-b177-4f3c-8801-8ef7ea1c9bce-scratch-2026-11-15-7357de/2d37f251-3d2e-41ee-ae9f-b74e9b5a9365/scratchpad; node --experimental-strip-types "$S/eoz-extrude-check.mts" frontend/lib/extrude.ts && node "$S/eoz-static-check.mjs" 1 && (cd frontend && npx tsc --noEmit)</automated>
  </verify>
  <done>Geometry check prints PASS for (a)-(f) and PASS or SKIP for (g); static check stage 1 passes; tsc reports 0 errors; with data3d on (default URL) and EV switched on, the EV stations are 6-sided columns with status colours and open EvChargingPopup at the column centre; with data3d off the EV layer and the purple infrastructure EV clusters draw exactly as before; commit created with the 8 files only.</done>
</task>

<task type="auto">
  <name>Task 2: Air-quality grid cells (EAQI per pollutant), parking columns with spread approximate garages, heat-demand columns</name>
  <files>frontend/lib/map-styles.ts, frontend/components/map/AirQualityHeatmapLayer.tsx, frontend/components/map/ParkingLayer.tsx, frontend/components/map/HeatDemandLayer.tsx, frontend/components/map/MapView.tsx</files>
  <read_first>frontend/components/map/AirQualityHeatmapLayer.tsx, frontend/components/map/ParkingLayer.tsx, frontend/components/map/HeatDemandLayer.tsx, frontend/lib/map-styles.ts (lines 35-56), frontend/lib/extrude.ts, frontend/components/map/ColumnLayer.tsx</read_first>
  <action>
map-styles.ts: next to AQI_TIER_COLORS add EAQI_TIER_ORDER (good, fair, moderate, poor, very_poor, extremely_poor) and EAQI_BREAKPOINTS keyed by 'pm25' | 'pm10' | 'no2' | 'o3' holding the five upper bounds of good..very_poor exactly as listed in the context (mirrors backend/app/schemas/geojson.py EAQI_BREAKPOINTS, EEA EAQI via airindex.eea.europa.eu; say so in a comment, and note that backend bands are inclusive upper bounds while a MapLibre step switches at the bound, a difference only at exact equality). Add eaqiColorExpression(pollutant): when the pollutant property is a number, a step expression over EAQI_BREAKPOINTS[pollutant] yielding AQI_TIER_COLORS of the six tiers in order; otherwise AQI_TIER_COLORS.unknown. Do not touch AQI_COLOR_RAMP or the WHO thresholds in the heatmap file.

AirQualityHeatmapLayer.tsx (design items 4 air, 7): new optional props extruded and beforeId; export AIR_QUALITY_CELLS_LAYER_ID = 'air-quality-cells-3d'. Named constants: AIR_CELL_INSET = 0.92, AIR_CELL_BASE_M = 20, AIR_CELL_MODERATE_TOP_M = 500, AIR_CELL_MAX_M = 1500, AIR_CELL_OPACITY = 0.6. airCellHeight(pollutant, value): value missing, non-finite or negative gives AIR_CELL_BASE_M; otherwise min(AIR_CELL_MAX_M, AIR_CELL_BASE_M + value x (AIR_CELL_MODERATE_TOP_M - AIR_CELL_BASE_M) / EAQI_BREAKPOINTS[pollutant][2]), so the top of the moderate band (pm25 25, pm10 50, no2 50, o3 130 ug/m3) is 500 m. Cells memoised on [extruded, data] only (never on activePollutant), built only while extruded: gridSpacing over the Point features (null spacing renders no cells), columnsFromPoints with the footprint function cellFromPoint(lng, lat, dLng x AIR_CELL_INSET, dLat x AIR_CELL_INSET), height = airCellHeight('pm25', pm25) and extra properties height_pm25, height_pm10, height_no2, height_o3 from airCellHeight per pollutant. The colour expression is memoised on activePollutant (eaqiColorExpression). Render the existing heatmap Source with visibility visible && !extruded, and a ColumnLayer (id AIR_QUALITY_CELLS_LAYER_ID, heightProperty 'height_' + activePollutant, the colour expression, opacity AIR_CELL_OPACITY, beforeId, visible = visible && extruded). Switching the pollutant then changes only paint properties. The sensor AQILayer stays untouched.

ParkingLayer.tsx (design item 4 parking): new optional props extruded and beforeId; export PARKING_COLUMNS_LAYER_ID = 'parking-columns-3d'. Constants PARKING_COLUMN_RADIUS_M = 30, PARKING_COLUMN_SIDES = 16, PARKING_MIN_SEPARATION_M = 75 (two radii plus a 15 m gap), PARKING_COLUMN_BASE_M = 20, PARKING_COLUMN_M_PER_SPOT = 2, PARKING_COLUMN_MAX_M = 300. Memoise the category-filtered collection on data, and only while extruded the columns: spreadApproximate with flagProperty 'location_approximate', minSeparationMeters PARKING_MIN_SEPARATION_M and sortKey garage_code + '|' + name (stable across polls, P1 occurs twice), then columnsFromPoints with 16 sides, radius 30, height min(MAX, BASE + PER_SPOT x free_spots) and BASE when free_spots is not a finite non-negative number. Colour: occupancy_pct is a number -> the same green/yellow/red step as the flat circles; else is_open equals false -> '#9ca3af'; else '#3b82f6'. Opacity 0.85. Keep the free-spot number visible in 3D: pass a child Layer with id 'parking-labels-3d' that reuses the flat label layer's layout and paint (MapLibre places a symbol on a polygon at its interior point, i.e. the column base). When extruded render the ColumnLayer (with that child) instead of the flat circle + label layers; otherwise exactly today's flat layers.

HeatDemandLayer.tsx (design item 4 heat): new optional props extruded and beforeId; export HEAT_DEMAND_COLUMNS_LAYER_ID = 'heat-demand-columns-3d'. Move the heat_class match expression into a module constant shared by the flat circles and the columns. Constants HEAT_COLUMN_MIN_RADIUS_M = 8, HEAT_COLUMN_MAX_RADIUS_M = 25, HEAT_COLUMN_M_PER_KWH = 0.6, HEAT_COLUMN_MIN_M = 5, HEAT_COLUMN_MAX_M = 400. Memoise the filtered collection on data and, only while extruded, the columns: 4 sides rotated 45 deg (axis-aligned square), radius = clamp(sqrt(area_m2 / 2), 8, 25) (a square of the building's floor area; missing area gives 8), height = clamp(0.6 x heat_demand_kwh_m2_y, 5, 400); opacity 0.85. When extruded render the ColumnLayer instead of the circles; otherwise exactly today's layer.

MapView.tsx (design item 5): pass extruded={data3dVisible} and beforeId={labelBeforeId} to AirQualityHeatmapLayer, ParkingLayer and HeatDemandLayer. Add PARKING_COLUMNS_LAYER_ID and HEAT_DEMAND_COLUMNS_LAYER_ID to interactiveLayerIds and map them to 'parking' and 'heatDemand' in the chain. Air-cell click decision: the existing air-quality popup does not fit grid cells (it is a sensor popup: title 'Luftqualitätssensor', 'Kein aktueller Messwert' because cells carry no aqi, unrounded concentrations, badge 'unknown', sensor-chart lookup without a feature_id), so a cell click opens nothing. Implement it by leaving AIR_QUALITY_CELLS_LAYER_ID out of interactiveLayerIds and removing features of that layer from the candidates in both the interactive results and the 10 px fallback results before the pick step from Task 1, so clicks fall through to columns, buildings or other features beneath; if nothing remains, return without a popup. Put the explanatory comment next to that filter, not inside the interactiveLayerIds array.

Commit (explicit paths: the 5 files): feat(quick-261116-eoz): air-quality cells, parking and heat-demand columns in 3D mode, plus the trailer.
  </action>
  <verify>
    <automated>S=/private/tmp/claude-501/-Users-hannessuhr-Library-Application-Support-Claude-scratch-workspaces-917fe486-0d98-4ede-ac88-e647c09dcb55-4c52147a-b177-4f3c-8801-8ef7ea1c9bce-scratch-2026-11-15-7357de/2d37f251-3d2e-41ee-ae9f-b74e9b5a9365/scratchpad; node "$S/eoz-static-check.mjs" 2 && (cd frontend && npx tsc --noEmit)</automated>
  </verify>
  <done>Static check stage 2 passes; tsc 0 errors; air cells memo has no activePollutant dependency (geometry stable across pollutant switches) while height property and colour follow the pollutant; the four approximate garages get distinct ring positions; flat forms render only when extruded is false; commit created with the 5 files only.</done>
</task>

<task type="auto">
  <name>Task 3: Traffic glow and moving dash, legend lines, full verification and PENDING browser list</name>
  <files>frontend/components/map/TrafficFlowLayer.tsx, frontend/components/map/LegendOverlay.tsx, frontend/components/map/MapView.tsx</files>
  <read_first>frontend/components/map/TrafficFlowLayer.tsx, frontend/components/map/LegendOverlay.tsx, frontend/components/map/BusPositionLayer.tsx (lines 405-475, the useMap plus requestAnimationFrame pattern)</read_first>
  <action>
TrafficFlowLayer.tsx (design item 4 traffic): new optional prop extruded. Export TRAFFIC_FLOW_GLOW_LAYER_ID = 'traffic-flow-glow' and TRAFFIC_FLOW_DASH_LAYER_ID = 'traffic-flow-dash'. Move the congestion colour interpolation into a module constant shared by the line and the glow. Memoise the TomTom-filtered collection on data (today a new object every render re-sends the source data on each MapView re-render). Inside the existing Source, keep the existing line layer first and unchanged; when extruded add, after it in JSX order (so the line exists when they are created), a glow line layer with beforeId 'traffic-flow-lines' (beneath the line), same colour constant, line-width by zoom 10 -> 12, 14 -> 24, 18 -> 36, line-blur 10 -> 6, 14 -> 12, 18 -> 18, opacity 0.35, round cap/join; and a dash line layer on top (no beforeId): colour '#ffffff', opacity 0.85, line-width 10 -> 1.5, 14 -> 3, 18 -> 4.5, butt cap, round join, line-dasharray starting at the first step of ANT_PATH_SEQUENCE, and line-dasharray-transition duration 0 if the paint type accepts it. All paint/layout objects are module constants so react-map-gl never re-applies the dasharray. ANT_PATH_SEQUENCE is MapLibre's ant-path example sequence of 14 steps: for s = 0, 0.5, ..., 3 the array [s, 4, 3 - s], then for s = 0.5, 1, ..., 3.5 the array [0, s, 3, 4 - s]. Animation: a useEffect using useMap() (as BusPositionLayer does) that runs only while extruded is true and the component is mounted (MapView mounts it only while the traffic-flow switch is on). It drives a requestAnimationFrame loop that advances the step at most every DASH_STEP_MS = 80 (about 12 updates per second) and calls map.setPaintProperty(TRAFFIC_FLOW_DASH_LAYER_ID, 'line-dasharray', ANT_PATH_SEQUENCE[step]) only when map.getLayer(TRAFFIC_FLOW_DASH_LAYER_ID) exists. Never put the step in React state (that would re-render and re-send the source every frame). The loop does not run while window.matchMedia('(prefers-reduced-motion: reduce)') matches (listen to its change event to start/stop) or while document.hidden is true (listen to visibilitychange to stop/restart). Cleanup cancels the frame and removes both listeners. Dash speed is constant in this slice; direction follows the LineString coordinate order.

LegendOverlay.tsx (design item 6): new optional props data3dLayers ({ airQuality, evCharging, parking, heatDemand, trafficFlow } booleans) and activePollutant (Pollutant type from AirQualityHeatmapLayer). Inside the open legend panel, after the existing legends, when any flag is true render a compact block: a small heading '3D-Daten' and one text-[12px] line per true flag: air 'Luft: Höhe = <label>-Konzentration, Farbe = EAQI-Stufe' with label PM2.5 / PM10 / NO₂ / O₃ for the active pollutant; 'E-Laden: Höhe = Ladeleistung (kW)'; 'Parken: Höhe = freie Plätze'; 'Wärme: Höhe = Wärmebedarf (kWh/m²·a)'; 'Verkehr: Lauflicht = Fahrtrichtung'. No other legend change.

MapView.tsx: pass extruded={data3dVisible} to TrafficFlowLayer. Add TRAFFIC_FLOW_GLOW_LAYER_ID and TRAFFIC_FLOW_DASH_LAYER_ID to interactiveLayerIds. In the layer-id chain replace the equality check against 'traffic-flow-lines' with a 'traffic-flow' prefix check that maps to 'trafficFlow' and stays before the generic 'traffic' prefix branch (otherwise glow/dash clicks would open the BASt TrafficPopup). Pass LegendOverlay data3dLayers = { airQuality: data3dVisible && layerVisibility.airQuality, evCharging: data3dVisible && evChargingVisible, parking: data3dVisible && parkingVisible, heatDemand: data3dVisible && heatDemandVisible, trafficFlow: data3dVisible && trafficFlowVisible } and activePollutant.

Full verification (all from the repo root): the geometry check and static check stage 3; cd frontend and npx tsc --noEmit (0 errors); cd frontend and npm run lint, compare the summary line with eoz-lint-baseline.txt (errors and warnings each not higher); npx eslint on the 12 pre-existing touched files plus extrude.ts and ColumnLayer.tsx, compare with eoz-eslint-touched-baseline.txt (no new problem; the two new files clean); cd frontend and npm run build passes; git diff --quiet on frontend/package.json and frontend/package-lock.json; git status shows no staged or committed file outside files_modified.

Commit (explicit paths: the 3 files): feat(quick-261116-eoz): traffic flow glow and moving dash, 3D legend lines, plus the trailer.

SUMMARY must contain: the lint/eslint before-after numbers, which Node runner executed the geometry check, the air-cell click decision (no popup, clicks fall through) and why, the named tuning constants per layer (for the orchestrator's visual pass), and this list verbatim under the heading 'PENDING - orchestrator (browser)':
1. data3d on (default URL): air-quality cells stand on the terrain (not below it, not floating; note any edge float/sink on slopes), cover the town bbox with small even gaps, opacity lets the city show through.
2. Switching the pollutant (PM2.5 / PM10 / NO2 / O3) changes cell heights and colours with no visible rebuild pause.
3. EV, parking and heat columns stand at their locations, colours match the flat layers, and clicking each opens its usual popup at the column.
4. The four approximate parking garages (P1 Kubus, P1 Rathaus, P6 Bahnhof, P3 Spritzenhausplatz) stand separately on a ring; free-spot numbers visible.
5. Traffic-flow lines glow and the white dash moves along them; it stops with reduced motion enabled and resumes after a hidden tab returns.
6. Clicking an air cell opens nothing; clicking a building or column inside the air field still opens its popup.
7. Switching data3d off restores today's flat layers exactly (air heatmap, EV status circles plus purple infrastructure clusters, parking circles plus labels, heat circles, plain traffic lines).
8. Legend panel shows the 3D lines for the layers that are on, with the active pollutant name.
9. No new console errors (in particular no 'Cannot add layer before non-existing layer').
  </action>
  <verify>
    <automated>S=/private/tmp/claude-501/-Users-hannessuhr-Library-Application-Support-Claude-scratch-workspaces-917fe486-0d98-4ede-ac88-e647c09dcb55-4c52147a-b177-4f3c-8801-8ef7ea1c9bce-scratch-2026-11-15-7357de/2d37f251-3d2e-41ee-ae9f-b74e9b5a9365/scratchpad; node --experimental-strip-types "$S/eoz-extrude-check.mts" frontend/lib/extrude.ts && node "$S/eoz-static-check.mjs" 3 && (cd frontend && npx tsc --noEmit && npm run build) && git diff --quiet -- frontend/package.json frontend/package-lock.json</automated>
  </verify>
  <done>Static check stage 3 and geometry check pass; tsc 0 errors; lint not worse than baseline and nothing new in touched files; build passes; package files unchanged; three feat commits exist on feat/3d-data-layers containing only files_modified; SUMMARY lists constants, decisions and the PENDING browser list.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| backend API -> browser | Public open-data feature properties (power_kw, free_spots, area_m2, concentrations, names) become geometry, paint values and popup text |
| browser main thread | A permanent animation loop and 1,400-polygon sources run on citizen devices |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-261116-eoz-01 | Tampering | extrude.ts columnsFromPoints / layer height functions | low | mitigate | non-Point features and non-finite coordinates or heights are skipped; every height has a named cap (EV 600 m, parking 300 m, heat 400 m, air 1500 m) and radii are clamped, so a malformed or extreme upstream value cannot produce giant or invalid geometry; checked by the scratch geometry script (f) |
| T-261116-eoz-02 | Denial of Service | TrafficFlowLayer dash animation | low | mitigate | updates throttled to DASH_STEP_MS 80; loop stops on unmount, 3D off, hidden tab and prefers-reduced-motion; animation uses setPaintProperty only, never React state, so no re-render or source re-upload per frame |
| T-261116-eoz-03 | Denial of Service | Column GeoJSON building | low | mitigate | column collections are memoised on the fetched data; the 1,400 air cells are not rebuilt on pollutant switches (memo excludes activePollutant) and are only built while 3D mode is on |
| T-261116-eoz-04 | Information Disclosure | Popups and legend | low | accept | data is public open data already shown by the flat layers; popups render through existing React components (text is escaped); legend text is static |
| T-261116-eoz-SC | Tampering | npm installs | high | mitigate | no package is installed or added; git diff --quiet on frontend/package.json and frontend/package-lock.json is part of the Task 1 static check and the Task 3 verify |
</threat_model>

<verification>
- Geometry: SCRATCH/eoz-extrude-check.mts passes (closed rings, sides + 1 positions, every vertex within 1 % of the radius by haversine at lat 48.84, counter-clockwise; grid cells tile with exactly the inset gap and no overlap; approximate garages at least 75 m apart and stable under input shuffling).
- Static: SCRATCH/eoz-static-check.mjs stage 3 passes (data3d in the registry and the default layers value; every new extrusion and traffic layer id in interactiveLayerIds and the onClick mapping; air-cell id excluded from interactiveLayerIds and filtered in onClick; package files unchanged).
- cd frontend && npx tsc --noEmit: 0 errors. npm run lint: not worse than the recorded baseline; eslint on touched files: nothing new. npm run build: passes.
- Commits: three feat(quick-261116-eoz) commits with the Fable 5.2 trailer, staged by explicit path, nothing pushed, no unrelated .planning/ or docs/ files.
- PENDING - orchestrator (browser): the nine-item list in Task 3 is copied into the SUMMARY.
</verification>

<success_criteria>
- A '3D-Daten' switch exists in the 3D group, on by default, independent of the master switch.
- With it on, air quality, EV charging, parking and heat demand stand as data-driven extrusions on the terrain and traffic flow glows with a moving dash; with it off, everything draws as on d17e3ba.
- Every clickable 3D layer opens the same popup as its flat form; air cells are deliberately non-clickable and do not block clicks beneath.
- No dependency, backend or test-runner change; tsc, lint (not worse) and build are green.
</success_criteria>

<output>
Create `.planning/quick/261116-eoz-3d-data-layers-air-quality-ev-charging-p/261116-eoz-SUMMARY.md` when done
</output>
