---
phase: 08-community-infrastructure-connectors
plan: "03"
subsystem: frontend
tags: [map, layers, popups, sidebar, community, infrastructure]
dependency_graph:
  requires: [08-01, 08-02]
  provides: [community-layer-ui, infrastructure-layer-ui, ev-charging-ui, roadworks-ui, solar-potential-ui]
  affects: [frontend/components/map/MapView.tsx, frontend/components/sidebar/Sidebar.tsx, frontend/app/page.tsx]
tech_stack:
  added: []
  patterns: [react-map-gl Source/Layer clustering, client-side GeoJSON filtering, WMS overlay toggle]
key_files:
  created:
    - frontend/components/map/CommunityLayer.tsx
    - frontend/components/map/InfrastructureLayer.tsx
    - frontend/components/map/CommunityPopup.tsx
    - frontend/components/map/EvChargingPopup.tsx
    - frontend/components/map/RoadworksPopup.tsx
  modified:
    - frontend/components/map/MapView.tsx
    - frontend/components/sidebar/Sidebar.tsx
    - frontend/app/page.tsx
decisions:
  - "CommunityLayer renders conditional sub-Sources per category (not a single Source) to allow independent toggling without re-fetching data"
  - "InfrastructureLayer always renders WmsOverlayLayer for solar potential with visible=false rather than conditional rendering, avoiding mount/unmount tile re-fetch cycles"
  - "toggleLayer function typed as keyof typeof LAYER_KEYS — automatically extends when new keys are added to LAYER_KEYS record"
metrics:
  duration_minutes: 4
  completed_date: "2026-04-06"
  tasks_completed: 2
  files_changed: 8
requirements: [COMM-01, COMM-02, COMM-03, COMM-04, INFR-01, INFR-02, INFR-03, INFR-04]
---

# Phase 8 Plan 03: Frontend Layer Components and Wiring Summary

**One-liner:** 5 new map components (2 layer renderers + 3 popups) with clustered GeoJSON sub-layers, German-labeled popups, and full sidebar/URL state wiring for all 8 community and infrastructure requirements.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Layer components + popup components | 0d92bc4 | CommunityLayer.tsx, InfrastructureLayer.tsx, CommunityPopup.tsx, EvChargingPopup.tsx, RoadworksPopup.tsx |
| 2 | MapView + Sidebar + page.tsx wiring | 7bfca80 | MapView.tsx, Sidebar.tsx, page.tsx |

## What Was Built

### CommunityLayer.tsx
Fetches community domain data once via `useLayerData('community', town)`, then client-side filters into 4 category sub-layers. Each sub-layer (schools, healthcare, parks, waste) conditionally mounts its own `<Source>` + cluster + count + points `<Layer>` trio only when its visibility prop is true. Colors: schools #3b82f6, healthcare #ef4444, parks #22c55e, waste #92400e.

### InfrastructureLayer.tsx
Fetches infrastructure domain data via `useLayerData('infrastructure', town)`. Renders EV charging (category=ev_charging, #a855f7) and roadworks (category=roadwork, #f97316) as clustered layers, plus WmsOverlayLayer for solar potential WMS with graceful deferral (opacity toggle pattern, no error boundary needed).

### Popup Components
- **CommunityPopup**: German category mapping (school→Schule/Kita, healthcare→Gesundheit, park→Park/Spielplatz, waste→Wertstoffhof), shows name, address, opening hours
- **EvChargingPopup**: operator, address, charging type (Normalladen/Schnellladen), plug types, max power kW, charging points count with German labels
- **RoadworksPopup**: name with "Baustelle" default, note/description, "Baustelle (OSM)" category label

### MapView.tsx Updates
- 7 new optional visibility props (schoolsVisible, healthcareVisible, parksVisible, wasteVisible, evChargingVisible, roadworksVisible, solarPotentialVisible)
- CommunityLayer and InfrastructureLayer rendered inside Map
- interactiveLayerIds extended with 6 new point layer IDs
- onClick routing extended: community-* points → CommunityPopup, infrastructure-ev-points → EvChargingPopup, infrastructure-roadworks-points → RoadworksPopup

### Sidebar.tsx Updates
- onToggleLayer union type extended with 7 new layer keys
- Gemeinwesen group (Schulen & Kitas, Gesundheit, Parks & Spielplaetze, Wertstoffhoefe)
- Infrastruktur group (Baustellen, E-Ladesaeulen, Solarpotenzial Daecher)

### page.tsx Updates
- 7 new keys in layerVisibility object (URL params: schools, healthcare, parks, waste, ev_charging, roadworks, solar_potential)
- 7 new entries in LAYER_KEYS record
- 7 new visibility props passed to MapView

## Verification

TypeScript: compiles without errors (`tsc --noEmit` exits 0).

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all layers are wired to real API endpoints via useLayerData.

## Self-Check: PASSED

Files verified:
- frontend/components/map/CommunityLayer.tsx — FOUND
- frontend/components/map/InfrastructureLayer.tsx — FOUND
- frontend/components/map/CommunityPopup.tsx — FOUND
- frontend/components/map/EvChargingPopup.tsx — FOUND
- frontend/components/map/RoadworksPopup.tsx — FOUND

Commits verified:
- 0d92bc4 — Task 1 (5 new components)
- 7bfca80 — Task 2 (3 modified files)
