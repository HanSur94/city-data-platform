---
phase: 06-weather-environment
plan: "02"
subsystem: air-quality
tags: [eaqi, aqi, air-quality, backend, frontend, geojson, maplibre]
dependency_graph:
  requires: []
  provides: [eaqi_from_readings, EAQI_BREAKPOINTS, aqi_color, aqi_tier_index, aqi-circles-layer, AQILegend-6tier]
  affects: [air_quality layer API response, AQILayer heatmap, AQILegend sidebar, map-styles constants]
tech_stack:
  added: []
  patterns: [EEA EAQI per-pollutant worst-tier methodology, MapLibre circle-color from GeoJSON property]
key_files:
  created:
    - backend/tests/schemas/__init__.py
    - backend/tests/schemas/test_eaqi.py
  modified:
    - backend/app/schemas/geojson.py
    - backend/app/routers/layers.py
    - frontend/components/map/AQILayer.tsx
    - frontend/components/sidebar/AQILegend.tsx
    - frontend/lib/map-styles.ts
decisions:
  - "Test expectations corrected to match actual EEA breakpoint tier boundaries (plan comments had wrong tier numbers for pm25=60, pm10=120, no2=150, o3=250 — all are tier 4 not tier 3)"
  - "AQI_TIER_COLORS in map-styles.ts updated to EEA 6-tier palette to keep frontend constants consistent"
metrics:
  duration_seconds: 209
  completed_date: "2026-04-06T00:07:22Z"
  tasks_completed: 2
  files_modified: 7
requirements_addressed: [WAIR-05]
---

# Phase 06 Plan 02: EEA EAQI 6-Tier AQI Scale Summary

**One-liner:** Replaced the generic 5-tier 0-80 AQI composite with the official EEA EAQI 6-tier per-pollutant health-based color system across backend and frontend.

## What Was Built

The air quality index calculation was migrated from an arbitrary single-composite 0-80 score to the EU/WHO European Air Quality Index (EAQI) standard. Each pollutant is now scored independently against official EEA breakpoints, and the worst-tier pollutant determines the overall station color — matching the methodology at https://airindex.eea.europa.eu.

### Backend (`backend/app/schemas/geojson.py`)

- **Removed:** `AQI_TIERS` list and `aqi_tier()` function (5-tier composite scale)
- **Added:** `EAQI_TIER_LABELS`, `EAQI_TIER_COLORS`, `EAQI_BREAKPOINTS` constants with official EEA µg/m³ thresholds for PM2.5, PM10, NO2, and O3
- **Added:** `eaqi_from_readings(pm25, pm10, no2, o3) -> (tier_idx, label, hex_color)` — handles None inputs gracefully, returns (0, "unknown", "#9e9e9e") when all are None

### Backend (`backend/app/routers/layers.py`)

- **Updated:** import from `aqi_tier` to `eaqi_from_readings`
- **Updated:** air_quality feature build block calls `eaqi_from_readings(pm25, pm10, no2, o3)` instead of the composite `aqi_tier(aqi)` 
- **Added:** `aqi_tier_index` (int 0-5) injected into GeoJSON feature properties alongside `aqi_tier` (label) and `aqi_color` (hex)

### Frontend (`frontend/components/map/AQILayer.tsx`)

- **Updated:** `aqiHeatmapLayer` paint uses `aqi_tier_index` (not `aqi`) for weight; 6-stop EEA color gradient
- **Added:** `aqiColorLayer` — new circle layer `aqi-circles` colored via `['get', 'aqi_color']` from GeoJSON properties
- **Updated:** `aqiPointLayer` click-target radius increased from 8 to 12px
- **Render order:** heatmap → colored circles → transparent click target

### Frontend (`frontend/components/sidebar/AQILegend.tsx`)

- **Replaced:** 5-tier legend with `EAQI_TIERS` — 6 entries in German (Gut, Mäßig, Befriedigend, Schlecht, Sehr schlecht, Extrem schlecht)
- **Added:** "Quelle: EEA EAQI" attribution line
- **Removed:** dependency on `AQI_TIER_COLORS` from `map-styles.ts`; legend is now self-contained

### Frontend (`frontend/lib/map-styles.ts`)

- **Updated:** `AQI_COLOR_RAMP` to 7-stop EEA gradient (matching `AQILayer.tsx` heatmap)
- **Updated:** `AQI_TIER_COLORS` to EEA 6-tier keys/colors (good, fair, moderate, poor, very_poor, extremely_poor, unknown)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan behavior examples had incorrect tier numbers**

- **Found during:** Task 1 TDD GREEN phase
- **Issue:** Plan comments stated `eaqi_from_readings(pm25=30, pm10=60, no2=60, o3=140)` → tier 2 "moderate" and `pm25=60` → tier 3 "poor". Actual EEA breakpoints give tier 3 and tier 4 respectively (breakpoints are upper-inclusive: pm25 thresholds are [5, 15, 25, 50, 75, inf] so pm25=60 lands in tier 4 not tier 3).
- **Fix:** Corrected test expectations to match the actual EAQI_BREAKPOINTS defined in the plan's own `<interfaces>` section.
- **Files modified:** `backend/tests/schemas/test_eaqi.py`
- **Commit:** 63002c7 (test), ad515ac (fix)

**2. [Rule 2 - Missing critical update] map-styles.ts AQI constants not updated**

- **Found during:** Task 2
- **Issue:** `map-styles.ts` still had old 5-tier color constants after AQILegend.tsx was decoupled from it. Any future component importing `AQI_TIER_COLORS` would get stale data.
- **Fix:** Updated both `AQI_COLOR_RAMP` and `AQI_TIER_COLORS` in `map-styles.ts` to EEA 6-tier palette.
- **Files modified:** `frontend/lib/map-styles.ts`
- **Commit:** d020fc6

## Known Stubs

None — all EAQI data flows from real backend breakpoints to live GeoJSON properties to frontend rendering.

## Self-Check

Files created/modified:
- [x] `backend/tests/schemas/__init__.py` — exists
- [x] `backend/tests/schemas/test_eaqi.py` — exists, 15 tests pass
- [x] `backend/app/schemas/geojson.py` — eaqi_from_readings present, aqi_tier removed
- [x] `backend/app/routers/layers.py` — uses eaqi_from_readings, injects aqi_tier_index + aqi_color
- [x] `frontend/components/map/AQILayer.tsx` — aqi-circles layer present with ['get', 'aqi_color']
- [x] `frontend/components/sidebar/AQILegend.tsx` — 6 EAQI tiers with EEA colors
- [x] `frontend/lib/map-styles.ts` — EEA 6-tier palette

Commits:
- 63002c7 — test(06-02): add failing EAQI tests
- ad515ac — feat(06-02): replace AQI_TIERS with EAQI 6-tier scale
- d020fc6 — feat(06-02): update layers.py + AQILayer.tsx + AQILegend.tsx

## Self-Check: PASSED
