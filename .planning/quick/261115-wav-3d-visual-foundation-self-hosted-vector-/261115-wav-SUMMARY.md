---
phase: quick-261115-wav
plan: 01
subsystem: frontend-map
tags: [maplibre, protomaps, terrain, hillshade, sky, 3d-buildings]
status: complete
requires: []
provides:
  - self-hosted Protomaps vector basemap (dark default, light) plus Luftbild/Satellit with vector labels
  - 3D terrain from open DEM tiles with sidebar toggle
  - DEM hillshade replacing the failing LGL DGM WMS
  - sun/weather-driven sky and light (MapAtmosphere)
  - opaque, height-coloured, shaded 3D buildings beneath labels on all four base styles
affects: [frontend/components/map, frontend/lib, frontend/hooks/useUrlState.ts, frontend/components/sidebar/Sidebar.tsx, frontend/app/page.tsx]
key-files:
  created:
    - frontend/lib/sun.ts
    - frontend/lib/atmosphere.ts
    - frontend/components/map/applyOnStyleLoad.ts
    - frontend/components/map/MapAtmosphere.tsx
  modified:
    - frontend/lib/map-styles.ts
    - frontend/hooks/useUrlState.ts
    - frontend/app/page.tsx
    - frontend/components/sidebar/Sidebar.tsx
    - frontend/components/map/MapView.tsx
    - frontend/components/map/BuildingsLayer.tsx
    - frontend/components/map/GeospatialOverlayLayer.tsx
  deleted:
    - frontend/components/map/WeatherSkybox.tsx
decisions:
  - "Terrain and hillshade visibility are switched imperatively (map.setTerrain / setLayoutProperty) and re-applied after every style.load via applyOnStyleLoad"
  - "Hillshade layer is baked (hidden) into every style; 3D buildings use the first symbol layer (address_label) as beforeId on all four styles"
  - "Orthophoto and satellite styles use the dark Protomaps sprite and dark-flavor label layers"
commits: 3
plan_head_before: 70576b3cd28f49108a1ba2b0140292f8c441c95a
plan_head_after: 16c7d8a7fe76c27da21217be35df1fc47748b916
actuals:
  tokens: 11000
  tasks: 3
  commits: 3
---

# Phase quick-261115-wav Plan 01: 3D Visual Foundation Summary

Self-hosted Protomaps vector basemap (dark/light) with open-DEM terrain and hillshade, a sun- and weather-driven sky/light, and opaque shaded 3D buildings beneath labels, with no new dependencies and no data-layer changes.

## Commits (branch feat/3d-visual-foundation, not pushed)

| Task | Commit | Message |
|------|--------|---------|
| 1 (tracer) | f957987 | feat(quick-261115-wav): self-hosted vector basemap with DEM sources and 3D camera |
| 2 | 2629c5e | feat(quick-261115-wav): terrain toggle, DEM hillshade and shaded 3D buildings beneath labels |
| 3 | 16c7d8a | feat(quick-261115-wav): sun-driven sky and lighting replace the dead fog skybox |

## What was built

- **map-styles.ts**: four styles (dark, light, orthophoto, satellite), each with `protomaps`, `terrain-dem`, `hillshade-dem` sources, a baked hidden `hillshade-relief` layer and default sky/light. `parseBaseLayer` whitelists the URL value (legacy `osm` -> `light`, unknown -> `dark`). OSM raster tile host removed. `BUILDING_PALETTES`, `HILLSHADE_PAINT`, `firstSymbolLayerId` exported. Follow-up comment for self-hosting glyphs/sprites/DEM added.
- **URL/sidebar/page**: default `layers` now `transit,aqi,buildings3d,terrain3d`; sidebar radio offers Dunkel, Hell, Luftbild (LGL), Satellit (Sentinel-2); toggles `3D-Gebaeude` and `3D-Gelaende`; `base` param dropped from the URL when it equals the default (dark).
- **MapView**: module-scope `MAP_STYLES` singletons for all four bases, `TOWN_CENTER`, initial pitch 60 / bearing -20, `maxPitch={80}`, auto-tilt effect skips the first run and eases to 60 / 0 when 3D buildings or terrain change.
- **applyOnStyleLoad**: apply now (when `map.style._loaded`) and after every `style.load`.
- **GeospatialOverlayLayer**: ALKIS WMS unchanged; failing DGM WMS removed; hillshade visibility and `map.setTerrain` driven through applyOnStyleLoad.
- **BuildingsLayer**: `buildings-3d` fill-extrusion, height-interpolated per-base palette, `min_height` base, vertical gradient, opacity fade 13 -> 14, inserted `beforeId` = first label layer.
- **sun.ts / atmosphere.ts / MapAtmosphere**: NOAA solar position, weather category, sky and light presets (day, low sun, twilight, night; clear/overcast/precip); MapAtmosphere applies `setSky`/`setLight`, live clock refreshed every 5 minutes or the time-slider timestamp. WeatherSkybox deleted.

## Verification results

