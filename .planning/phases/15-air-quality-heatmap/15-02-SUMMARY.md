---
phase: 15-air-quality-heatmap
plan: 02
subsystem: ui
tags: [maplibre, heatmap, air-quality, recharts, react, pollutant-toggle]

requires:
  - phase: 15-air-quality-heatmap
    provides: "AirQualityGridConnector with IDW interpolation, feature_type=air_grid filter on /layers/air_quality endpoint"
  - phase: 04-air-quality
    provides: "AQILayer sensor points, air_quality_readings timeseries data"
provides:
  - "AirQualityHeatmapLayer with IDW grid overlay and WHO-based color ramp"
  - "Pollutant toggle UI (PM2.5/PM10/NO2/O3) in sidebar"
  - "SensorPopupChart with 24h time-series on sensor click"
  - "Pulsing glow effect on sensor dots"
affects: [15-air-quality-heatmap]

tech-stack:
  added: []
  patterns: ["heatmap layer with dynamic paint expression rebuild on pollutant change", "separate GeoJSON source for grid vs sensor points", "inline popup chart with useTimeseries hook"]

key-files:
  created:
    - frontend/components/map/AirQualityHeatmapLayer.tsx
    - frontend/components/map/SensorPopupChart.tsx
    - frontend/components/sidebar/PollutantToggle.tsx
    - frontend/hooks/useGridLayerData.ts
  modified:
    - frontend/components/map/AQILayer.tsx
    - frontend/components/map/MapView.tsx
    - frontend/components/sidebar/Sidebar.tsx
    - frontend/app/page.tsx
    - frontend/lib/api.ts

key-decisions:
  - "MapLibre heatmap layer type for grid overlay with heatmap-weight driven by active pollutant value"
  - "Separate air-quality-grid source ID to avoid conflict with existing air-quality sensor source"
  - "WHO guideline thresholds for pollutant value normalization to 0-1 heatmap weight"
  - "Pulsing effect via secondary circle layer with blur rather than CSS animation (MapLibre limitation)"

patterns-established:
  - "Dynamic paint expression rebuild: useMemo to regenerate layer spec when pollutant changes"
  - "fetchGridLayer with feature_type param for filtered GeoJSON fetching"

requirements-completed: [REQ-AIR-02, REQ-AIR-03, REQ-AIR-04, REQ-AIR-05]

duration: 4min
completed: 2026-04-06
---

# Phase 15 Plan 02: Air Quality Heatmap Frontend Summary

**MapLibre heatmap grid overlay with WHO-based green-to-purple color ramp, pollutant toggle (PM2.5/PM10/NO2/O3), pulsing sensor dots, and 24h time-series popup chart on sensor click**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-06T22:01:40Z
- **Completed:** 2026-04-06T22:05:39Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- AirQualityHeatmapLayer rendering IDW grid cells as translucent MapLibre heatmap with green/yellow/orange/red/purple ramp (REQ-AIR-02)
- Pollutant toggle pill buttons in sidebar switching between PM2.5/PM10/NO2/O3 with dynamic layer expression rebuild (REQ-AIR-03)
- Pulsing glow effect on sensor dots via secondary circle layer with blur and reduced opacity (REQ-AIR-04)
- SensorPopupChart showing 24h Recharts line chart for PM2.5/PM10 when clicking sensor dot (REQ-AIR-05)

## Task Commits

Each task was committed atomically:

1. **Task 1: AirQualityHeatmapLayer with pollutant toggle and pulsing sensors** - `4340f6f` (feat)
2. **Task 2: MapView wiring, pollutant toggle UI, and sensor popup chart** - `1c52188` (feat)

## Files Created/Modified
- `frontend/components/map/AirQualityHeatmapLayer.tsx` - Heatmap grid overlay with WHO-based pollutant normalization and color ramp
- `frontend/components/map/SensorPopupChart.tsx` - Compact 24h Recharts line chart for sensor click popup
- `frontend/components/sidebar/PollutantToggle.tsx` - Pill-style toggle buttons for PM2.5/PM10/NO2/O3
- `frontend/hooks/useGridLayerData.ts` - Hook for fetching grid layer data with feature_type filter
- `frontend/components/map/AQILayer.tsx` - Added pulsing glow ring layer behind sensor dots
- `frontend/components/map/MapView.tsx` - Wired AirQualityHeatmapLayer, SensorPopupChart, new props
- `frontend/components/sidebar/Sidebar.tsx` - Added PollutantToggle below AQI layer toggle
- `frontend/app/page.tsx` - Added activePollutant state, grid data fetch, prop passing
- `frontend/lib/api.ts` - Added fetchGridLayer function with feature_type parameter

## Decisions Made
- Used MapLibre heatmap layer type with heatmap-weight driven by pollutant value -- creates smooth translucent overlay naturally
- Separate source ID (air-quality-grid) from existing air-quality source to avoid layer conflicts
- WHO guideline thresholds (PM2.5: 0-15-30-55-75, PM10: 0-45-90-180-250, etc.) for normalizing values to heatmap weight
- Pulsing effect via circle-blur and secondary translucent circle layer since MapLibre does not support CSS keyframes on layers

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed TypeScript type narrowing in popup domain check**
- **Found during:** Task 2
- **Issue:** After adding airQuality-specific popup branch, the fallthrough ternary for FeaturePopup still checked `popupInfo.domain === 'airQuality'` which TypeScript correctly flagged as impossible
- **Fix:** Removed the dead airQuality branch from the FeaturePopup lastFetched ternary
- **Files modified:** frontend/components/map/MapView.tsx
- **Committed in:** 1c52188 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Trivial fix for TypeScript strictness. No scope creep.

## Issues Encountered
None.

## User Setup Required
None -- no external service configuration required.

## Next Phase Readiness
- Air quality heatmap fully functional with pollutant switching and interactive sensor popups
- Phase 15 (air quality heatmap) complete -- both backend grid computation and frontend visualization done

---
*Phase: 15-air-quality-heatmap*
*Completed: 2026-04-06*
