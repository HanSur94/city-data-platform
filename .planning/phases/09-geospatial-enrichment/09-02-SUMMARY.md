---
phase: 09-geospatial-enrichment
plan: 02
subsystem: frontend/map
tags: [maplibre, 3d-buildings, fill-extrusion, pmtiles, sidebar, url-state]
dependency_graph:
  requires: [09-01]
  provides: [buildings-3d-layer, buildings3d-url-param]
  affects: [frontend/components/map/MapView.tsx, frontend/components/sidebar/Sidebar.tsx, frontend/app/page.tsx]
tech_stack:
  added: []
  patterns: [fill-extrusion, mapref-auto-tilt, opacity-toggle, url-layer-key]
key_files:
  created:
    - frontend/components/map/BuildingsLayer.tsx
  modified:
    - frontend/components/map/MapView.tsx
    - frontend/components/sidebar/Sidebar.tsx
    - frontend/app/page.tsx
decisions:
  - BuildingsLayer uses opacity toggle (0 vs 0.7) not layout visibility — consistent with WmsOverlayLayer pattern
  - FillExtrusionLayerSpecification imported from maplibre-gl (not react-map-gl/maplibre) — more reliable type path
  - mapRef added to existing Map component for easeTo pitch control on 3D toggle
  - Default building height fallback is 10m — many OSM buildings lack explicit height tags
metrics:
  duration_minutes: 8
  completed_date: "2026-04-06"
  tasks_completed: 2
  files_changed: 4
---

# Phase 09 Plan 02: 3D Building Extrusion Layer Summary

**One-liner:** MapLibre fill-extrusion 3D buildings from Protomaps OSM PMTiles source with auto-tilt and URL-persisted toggle in Geospatial sidebar.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | BuildingsLayer fill-extrusion component | 9d222b3 | BuildingsLayer.tsx |
| 2 | Wire 3D toggle into MapView, Sidebar, page.tsx | ff33ba9 | MapView.tsx, Sidebar.tsx, page.tsx |

## What Was Built

### BuildingsLayer.tsx
- MapLibre `fill-extrusion` layer targeting the `buildings` source-layer in the Protomaps PMTiles vector tiles
- OSM `height` property used for extrusion height; defaults to 10m for buildings without explicit height data
- Opacity-based visibility: 0.7 when visible, 0 when hidden (consistent with WMS overlay pattern)
- Minimum zoom 14 to avoid rendering at city overview scale

### MapView.tsx changes
- Added `buildings3dVisible?: boolean` prop to `MapViewProps`
- Added `mapRef = useRef<MapRef | null>(null)` and `ref={mapRef}` on `<Map>` component
- `useEffect` watches `buildings3dVisible`: `easeTo({ pitch: 45 })` on enable, `easeTo({ pitch: 0 })` on disable (500ms transition)
- Renders `<BuildingsLayer visible={buildings3dVisible} />` after `<GeospatialOverlayLayer>`

### Sidebar.tsx changes
- Added `buildings3dVisible?: boolean` to `SidebarProps`
- Extended `onToggleLayer` union type to include `'buildings3d'`
- Added "3D" sub-heading and "3D Gebaeude (LoD1)" `LayerToggle` in the Geospatial section

### page.tsx changes
- Added `buildings3d: state.layers.includes('buildings3d')` to `layerVisibility`
- Added `buildings3d: 'buildings3d'` to `LAYER_KEYS`
- Passed `buildings3dVisible={layerVisibility.buildings3d}` to both `<Sidebar>` and `<MapView>`

## Success Criteria Check

- [x] 3D building toggle appears in Geospatial sidebar section under "3D" sub-heading
- [x] Enabling toggle renders OSM building polygons as 3D extrusions with height
- [x] Map auto-tilts to ~45 degrees when 3D enabled, returns to 0 when disabled
- [x] Toggle state persists in URL (?layers=...buildings3d...)
- [x] TypeScript type patterns consistent with existing codebase

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — BuildingsLayer reads real data from the Protomaps PMTiles `buildings` source-layer. The layer will only render if the PMTiles file covers the target area and includes building polygons from OSM.

## Self-Check: PASSED

- frontend/components/map/BuildingsLayer.tsx: FOUND
- frontend/components/map/MapView.tsx: modified with BuildingsLayer, pitch, mapRef
- frontend/components/sidebar/Sidebar.tsx: modified with buildings3d toggle
- frontend/app/page.tsx: modified with buildings3d layer key and props
- Commit 9d222b3: FOUND (BuildingsLayer component)
- Commit ff33ba9: FOUND (wiring task)