- Check script (`check-3d-foundation.ts all`): `styles: OK` and `atmosphere: OK`. RED confirmed first for Task 3 (`Cannot find module .../frontend/lib/sun.ts`).
- `npx tsc --noEmit`: 0 errors.
- `npm --prefix frontend run build`: passed (exit 0, routes `/`, `/_not-found`, `/admin`).
- Lint whole project: before `24 problems (11 errors, 13 warnings)`, after `23 problems (10 errors, 13 warnings)` (the WeatherSkybox no-explicit-any left with the deleted file).
- Lint on the 11 touched/new files: `5 problems (2 errors, 3 warnings)`, exactly the pre-existing ones (MapView setPopupInfo used before declaration; no-explicit-any on the queryRenderedFeatures fallback; warnings: page.tsx unused `useMemo`, MapView `_mobiDataVisible`, MapView exhaustive-deps `popupInfo`). No new findings in new files.
- `git grep tile.openstreetmap.org -- frontend`: no output. `git grep setFog -- frontend`: no output. `git grep WeatherSkybox -- frontend`: no output. No `WMS_LGL-BW_ATKIS_DGM` reference remains.
- `git diff --quiet master -- frontend/package.json frontend/package-lock.json`: exit 0 (no dependency changes).
- `git status`: nothing modified or staged; only the pre-existing untracked `.planning/` and `docs/` entries remain. Nothing pushed.

## Deviations from Plan

None of substance. Small implementation notes:

- BuildingsLayer defines `const BUILDINGS_LAYER_ID = 'buildings-3d'` and passes it as `id`, so the literal `'buildings-3d'` the plan's grep gate looks for is present; behaviour identical.
- No `as ExpressionSpecification` cast was needed beyond the one on the spread-built interpolate expression (as the plan allowed).

## Known Stubs

None.

## Threat Flags

None. No new network endpoints beyond the planned public DEM host (AWS Terrain Tiles); T-261115wav-01 mitigated by `parseBaseLayer` whitelist (asserted by check script).

## PENDING VISUAL CHECK (not performed; for the orchestrator)

- [ ] Dark vector basemap renders from local PMTiles with no OSM PNG tiles in the network tab; Hell switches to the light flavor; `?base=osm` opens Hell.
- [ ] Terrain relief visible at pitch 60-80, disappears with 3D-Gelaende off, and returns after switching base maps.
- [ ] A sky is drawn above the horizon; colour changes with the time slider (day, twilight, night) and with weather (overcast, rain).
- [ ] Buildings are opaque, height-coloured, vertically shaded and sit beneath street/place labels.
- [ ] 3D buildings also appear on Luftbild (LGL) and Satellit (Sentinel-2) with labels on top.
- [ ] Gelaenderelief (DGM) toggle shows/hides the subtle hillshade; Kataster (ALKIS) unchanged.
- [ ] Transit stops, bus routes/positions still render; their popups and the building popup (`buildings-3d` -> UnifiedBuildingPopup) still open; no new browser console errors.
- [ ] Possible risk to eyeball: switching base maps while terrain is on (style diff then re-apply of terrain/sky/light via `style.load`).

## Self-Check: PASSED

- Created files exist: frontend/lib/sun.ts, frontend/lib/atmosphere.ts, frontend/components/map/applyOnStyleLoad.ts, frontend/components/map/MapAtmosphere.tsx; WeatherSkybox.tsx removed.
- Commits f957987, 2629c5e, 16c7d8a are on HEAD (`git rev-list --count 70576b3..HEAD` = 3).

## Orchestrator browser verification and tuning (2026-11-15/16)

Checked on a local production build (`next start`, port 3112) against the running backend. The pending visual checks above are resolved as follows.

Verified working:
- Dark and light vector basemaps render from the local PMTiles; no request to tile.openstreetmap.org.
- 3D terrain is visible at pitch 60-80; the "3D-Gelaende" switch turns it off and on (`map.getTerrain()` null / set) and it survives base-map switches.
- Sky and light follow the time: noon via `?ts=` gives the day preset, live at night gives the night sky and a dim blue light.
- Buildings are opaque, height-coloured, shaded and sit beneath the labels; they also render on the satellite base, which now drapes over the terrain with labels on top.
- The relief switch shows and hides the DEM hillshade layer.
- Transit stops, bus routes and the building popup still work.

Found and fixed in commit 2d25d18:
- The stock Protomaps dark flavor was grey on near-black with almost invisible roads. Replaced by a blue-tinted variant (`flavorFor` in lib/map-styles.ts), brighter building palette and dark-base sky presets (`skyFor(..., darkBase)`).
- Generic POI icons removed from all base styles (`basemapLayers`).
- Switching dark -> light at runtime left water and landcover black (stale style diff). `styleDiffing={false}` on the map forces a full style reload; verified dark -> light -> satellite -> dark.
- WMS overlays (flood, rail noise, solar potential, cadastre) were mounted at opacity 0 and requested 178 tiles from slow or failing servers on a plain page load. They are now mounted only while visible; a plain load makes no WMS request.

Not verified / still open:
- Luftbild (LGL): the LGL WMS answers HTTP 500 today, so the aerial image itself could not be seen; buildings, terrain and labels render on a white ground there.
- Weather-dependent sky presets (overcast, rain): no weather condition was available from the backend during the check.
- With transit layers on, the map stays blank for about 50 s until the 29 MB transit shapes payload has loaded. This predates this task (same behaviour on the old raster map) and belongs to the layer-loading slice.
- The app fetches every layer endpoint on load regardless of the switches, twice. Same slice.
- Glyphs, sprites and DEM tiles still come from external hosts (protomaps.github.io, AWS Terrain Tiles).
- The sidebar and dashboard panels are still light-themed next to the dark map.
