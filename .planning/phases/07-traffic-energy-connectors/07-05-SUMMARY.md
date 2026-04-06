---
phase: 07-traffic-energy-connectors
plan: 05
subsystem: ui
tags: [react, maplibre, react-map-gl, typescript, traffic, energy, map-layers]

requires:
  - phase: 07-04
    provides: API routers for traffic and energy domains, useLayerData hook support

provides:
  - TrafficLayer component: BASt/MobiData traffic circles colored green/yellow/red by congestion
  - AutobahnLayer component: roadwork/closure symbol markers (⚠ orange / ✗ red)
  - EnergyLayer component: clustered MaStR renewable installations colored by type
  - TrafficPopup component: shows Kfz/h, SV/h, speed, congestion badge
  - AutobahnPopup component: shows Baustelle/Sperrung type, detour, blocked status
  - EnergyPopup component: shows Solaranlage/Windkraftanlage/Batteriespeicher, capacity kW
  - MapView updated with trafficVisible/autobahnVisible/energyVisible props

affects:
  - page.tsx (will need to pass new visibility props to MapView)
  - dashboard layer toggles

tech-stack:
  added: []
  patterns:
    - "TrafficLayer/AutobahnLayer share same useLayerData('traffic') source, filter features by type property"
    - "EnergyLayer follows TransitLayer clustering pattern (cluster=true, clusterMaxZoom=10, clusterRadius=50)"
    - "MapView popup routing: layerId prefix determines domain which selects popup component"
    - "New layers pass town+visible+timestamp props; useLayerData called internally"

key-files:
  created:
    - frontend/components/map/TrafficLayer.tsx
    - frontend/components/map/AutobahnLayer.tsx
    - frontend/components/map/TrafficPopup.tsx
    - frontend/components/map/AutobahnPopup.tsx
    - frontend/components/map/EnergyLayer.tsx
    - frontend/components/map/EnergyPopup.tsx
  modified:
    - frontend/components/map/MapView.tsx

key-decisions:
  - "TrafficLayer and AutobahnLayer both use useLayerData('traffic') and split features by properties.type (roadwork/closure go to Autobahn)"
  - "MapView popup routing extended via layerId prefix matching for traffic/autobahn/energy domains"
  - "EnergyLayer uses cluster=true, clusterMaxZoom=10 — dissolves at zoom>=11 as specified"

patterns-established:
  - "Layer components own their data fetching via useLayerData — no data props required from parent"
  - "Two layers sharing same data domain: each calls useLayerData independently, each filters to its subset"

requirements-completed:
  - TRAF-03
  - TRAF-04
  - TRAF-05
  - ENRG-02

duration: 4min
completed: 2026-04-06
---

# Phase 07 Plan 05: Traffic and Energy Map Layers Summary

**6 map layer/popup components for traffic circles (BASt/MobiData), Autobahn roadwork markers, and clustered MaStR renewable installations, all wired into MapView with domain-routed popups**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-06T17:56:16Z
- **Completed:** 2026-04-06T17:59:40Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- TrafficLayer renders BASt/MobiData circles: green (free), yellow (moderate), red (congested) with radius scaled to vehicle count
- AutobahnLayer renders roadwork (⚠ orange) and closure (✗ red) symbol markers from same traffic data source
- EnergyLayer renders clustered MaStR installations: solar rooftop amber, solar ground yellow, wind blue, battery green
- Popup system extended: TrafficPopup shows Kfz/h + SV/h + speed, AutobahnPopup shows Baustelle/Sperrung + detour, EnergyPopup shows type label + kW capacity
- MapView extended with new props and layer renders, TypeScript compiles clean

## Task Commits

1. **Task 1: TrafficLayer + AutobahnLayer + popups** - `7e515a5` (feat)
2. **Task 2: EnergyLayer + popup + MapView wiring** - `bb12f32` (feat)

**Plan metadata:** (to be added by final commit)

## Files Created/Modified

- `frontend/components/map/TrafficLayer.tsx` - BASt/MobiData traffic circles with congestion color + vehicle count radius
- `frontend/components/map/AutobahnLayer.tsx` - Autobahn roadwork/closure symbol markers via SymbolLayerSpecification
- `frontend/components/map/TrafficPopup.tsx` - Traffic feature popup: station name, Kfz/h, SV/h, speed, congestion badge
- `frontend/components/map/AutobahnPopup.tsx` - Autobahn popup: Baustelle/Sperrung label, detour extent, blocked status badge
- `frontend/components/map/EnergyLayer.tsx` - Clustered MaStR installations with energy type colors
- `frontend/components/map/EnergyPopup.tsx` - Energy popup: Solaranlage/Windkraftanlage/Batteriespeicher, capacity kW, commissioning year
- `frontend/components/map/MapView.tsx` - Added TrafficLayer, AutobahnLayer, EnergyLayer imports and conditional renders; extended popup routing

## Decisions Made

- TrafficLayer and AutobahnLayer both fetch useLayerData('traffic') independently and filter by properties.type — avoids a shared data wrapper component, keeps each layer self-contained
- MobiData BW data comes through the same 'traffic' domain as BASt — no separate MobiDataLayer needed
- MapView popup routing extends the existing layerId-prefix pattern for 3 new domains

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- node_modules not present in git worktree — symlinked from main project directory to run TypeScript checks. Not a code issue.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 3 new map layers are implemented and wired into MapView
- page.tsx will need to pass trafficVisible/autobahnVisible/energyVisible props to MapView to activate layers from UI toggles
- Layer toggle UI components (sidebar/panel) will need the new visibility keys added

---
*Phase: 07-traffic-energy-connectors*
*Completed: 2026-04-06*
