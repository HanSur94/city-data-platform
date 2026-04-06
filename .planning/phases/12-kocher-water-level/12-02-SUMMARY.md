---
phase: 12-kocher-water-level
plan: 02
subsystem: ui
tags: [react, recharts, maplibre, water-level, kocher, dashboard, map-layer]

requires:
  - phase: 12-kocher-water-level
    provides: "WaterKPI type, /api/kpi water field, /api/layers/water LHP features"
provides:
  - "KocherGaugeWidget with color-coded bar, trend, sparkline, warning badge"
  - "KocherLayer with gauge pin and river line colored by warning stage"
  - "KocherPopup with German labels for gauge details"
  - "Sidebar toggle for Kocher Pegel (LHP)"
  - "Water legend with stage color scale"
affects: []

tech-stack:
  added: []
  patterns: ["Stage-based color expressions for map layers", "Separate GeoJSON source for domain-specific filtering"]

key-files:
  created:
    - frontend/components/dashboard/KocherGaugeWidget.tsx
    - frontend/components/map/KocherLayer.tsx
    - frontend/components/map/KocherPopup.tsx
  modified:
    - frontend/components/dashboard/DashboardPanel.tsx
    - frontend/components/map/MapView.tsx
    - frontend/components/sidebar/Sidebar.tsx
    - frontend/components/sidebar/WaterLegend.tsx
    - frontend/app/page.tsx

key-decisions:
  - "Separate kocher-features source to avoid interfering with existing water-features source"
  - "Static GeoJSON LineString for Kocher river path rather than fetching from API"
  - "River line color derived from first LHP feature stage rather than data-driven expression"

patterns-established:
  - "Stage-based coloring: step expression on warning stage property for circle and line layers"
  - "Separate source pattern: domain-specific filtering via separate GeoJSON source ID"

requirements-completed: [REQ-KOCHER-02, REQ-KOCHER-03, REQ-KOCHER-04, REQ-KOCHER-05]

duration: 2min
completed: 2026-04-06
---

# Phase 12 Plan 02: Kocher Frontend Summary

**Kocher water level dashboard widget with color-coded bar, trend, sparkline, warning badge, plus map layer with gauge pin and river line colored by warning stage**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-06T21:09:01Z
- **Completed:** 2026-04-06T21:11:55Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- KocherGaugeWidget displays current cm with color-coded bar (green/yellow/orange/red thresholds), trend direction in German, 7-day sparkline via useTimeseries, and warning badge for stage >= 1
- KocherLayer renders gauge pin with stage-based coloring and Kocher river line with dynamic color matching warning stage
- KocherPopup shows station name, river, Wasserstand, Abfluss, Warnstufe badge, Trend in German
- Full wiring into page state, sidebar toggle, dashboard panel, map popup routing, and water legend

## Task Commits

Each task was committed atomically:

1. **Task 1: Create KocherGaugeWidget, KocherLayer, and KocherPopup components** - `97b231b` (feat)
2. **Task 2: Wire KocherGaugeWidget and KocherLayer into page, sidebar, and dashboard** - `b1ecc20` (feat)

## Files Created/Modified
- `frontend/components/dashboard/KocherGaugeWidget.tsx` - Kocher gauge widget with level, color bar, trend, sparkline, warning badge
- `frontend/components/map/KocherLayer.tsx` - Map layer with gauge pin (stage-colored) and river line
- `frontend/components/map/KocherPopup.tsx` - Popup for gauge pin click with German labels
- `frontend/components/dashboard/DashboardPanel.tsx` - Added KocherGaugeWidget rendering when water data available
- `frontend/components/map/MapView.tsx` - Added KocherLayer, KocherPopup, interactive layer IDs, popup routing
- `frontend/components/sidebar/Sidebar.tsx` - Added Kocher Pegel (LHP) toggle
- `frontend/components/sidebar/WaterLegend.tsx` - Added Kocher stage color scale legend
- `frontend/app/page.tsx` - Added kocher layer key and kocherVisible prop

## Decisions Made
- Used separate `kocher-features` source ID to avoid interfering with existing `water-features` source used by WaterLayer
- Used static GeoJSON LineString for the Kocher river path (approximate coordinates from Oberkochen through Aalen to Huettlingen)
- Derived river line color from the first LHP feature's stage property rather than a MapLibre data-driven expression (since river line is in a separate source without stage data)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Kocher frontend complete with all visual indicators
- No blockers for subsequent phases

---
*Phase: 12-kocher-water-level*
*Completed: 2026-04-06*
