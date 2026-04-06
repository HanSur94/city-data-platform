---
phase: 07-traffic-energy-connectors
plan: "06"
subsystem: ui
tags: [react, recharts, nextjs, typescript, tailwind, shadcn]

requires:
  - phase: 07-traffic-energy-connectors
    provides: "Traffic and energy API routes, KPI endpoint returning TrafficKPI/EnergyKPI, timeseries endpoint for traffic/energy domains"

provides:
  - "EnergyMixBar component: horizontal stacked BarChart for generation mix with SOURCE_COLORS"
  - "TrafficLegend: Frei/Maessig/Stau + Autobahn swatches"
  - "EnergyLegend: Solar/Wind/Batterie/Dach-Solar swatches"
  - "Sidebar: Verkehr group (3 toggles) + Energie group (1 toggle) with legends"
  - "DomainDetailPanel: traffic (flow LineChart) and energy (stacked AreaChart + price LineChart) branches"
  - "DashboardPanel: Verkehr and Energie KPI tiles with EnergyMixBar compact slot"
  - "page.tsx: full wiring of traffic/autobahn/mobiData/energy layers, hooks, and props"

affects:
  - "frontend/components/map/MapView.tsx — receives trafficVisible, autobahnVisible, energyVisible optional props"

tech-stack:
  added: []
  patterns:
    - "KpiTile children slot pattern for embedding compact sub-charts (e.g. EnergyMixBar compact)"
    - "Domain switch pattern in DomainDetailPanel: case 'traffic' / case 'energy' branches"
    - "SOURCE_COLORS constant shared between EnergyMixBar and DomainDetailPanel energy area chart"

key-files:
  created:
    - frontend/components/dashboard/EnergyMixBar.tsx
    - frontend/components/sidebar/TrafficLegend.tsx
    - frontend/components/sidebar/EnergyLegend.tsx
  modified:
    - frontend/components/sidebar/Sidebar.tsx
    - frontend/components/dashboard/DomainDetailPanel.tsx
    - frontend/components/dashboard/DashboardPanel.tsx
    - frontend/components/dashboard/KpiTile.tsx
    - frontend/components/map/MapView.tsx
    - frontend/app/page.tsx

key-decisions:
  - "KpiTile extended with optional children prop to support embedded compact sub-charts without a new component"
  - "MapView extended with optional trafficVisible/autobahnVisible/energyVisible props (defaulting to false) for future traffic/energy layer rendering"
  - "EnergyMixBar uses ResponsiveContainer + BarChart (not shadcn ChartContainer) to avoid tooltip type incompatibility with stacked multi-series format"

patterns-established:
  - "Compact mini-chart slot in KPI tile: pass EnergyMixBar compact as children to KpiTile"
  - "Domain branch in DomainDetailPanel: add case checks before chartDomain fallback"

requirements-completed:
  - TRAF-03
  - TRAF-04
  - ENRG-01
  - ENRG-03
  - ENRG-04

duration: 6min
completed: "2026-04-06"
---

# Phase 07 Plan 06: Frontend Integration — Traffic + Energy KPI Tiles, Detail Panels, Sidebar Summary

**Horizontal stacked EnergyMixBar, Verkehr/Energie sidebar groups, traffic/energy KPI tiles in DashboardPanel, domain-specific detail panels with flow LineChart and generation mix AreaChart + price LineChart, all wired into page.tsx.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-06T17:56:32Z
- **Completed:** 2026-04-06T17:62:09Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Created EnergyMixBar with horizontal stacked BarChart, compact mode (24px), full mode (40px) with source labels, using UI-SPEC SOURCE_COLORS
- Extended Sidebar with Verkehr group (BASt/Autobahn/MobiData toggles) and Energie group (MaStR toggle) plus conditional TrafficLegend and EnergyLegend
- Extended DomainDetailPanel with traffic branch (flow LineChart) and energy branch (stacked AreaChart for generation mix + price LineChart)
- Added Verkehr and Energie KPI tiles to DashboardPanel with EnergyMixBar compact slot
- Updated page.tsx with full layer visibility wiring, useLayerData hooks for traffic/energy, Sidebar error props, MapView trafficVisible/autobahnVisible/energyVisible props

