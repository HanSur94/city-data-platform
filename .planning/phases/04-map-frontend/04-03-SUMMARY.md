---
phase: 04-map-frontend
plan: 03
subsystem: ui
tags: [react-map-gl, maplibre, geojson, heatmap, clustering, popup, freshness]

requires:
  - phase: 04-map-frontend/04-02
    provides: MapView shell with PMTiles base map, Sidebar with layer toggles, useLayerData hook

provides:
  - TransitLayer with MapLibre clustering (zoom<14 clusters, zoom>=14 individual colored dots)
  - AQILayer with heatmap + transparent click-target circles
  - FeaturePopup rendering transit stop or AQI sensor data at click coordinates
  - FreshnessIndicator colored dot (green/yellow/red) with relative time and tooltip
  - MapView extended with interactiveLayerIds, popup state, onClick handler
  - page.tsx wired to useLayerData for both transit and air_quality domains

affects: [05-dashboard, future phases using map layer patterns]

tech-stack:
  added: []
  patterns:
    - "Layer visibility via layout.visibility prop (not React state re-render) — no flash"
    - "Heatmap layers not clickable: separate transparent circle layer (aqi-points) for click targets"
    - "LayerSpecification types from @vis.gl/react-maplibre (CircleLayerSpecification, etc.) not CircleLayer aliases"
    - "base-ui TooltipTrigger uses render prop instead of asChild for custom element rendering"

key-files:
  created:
    - frontend/components/map/TransitLayer.tsx
    - frontend/components/map/AQILayer.tsx
    - frontend/components/map/FeaturePopup.tsx
    - frontend/components/map/FreshnessIndicator.tsx
  modified:
    - frontend/components/map/MapView.tsx
    - frontend/app/page.tsx

key-decisions:
  - "Use CircleLayerSpecification/SymbolLayerSpecification/HeatmapLayerSpecification (not CircleLayer aliases) — actual exports from react-map-gl/maplibre"
  - "base-ui Tooltip render prop instead of asChild — base-ui TooltipTrigger does not support asChild"
  - "visibility() helper returns 'visible' | 'none' with explicit return type (not `as const`) — TypeScript doesn't allow `as const` on ternary expressions"

patterns-established:
  - "Pattern: Heatmap + click target — always add transparent circle layer alongside heatmap and include in interactiveLayerIds"
  - "Pattern: Layer visibility — spread layout and override visibility property on Layer component"

requirements-completed: [MAP-02, MAP-03, MAP-04, MAP-05, MAP-07]

duration: 25min
completed: 2026-04-05
---

# Phase 04 Plan 03: Data Layers, Popups, and Freshness Summary

**Transit clustering and AQI heatmap wired to live API data with feature popups, FreshnessIndicator, and 60s polling via react-map-gl Sources and Layers**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-04-05T22:35:00Z
- **Completed:** 2026-04-05T23:00:00Z
- **Tasks:** 2 auto + 1 checkpoint (auto-approved)
- **Files modified:** 6

## Accomplishments
- TransitLayer: three MapLibre layers (cluster circles, count labels, individual stop dots) with route-type color matching
- AQILayer: heatmap weighted by `aqi` property + transparent `aqi-points` circle layer for click targets (Pitfall 4 fix)
- FeaturePopup: domain-detected rendering (transit vs AQI) with shadcn Badge for AQI tier
- FreshnessIndicator: green/yellow/red colored dot with useRelativeTime text and exact-timestamp tooltip
- Layer visibility controlled via `layout.visibility` prop (not React re-render) — immediate toggle, no flash
- page.tsx wired both useLayerData hooks; MapView receives data props and lastFetched timestamps

## Task Commits

1. **Task 1: Build TransitLayer, AQILayer, wire into MapView** - `dba8092` (feat)
2. **Task 2: Build FeaturePopup and FreshnessIndicator** - `2526a97` (feat)
3. **Task 3: Human verification (auto-approved)** - N/A

**Plan metadata:** (pending)

## Files Created/Modified
- `frontend/components/map/TransitLayer.tsx` - GeoJSON source with clustering, 3 MapLibre layers
- `frontend/components/map/AQILayer.tsx` - Heatmap layer + transparent click-target circle layer
- `frontend/components/map/FeaturePopup.tsx` - Popup card for transit stop or AQI sensor data
- `frontend/components/map/FreshnessIndicator.tsx` - Colored dot + relative time + tooltip
- `frontend/components/map/MapView.tsx` - Extended props, interactiveLayerIds, popup state/handler
- `frontend/app/page.tsx` - useLayerData hooks for transit and air_quality wired to MapView

## Decisions Made
- `CircleLayerSpecification` (not `CircleLayer`) — actual exported type from react-map-gl/maplibre via @vis.gl/react-maplibre
- base-ui `TooltipTrigger` uses `render` prop not `asChild` — different API from Radix UI Tooltip
- `visibility()` function uses explicit return type `'visible' | 'none'` — TypeScript cannot infer `as const` in ternary

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed incorrect type names for MapLibre layer specs**
- **Found during:** Task 1 (build TransitLayer and AQILayer)
- **Issue:** Plan used `CircleLayer`, `SymbolLayer`, `HeatmapLayer` but react-map-gl/maplibre exports `CircleLayerSpecification`, `SymbolLayerSpecification`, `HeatmapLayerSpecification`
- **Fix:** Updated imports and type annotations to use `*LayerSpecification` names
- **Files modified:** TransitLayer.tsx, AQILayer.tsx
- **Verification:** TypeScript build passes (0 errors)
- **Committed in:** dba8092

**2. [Rule 1 - Bug] Fixed `as const` on ternary expression**
- **Found during:** Task 1 (type checking)
- **Issue:** TypeScript doesn't allow `as const` assertions on ternary expressions
- **Fix:** Changed to explicit return type annotation `(v: boolean): 'visible' | 'none'`
- **Files modified:** TransitLayer.tsx, AQILayer.tsx
- **Verification:** TypeScript build passes
- **Committed in:** dba8092

**3. [Rule 1 - Bug] Fixed FreshnessIndicator TooltipTrigger API**
- **Found during:** Task 2 (FreshnessIndicator build)
- **Issue:** Used `asChild` on TooltipTrigger but project uses base-ui (not Radix UI) — base-ui uses `render` prop
- **Fix:** Changed `<TooltipTrigger asChild>` to `<TooltipTrigger render={<div ... />}>`
- **Files modified:** FreshnessIndicator.tsx
- **Verification:** TypeScript build passes
- **Committed in:** 2526a97

---

**Total deviations:** 3 auto-fixed (3 Rule 1 bugs — API mismatches between plan assumptions and actual installed packages)
**Impact on plan:** All auto-fixes necessary for correctness. No scope creep. All acceptance criteria still met.

## Issues Encountered
- Build required `npm install` in the worktree's frontend directory (node_modules not present in git worktree)
- base-ui tooltip API differs significantly from Radix UI — `render` prop pattern instead of `asChild`

## Known Stubs
None — all data flows through real API calls from useLayerData hooks; FeaturePopup renders actual feature.properties from API responses.

## Next Phase Readiness
- Complete Phase 4 map frontend is functional: transit clustering, AQI heatmap, popups, freshness, layer toggles
- Ready for Phase 5 (dashboard and historical data)
- No blockers

---
*Phase: 04-map-frontend*
*Completed: 2026-04-05*
