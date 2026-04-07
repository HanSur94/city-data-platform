---
phase: quick-260407-pft
plan: 01
subsystem: transit / frontend
tags: [bus, gtfs, maplibre, react, visualization, sidebar]
dependency_graph:
  requires: []
  provides: [per-line-colors, train-bus-distinction, per-line-toggles]
  affects: [BusPositionLayer, BusLineFilter, Sidebar, MapView, bus_interpolation models]
tech_stack:
  added: []
  patterns:
    - Deterministic color hash from line name for per-line styling
    - Data-driven MapLibre paint expressions via _color feature property
    - FilterSpecification from maplibre-gl for hidden line filtering
    - Exported lineColor() shared between BusPositionLayer and BusLineFilter
key_files:
  created:
    - frontend/components/sidebar/BusLineFilter.tsx
  modified:
    - backend/app/models/bus_interpolation.py
    - backend/app/connectors/bus_interpolation.py
    - frontend/components/map/BusPositionLayer.tsx
    - frontend/components/sidebar/Sidebar.tsx
    - frontend/components/map/MapView.tsx
    - frontend/app/page.tsx
decisions:
  - Injected _color property during processBusData() rather than building match expressions; avoids needing all line names upfront and works cleanly with MapLibre 'get' expressions
  - Trains distinguished by larger circle-radius (10 vs 8) and thicker stroke (3 vs 2) instead of square icons; simpler and more robust without needing custom sprites
  - lineColor() exported from BusPositionLayer.tsx so BusLineFilter can share the same palette without importing a separate utility module
  - FilterSpecification imported from maplibre-gl (not react-map-gl/maplibre which lacks it)
  - Layer spec objects cast as CircleLayerSpecification etc. rather than typed inline to avoid TypeScript issues with complex paint expression inference
metrics:
  duration: ~25 minutes
  completed_date: "2026-04-07T16:27:13Z"
  tasks_completed: 2
  files_changed: 7
---

# Quick Task 260407-pft: Bus Position Layer Visual Overhaul Summary

**One-liner:** Per-line deterministic colors on bus dots and route lines via hash palette, delay-based stroke, train/bus size distinction via route_type from GTFS, and per-line sidebar filter checkboxes.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Backend — add route_type to models and connector | 52e04aa | models/bus_interpolation.py, connectors/bus_interpolation.py |
| 2 | Frontend — per-line colors, train/bus shapes, sidebar filter | d120c78 | BusPositionLayer.tsx, BusLineFilter.tsx (new), Sidebar.tsx, MapView.tsx, page.tsx |

## What Was Built

### Backend
- `BusPosition` and `ActiveTrip` models now have `route_type: int = 3` (default=bus)
- `route_info` dict expanded to `(short_name, long_name, route_type)` tuples
- `interpolate_position()` propagates `route_type` from `ActiveTrip` to all `BusPosition` return paths
- `run()` method includes `route_type` in GeoJSON feature properties dict

### Frontend — BusPositionLayer.tsx
- 15-color `LINE_COLORS` palette with `lineColor(name)` hash function (both exported)
- `processBusData()` injects `_color = lineColor(line_name)` into every position and route line feature's properties
- Circle dots styled with `'circle-color': ['get', '_color']` — each line gets a unique color
- Delay indication moved to `circle-stroke-color` with step expression (green/yellow/orange/red at 0/120/300/600s)
- Train/bus distinction: `circle-radius: ['match', ['get', 'route_type'], 0, 10, 1, 10, 2, 10, 8]` and matching stroke-width 3 vs 2
- Route lines (driven + remaining) use `'line-color': ['get', '_color']` for same per-line color
- New `hiddenLines?: Set<string>` prop applies MapLibre filter to all 4 layers
- New `onLinesDiscovered?: (lines: string[]) => void` callback fires only when line set changes
- Lerp animation fully preserved — `lerpPositions()` and animation loop unchanged

### Frontend — BusLineFilter.tsx (new)
- Scrollable list (max-height 200px) of checkboxes for each discovered line
- Per-line colored dot using same `lineColor()` function
- Naturally sorted numerically (`localeCompare` numeric option)
- "Alle anzeigen" / "Alle ausblenden" toggle button at top

### Frontend — Sidebar.tsx
- New props: `busLines`, `hiddenBusLines`, `onToggleBusLine`
- `<BusLineFilter>` rendered conditionally below bus-position toggle when layer is active and lines are discovered

### Frontend — MapView.tsx + page.tsx
- `hiddenBusLines` and `onBusLinesDiscovered` props wired through MapView to BusPositionLayer
- `busLines` state, `hiddenBusLines` state, and `handleToggleBusLine` callback added to HomeInner in page.tsx

## Deviations from Plan

None — plan executed exactly as written, with one auto-fix:

**[Rule 3 - Blocking] FilterSpecification not exported from react-map-gl/maplibre**
- **Found during:** Task 2 frontend build
- **Issue:** `FilterSpecification` is not re-exported by react-map-gl/maplibre — build error
- **Fix:** Import `FilterSpecification` from `maplibre-gl` directly instead
- **Files modified:** frontend/components/map/BusPositionLayer.tsx

**[Rule 3 - Blocking] TypeScript inference failure on inline layer spec objects**
- **Found during:** Task 2 frontend build
- **Issue:** TypeScript inferred `paint` as `undefined` in conditional type of `CircleLayerSpecification['paint']`, blocking property access
- **Fix:** Construct layer objects as plain objects then cast `as CircleLayerSpecification` (avoids inferring through the optional paint type)
- **Files modified:** frontend/components/map/BusPositionLayer.tsx

## Known Stubs

None — all functionality is fully wired from GTFS backend through to frontend filter.

## Self-Check: PASSED