## Task Commits

1. **Task 1: EnergyMixBar + Sidebar toggle groups + legends** - `d2bb148` (feat)
2. **Task 2: DomainDetailPanel traffic+energy + DashboardPanel KPI tiles + page.tsx wiring** - `32af75b` (feat)

## Files Created/Modified

- `frontend/components/dashboard/EnergyMixBar.tsx` - Horizontal stacked BarChart for generation mix, SOURCE_COLORS, compact/full modes
- `frontend/components/sidebar/TrafficLegend.tsx` - Frei/Maessig/Stau + Autobahn color swatches
- `frontend/components/sidebar/EnergyLegend.tsx` - Solar/Wind/Batterie/Dach-Solar color swatches
- `frontend/components/sidebar/Sidebar.tsx` - Extended with Verkehr (3 toggles) and Energie (1 toggle) groups + TrafficLegend/EnergyLegend
- `frontend/components/dashboard/DomainDetailPanel.tsx` - Added traffic (flow LineChart) and energy (AreaChart + price LineChart) domain branches
- `frontend/components/dashboard/DashboardPanel.tsx` - Added Verkehr KPI tile (Car icon) and Energie KPI tile (Zap icon) with EnergyMixBar compact slot
- `frontend/components/dashboard/KpiTile.tsx` - Added optional children prop for compact sub-chart slot
- `frontend/components/map/MapView.tsx` - Added optional trafficVisible, autobahnVisible, energyVisible props
- `frontend/app/page.tsx` - Full wiring: layerVisibility for traffic/autobahn/mobiData/energy, useLayerData hooks, trafficError/energyError to Sidebar, trafficVisible/autobahnVisible/energyVisible to MapView

## Decisions Made

- KpiTile extended with optional `children` prop — keeps component stable and reusable without a new component per domain
- MapView extended with optional `trafficVisible`/`autobahnVisible`/`energyVisible` props defaulting to false — future traffic/energy layer rendering hooks without breaking existing callers
- EnergyMixBar uses Recharts directly (BarChart + ResponsiveContainer) rather than shadcn ChartContainer — avoids tooltip formatter type incompatibility with multi-series stacked format

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added children prop to KpiTile**
- **Found during:** Task 2 (DashboardPanel KPI tiles)
- **Issue:** Plan required embedding EnergyMixBar inside energy KpiTile but KpiTile had no children prop
- **Fix:** Added optional `children?: React.ReactNode` to KpiTileProps and rendered below metric value
- **Files modified:** frontend/components/dashboard/KpiTile.tsx
- **Verification:** TypeScript compiles cleanly
- **Committed in:** 32af75b (Task 2 commit)

**2. [Rule 3 - Blocking] Added trafficVisible/autobahnVisible/energyVisible to MapView interface**
- **Found during:** Task 2 (page.tsx wiring)
- **Issue:** page.tsx passes these props to MapView but MapView interface didn't declare them, causing TypeScript error
- **Fix:** Added optional boolean props with defaults to MapViewProps interface and destructuring
- **Files modified:** frontend/components/map/MapView.tsx
- **Verification:** TypeScript exit 0
- **Committed in:** 32af75b (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 missing critical, 1 blocking)
**Impact on plan:** Both auto-fixes necessary for correctness and TypeScript compile. No scope creep.

## Issues Encountered

- Recharts `Tooltip.formatter` type expects `ValueType | undefined` not `number` — fixed by using `Number()` cast instead of typed parameter

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Frontend fully wired for traffic and energy domains: KPI tiles show live data, detail panels render domain charts, sidebar has all toggles
- MapView has optional props ready for when traffic/energy map layers are added
- TypeScript compiles cleanly (exit 0)

---
*Phase: 07-traffic-energy-connectors*
*Completed: 2026-04-06*
