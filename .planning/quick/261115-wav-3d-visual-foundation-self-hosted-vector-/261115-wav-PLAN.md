---
phase: quick-261115-wav
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/lib/map-styles.ts
  - frontend/hooks/useUrlState.ts
  - frontend/app/page.tsx
  - frontend/components/sidebar/Sidebar.tsx
  - frontend/components/map/MapView.tsx
  - frontend/components/map/applyOnStyleLoad.ts
  - frontend/components/map/BuildingsLayer.tsx
  - frontend/components/map/GeospatialOverlayLayer.tsx
  - frontend/lib/sun.ts
  - frontend/lib/atmosphere.ts
  - frontend/components/map/MapAtmosphere.tsx
  - frontend/components/map/WeatherSkybox.tsx
autonomous: true
requirements:
  - quick-261115-wav

estimate:
  tokens: 130000
  raw_tokens: 130000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "Opening the app without a base param renders the dark Protomaps vector basemap from /tiles/aalen.pmtiles; the sidebar radio group offers Dunkel, Hell, Luftbild (LGL), Satellit (Sentinel-2); a legacy URL with base=osm opens Hell; no request goes to the OSM raster tile host"
    - "3D terrain from open DEM tiles is on by default (layers default transit,aqi,buildings3d,terrain3d), can be switched off with the 3D-Gelaende toggle, and survives a base map switch"
    - "3D buildings are opaque, coloured by height with a per-base palette, vertically shaded, sit beneath the place/street labels, and appear on all four base maps (including Luftbild and Satellit)"
    - "The Gelaenderelief (DGM) toggle shows a subtle MapLibre hillshade drawn from the open DEM instead of the failing LGL WMS; the Kataster (ALKIS) WMS overlay is unchanged"
    - "A sky is drawn above the horizon and the building light follows the sun position for the current time (or the time-slider timestamp) and the current weather; night, twilight, overcast and rain look different"
    - "Camera allows pitch up to 80, starts at pitch 60 / bearing -20; flyTo, popups (including buildings-3d -> UnifiedBuildingPopup) and all existing data layers keep working"
  artifacts:
    - path: "frontend/lib/map-styles.ts"
      provides: "Four base styles, each with protomaps + terrain-dem + hillshade-dem sources, baked hidden hillshade layer, default sky/light; palettes and ids"
      exports: ["BaseLayer", "BASE_LAYERS", "DEFAULT_BASE_LAYER", "parseBaseLayer", "getMapStyle", "firstSymbolLayerId", "PROTOMAPS_SOURCE_ID", "TERRAIN_SOURCE_ID", "HILLSHADE_SOURCE_ID", "HILLSHADE_LAYER_ID", "TERRAIN_EXAGGERATION", "BUILDING_PALETTES", "HILLSHADE_PAINT", "AQI_COLOR_RAMP", "AQI_TIER_COLORS", "TRANSIT_COLORS"]
    - path: "frontend/lib/sun.ts"
      provides: "Pure solar position approximation"
      exports: ["sunPosition"]
    - path: "frontend/lib/atmosphere.ts"
      provides: "Pure weather/sun -> MapLibre sky and light presets"
      exports: ["weatherCategory", "skyFor", "lightFor"]
    - path: "frontend/components/map/applyOnStyleLoad.ts"
      provides: "Apply-now-and-after-every-style.load helper for imperative style state"
      exports: ["applyOnStyleLoad"]
    - path: "frontend/components/map/MapAtmosphere.tsx"
      provides: "Replaces WeatherSkybox; calls map.setSky/map.setLight"
    - path: "frontend/components/map/BuildingsLayer.tsx"
      provides: "buildings-3d fill-extrusion with palette, gradient, beforeId"
    - path: "frontend/components/map/GeospatialOverlayLayer.tsx"
      provides: "Cadastral WMS + hillshade visibility + terrain on/off"
  key_links:
    - from: "frontend/components/map/MapView.tsx"
      to: "frontend/lib/map-styles.ts"
      via: "module-scope MAP_STYLES singletons built with getMapStyle for every BaseLayer"
      pattern: "getMapStyle\\("
    - from: "frontend/hooks/useUrlState.ts"
      to: "frontend/lib/map-styles.ts"
      via: "parseBaseLayer maps the base URL param (legacy osm -> light, unknown/missing -> dark)"
      pattern: "parseBaseLayer\\("
    - from: "frontend/components/map/BuildingsLayer.tsx"
      to: "frontend/lib/map-styles.ts"
      via: "beforeId = firstSymbolLayerId(mapStyle) passed from MapView; palette = BUILDING_PALETTES[baseLayer]"
      pattern: "beforeId"
    - from: "frontend/components/map/GeospatialOverlayLayer.tsx"
      to: "terrain-dem / hillshade-relief in every style"
      via: "applyOnStyleLoad -> map.setTerrain / map.setLayoutProperty(HILLSHADE_LAYER_ID)"
      pattern: "setTerrain"
    - from: "frontend/components/map/MapAtmosphere.tsx"
      to: "frontend/lib/atmosphere.ts + frontend/lib/sun.ts"
      via: "sunPosition(time, center) -> skyFor/lightFor -> applyOnStyleLoad -> map.setSky/map.setLight"
      pattern: "setSky\\("
---

<objective>
Slice 1 of "a really cool 3D version of the city": the visual foundation. Replace the flat OSM raster picture with a self-hosted Protomaps vector basemap (dark default + light) from the local PMTiles, real 3D terrain and an optional hillshade from open DEM tiles, a working sky and sun-driven lighting (the old fog code never drew anything), and opaque, shaded 3D buildings that sit beneath labels on every base style.

Purpose: Make the map look like a 3D city instead of a flat image, without adding dependencies and without touching any data layer.
Output: Rewritten frontend/lib/map-styles.ts, new frontend/lib/sun.ts, frontend/lib/atmosphere.ts, frontend/components/map/applyOnStyleLoad.ts, frontend/components/map/MapAtmosphere.tsx; updated BuildingsLayer, GeospatialOverlayLayer, MapView, Sidebar, page.tsx, useUrlState; WeatherSkybox deleted. Three atomic commits on branch feat/3d-visual-foundation (not pushed).

