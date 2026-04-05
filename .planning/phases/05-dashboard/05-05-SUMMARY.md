---
phase: 05-dashboard
plan: 05
subsystem: frontend/dashboard
tags: [react, recharts, shadcn, date-picker, charts, typescript]
dependency_graph:
  requires: [05-03]
  provides: [DateRangePicker, TimeSeriesChart, DomainDetailPanel]
  affects: [DashboardPanel]
tech_stack:
  added: []
  patterns:
    - Base UI Popover render prop (not asChild) for custom trigger rendering
    - Recharts AreaChart/LineChart wrapped in shadcn ChartContainer
    - date-fns for date formatting and preset calculation
key_files:
  created:
    - frontend/components/dashboard/DateRangePicker.tsx
    - frontend/components/dashboard/TimeSeriesChart.tsx
    - frontend/components/dashboard/DomainDetailPanel.tsx
  modified: []
decisions:
  - Base UI Popover.Trigger does not support asChild — used render prop pattern instead
  - npm install was required to resolve missing recharts and react-day-picker packages
metrics:
  duration_minutes: 2
  completed_date: "2026-04-05"
  tasks_completed: 2
  files_created: 3
---

# Phase 05 Plan 05: DateRangePicker + TimeSeriesChart + DomainDetailPanel Summary

**One-liner:** Date range picker with calendar popover, area/line charts via shadcn ChartContainer, and domain detail panel with back navigation and attribution.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | DateRangePicker component | 60e2434 | frontend/components/dashboard/DateRangePicker.tsx |
| 2 | TimeSeriesChart and DomainDetailPanel | e87d14f | frontend/components/dashboard/TimeSeriesChart.tsx, frontend/components/dashboard/DomainDetailPanel.tsx |

---

## What Was Built

### DateRangePicker (`DateRangePicker.tsx`)

- Three preset buttons: "24h", "7 Tage", "30 Tage" — active preset uses `variant="default"` (filled), inactive uses `variant="outline"`
- Active preset detection within 1-hour tolerance to handle real-time clock drift
- "Zeitraum..." trigger button that opens a calendar popover when no preset is active, or shows the custom date range as "DD.MM.YYYY – DD.MM.YYYY" when a custom range is selected
- Calendar popover with `mode="range"`, 2 months visible, future dates disabled, max range capped at `maxDays` (default 90)
- "Übernehmen" (apply) and "Abbrechen" (cancel) buttons in popover footer

### TimeSeriesChart (`TimeSeriesChart.tsx`)

- Accepts `domain: 'air_quality' | 'weather'`, `points`, `loading`, `error`, `dateRange`
- Air quality domain: Recharts `AreaChart` with two overlaid areas — PM2.5 (chart-2) and PM10 (chart-4)
- Weather domain: Recharts `LineChart` with temperature line (chart-2)
- All series: `isAnimationActive={false}` per UI-SPEC
- X-axis tick format: `HH:mm` for ≤1 day range, `dd.MM` for longer ranges
- Tooltip label formatted as `dd.MM.yyyy HH:mm` (German format)
- Loading state: `animate-pulse` skeleton div
- Empty state: "Keine Messwerte im gewählten Zeitraum."
- Error state: "Daten konnten nicht geladen werden. Bitte Zeitraum anpassen oder Seite neu laden."

### DomainDetailPanel (`DomainDetailPanel.tsx`)

- Displays domain title (e.g., "Luftqualität — Messverlauf", "Wetter — Temperaturverlauf")
- "Zurück" back button with ChevronLeft icon, calls `onBack` callback
- Embeds `TimeSeriesChart` for aqi/weather domains, uses `useTimeseries` hook
- Transit domain shows static message: "ÖPNV-Daten sind statisch (GTFS). Zeitverlauf ist nicht verfügbar."
- Attribution section renders Quelle + linked source name + license from API response

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Base UI PopoverTrigger does not support `asChild`**
- **Found during:** Task 1
- **Issue:** Plan code used `<PopoverTrigger asChild>` which is a Radix UI pattern. The local `popover.tsx` wraps Base UI's Popover, which uses `render` prop instead of `asChild` for custom element rendering.
- **Fix:** Used Base UI `render` prop on `PopoverTrigger` to render a styled native `<button>` element that matches the shadcn Button sm/outline appearance.
- **Files modified:** `frontend/components/dashboard/DateRangePicker.tsx`
- **Commit:** 60e2434

**2. [Rule 3 - Blocking] Missing npm packages: recharts and react-day-picker**
- **Found during:** Task 1 verification
- **Issue:** Both `recharts` and `react-day-picker` were listed in `package.json` but not present in `node_modules`. This caused TypeScript errors in pre-existing `calendar.tsx` and `chart.tsx`.
- **Fix:** Ran `npm install` in the frontend directory to install missing packages.
- **Files modified:** none (dependency install only)
- **Commit:** n/a (infrastructure fix)

---

## Known Stubs

None — all data flow is wired through real `useTimeseries` hook and actual chart components.

---

## Self-Check: PASSED

- FOUND: frontend/components/dashboard/DateRangePicker.tsx
- FOUND: frontend/components/dashboard/TimeSeriesChart.tsx
- FOUND: frontend/components/dashboard/DomainDetailPanel.tsx
- FOUND: commit 60e2434 (feat(05-05): implement DateRangePicker component)
- FOUND: commit e87d14f (feat(05-05): implement TimeSeriesChart and DomainDetailPanel)
