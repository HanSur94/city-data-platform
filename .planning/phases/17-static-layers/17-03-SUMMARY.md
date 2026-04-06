---
phase: 17-static-layers
plan: 03
subsystem: ui
tags: [react, maplibre, geojson, heat-demand, cycling, react-map-gl]

requires:
  - phase: 17-static-layers
    provides: "Backend connectors for heat demand (KEA-BW) and cycling infrastructure (OSM)"
provides:
  - "HeatDemandLayer component rendering buildings by heat class (6-tier blue-to-red)"
  - "CyclingLayer component rendering road segments by infra type (5-tier green-to-red)"
  - "Popup components for heat demand and cycling with German labels"
  - "Sidebar legend components for heat demand and cycling"
  - "Full wiring: sidebar toggles, MapView rendering, popups, URL state persistence"
affects: [frontend-layers, map-view, sidebar]

tech-stack:
  added: []
  patterns:
    - "Custom fetch with source query param for cycling infrastructure (vs useLayerData)"
    - "Client-side feature_type filtering for heat demand within energy domain"

key-files:
  created:
    - frontend/components/map/HeatDemandLayer.tsx
    - frontend/components/map/HeatDemandPopup.tsx
    - frontend/components/map/CyclingLayer.tsx
    - frontend/components/map/CyclingPopup.tsx
    - frontend/components/sidebar/CyclingLegend.tsx
    - frontend/components/sidebar/HeatDemandLegend.tsx
  modified:
    - frontend/components/sidebar/Sidebar.tsx
    - frontend/components/map/MapView.tsx
    - frontend/app/page.tsx

key-decisions:
  - "CyclingLayer uses inline fetch with source=cycling query param instead of useLayerData (API supports source filtering)"
  - "HeatDemandLayer reuses useLayerData('energy') with client-side feature_type filtering"

patterns-established:
  - "Source query param pattern: /api/layers/infrastructure?source=cycling for domain sub-filtering"

requirements-completed: [REQ-HEAT-01, REQ-CYCLE-01]

duration: 3min
completed: 2026-04-06
---

# Phase 17 Plan 03: Heat Demand + Cycling Frontend Layers Summary

**Heat demand building coloring (6-tier blue-to-red by kWh/m2/a) and cycling infrastructure road segments (5-tier green-to-red by type) with popups, legends, and sidebar toggles**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-06T22:39:23Z
- **Completed:** 2026-04-06T22:42:30Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- HeatDemandLayer renders energy building features as colored circles using match expression on heat_class property
- CyclingLayer renders infrastructure road segments as colored lines using match expression on infra_type property
- Both layers have popups with German labels, source attribution, and colored badges
- Sidebar toggles added under Energie (Waermebedarf) and Verkehr (Radinfrastruktur) sections
- Legends show when layers are active, URL params persist visibility state

## Task Commits

Each task was committed atomically:

1. **Task 1: HeatDemandLayer + CyclingLayer components with popups and legends** - `c706e58` (feat)
2. **Task 2: Wire HeatDemand + Cycling into Sidebar + MapView + page.tsx** - `6278157` (feat)

## Files Created/Modified
- `frontend/components/map/HeatDemandLayer.tsx` - Circle layer rendering buildings by heat_class with 6-color scheme
- `frontend/components/map/HeatDemandPopup.tsx` - Popup showing kWh/m2/a value and heat class badge
- `frontend/components/map/CyclingLayer.tsx` - Line layer rendering road segments by infra_type with 5-color scheme
- `frontend/components/map/CyclingPopup.tsx` - Popup showing road name and infra type with German labels
- `frontend/components/sidebar/CyclingLegend.tsx` - 5-entry legend for cycling infrastructure types
- `frontend/components/sidebar/HeatDemandLegend.tsx` - 6-entry legend for heat demand ranges in kWh/m2/a
- `frontend/components/sidebar/Sidebar.tsx` - Added heatDemand and cycling toggles and legends
- `frontend/components/map/MapView.tsx` - Added layer rendering, popup routing, interactive layer IDs
- `frontend/app/page.tsx` - Added heat_demand/cycling URL params and MapView prop wiring

## Decisions Made
- CyclingLayer uses inline fetch with source=cycling query param to leverage API source filtering instead of useLayerData
- HeatDemandLayer reuses useLayerData('energy') and filters client-side by feature_type='heat_demand'

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all components are fully wired to backend API endpoints.

## Next Phase Readiness
- All 5 Phase 17 static layers are now operational (road noise WMS, fernwaerme, demographics grid, heat demand, cycling)
- Phase 17 complete and ready for verification

---
*Phase: 17-static-layers*
*Completed: 2026-04-06*
