---
phase: 18-data-transparency
plan: "02"
subsystem: frontend
tags: [data-transparency, sidebar, dashboard, popups, badges, metadata]
dependency_graph:
  requires: ["18-01"]
  provides: ["sidebar-badges", "kpi-footers", "popup-data-sources", "stale-detection"]
  affects: ["sidebar", "dashboard", "all-popups"]
tech_stack:
  added: []
  patterns: ["useLayerMetadata hook for freshness polling", "DataTypeBadge in sidebar toggles", "DataSourceSection in all popups"]
key_files:
  created:
    - frontend/hooks/useLayerMetadata.ts
  modified:
    - frontend/components/sidebar/LayerToggle.tsx
    - frontend/components/sidebar/Sidebar.tsx
    - frontend/components/dashboard/KpiTile.tsx
    - frontend/components/dashboard/DashboardPanel.tsx
    - frontend/components/map/TrafficFlowPopup.tsx
    - frontend/components/map/FeaturePopup.tsx
    - frontend/components/map/EnergyPopup.tsx
    - frontend/components/map/TrafficPopup.tsx
    - frontend/components/map/AutobahnPopup.tsx
    - frontend/components/map/CommunityPopup.tsx
    - frontend/components/map/RoadworksPopup.tsx
    - frontend/components/map/KocherPopup.tsx
    - frontend/components/map/ParkingPopup.tsx
    - frontend/components/map/BusPopup.tsx
    - frontend/components/map/EvChargingPopup.tsx
    - frontend/components/map/SolarPopup.tsx
    - frontend/components/map/HeatDemandPopup.tsx
    - frontend/components/map/CyclingPopup.tsx
    - frontend/components/map/DemographicsPopup.tsx
decisions:
  - "useLayerMetadata hook polls /api/metadata/layers every 60s with stale detection at 2x interval"
  - "CommunityPopup dynamically resolves layer key from category (school->schools, healthcare->healthcare, park->parks, waste->waste)"
  - "Layers without metadata entries (floodHazard, railNoise, lubwEnv, cadastral, hillshade, buildings3d) render without badges"
metrics:
  duration: "7m 30s"
  completed: "2026-04-06T23:02:30Z"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 20
---

# Phase 18 Plan 02: UI Data Transparency Wiring Summary

Sidebar badges + info popovers on all ~25 layers, KPI tile source footers, and DataSourceSection in all 15 popup components with stale data warning via useLayerMetadata hook

## What Was Done

### Task 1: Sidebar layer toggles with badges, info icon, stale warning, and useLayerMetadata hook (8842e1f)

Created `useLayerMetadata` hook that fetches `/api/metadata/layers?town=aalen` on mount with 60-second polling interval. The hook computes stale status by comparing `lastUpdated` against `2 * updateIntervalSeconds` from the static LAYER_METADATA registry.

Modified `LayerToggle` to accept optional `layerKey`, `dataType`, `isStale`, `metadata`, and `lastUpdated` props. When provided, it renders a colored `DataTypeBadge` next to the label, an orange `AlertTriangle` icon for stale data, and an `Info` icon that opens a Popover with five metadata fields: Quelle (source link), Typ (badge), Aktualisierung (human-readable interval), Lizenz (license link), and Letztes Update (timestamp).

Wired all ~25 layers in `Sidebar.tsx` with metadata props. Layers without entries in LAYER_METADATA (floodHazard, railNoise, lubwEnv, cadastral, hillshade, buildings3d) render unchanged.

### Task 2: KPI widget footers and popup DataSourceSection wiring (5807be3)

Added `sourceAbbrev`, `sourceTimestamp`, and `dataType` optional props to `KpiTile`. When `sourceAbbrev` is present, renders a footer in "ABBREV . HH:mm . BADGE" format below the tile content.

Wired all KPI tiles in `DashboardPanel` with source metadata: aqi->airQuality, weather->water, transit->transit, traffic->traffic, energy->energy, demographics->demographics, parking->parking. Timestamps come from `useLayerMetadata` formatted as HH:mm.

Added `DataSourceSection` component to all 15 popup components with appropriate layer key mappings. CommunityPopup dynamically resolves the layer key from the feature's `category` property.

## Deviations from Plan

None -- plan executed exactly as written.

## Known Stubs

None -- all data sources are wired to LAYER_METADATA registry entries and useLayerMetadata hook.

## Commits

| Task | Commit  | Message                                                              |
|------|---------|----------------------------------------------------------------------|
| 1    | 8842e1f | feat(18-02): sidebar layer toggles with data type badges, info popover, and stale warning |
| 2    | 5807be3 | feat(18-02): KPI tile source footers and DataSourceSection in all 15 popup components     |

## Self-Check: PASSED
