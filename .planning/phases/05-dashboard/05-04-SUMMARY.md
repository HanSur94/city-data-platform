---
phase: 05-dashboard
plan: 04
subsystem: ui
tags: [react, shadcn, tailwind, lucide-react, kpi, dashboard]

# Dependency graph
requires:
  - phase: 05-03
    provides: KPIResponse types in frontend/types/kpi.ts, useKpi hook in frontend/hooks/useKpi.ts

provides:
  - KpiTile component — Card wrapper with icon, Display-28px value, unit label, trend arrow, active ring
  - TrendArrow component — up/down/flat indicator with German copy
  - DashboardPanel container — 320px right panel with KPI tiles, skeleton loading, chart slot

affects: [05-05, 05-06, 05-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "KpiTile toggle pattern: clicking active domain calls onDomainSelect(null) to collapse"
    - "DashboardPanel children slot: chart/detail area passed as children, keeping panel stable across plans"
    - "Skeleton shimmer: animate-pulse placeholder divs shown during KPI load (loading && !data)"

key-files:
  created:
    - frontend/components/dashboard/TrendArrow.tsx
    - frontend/components/dashboard/KpiTile.tsx
    - frontend/components/dashboard/DashboardPanel.tsx
  modified: []

key-decisions:
  - "KpiTile toggle: clicking the active tile passes null to onDomainSelect, collapsing the detail panel"
  - "DashboardPanel children prop used as chart/detail slot — keeps panel component stable for Plan 05 extension"
  - "Skeleton shimmer uses loading && !data condition to only show before first fetch, not on refresh polls"
  - "Trend suppressed for weather and transit tiles (trend=null) per UI-SPEC — only AQI could have trend data"

patterns-established:
  - "Toggle-select pattern: onSelect(domain) → parent toggles null/domain, tile receives active prop"
  - "Render slot via children prop instead of explicit chart prop — enables swapping chart content in later plans"

requirements-completed: [DASH-01, DASH-03]

# Metrics
duration: 1min
completed: 2026-04-05
---

# Phase 5 Plan 04: KPI Tiles + Dashboard Panel Summary

**shadcn Card-based KPI tiles (Luftqualität, Wetter, ÖPNV) with toggle-select active ring and 320px DashboardPanel container using children slot for extensible chart area**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-04-05T23:22:19Z
- **Completed:** 2026-04-05T23:23:13Z
- **Tasks:** 2
- **Files modified:** 3 created

## Accomplishments

- KpiTile component: Card with icon + 28px value + unit label + TrendArrow + active ring-2 ring-primary
- TrendArrow component: TrendingUp/TrendingDown icons + German copy ("+N% gegenüber gestern" / "Unverändert")
- DashboardPanel: 320px fixed right panel, hidden below lg breakpoint, 3 KPI tiles, skeleton shimmer, Separator, children slot for chart area

## Task Commits

1. **Task 1: KpiTile and TrendArrow components** - `8c657f2` (feat)
2. **Task 2: DashboardPanel container with KPI section and chart slot** - `f1b9f99` (feat)

## Files Created/Modified

- `frontend/components/dashboard/TrendArrow.tsx` - Up/down/flat trend indicator with German labels
- `frontend/components/dashboard/KpiTile.tsx` - Card-based KPI tile with active ring and no-data state
- `frontend/components/dashboard/DashboardPanel.tsx` - 320px right panel container consuming useKpi hook

## Decisions Made

- KpiTile toggle: clicking active domain passes null to parent onDomainSelect, collapsing detail panel
- DashboardPanel exposes `children` prop as a chart/detail render slot — Plan 05 will pass TimeSeriesChart here
- Skeleton shimmer guarded by `loading && !data` so refresh polls don't re-show the skeleton
- All three tiles have `trend={null}` since the API doesn't expose trend percentage data yet (will be wired when historical comparison endpoint exists)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- KpiTile, TrendArrow, and DashboardPanel are stable and ready for Plan 05 (TimeSeriesChart wiring)
- Plan 07 wires DashboardPanel into page.tsx with activeDomain state
- Children slot in DashboardPanel ready to accept any chart or detail component
- No blockers

---
*Phase: 05-dashboard*
*Completed: 2026-04-05*

## Self-Check: PASSED

- FOUND: frontend/components/dashboard/TrendArrow.tsx
- FOUND: frontend/components/dashboard/KpiTile.tsx
- FOUND: frontend/components/dashboard/DashboardPanel.tsx
- FOUND: .planning/phases/05-dashboard/05-04-SUMMARY.md
- FOUND: commit 8c657f2 (Task 1)
- FOUND: commit f1b9f99 (Task 2)
