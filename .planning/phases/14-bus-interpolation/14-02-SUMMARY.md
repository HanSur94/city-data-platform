---
phase: 14-bus-interpolation
plan: 02
subsystem: ui
tags: [maplibre, react, bus, transit, geojson, realtime, visualization]

requires:
  - phase: 14-bus-interpolation
    provides: "BusInterpolationConnector producing bus_position features via /api/layers/transit"
  - phase: 05-transit
    provides: "Transit layer, useLayerData hook, fetchLayer API"
provides:
  - "BusPositionLayer component with delay-based colored circles and 30s refresh"
  - "BusRouteLayer component showing faint GTFS route shapes"
  - "BusPopup component with line number, destination, delay, next stop"
  - "Bus-Positionen (live) sidebar toggle wired to URL state"
affects: []

tech-stack:
  added: []
  patterns: ["Inline fetch with useState+useEffect for custom poll interval (30s vs default 60s)", "Separate GeoJSON source IDs to avoid interference with existing transit source"]

key-files:
  created:
    - frontend/components/map/BusPositionLayer.tsx
    - frontend/components/map/BusRouteLayer.tsx
    - frontend/components/map/BusPopup.tsx
  modified:
    - frontend/components/map/MapView.tsx
    - frontend/components/sidebar/Sidebar.tsx
    - frontend/app/page.tsx

key-decisions:
  - "Used inline fetchLayer with 30s setInterval instead of useLayerData (hardcoded at 60s) for bus position refresh"
  - "Separate source IDs bus-positions and bus-routes to avoid interference with existing transit Source"
  - "Show all transit shapes as faint route lines when bus layer active (simpler than route-matching)"

patterns-established:
  - "Custom poll interval pattern: bypass useLayerData with direct fetchLayer + setInterval for non-standard refresh rates"

requirements-completed: [REQ-BUS-02, REQ-BUS-03, REQ-BUS-04, REQ-BUS-06]

duration: 3min
completed: 2026-04-06
---

# Phase 14 Plan 02: Bus Frontend Visualization Summary

**MapLibre bus position layer with delay-colored dots, faint route lines, click popup showing line/destination/delay/next-stop, and 30s live refresh**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-06T21:45:15Z
- **Completed:** 2026-04-06T21:48:16Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- BusPositionLayer renders colored circles (green/yellow/orange/red) based on delay thresholds with line name labels
- BusRouteLayer shows faint indigo GTFS shape polylines when bus layer is active
- BusPopup displays "Linie X", "Richtung Y", delay text with matching color, and next stop name
- Full wiring: sidebar toggle, URL state persistence (bus_position key), MapView click routing, popup rendering

## Task Commits

Each task was committed atomically:

1. **Task 1: BusPositionLayer, BusRouteLayer, and BusPopup components** - `a2a2823` (feat)
2. **Task 2: Wire bus components into MapView, Sidebar, and page state** - `96b1e63` (feat)

## Files Created/Modified
- `frontend/components/map/BusPositionLayer.tsx` - Colored bus dots with 30s refresh, delay-based step color expression
- `frontend/components/map/BusRouteLayer.tsx` - Faint indigo route shapes from transit layer shapes
- `frontend/components/map/BusPopup.tsx` - Bus click popup with line, destination, delay, next stop
- `frontend/components/map/MapView.tsx` - Bus layer rendering, click routing, popup dispatch
- `frontend/components/sidebar/Sidebar.tsx` - "Bus-Positionen (live)" toggle in Ebenen section
- `frontend/app/page.tsx` - busPosition layer key in URL state and visibility map

## Decisions Made
- Used inline fetchLayer with useState/useEffect and 30s setInterval instead of useLayerData hook (which has hardcoded 60s interval) to meet REQ-BUS-06 requirement for 30s bus position updates
- Created separate GeoJSON source IDs (bus-positions, bus-routes) to avoid interfering with the existing clustered transit Source
- Show all transit shapes as faint route lines when bus layer is active rather than matching active routes -- simpler and still useful for orientation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Bus frontend visualization complete
- All Phase 14 plans (01 + 02) done: backend interpolation engine + frontend visualization
- Bus positions visible on map with delay coloring, route lines, and click popup
- Ready for subsequent phases

## Known Stubs
None - all components are fully implemented with real data wiring.

---
*Phase: 14-bus-interpolation*
*Completed: 2026-04-06*
