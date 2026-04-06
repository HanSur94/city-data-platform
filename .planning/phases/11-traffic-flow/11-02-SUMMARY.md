---
phase: 11-traffic-flow
plan: 02
subsystem: ui
tags: [maplibre, react-map-gl, traffic, tomtom, geojson, line-layer]

requires:
  - phase: 11-01
    provides: TomTom traffic flow connector producing GeoJSON LineString features with congestion_ratio
provides:
  - TrafficFlowLayer component rendering TomTom road segments as colored lines
  - TrafficFlowPopup component for segment detail display
  - Sidebar toggle for traffic flow layer (Verkehrsfluss)
  - Traffic flow legend with 4 color bands
affects: [traffic, map-layers]

tech-stack:
  added: []
  patterns: [line-layer-with-data-driven-color, feature-filtering-by-data-source]

key-files:
  created:
    - frontend/components/map/TrafficFlowLayer.tsx
    - frontend/components/map/TrafficFlowPopup.tsx
  modified:
    - frontend/components/map/MapView.tsx
    - frontend/components/sidebar/Sidebar.tsx
    - frontend/components/sidebar/TrafficLegend.tsx
    - frontend/app/page.tsx

key-decisions:
  - "Separate source ID 'traffic-flow' to avoid conflict with existing 'traffic' source for BASt circles"
  - "traffic-flow-lines click check placed BEFORE generic traffic startsWith check to avoid false match"

patterns-established:
  - "Line layer pattern: LineLayerSpecification with interpolated color ramp based on numeric property"
  - "Feature source filtering: filterTomTomFeatures filters shared /api/layers/traffic data by data_source property"

requirements-completed: [REQ-TRAFFIC-02, REQ-TRAFFIC-05]

duration: 2min
completed: 2026-04-06
---

# Phase 11 Plan 02: Traffic Flow Frontend Layer Summary

**MapLibre line layer rendering TomTom road segments with congestion-ratio color ramp (green/yellow/orange/red), sidebar toggle, click popup, and flow legend**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-06T20:49:53Z
- **Completed:** 2026-04-06T20:52:05Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- TrafficFlowLayer renders TomTom road segments as colored lines with data-driven congestion_ratio color ramp
- TrafficFlowPopup displays road name, speed, freeflow speed, congestion ratio, and confidence in German
- Sidebar toggle "Verkehrsfluss (TomTom)" in Verkehr section with independent control
- TrafficLegend extended with flow-specific legend showing 4 color bands with percentage thresholds
- Layer coexists with existing BASt TrafficLayer using separate source ID

## Task Commits

Each task was committed atomically:

1. **Task 1: Create TrafficFlowLayer and TrafficFlowPopup components** - `e5785c6` (feat)
2. **Task 2: Wire TrafficFlowLayer into MapView, Sidebar, and page state** - `381ccc2` (feat)

## Files Created/Modified
- `frontend/components/map/TrafficFlowLayer.tsx` - MapLibre line layer with congestion-ratio color interpolation, TomTom feature filtering
- `frontend/components/map/TrafficFlowPopup.tsx` - Popup showing road name, speed, freeflow, ratio, confidence in German
- `frontend/components/map/MapView.tsx` - Added TrafficFlowLayer rendering, interactive layer ID, popup domain routing
- `frontend/components/sidebar/Sidebar.tsx` - Added Verkehrsfluss toggle in Verkehr section
- `frontend/components/sidebar/TrafficLegend.tsx` - Added TRAFFIC_FLOW_LEGEND with 4 color bands and line indicators
- `frontend/app/page.tsx` - Added trafficFlow to layer visibility state and MapView prop pass-through

## Decisions Made
- Used separate source ID 'traffic-flow' to avoid conflict with existing 'traffic' source used by BASt circle layer
- Placed traffic-flow-lines click check before generic `layerId.startsWith('traffic')` to prevent false domain match

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Traffic flow visualization complete and toggleable independently from BASt count stations
- TomTom API key still needed for backend connector (documented in 11-01)

---
*Phase: 11-traffic-flow*
*Completed: 2026-04-06*

## Self-Check: PASSED
