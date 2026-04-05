---
phase: 05-dashboard
plan: 03
subsystem: ui
tags: [typescript, react, next.js, hooks, api, timeseries, kpi, url-state]

# Dependency graph
requires:
  - phase: 04-map-frontend
    provides: useLayerData hook pattern and fetchLayer in lib/api.ts
  - phase: 05-02
    provides: recharts and shadcn components installed
provides:
  - TypeScript types for KPI (KPIResponse, AirQualityKPI, WeatherKPI, TransitKPI)
  - TypeScript types for timeseries (TimeseriesResponse, TimeseriesPoint)
  - fetchKpi() and fetchTimeseries() in lib/api.ts
  - useKpi hook with 60s polling
  - useTimeseries hook with dependency-safe ISO string deps
  - useUrlState hook reading/writing 9 URL search params
  - Extended useLayerData with optional timestamp param and conditional polling
affects: [05-04, 05-05, 05-06, 05-07]

# Tech tracking
tech-stack:
  added: [date-fns (subDays, endOfDay already installed)]
  patterns:
    - cancelled-flag pattern for all async useEffect hooks
    - ISO string serialization for Date deps in useEffect to avoid object reference churn
    - Polling disabled for historical queries (timestamp param set)
    - useUrlState requires Suspense boundary at call site

key-files:
  created:
    - frontend/types/kpi.ts
    - frontend/types/timeseries.ts
    - frontend/hooks/useKpi.ts
    - frontend/hooks/useTimeseries.ts
    - frontend/hooks/useUrlState.ts
  modified:
    - frontend/lib/api.ts
    - frontend/hooks/useLayerData.ts

key-decisions:
  - "useLayerData stops polling when timestamp is set — historical data does not auto-refresh"
  - "useTimeseries uses ISO string dep values (from.toISOString()) to avoid object reference churn"
  - "useUrlState Suspense requirement documented in code comment; enforcement deferred to Plan 07"

patterns-established:
  - "Pattern: All async useEffect hooks use cancelled flag + cleanup to prevent setState on unmounted components"
  - "Pattern: Date objects in useEffect deps serialized to ISO strings to avoid infinite re-render loops"

requirements-completed: [DASH-01, DASH-02, DASH-04]

# Metrics
duration: 5min
completed: 2026-04-05
---

# Phase 5 Plan 03: Types + Hooks Summary

**KPI, timeseries, and URL state hooks with full TypeScript types — the data contracts all dashboard components will import**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-05T23:18:22Z
- **Completed:** 2026-04-05T23:23:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Created typed KPI and timeseries type files mirroring backend Pydantic schemas exactly
- Implemented useKpi (60s polling), useTimeseries (date-range aware), useUrlState (9 params), all with cancelled-flag cleanup
- Extended fetchLayer and useLayerData with optional historical timestamp param and conditional polling

## Task Commits

Each task was committed atomically:

1. **Task 1: TypeScript type definitions for KPI and timeseries** - `7b3e3a9` (feat)
2. **Task 2: API functions, hooks, and extend useLayerData** - `cd782f5` (feat)

## Files Created/Modified
- `frontend/types/kpi.ts` - KPIResponse, AirQualityKPI, WeatherKPI, TransitKPI, Attribution interfaces
- `frontend/types/timeseries.ts` - TimeseriesResponse, TimeseriesPoint interfaces
- `frontend/lib/api.ts` - Added fetchKpi, fetchTimeseries; extended fetchLayer with optional at param
- `frontend/hooks/useKpi.ts` - KPI polling hook (60s interval)
- `frontend/hooks/useTimeseries.ts` - Timeseries fetch hook with ISO dep strings
- `frontend/hooks/useUrlState.ts` - URL search param read/write with 9 fields
- `frontend/hooks/useLayerData.ts` - Extended with optional timestamp, conditional polling

## Decisions Made
- useLayerData stops polling when a historical timestamp is set — historical data does not auto-refresh (live data always polls)
- useTimeseries serializes Date deps as ISO strings to avoid object reference churn causing infinite re-renders
- useUrlState Suspense requirement documented in inline comment; enforcement via Suspense boundary deferred to Plan 07 (page.tsx integration)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All data contracts are established — Plans 04, 05, 06 can import types and hooks directly
- useUrlState requires Suspense boundary at call site (documented, enforced in Plan 07)
- tsc --noEmit passes with 0 errors

---
*Phase: 05-dashboard*
*Completed: 2026-04-05*