Settled design from the orchestrator (implement exactly; no D-NN ids exist for quick tasks, so the numbered design items are cited as DESIGN-1..DESIGN-6):
- DESIGN-1 vector basemap, DEM sources, sky/light defaults, helper exports, attributions (Task 1)
- DESIGN-2 terrain (terrain3d key, default ON, label 3D-Gelaende) and hillshade from hillshade-dem (Tasks 1 + 2)
- DESIGN-3 sky and sun light replacing the dead fog code (Task 3)
- DESIGN-4 3D buildings palette/opacity/gradient/beforeId, label 3D-Gebaeude (Tasks 1 + 2)
- DESIGN-5 camera maxPitch 80, pitch 60, bearing -20, NavigationControl visualizePitch (Task 1)
- DESIGN-6 sidebar radio group + 3D-Gelaende toggle + URL state (Task 1)

Out of scope (do NOT do): restyling or refetching any data layer, deck.gl, LoD2 models, self-hosting glyphs/sprites/DEM (leave a follow-up comment only), backend changes, fixing the 11 pre-existing lint errors, a layer registry, "all on/off", an app-wide dark theme or sidebar/dashboard restyling, adding any npm dependency.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@frontend/AGENTS.md
@frontend/lib/map-styles.ts
@frontend/components/map/MapView.tsx
@frontend/components/map/BuildingsLayer.tsx
@frontend/components/map/WeatherSkybox.tsx
@frontend/components/map/GeospatialOverlayLayer.tsx
@frontend/hooks/useUrlState.ts

Facts verified at planning time (2026-11-15, HEAD 70576b3 on feat/3d-visual-foundation):

