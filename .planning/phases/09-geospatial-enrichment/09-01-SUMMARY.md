---
phase: 09-geospatial-enrichment
plan: "01"
subsystem: frontend
tags: [geospatial, map, base-layer, wms, url-state, sidebar]
dependency_graph:
  requires: []
  provides: [base-layer-switching, cadastral-overlay, hillshade-overlay, geospatial-url-state]
  affects: [frontend/lib/map-styles.ts, frontend/components/map/MapView.tsx, frontend/components/sidebar/Sidebar.tsx, frontend/hooks/useUrlState.ts, frontend/app/page.tsx]
tech_stack:
  added: []
  patterns: [WMS raster overlay, MapLibre style switching, URL state persistence]
key_files:
  created:
    - frontend/components/map/GeospatialOverlayLayer.tsx
  modified:
    - frontend/lib/map-styles.ts
    - frontend/components/map/MapView.tsx
    - frontend/components/sidebar/Sidebar.tsx
    - frontend/hooks/useUrlState.ts
    - frontend/app/page.tsx
decisions:
  - "EOX Sentinel-2 cloudless WMTS used for satellite layer — free, no API key, global mosaic"
  - "Base layer uses separate 'base' URL param (not layers CSV) — cleaner URL structure"
  - "OSM omits 'base' param from URL (null) to keep default URLs clean"
  - "Geospatial overlays (cadastral, hillshade) use existing layers CSV mechanism for consistency"
metrics:
  duration: 15
  completed_date: "2026-04-06"
  tasks: 2
  files: 5
---

# Phase 9 Plan 01: Geospatial Base Layers and WMS Overlays Summary

Base layer switching (OSM/Orthophoto/Satellite via LGL DOP WMS and EOX Sentinel-2 WMTS) and geospatial WMS overlays (LGL ALKIS cadastral, LGL DGM hillshade) with sidebar radio group and URL persistence.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Base layer style builders + MapView dynamic style + GeospatialOverlayLayer | d9b9b9f | frontend/lib/map-styles.ts, frontend/components/map/GeospatialOverlayLayer.tsx, frontend/components/map/MapView.tsx |
| 2 | Sidebar Geospatial group + useUrlState + page.tsx wiring | 59d821f | frontend/components/sidebar/Sidebar.tsx, frontend/hooks/useUrlState.ts, frontend/app/page.tsx |

## What Was Built

### map-styles.ts
- Added `BaseLayer` type (`'osm' | 'orthophoto' | 'satellite'`)
- `buildOrthophotoStyle()` — MapLibre style using LGL BW DOP WMS raster source (dl-de/by-2-0 licensed)
- `buildSatelliteStyle()` — MapLibre style using EOX S2 cloudless WMTS (Copernicus Sentinel-2 mosaic, no API key required)
- `getMapStyle(baseLayer, pmtilesUrl)` — dispatches to correct style builder

### GeospatialOverlayLayer.tsx
- New component composing two WmsOverlayLayer instances:
  - Cadastral (LGL ALKIS: `Flurstueck,Gebaeude` layers, opacity 0.7)
  - Hillshade (LGL DGM Schummerung, opacity 0.5)

### MapView.tsx
- New props: `baseLayer`, `cadastralVisible`, `hillshadeVisible`
- `buildMapStyle` replaced with `getMapStyle(baseLayer, PMTILES_URL)` for dynamic switching
- `GeospatialOverlayLayer` rendered after `InfrastructureLayer`

### useUrlState.ts
- `baseLayer` added to `UrlState` interface, parsed from `?base=` URL param (default `'osm'`)

### Sidebar.tsx
- New props: `baseLayer`, `onBaseLayerChange`, `cadastralVisible`, `hillshadeVisible`
- `onToggleLayer` union extended with `'cadastral' | 'hillshade'`
- New "Geospatial" section added after Infrastruktur group:
  - Radio group: OpenStreetMap / Luftbild (LGL) / Satellit (Sentinel-2)
  - Toggle: Kataster (ALKIS)
  - Toggle: Gelaenderelief (DGM)

### page.tsx
- `cadastral` and `hillshade` added to `layerVisibility` and `LAYER_KEYS`
- `handleBaseLayerChange` function (omits `base` param for OSM default)
- New props passed to both `Sidebar` and `MapView`

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all data sources are wired to real LGL BW and EOX WMS/WMTS endpoints.

## Self-Check: PASSED

- frontend/components/map/GeospatialOverlayLayer.tsx: FOUND
- frontend/lib/map-styles.ts: FOUND (buildOrthophotoStyle, buildSatelliteStyle, getMapStyle, BaseLayer)
- frontend/components/map/MapView.tsx: FOUND (baseLayer, GeospatialOverlayLayer, getMapStyle)
- frontend/hooks/useUrlState.ts: FOUND (baseLayer)
- frontend/components/sidebar/Sidebar.tsx: FOUND (Geospatial, Basiskarte, onBaseLayerChange)
- frontend/app/page.tsx: FOUND (baseLayer, handleBaseLayerChange, cadastralVisible, hillshadeVisible)
- Commits d9b9b9f and 59d821f: FOUND in git log
