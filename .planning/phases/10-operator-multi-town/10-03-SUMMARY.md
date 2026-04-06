---
phase: 10-operator-multi-town
plan: "03"
subsystem: frontend
tags: [admin, health, demographics, attribution, kpi, ui]
dependency_graph:
  requires: ["10-01", "10-02"]
  provides: [admin-health-page, demographics-kpi, attribution-footer]
  affects: [frontend/app/admin, frontend/components/admin, frontend/components/dashboard, frontend/types/kpi, frontend/app/layout]
tech_stack:
  added: []
  patterns: [useKpi-pattern-for-useAdminHealth, StatCard-helper, StalenessBar-badge, relative-time-formatting-without-date-fns]
key_files:
  created:
    - frontend/types/admin.ts
    - frontend/hooks/useAdminHealth.ts
    - frontend/components/admin/StalenessBar.tsx
    - frontend/components/admin/ConnectorHealthTable.tsx
    - frontend/app/admin/page.tsx
  modified:
    - frontend/lib/api.ts
    - frontend/types/kpi.ts
    - frontend/components/dashboard/DomainDetailPanel.tsx
    - frontend/components/dashboard/DashboardPanel.tsx
    - frontend/app/layout.tsx
decisions:
  - "useAdminHealth follows useKpi pattern exactly with 30s refresh interval for operator monitoring use case"
  - "ConnectorHealthTable sorts domains by worst status, connectors within domain by severity (red first)"
  - "DomainDetailPanel uses useKpi data for demographics panel (no separate timeseries endpoint needed)"
  - "Attribution footer is static in layout.tsx (server component) — dynamic per-layer attribution already in feature popups"
  - "StatCard helper added inline in DomainDetailPanel to avoid a separate component file for simple stat display"
metrics:
  duration: 10
  completed_date: "2026-04-06"
  tasks: 2
  files: 10
---

# Phase 10 Plan 03: Frontend Admin Health Dashboard + Demographics UI Summary

**One-liner:** Operator /admin page with connector health table and green/yellow/red staleness badges, demographics KPI tile with population/age/employment stats, and Datenlizenz Deutschland attribution footer.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Admin health page + connector table + staleness components | bc31850 | frontend/types/admin.ts, frontend/hooks/useAdminHealth.ts, frontend/lib/api.ts, frontend/components/admin/StalenessBar.tsx, frontend/components/admin/ConnectorHealthTable.tsx, frontend/app/admin/page.tsx |
| 2 | Demographics KPI tile + detail panel + attribution footer | 5a7ea51 | frontend/types/kpi.ts, frontend/components/dashboard/DomainDetailPanel.tsx, frontend/components/dashboard/DashboardPanel.tsx, frontend/app/layout.tsx |

## What Was Built

### Admin Health Page (/admin)
- `frontend/types/admin.ts`: AdminHealthItem and AdminHealthResponse TypeScript interfaces mirroring backend API contract
- `frontend/hooks/useAdminHealth.ts`: Hook following useKpi.ts pattern, fetches from `/api/admin/health?town=`, auto-refreshes every 30 seconds
- `frontend/lib/api.ts`: Added fetchAdminHealth() function
- `frontend/components/admin/StalenessBar.tsx`: Colored badge pill (emerald/amber/red/slate) for OK/Verzoegert/Ausgefallen/Nie abgerufen
- `frontend/components/admin/ConnectorHealthTable.tsx`: HTML table with domain grouping, red-first sorting, relative time formatting using Intl (no date-fns), sticky header, striped rows
- `frontend/app/admin/page.tsx`: Admin page with 4-color summary bar, legend, skeleton loading, red error banner with retry

### Demographics KPI + Detail Panel
- `frontend/types/kpi.ts`: Added DemographicsKPI interface and `demographics: DemographicsKPI | null` field to KPIResponse
- `frontend/components/dashboard/DashboardPanel.tsx`: Added demographics KpiTile with Users icon, formatted population count (de-DE locale), year in unit, only renders if data.demographics is not null
- `frontend/components/dashboard/DomainDetailPanel.tsx`: Added 'demographics' to DOMAIN_TITLES, added demographics detail view with 4 StatCard tiles (population, under-18%, over-65%, unemployment rate), source attribution text, StatCard helper component

### Attribution Footer
- `frontend/app/layout.tsx`: Added static footer bar listing all 15 data sources with "Datenlizenz Deutschland" — appears on every page including /admin

## Decisions Made

1. `useAdminHealth` follows `useKpi.ts` pattern exactly with 30s refresh interval for operator monitoring use case
2. `ConnectorHealthTable` sorts domains by worst status and connectors within domain by severity (red first)
3. `DomainDetailPanel` uses `useKpi` data for the demographics panel — no separate timeseries endpoint needed for demographic indicators
4. Attribution footer is static in `layout.tsx` (server component) — dynamic per-layer attribution already in feature popups
5. `StatCard` helper added inline in `DomainDetailPanel` to keep component count low

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All tiles render real data from the backend API. Demographics tile conditionally renders only when `data.demographics` is not null — the tile will be absent if the backend does not return demographics data, which is correct behavior (not a stub).

## Self-Check: PASSED

Files created/verified:
- frontend/app/admin/page.tsx: FOUND (commit bc31850)
- frontend/components/admin/ConnectorHealthTable.tsx: FOUND (commit bc31850)
- frontend/components/admin/StalenessBar.tsx: FOUND (commit bc31850)
- frontend/types/admin.ts: FOUND (commit bc31850)
- frontend/hooks/useAdminHealth.ts: FOUND (commit bc31850)
- frontend/types/kpi.ts modified: FOUND (commit 5a7ea51)
- frontend/components/dashboard/DashboardPanel.tsx modified: FOUND (commit 5a7ea51)
- frontend/components/dashboard/DomainDetailPanel.tsx modified: FOUND (commit 5a7ea51)
- frontend/app/layout.tsx modified: FOUND (commit 5a7ea51)
- TypeScript: 0 errors
