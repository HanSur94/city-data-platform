---
phase: 17-static-layers
plan: 02
subsystem: ui
tags: [wms, maplibre, react-map-gl, zensus, lubw, fernwaerme, choropleth]

# Dependency graph
requires:
  - phase: 17-static-layers
    provides: WmsOverlayLayer component pattern for WMS overlays
provides:
  - NoiseWmsLayer for LUBW road noise LDEN/LNight WMS overlay
  - FernwaermeLayer for Aalen district heating coverage polygons
  - DemographicsGridLayer for Zensus 2022 100m grid WMS choropleth
  - DemographicsPopup for census data display
  - Sidebar toggles for all three new layers with sub-metric controls
affects: [18-polish, frontend-map-layers]

# Tech tracking
tech-stack:
  added: []
  patterns: [WMS metric toggle via dual WmsOverlayLayer instances, hardcoded GeoJSON polygons for known coverage areas, sub-toggle buttons in sidebar for metric selection]

key-files:
  created:
    - frontend/components/map/NoiseWmsLayer.tsx
    - frontend/components/map/FernwaermeLayer.tsx
    - frontend/components/map/DemographicsGridLayer.tsx
    - frontend/components/map/DemographicsPopup.tsx
  modified:
    - frontend/components/sidebar/Sidebar.tsx
    - frontend/components/map/MapView.tsx
    - frontend/app/page.tsx

key-decisions:
  - "Dual WmsOverlayLayer instances for LDEN/LNight to avoid tile reload on metric toggle"
  - "Zensus 2022 WMS for demographics grid instead of point data from backend"
  - "Hardcoded rectangle polygons for 4 known Aalen Fernwaerme coverage areas"

patterns-established:
  - "Sub-toggle buttons: inline button row below LayerToggle for metric selection (LDEN/LNight, population/age/rent/heating)"

requirements-completed: [REQ-NOISE-01, REQ-FERN-01, REQ-DEMO-01]

# Metrics
duration: 3min
completed: 2026-04-06
---

# Phase 17 Plan 02: Static Layers Frontend Summary

**LUBW road noise WMS with LDEN/LNight toggle, Fernwaerme coverage polygons, and Zensus 2022 demographics grid with metric selection -- all sidebar-toggleable**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-06T22:33:59Z
- **Completed:** 2026-04-06T22:37:23Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- Road noise WMS overlay with LDEN/LNight sub-toggle using dual WmsOverlayLayer instances
- Fernwaerme coverage layer with 4 hardcoded orange polygons for known Aalen neighborhoods
- Demographics grid layer using Zensus 2022 WMS with 4-metric selection (population, age, rent, heating)
- All three layers wired into Sidebar, MapView, and page.tsx with URL param persistence

## Task Commits

Each task was committed atomically:

1. **Task 1: NoiseWmsLayer + FernwaermeLayer components** - `0c0c603` (feat)
2. **Task 2: DemographicsGridLayer + DemographicsPopup** - `d6f2029` (feat)
3. **Task 3: Wire all three layers into Sidebar + MapView + page.tsx** - `fcb9474` (feat)

## Files Created/Modified
- `frontend/components/map/NoiseWmsLayer.tsx` - LUBW road noise WMS with LDEN/LNight toggle
- `frontend/components/map/FernwaermeLayer.tsx` - 4 Aalen Fernwaerme coverage polygons (Schlossaecker, Weisse Steige, Maiergasse/Talschule, Ostalbklinikum)
- `frontend/components/map/DemographicsGridLayer.tsx` - Zensus 2022 WMS grid with population/age/rent/heating metric
- `frontend/components/map/DemographicsPopup.tsx` - Census data popup (population, households, AGS)
- `frontend/components/sidebar/Sidebar.tsx` - Added roadNoise, fernwaerme, demographics toggles with sub-toggle buttons
- `frontend/components/map/MapView.tsx` - Renders three new layers conditionally, added demographics popup
- `frontend/app/page.tsx` - Added road_noise/fernwaerme/demographics URL params and metric state

## Decisions Made
- Used dual WmsOverlayLayer instances for LDEN/LNight to avoid tile reload on metric toggle (same pattern works for all WMS metric layers)
- Used Zensus 2022 WMS for demographics grid overlay instead of rendering backend point data as grid cells
- Hardcoded rectangle polygons for Fernwaerme coverage since data is static and known

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All three static layers complete and toggleable
- Ready for Phase 18 polish or verification

---
*Phase: 17-static-layers*
*Completed: 2026-04-06*

## Self-Check: PASSED
All 4 created files exist. All 3 task commits verified.