- Installed: maplibre-gl 6.18.0 (ships its own types and re-exports every style-spec type, e.g. SkySpecification, LightSpecification, TerrainSpecification, HillshadeLayerSpecification, FillExtrusionLayerSpecification, ExpressionSpecification, via `export type *` from @maplibre/maplibre-gl-style-spec 26.8.0), react-map-gl 8.1.3 (@vis.gl/react-maplibre), @protomaps/basemaps 5.7.2, next 16.4.6, react 19.2.4. The devDependency @types/maplibre-gl 1.x is NOT what TypeScript resolves (maplibre-gl's own `types` field wins). Do not add or change dependencies.
- `layers('protomaps', namedFlavor('dark' | 'light'), {lang: 'de'})` returns 71 layers in this order: background, earth, landcover, landuse_* fills, then the first road layer `roads_runway` (index 11), ..., water, ..., the flat `buildings` fill, roads, boundaries, bridges, then 14 symbol layers starting with `address_label` (then water_waterway_label, roads_oneway, roads_labels_minor, ..., pois, places_*). The symbol layer ids are identical for both flavors, so the first label layer id is `address_label` in every style built by this plan.
- @protomaps/basemaps types its return as LayerSpecification[] from the same @maplibre/maplibre-gl-style-spec that maplibre-gl uses, so it is assignable to StyleSpecification['layers'] without casts.
- react-map-gl `<Layer beforeId>`: on create calls `map.addLayer(spec, beforeId)` (the beforeId must exist in the current style); when the beforeId prop changes it calls `map.moveLayer`. react-maplibre applies `setProps`/`setStyle` in a layout effect AFTER children render, so a beforeId that exists only in the next style would raise a MapLibre error. That is why the hillshade layer is baked into each style (position per style) and only its visibility is toggled at runtime, while 3D buildings use `address_label` (present in all four styles).
- react-map-gl switches base styles with `setStyle(style, {diff: true})`. In MapLibre 6.18 both a successful diff (Style.setState) and a full reload fire `style.load`, and a diff resets sky/light/terrain/visibility to what the new style says. Anything applied imperatively must therefore be re-applied on every `style.load`.
- `map.isStyleLoaded()` returns false while ANY source tiles are still loading (Style.loaded checks tile managers), so it must not be used as the "can I call setSky/setTerrain now" check. `map.style._loaded` (typed `_loaded: boolean` on the public Style class) is the flag react-map-gl itself uses.
- react-map-gl's public `<Map terrain>` prop is typed `TerrainSpecification` (no null) and at runtime ignores `undefined`; only `null` removes terrain. Using it for an on/off switch would need a cast, so terrain is switched imperatively with `map.setTerrain(spec | null)` (MapLibre signature `setTerrain(options: TerrainSpecification | null)`).
- MapLibre 6 Map has `setSky(sky: SkySpecification)`, `setLight(light: LightSpecification)`, `setTerrain(...)`, `getTerrain()`, `setLayoutProperty`. There is no fog API in MapLibre; the current WeatherSkybox never drew anything.
- Grep gates at HEAD (each FAILS today, so each is a real gate): `git grep --untracked -n "tile.openstreetmap.org" -- frontend` = 1 match (lib/map-styles.ts:48); `git grep --untracked -n "setFog" -- frontend` = 4 matches (WeatherSkybox.tsx); `git grep --untracked -n "WMS_LGL-BW_ATKIS_DGM" -- frontend` = 1 match (GeospatialOverlayLayer.tsx:24). frontend/lib/map-styles.ts currently contains zero occurrences of `any`.
- Lint baseline: whole project `npm --prefix frontend run lint` ends with `24 problems (11 errors, 13 warnings)`. For the in-scope files (lib/map-styles.ts, components/map/MapView.tsx, BuildingsLayer.tsx, WeatherSkybox.tsx, GeospatialOverlayLayer.tsx, components/sidebar/Sidebar.tsx, app/page.tsx, hooks/useUrlState.ts) there are 3 errors / 3 warnings, all pre-existing: MapView "Cannot access variable before it is declared" (setPopupInfo used in an effect above its useState), MapView no-explicit-any on the queryRenderedFeatures fallback cast, WeatherSkybox no-explicit-any (goes away with the deletion); warnings: page.tsx unused useMemo, MapView unused _mobiDataVisible, MapView exhaustive-deps (popupInfo). Leave those as they are. The eslint config includes the React-Compiler-based react-hooks rules (e.g. set-state-in-effect, purity, refs) — new code must satisfy them without disable comments.
- Tooling: no test runner in frontend (do not add one). `frontend/node_modules/.bin/jiti` (2.6.1) runs TypeScript files directly and resolves packages relative to the imported file. The verification script below was written and validated at planning time (it passes against a throwaway prototype of the specified API and fails against HEAD).

CHECK SCRIPT (outside the repo, pre-written, not to be committed):
/private/tmp/claude-501/-Users-hannessuhr-Library-Application-Support-Claude-scratch-workspaces-917fe486-0d98-4ede-ac88-e647c09dcb55-4c52147a-b177-4f3c-8801-8ef7ea1c9bce-scratch-2026-11-15-7357de/2d37f251-3d2e-41ee-ae9f-b74e9b5a9365/scratchpad/check-3d-foundation.ts
Run it from the repo root as `frontend/node_modules/.bin/jiti "<CHECK SCRIPT>" styles|atmosphere|all`. It imports frontend/lib/map-styles.ts, frontend/lib/sun.ts and frontend/lib/atmosphere.ts directly by path, so those three files must NOT use the `@/` alias (use relative imports between lib files if needed) and must not import maplibre-gl/react at runtime (type-only imports are fine). Read the script once before Task 1 — its assertions are the exact contract for the exported names, values and layer order. Baseline at HEAD: `styles` fails with "m.BASE_LAYERS is not iterable"; `atmosphere` fails because lib/sun.ts does not exist. If the file is missing, stop and report it (do not invent a weaker check).

Note for frontend/AGENTS.md: this task introduces no Next.js-specific API (page.tsx changes are plain React state wiring in an existing 'use client' file). If you find you need a Next API, read the matching guide in frontend/node_modules/next/dist/docs/ first.
</context>

<tasks>

<task type="tracer">
  <name>Task 1 (tracer): Dark/light Protomaps vector basemap with DEM sources, wired URL -> sidebar -> MapView, plus 3D camera and the terrain3d URL key</name>
  <files>frontend/lib/map-styles.ts, frontend/hooks/useUrlState.ts, frontend/app/page.tsx, frontend/components/sidebar/Sidebar.tsx, frontend/components/map/MapView.tsx</files>
  <precondition>The CHECK SCRIPT file exists (test -f on the absolute path in the context block) and `frontend/node_modules/.bin/jiti` exists.</precondition>
  <read_first>
    - The CHECK SCRIPT (absolute path in the context block) — exact contract for the `styles` section
    - frontend/lib/map-styles.ts, frontend/hooks/useUrlState.ts, frontend/components/map/MapView.tsx (full)
    - frontend/app/page.tsx lines 25-110 and 225-325 (layerVisibility, LAYER_KEYS, handleBaseLayerChange, Sidebar/MapView props)
    - frontend/components/sidebar/Sidebar.tsx lines 25-80 (props) and 470-510 (Geospatial group)
    - frontend/node_modules/@protomaps/basemaps/dist/esm/index.d.ts (layers / namedFlavor signatures)
  </read_first>
  <action>
Thinnest end-to-end path first: the user picks a base map (URL or sidebar) and MapView renders the matching vector/raster style, and every style already carries the protomaps vector source and both DEM sources. Implements DESIGN-1, DESIGN-5, DESIGN-6 and the data/URL half of DESIGN-2 and DESIGN-4.

1. Rewrite frontend/lib/map-styles.ts (DESIGN-1). Runtime import only `layers` and `namedFlavor` from @protomaps/basemaps (replacing the commented-out import); everything from maplibre-gl is one single-line `import type { ... } from 'maplibre-gl'` statement (the purity gate in Task 3 greps line-wise, so do not wrap that import across lines and do not use the inline `import { type X }` form). No `@/` imports, no untyped casts. Keep AQI_COLOR_RAMP, AQI_TIER_COLORS and TRANSIT_COLORS byte-for-byte unchanged (FeaturePopup, TransitLegend and the heatmap import them). Export:
   - `BASE_LAYERS` as a readonly tuple `['dark', 'light', 'orthophoto', 'satellite'] as const`, `type BaseLayer` derived from it, `DEFAULT_BASE_LAYER: BaseLayer = 'dark'`.
   - `parseBaseLayer(raw: string | null | undefined): BaseLayer` — returns raw when it is one of BASE_LAYERS, maps the legacy value 'osm' to 'light', and returns DEFAULT_BASE_LAYER for null/undefined/empty/unknown.
   - Source/layer id constants: `PROTOMAPS_SOURCE_ID = 'protomaps'`, `TERRAIN_SOURCE_ID = 'terrain-dem'`, `HILLSHADE_SOURCE_ID = 'hillshade-dem'`, `HILLSHADE_LAYER_ID = 'hillshade-relief'`, and `TERRAIN_EXAGGERATION = 1.3`.
   - Shared sources present in EVERY style: `protomaps` = vector source with `url` = the pmtilesUrl argument and attribution `<a href="https://protomaps.com">Protomaps</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>` (drop the stale attribution text of the old source); `terrain-dem` and `hillshade-dem` = two SEPARATE raster-dem sources (MapLibre recommends separate sources for terrain and hillshade) with identical settings: tiles `['https://elevation-tiles-prod.s3.amazonaws.com/terrarium/{z}/{x}/{y}.png']`, encoding 'terrarium', tileSize 256, maxzoom 15, attribution `Terrain: <a href="https://github.com/tilezen/joerd/blob/master/docs/attribution.md">Mapzen / AWS Terrain Tiles</a>` (same string on both; MapLibre de-duplicates identical attributions). Build fresh source objects per style (no shared mutable object between styles).
   - Remove the OSM raster source and the `osm-tiles` layer entirely; no URL of the OSM raster tile host may remain anywhere in the frontend.
   - Every style gets top-level `sky` and `light` defaults (clear day: e.g. sky-color '#5a8fd8', horizon-color '#cfe3f5', fog-color '#dfe9f3', sky-horizon-blend 0.5, horizon-fog-blend 0.6, fog-ground-blend 0.5; light anchor 'map', position [1.5, 210, 40], color '#ffffff', intensity 0.5). These are only the fallback until MapAtmosphere (Task 3) applies the live values. Do NOT put a top-level `terrain` into any style (terrain is switched at runtime in Task 2; baking it in would fight the toggle on every style diff).
   - `HILLSHADE_PAINT: Record<BaseLayer, NonNullable<HillshadeLayerSpecification['paint']>>` — subtle, tuned per flavor; suggested: dark shadow '#05070b', highlight '#3d4a5e', accent '#141922', exaggeration 0.35; light shadow '#6b604f', highlight '#ffffff', accent '#8c826f', exaggeration 0.3; orthophoto and satellite shadow '#000000', highlight '#ffffff', accent '#000000', exaggeration 0.25 (all exaggerations must stay in (0, 0.6]).
   - Every style contains one baked layer `{id: HILLSHADE_LAYER_ID, type: 'hillshade', source: HILLSHADE_SOURCE_ID, layout: {visibility: 'none'}, paint: HILLSHADE_PAINT[base]}` — hidden by default, its visibility is toggled in Task 2. Position: in dark/light insert it directly before the first layer whose id starts with 'roads' (above the earth/landcover/landuse fills, beneath water, roads, buildings and labels); in orthophoto/satellite put it directly after the raster layer (index 1).
   - dark / light: version 8, glyphs unchanged (`https://protomaps.github.io/basemaps-assets/fonts/{fontstack}/{range}.pbf`), sprite `https://protomaps.github.io/basemaps-assets/sprites/v4/` + flavor, layers = `layers(PROTOMAPS_SOURCE_ID, namedFlavor(flavor), {lang: 'de'})` with the hillshade layer spliced in as above. Keep the flat `buildings` fill layer (it is what shows when 3D buildings are switched off).
   - orthophoto / satellite: keep the existing raster source objects (ids `orthophoto` / `satellite`, tiles URLs, tileSize, attribution strings 'LGL Baden-Wuerttemberg, dl-de/by-2-0' and 'Sentinel-2 cloudless by EOX, contains Copernicus Sentinel data' exactly as today) plus the shared sources; layers = the raster layer (`orthophoto-tiles` / `satellite-tiles`) first, then the hillshade layer, then ONLY the symbol layers of `layers(PROTOMAPS_SOURCE_ID, namedFlavor('dark'), {lang: 'de'})` filtered to type 'symbol'. Discretion choice: the dark flavor's labels (light text, dark halo) read best on aerial imagery, so these two styles use the dark sprite as well.
   - `getMapStyle(baseLayer: BaseLayer, pmtilesUrl: string): StyleSpecification` dispatches to the builders. Delete the old exported builder functions (MapView is their only consumer, confirmed by git grep at planning time).
   - `firstSymbolLayerId(style: StyleSpecification): string | undefined` — id of the first layer with type 'symbol' (pure; used as beforeId for 3D buildings).
   - `BUILDING_PALETTES: Record<BaseLayer, { stops: Array<[number, string]>; opacity: number }>` (heights in metres, ascending, at least 3 stops) — dark [[0,'#232a36'],[20,'#3b4a61'],[60,'#6f86a8']] opacity 1; light [[0,'#ece7dd'],[20,'#cfc8b8'],[60,'#a89f8d']] opacity 1; orthophoto and satellite neutral light greys e.g. [[0,'#e6e6e6'],[20,'#d2d2d2'],[60,'#bdbdbd']] opacity 0.9 (DESIGN-4 data; consumed in Task 2).
   - Add a one-line comment near the glyph/sprite/DEM URLs: follow-up — self-host glyphs, sprites and DEM tiles. Do not download any asset into the repo.

2. frontend/hooks/useUrlState.ts (DESIGN-6, DESIGN-2): type `baseLayer` as BaseLayer (import type from '@/lib/map-styles') and compute it with `parseBaseLayer(searchParams.get('base'))` (runtime import of parseBaseLayer is fine — map-styles has no maplibre/react runtime imports, so it is SSR-safe). Change the default `layers` string to 'transit,aqi,buildings3d,terrain3d'.

3. frontend/app/page.tsx (DESIGN-6): `handleBaseLayerChange(base: BaseLayer)` writes `null` when base equals DEFAULT_BASE_LAYER ('dark'), else the value. Add `terrain3d: state.layers.includes('terrain3d')` to layerVisibility and `terrain3d: 'terrain3d'` to LAYER_KEYS. Pass `terrain3dVisible={layerVisibility.terrain3d}` to both Sidebar and MapView. Nothing else in page.tsx changes (leave the pre-existing unused useMemo import alone).

4. frontend/components/sidebar/Sidebar.tsx (DESIGN-6, DESIGN-4): type `baseLayer` / `onBaseLayerChange` with BaseLayer; render the radio group from BASE_LAYERS with a local label map — dark 'Dunkel', light 'Hell', orthophoto 'Luftbild (LGL)', satellite 'Satellit (Sentinel-2)' (same markup/classes as today). Add 'terrain3d' to the onToggleLayer union and a `terrain3dVisible?: boolean` prop. In the "3D" group: rename the buildings toggle label to '3D-Gebaeude' (keep id buildings3d-toggle) and add a LayerToggle id 'terrain3d-toggle', label '3D-Gelaende', checked `terrain3dVisible ?? false`, onCheckedChange toggling 'terrain3d', placed next to it. Keep the 'Gelaenderelief (DGM)' and 'Kataster (ALKIS)' toggles. No other sidebar styling changes.

5. frontend/components/map/MapView.tsx (DESIGN-1, DESIGN-5): import getMapStyle, DEFAULT_BASE_LAYER and type BaseLayer / StyleSpecification instead of the deleted builders. Build `MAP_STYLES: Record<BaseLayer, StyleSpecification>` at module scope as an explicit four-entry literal (dark, light, orthophoto, satellite), each `getMapStyle(key, PMTILES_URL)` — keep the existing comment explaining why module-scope singletons are required (react-map-gl compares mapStyle by reference). Keep the pmtiles Protocol registration unchanged. Default prop `baseLayer = DEFAULT_BASE_LAYER`. Add a module-level `TOWN_CENTER = { lng: 10.0918, lat: 48.8374 }` (the same coordinates already used in initialViewState — no new hardcoding; Task 3 reuses it for the sun position) and use it in initialViewState together with zoom 13, pitch 60, bearing -20; add `maxPitch={80}` on `<Map>`; keep minZoom 8 / maxZoom 18, flyTo, interactiveLayerIds and the existing NavigationControl (it already has visualizePitch). Add prop `terrain3dVisible?: boolean` (default true). Rewrite the auto-tilt effect so the initial pitch 60 is not overridden: skip the first run with a ref flag (set inside the effect), then whenever buildings3dVisible or terrain3dVisible changes ease to pitch 60 if either is on, else to 0 (both values in the dependency array so react-hooks/exhaustive-deps stays clean).

6. Run the verify block, then commit: stage exactly the five files by path (never `git add -A` / `git add .`; the untracked files under .planning/ and docs/ stay untracked), message `feat(quick-261115-wav): self-hosted vector basemap with DEM sources and 3D camera`, ending with the Co-Authored-By trailer from your session's attribution system-reminder (the orchestrator requested `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`). Do not push.
  </action>
  <verify>
    <automated>frontend/node_modules/.bin/jiti "/private/tmp/claude-501/-Users-hannessuhr-Library-Application-Support-Claude-scratch-workspaces-917fe486-0d98-4ede-ac88-e647c09dcb55-4c52147a-b177-4f3c-8801-8ef7ea1c9bce-scratch-2026-11-15-7357de/2d37f251-3d2e-41ee-ae9f-b74e9b5a9365/scratchpad/check-3d-foundation.ts" styles && (cd frontend && npx tsc --noEmit) && test -z "$(git grep --untracked -n 'tile.openstreetmap.org' -- frontend)" && test -z "$(grep -n "@/" frontend/lib/map-styles.ts)" && test -z "$(grep -nE 'as any|: any\b|<any>' frontend/lib/map-styles.ts)" && grep -q "maxPitch={80}" frontend/components/map/MapView.tsx && grep -q "terrain3d" frontend/hooks/useUrlState.ts && grep -q "3D-Gelaende" frontend/components/sidebar/Sidebar.tsx</automated>
  </verify>
  <done>Check script prints "styles: OK"; tsc 0 errors; no OSM raster tile URL left in frontend; base=osm resolves to 'light', missing base to 'dark'; Sidebar shows Dunkel/Hell/Luftbild (LGL)/Satellit (Sentinel-2) and the 3D-Gebaeude + 3D-Gelaende toggles; MapView renders MAP_STYLES[baseLayer] with pitch 60 / bearing -20 / maxPitch 80; commit created with only the five files.</done>
</task>

<task type="auto">
  <name>Task 2: Terrain on/off, hillshade relief from the open DEM, and city-like 3D buildings beneath labels on every base style</name>
  <files>frontend/components/map/applyOnStyleLoad.ts, frontend/components/map/BuildingsLayer.tsx, frontend/components/map/GeospatialOverlayLayer.tsx, frontend/components/map/MapView.tsx</files>
  <read_first>
    - frontend/components/map/BuildingsLayer.tsx, frontend/components/map/GeospatialOverlayLayer.tsx, frontend/components/map/WmsOverlayLayer.tsx
    - frontend/lib/map-styles.ts as written in Task 1 (ids, BUILDING_PALETTES, firstSymbolLayerId)
    - frontend/node_modules/@vis.gl/react-maplibre/src/components/layer.ts (create/update/beforeId behaviour)
  </read_first>
  <action>
Implements the runtime half of DESIGN-2 (terrain + hillshade) and DESIGN-4 (buildings).

1. New frontend/components/map/applyOnStyleLoad.ts: export `applyOnStyleLoad(map: MapLibreMap, apply: () => void): () => void` (type-only import of the maplibre-gl Map type). It calls `apply()` immediately when `map.style?._loaded` is true, always subscribes `apply` to the map's 'style.load' event, and returns a function that unsubscribes it. Document in one comment why: react-map-gl swaps base styles with a style diff that resets sky/light/terrain/visibility and MapLibre 6.18 fires 'style.load' after both diffs and full reloads; `map.isStyleLoaded()` must not be used here because it stays false while tiles are still loading. Both Task 2 components and Task 3's MapAtmosphere use this helper.

2. frontend/components/map/GeospatialOverlayLayer.tsx (DESIGN-2): new props `terrainVisible: boolean` (in addition to cadastralVisible, hillshadeVisible). Keep the cadastral WmsOverlayLayer exactly as it is. Remove the hillshade WmsOverlayLayer that points at the LGL DGM Schummerung WMS (it answers HTTP 500). Get the map via `useMap()` from react-map-gl/maplibre (`current?.getMap()`). Effect A (deps map, hillshadeVisible): via applyOnStyleLoad, when `map.getLayer(HILLSHADE_LAYER_ID)` exists set its layout 'visibility' to 'visible' or 'none'. Effect B (deps map, terrainVisible): via applyOnStyleLoad, when on and `map.getSource(TERRAIN_SOURCE_ID)` exists call `map.setTerrain({ source: TERRAIN_SOURCE_ID, exaggeration: TERRAIN_EXAGGERATION })`; when off and `map.getTerrain()` is set call `map.setTerrain(null)`. Each effect returns the unsubscribe from applyOnStyleLoad. This is imperative on purpose (react-map-gl's terrain prop type has no null; see context). No untyped casts.

3. frontend/components/map/BuildingsLayer.tsx (DESIGN-4): props `visible: boolean; baseLayer: BaseLayer; beforeId?: string`. Keep `id: 'buildings-3d'` (it is in interactiveLayerIds and drives UnifiedBuildingPopup), `type: 'fill-extrusion'`, `source: PROTOMAPS_SOURCE_ID`, `'source-layer': 'buildings'`, `minzoom: 13`, and the layout visibility toggle. Build the paint with useMemo keyed on baseLayer from BUILDING_PALETTES[baseLayer]:
   - fill-extrusion-color: linear interpolate over the building height (`coalesce` of `height` with 9) through the palette stops (flatten the [height, colour] pairs into the expression);
   - fill-extrusion-height: `coalesce` of `height` with default 9;
   - fill-extrusion-base: `coalesce` of `min_height` with default 0;
   - fill-extrusion-opacity: linear interpolate on zoom — 0 at zoom 13 to the palette opacity at zoom 14 (1 for dark/light, 0.9 for orthophoto/satellite);
   - fill-extrusion-vertical-gradient: true.
   Type the paint as the FillExtrusionLayerSpecification paint type; if the spread-built interpolate expression needs a nudge use `as ExpressionSpecification` (a precise type, never an untyped cast). Pass `beforeId` through to `<Layer>` so buildings are inserted beneath the first label layer.

4. frontend/components/map/MapView.tsx: next to the `mapStyle` lookup compute `labelBeforeId = firstSymbolLayerId(mapStyle)` (resolves to 'address_label' for all four styles, so react-map-gl never has to move the layer on a base switch). Render `<BuildingsLayer visible={buildings3dVisible} baseLayer={baseLayer} beforeId={labelBeforeId} />` and `<GeospatialOverlayLayer cadastralVisible={cadastralVisible} hillshadeVisible={hillshadeVisible} terrainVisible={terrain3dVisible} />`. Do not touch any data layer component, popup or interactiveLayerIds.

5. Run the verify block, then commit exactly these four files by path: `feat(quick-261115-wav): terrain toggle, DEM hillshade and shaded 3D buildings beneath labels` with the same trailer rule as Task 1. Do not push.
  </action>
  <verify>
    <automated>(cd frontend && npx tsc --noEmit) && frontend/node_modules/.bin/jiti "/private/tmp/claude-501/-Users-hannessuhr-Library-Application-Support-Claude-scratch-workspaces-917fe486-0d98-4ede-ac88-e647c09dcb55-4c52147a-b177-4f3c-8801-8ef7ea1c9bce-scratch-2026-11-15-7357de/2d37f251-3d2e-41ee-ae9f-b74e9b5a9365/scratchpad/check-3d-foundation.ts" styles && test -z "$(git grep --untracked -n 'WMS_LGL-BW_ATKIS_DGM' -- frontend)" && grep -q "WMS_LGL-BW_ATKIS_ALKIS" frontend/components/map/GeospatialOverlayLayer.tsx && grep -q "setTerrain" frontend/components/map/GeospatialOverlayLayer.tsx && grep -q "HILLSHADE_LAYER_ID" frontend/components/map/GeospatialOverlayLayer.tsx && grep -q "fill-extrusion-vertical-gradient" frontend/components/map/BuildingsLayer.tsx && grep -q "min_height" frontend/components/map/BuildingsLayer.tsx && grep -q "'buildings-3d'" frontend/components/map/BuildingsLayer.tsx && grep -q "beforeId" frontend/components/map/BuildingsLayer.tsx && grep -q "style.load" frontend/components/map/applyOnStyleLoad.ts && grep -q "_loaded" frontend/components/map/applyOnStyleLoad.ts && test -z "$(grep -nE 'as any|: any\b' frontend/components/map/applyOnStyleLoad.ts frontend/components/map/BuildingsLayer.tsx frontend/components/map/GeospatialOverlayLayer.tsx)"</automated>
  </verify>
  <done>tsc 0 errors; the failing DGM WMS is gone while the ALKIS WMS stays; terrain is switched with map.setTerrain and re-applied after every style.load; hillshade-relief visibility follows the Gelaenderelief toggle; buildings-3d is an opaque, height-coloured, vertically shaded fill-extrusion with per-base palette inserted before the first label layer on all four styles; commit created with only the four files.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Sun position + weather-driven sky and light (MapAtmosphere replaces the dead WeatherSkybox)</name>
  <files>frontend/lib/sun.ts, frontend/lib/atmosphere.ts, frontend/components/map/MapAtmosphere.tsx, frontend/components/map/WeatherSkybox.tsx, frontend/components/map/MapView.tsx</files>
  <read_first>
    - The `atmosphere` section of the CHECK SCRIPT (exact ranges and comparisons)
    - frontend/components/map/WeatherSkybox.tsx (Bright Sky icon mapping to reuse; file is deleted in this task)
    - frontend/components/map/applyOnStyleLoad.ts (Task 2)
  </read_first>
  <behavior>
    - sunPosition(2026-06-21T11:22Z, 48.8374, 10.0918): altitude in [63, 66.5], azimuth in [165, 195]; 2026-12-21T11:22Z: altitude in [16, 19.5]; 2026-06-21T06:00Z: altitude in [19, 28], azimuth in [65, 100]; 2026-06-21T23:22Z: altitude below -6; azimuth always in [0, 360), altitude in [-90, 90]
    - weatherCategory: clear-day, clear-night, partly-cloudy-day, partly-cloudy-night, wind, null, unknown -> 'clear'; cloudy, fog -> 'overcast'; rain, sleet, snow, hail, thunderstorm -> 'precip'
    - skyFor: string sky-color/horizon-color/fog-color, blends within [0, 1]; clear day, overcast day, rain day, twilight (altitude between -6 and +6, warm horizon) and night (altitude below -6, dark blue) are all different; skyFor(null, 0) differs from skyFor(null, 10) and skyFor(null, -10)
    - lightFor(az, alt): anchor 'map', position [1.5, az normalised to 0..360, polar] with polar = 90 - alt clamped to [15, 80]; higher sun gives a smaller polar angle; intensity within [0.1, 1] and lower at night than by day; low sun is warmer than midday; night light is cooler than midday
  </behavior>
  <action>
<!-- planner-discipline-allow: WeatherSkybox -->
Implements DESIGN-3. RED first: run the check script `atmosphere` section and confirm it fails (lib/sun.ts missing) before writing the modules; GREEN when it prints "atmosphere: OK".

1. New frontend/lib/sun.ts — `sunPosition(date: Date, lat: number, lng: number): { azimuthDeg: number; altitudeDeg: number }`, no imports at all. Use the standard NOAA fractional-year approximation: fractional year gamma from the UTC day of year and UTC hour; equation of time (minutes) and solar declination (radians) from the usual gamma Fourier series; true solar time = UTC minutes + equation of time + 4 * lng; hour angle = trueSolarTime / 4 - 180 degrees; altitude = asin(sin(lat) sin(decl) + cos(lat) cos(decl) cos(hourAngle)) with the argument clamped to [-1, 1]; azimuth (clockwise from north) = atan2(sin(hourAngle), cos(hourAngle) sin(lat) - tan(decl) cos(lat)) + 180, normalised to [0, 360). (This formula was validated against the check ranges at planning time.)

2. New frontend/lib/atmosphere.ts — one single-line `import type { LightSpecification, SkySpecification } from 'maplibre-gl'` statement, nothing else (same line-wise purity gate as map-styles.ts). Export `weatherCategory(condition)` returning 'clear' | 'overcast' | 'precip' per the behaviour list (Bright Sky icon strings), `skyFor(condition, altitudeDeg): SkySpecification` and `lightFor(azimuthDeg, altitudeDeg): LightSpecification`. Sun bands: night < -6, twilight -6..+6, low sun +6..+20, day > 20. Sky presets (suggested colours, keep them distinct): clear day sky '#5a8fd8' / horizon '#cfe3f5' haze / fog '#dfe9f3'; overcast or fog day greys ('#9aa3ad' / '#c9ced3' / '#cfd3d7'); rain/snow day dark greys ('#5f656d' / '#8a9097' / '#8f949a'); twilight warm horizon (e.g. sky '#3a5a8c' for clear or '#6f747c' for overcast/precip, horizon '#f2a65a', fog '#e8b98a'); night dark blue ('#0b1026' / '#1c2540' / '#0e1424'). Set sky-horizon-blend, horizon-fog-blend and fog-ground-blend to values in [0, 1] (more haze for overcast/precip). Light: anchor 'map', position [1.5, normalised azimuth, clamp(90 - altitude, 15, 80)] so buildings never go fully black; colour warm at low sun/twilight (e.g. '#ffd2a1' / '#ffb37a'), white by day, cool blue at night (e.g. '#8fa3d6'); intensity dimmer at night (e.g. 0.25 night, 0.4 twilight, 0.5-0.55 day).

3. New frontend/components/map/MapAtmosphere.tsx ('use client'; renamed replacement for WeatherSkybox) — props `{ condition: string | null; timestamp: Date | null; center: { lat: number; lng: number } }`, renders null. Live clock: `useState(() => new Date())` lazy initializer; one effect keyed on `timestamp` that, only while timestamp is null, schedules an immediate refresh with a 0 ms timeout plus a 5-minute interval (both calling setNow(new Date()) inside the callbacks — never call setState synchronously in the effect body, the react-hooks set-state-in-effect rule forbids it) and clears both on cleanup. time = timestamp ?? now; useMemo sunPosition(time, center.lat, center.lng), then useMemo skyFor(condition, altitude) and lightFor(azimuth, altitude). Effect (deps map, sky, light): `applyOnStyleLoad(map, () => { map.setSky(sky); map.setLight(light); })`, returning its unsubscribe. Use the typed MapLibre methods directly — no untyped casts, no try/catch swallowing, and do not mention the Mapbox fog API anywhere (not even in comments). Do not mention the old component's name in any new code or comment either (the final gate greps the frontend for it and must find nothing).

4. Delete the old component with `git rm frontend/components/map/WeatherSkybox.tsx`.

5. frontend/components/map/MapView.tsx: replace the WeatherSkybox import and element with `<MapAtmosphere condition={weatherCondition ?? null} timestamp={historicalTimestamp ?? null} center={TOWN_CENTER} />` inside `<Map>` (TOWN_CENTER is the module-level constant from Task 1, so the prop reference is stable).

6. Run the verify block, then commit exactly frontend/lib/sun.ts, frontend/lib/atmosphere.ts, frontend/components/map/MapAtmosphere.tsx, frontend/components/map/MapView.tsx and the staged deletion of WeatherSkybox.tsx: `feat(quick-261115-wav): sun-driven sky and lighting replace the dead fog skybox`, same trailer rule. Do not push.
  </action>
  <verify>
    <automated>frontend/node_modules/.bin/jiti "/private/tmp/claude-501/-Users-hannessuhr-Library-Application-Support-Claude-scratch-workspaces-917fe486-0d98-4ede-ac88-e647c09dcb55-4c52147a-b177-4f3c-8801-8ef7ea1c9bce-scratch-2026-11-15-7357de/2d37f251-3d2e-41ee-ae9f-b74e9b5a9365/scratchpad/check-3d-foundation.ts" all && (cd frontend && npx tsc --noEmit) && test -z "$(git grep --untracked -n 'setFog' -- frontend)" && test -z "$(git grep --untracked -n 'WeatherSkybox' -- frontend)" && test ! -e frontend/components/map/WeatherSkybox.tsx && grep -q "setSky(" frontend/components/map/MapAtmosphere.tsx && grep -q "setLight(" frontend/components/map/MapAtmosphere.tsx && grep -q "applyOnStyleLoad" frontend/components/map/MapAtmosphere.tsx && test -z "$(grep -nE 'as any|: any\b|@/' frontend/lib/sun.ts frontend/lib/atmosphere.ts)" && test -z "$(grep -nE 'as any|: any\b' frontend/components/map/MapAtmosphere.tsx)" && test -z "$(grep -nE "from '(maplibre-gl|react|react-map-gl[^']*)'" frontend/lib/map-styles.ts frontend/lib/sun.ts frontend/lib/atmosphere.ts | grep -v ':import type ')"</automated>
  </verify>
  <done>Check script prints "styles: OK" and "atmosphere: OK"; tsc 0 errors; WeatherSkybox and every fog call are gone; MapAtmosphere applies typed setSky/setLight now and after every style.load, driven by weather + sun for now (refreshed every 5 min) or the time-slider timestamp; lib files are pure (type-only maplibre imports, no alias); commit created with only the listed paths.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| URL query -> client state | `base` and `layers` params are user-controlled strings read by useUrlState |
