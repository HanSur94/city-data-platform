---
phase: 06-weather-environment
plan: "04"
subsystem: frontend
tags: [map, wms, water, layers, sidebar, url-state]
dependency_graph:
  requires: [06-01, 06-02, 06-03]
  provides: [WaterLayer, WmsOverlayLayer, WaterLegend, water-toggle, flood-toggle, rail-noise-toggle, lubw-env-toggle]
  affects: [frontend/app/page.tsx, frontend/components/map/MapView.tsx, frontend/components/sidebar/Sidebar.tsx]
tech_stack:
  added: []
  patterns: [raster-opacity-toggle, geojson-filter-sublayers, url-state-layer-keys]
key_files:
  created:
    - frontend/components/map/WmsOverlayLayer.tsx
    - frontend/components/map/WaterLayer.tsx
    - frontend/components/sidebar/WaterLegend.tsx
  modified:
    - frontend/components/map/MapView.tsx
    - frontend/components/sidebar/Sidebar.tsx
    - frontend/app/page.tsx
decisions:
  - "WmsOverlayLayer uses raster-opacity: 0 (not layout visibility: none) so tiles stay loaded during toggle — prevents re-fetch on every show/hide"
  - "WaterLayer uses 3 filtered sub-layers sharing one GeoJSON source, filtered by source_id prefix (pegelonline/naturschutz/wasserschutz)"
  - "lubwEnv toggle controls naturschutz/wasserschutz sub-layers via lubwEnvVisible prop; water toggle controls gauge stations independently"
metrics:
  duration_seconds: 230
  completed_date: "2026-04-06"
  tasks_completed: 2
  files_changed: 6
---

# Phase 06 Plan 04: Frontend Water/WMS Layers Summary

**One-liner:** 4 new toggleable map layers (water gauges, flood hazard WMS, railway noise WMS, LUBW protection zones) wired through Sidebar toggles and URL state.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | WmsOverlayLayer + WaterLayer + WaterLegend | 7402b42 | WmsOverlayLayer.tsx, WaterLayer.tsx, WaterLegend.tsx |
| 2 | MapView + Sidebar + page.tsx wiring | d8daede | MapView.tsx, Sidebar.tsx, page.tsx |

## What Was Built

### WmsOverlayLayer.tsx
Reusable WMS raster overlay component. Accepts `id`, `wmsUrl`, `layers`, `visible`, and optional `opacity`. Uses `raster-opacity` (0 or target value) instead of `layout.visibility` so MapLibre keeps tiles loaded in the tile cache when toggled off — prevents re-fetching on every toggle cycle.

Two instances added to MapView:
- Flood hazard (LUBW HQ100 + USG): `https://rips-gdi.lubw.baden-wuerttemberg.de/...`, layers `0,1`, opacity `0.65`
- Railway noise (EBA Lden): `https://geoinformation.eisenbahn-bundesamt.de/wms/isophonen`, layers `isophonen_ek_lden`, opacity `0.6`

### WaterLayer.tsx
Single GeoJSON source `water-features` with 4 sub-layers:
- `water-gauges`: pegelonline stations — blue (#1565C0), radius 8, interactive (popup support)
- `water-labels`: text labels showing `level_cm` + "cm" for gauge stations
- `water-naturschutz`: nature protection zones — green (#2E7D32), radius 6
- `water-wasserschutz`: water protection zones — teal (#00796B), radius 6

Sub-layers are independently controlled: `visible` prop gates gauge/label layers; `lubwEnvVisible` prop additionally gates the protection zone layers.

### WaterLegend.tsx
Three-item legend with colored dot + label, matching TransitLegend pattern. Rendered conditionally in Sidebar when `layerVisibility.water` is true.

### MapView.tsx Extensions
- `LayerVisibility` type extended: `water`, `floodHazard`, `railNoise`, `lubwEnv`
- `waterData?: LayerResponse | null` and `waterLastFetched?: Date | null` props added
- `water-gauges` added to `interactiveLayerIds` for popup click support
- Click handler updated: layer IDs starting with `water` map to `domain: 'water'`

### Sidebar.tsx Extensions
6 total layer toggles (was 2):
- Existing: "ÖPNV (Bus & Bahn)", "Luftqualität"
- New: "Pegel & Gewässer", "Hochwassergefahr (HQ100)", "Bahnlärm (Lden)", "Schutzgebiete (LUBW)"

### page.tsx Extensions
`layerVisibility` derives 6 booleans from URL `layers` param:
- `transit` ← `'transit'`
- `airQuality` ← `'aqi'`
- `water` ← `'water'`
- `floodHazard` ← `'flood'`
- `railNoise` ← `'rail_noise'`
- `lubwEnv` ← `'lubw_env'`

`LAYER_KEYS` map drives `toggleLayer` to encode/decode all 6 keys. `useLayerData('water', ...)` hook added; data passed to MapView.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all layer props are fully wired from URL state through data hooks to map components.

## Self-Check: PASSED