| browser -> third-party tile/asset hosts | DEM tiles (AWS S3 Terrain Tiles), glyphs/sprites (protomaps.github.io), LGL orthophoto/ALKIS WMS, EOX Sentinel-2 tiles; all fetched by MapLibre from the user's browser |
| build -> npm registry | no new packages in this task |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-261115wav-01 | Tampering | hooks/useUrlState.ts `base` param | low | mitigate | parseBaseLayer whitelists the four BaseLayer values, maps legacy 'osm' to 'light' and falls back to 'dark' for anything else, so MAP_STYLES lookups can never be undefined or attacker-chosen (asserted by the check script) |
| T-261115wav-02 | Information Disclosure | DEM / glyph / sprite / imagery requests | low | accept | Tile requests reveal the viewed area to public CDNs (AWS S3, GitHub Pages, LGL, EOX) — same exposure class as the OSM raster tiles they partly replace; no cookies, keys or personal data are sent. Self-hosting is recorded as a follow-up comment in map-styles.ts |
| T-261115wav-03 | Denial of Service | Terrain + 3D extrusions at pitch 60-80 on weak GPUs | low | mitigate | Terrain has a sidebar off switch (3D-Gelaende) and 3D buildings keep theirs; buildings only render from zoom 13 and fade in until 14; DEM maxzoom capped at 15 |
| T-261115wav-04 | Denial of Service | Third-party DEM host unavailable | low | accept | MapLibre treats failed raster-dem tiles as missing data; the basemap, labels and data layers still render, and terrain can be switched off |
| T-261115wav-05 | Spoofing / XSS | Attribution HTML strings | low | accept | All attribution strings are static constants in map-styles.ts with no user input interpolated |
| T-261115wav-SC | Tampering | npm installs | high | mitigate | No dependency is added or upgraded; the final verification asserts `git diff --quiet master -- frontend/package.json frontend/package-lock.json` |
</threat_model>

<verification>
Run from the repository root after all three tasks (do not start a dev server; do not rebuild, restart or stop the Docker containers):

1. `cd frontend && npx tsc --noEmit` -> 0 errors.
2. `npm --prefix frontend run lint` -> the summary shows at most 10 errors (baseline 11, minus the WeatherSkybox no-explicit-any that left with the deleted file) and no error in any file this plan created. Per-file check: `cd frontend && npx eslint lib/map-styles.ts lib/sun.ts lib/atmosphere.ts hooks/useUrlState.ts app/page.tsx components/sidebar/Sidebar.tsx components/map/MapView.tsx components/map/BuildingsLayer.tsx components/map/GeospatialOverlayLayer.tsx components/map/MapAtmosphere.tsx components/map/applyOnStyleLoad.ts` -> exactly the two pre-existing MapView errors (setPopupInfo used before its declaration; no-explicit-any on the queryRenderedFeatures fallback) and no new warnings beyond the three listed in the context block.
3. `npm --prefix frontend run build` -> passes.
4. `frontend/node_modules/.bin/jiti "/private/tmp/claude-501/-Users-hannessuhr-Library-Application-Support-Claude-scratch-workspaces-917fe486-0d98-4ede-ac88-e647c09dcb55-4c52147a-b177-4f3c-8801-8ef7ea1c9bce-scratch-2026-11-15-7357de/2d37f251-3d2e-41ee-ae9f-b74e9b5a9365/scratchpad/check-3d-foundation.ts" all` -> "styles: OK" and "atmosphere: OK" (every base style contains the protomaps, terrain-dem and hillshade-dem sources).
5. `git grep -n "tile.openstreetmap.org" -- frontend` and `git grep -n "setFog" -- frontend` -> no output (baselines at HEAD: 1 and 4 matches).
6. `git diff --quiet master -- frontend/package.json frontend/package-lock.json` -> exit 0 (no dependency changes).
7. `git status --short` -> only the pre-existing untracked .planning/ and docs/ entries remain; nothing staged or modified under frontend/; `git log --oneline master..HEAD` shows the three feat(quick-261115-wav) commits; nothing pushed.

PENDING VISUAL CHECK (for the orchestrator, who opens the app in a browser after execution; record it in the SUMMARY as pending, not as passed):
- the dark vector basemap renders from the local PMTiles (no OSM PNG tiles in the network tab) and Hell switches to the light flavor;
- terrain relief is visible at pitch 60-80 and disappears when 3D-Gelaende is switched off, and comes back after switching base maps;
- a sky is drawn above the horizon (colour changes with the time slider: day, twilight, night);
- buildings are opaque, height-coloured, shaded and sit beneath street/place labels;
- 3D buildings also appear on Luftbild (LGL) and Satellit (Sentinel-2), with labels on top;
- the Gelaenderelief (DGM) toggle shows/hides the subtle hillshade; Kataster (ALKIS) is unchanged;
- existing data layers (transit stops, bus routes/positions) still render and their popups (and the building popup) still open; no new errors in the browser console.
</verification>

<success_criteria>
- All three tasks committed atomically with explicit-path staging on feat/3d-visual-foundation; nothing pushed; no dependency changes.
- tsc 0 errors, build passes, lint at or below baseline with no new errors in touched files.
- Check script passes both sections; OSM raster tile host and fog calls are gone from the frontend; the failing DGM WMS is replaced by a MapLibre hillshade from the open DEM.
- Every base style carries the protomaps vector source plus separate terrain-dem / hillshade-dem sources with correct Protomaps/OpenStreetMap and Mapzen/AWS Terrain Tiles attribution (LGL/EOX attribution unchanged).
- Pending visual check list handed to the orchestrator in the SUMMARY.
</success_criteria>

<output>
Create `.planning/quick/261115-wav-3d-visual-foundation-self-hosted-vector-/261115-wav-SUMMARY.md` when done (include the lint before/after numbers, the check script output, and the PENDING VISUAL CHECK list).
</output>
