---
phase: 05-dashboard
verified: 2026-04-05T00:00:00Z
status: gaps_found
score: 5/6 must-haves verified
re_verification: false
gaps:
  - truth: "TypeScript compiles clean — all Phase 5 components pass tsc --noEmit"
    status: failed
    reason: "3 TypeScript errors remain: 2 in TimeSeriesChart.tsx (chartData union type mismatch vs recharts ChartData generic) and 1 in useUrlState.ts (params.set receives string | undefined instead of string)"
    artifacts:
      - path: "frontend/components/dashboard/TimeSeriesChart.tsx"
        issue: "Lines 77 and 119: chartData is typed as a union of the two domain-specific array shapes; Recharts ChartContainer infers the type from the first branch and rejects the second. Fix: cast chartData as Record<string, unknown>[] or define a shared ChartRow union type."
      - path: "frontend/hooks/useUrlState.ts"
        issue: "Line 45: inside the else branch of the null check, TypeScript does not narrow v from string | undefined to string. URLSearchParams.set requires string. Fix: cast to string or use a non-null assertion."
    missing:
      - "Fix chartData type in TimeSeriesChart.tsx to be accepted by both AreaChart and LineChart ChartContainer"
      - "Fix useUrlState.ts line 45 params.set argument to be unambiguously string"
human_verification:
  - test: "KPI tiles display real AQI, temperature, and route count values"
    expected: "Dashboard panel shows three tiles — Luftqualitaet with a numeric AQI value, Wetter with a temperature in degC, OEPNV with a route count — all populated from /api/kpi response"
    why_human: "Requires live backend with populated DB; cannot verify data values programmatically without running the full stack"
  - test: "Time slider scrubs to historical timestamp and map updates"
    expected: "Dragging the slider left shows 'HH:mm Uhr' label; map layer data refetches with ?at= param; air quality sensor colors change to historical values"
    why_human: "Requires running frontend + backend + populated TimescaleDB; end-to-end interaction cannot be verified statically"
  - test: "Pasting a URL with state params restores the exact view"
    expected: "URL like /?layers=transit%2Caqi&domain=aqi&from=2026-04-04&to=2026-04-05 restores active domain detail panel and correct date range on a fresh tab load"
    why_human: "Requires browser to verify URL round-trip through Next.js router"
  - test: "Layout is usable at 768px width with no horizontal scroll"
    expected: "DashboardPanel hidden (hidden lg:flex), Sidebar and map fill viewport, no horizontal overflow"
    why_human: "Visual/CSS verification requires browser at 768px viewport"
---

# Phase 5: Dashboard Verification Report

**Phase Goal:** Citizens and officials can view KPI tiles, trend charts, and a time slider alongside the map, and share a specific view via URL
**Verified:** 2026-04-05
**Status:** gaps_found — 3 TypeScript errors block a clean build; all structural wiring verified
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | KPI tiles show current AQI, weather, and transit metrics alongside the map | VERIFIED | DashboardPanel.tsx renders 3 KpiTile components using useKpi() hook; wired through page.tsx |
| 2 | Date range picker lets user select window; charts update to reflect selection | VERIFIED | DateRangePicker.tsx with 3 presets + Zeitraum popover; useTimeseries hook re-fetches on from/to change |
| 3 | Clicking a KPI tile opens per-domain detail panel with extended chart and attribution | VERIFIED | DomainDetailPanel.tsx renders TimeSeriesChart + attribution; KpiTile onSelect sets activeDomain in URL |
| 4 | Time slider on map moves historical snapshots; map layers reflect selected timestamp | VERIFIED | TimeSlider.tsx with 96-step 15-min resolution; MapView has historicalTimestamp prop; useLayerData passes ?at= |
| 5 | Current view state encoded in URL; pasting URL restores exact view | VERIFIED | useUrlState.ts reads/writes all 9 params (town, layers, zoom, lat, lng, from, to, ts, domain) via router.replace |
| 6 | TypeScript compiles clean across all Phase 5 files | FAILED | 3 errors: 2 in TimeSeriesChart.tsx (recharts ChartData type mismatch), 1 in useUrlState.ts (params.set argument type) |

**Score:** 5/6 truths verified (goal structurally achieved; clean build blocked)

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/routers/layers.py` | Optional ?at= param on GET /api/layers/{domain} | VERIFIED | `at: datetime \| None = Query(None)` present; LATERAL join includes `AND (:at IS NULL OR time <= :at)`; at_aware passed to query dict |
| `frontend/components/ui/chart.tsx` | ChartContainer, ChartTooltip exports | VERIFIED | File exists; imported correctly in TimeSeriesChart.tsx |
| `frontend/components/ui/calendar.tsx` | Calendar component | VERIFIED | File exists; used in DateRangePicker.tsx |
| `frontend/components/ui/popover.tsx` | Popover, PopoverTrigger, PopoverContent | VERIFIED | File exists; used in DateRangePicker.tsx |
| `frontend/components/ui/slider.tsx` | Slider component | VERIFIED | File exists; imported in TimeSlider.tsx |
| `frontend/types/kpi.ts` | KPIResponse, AirQualityKPI, WeatherKPI, TransitKPI | VERIFIED | All 4 interfaces exported; nullable fields correct |
| `frontend/types/timeseries.ts` | TimeseriesResponse, TimeseriesPoint | VERIFIED | Both interfaces exported; values typed as Record |
| `frontend/hooks/useKpi.ts` | KPI polling hook, 60s interval | VERIFIED | setInterval(load, 60_000) present; returns {data, loading, error} |
| `frontend/hooks/useTimeseries.ts` | Timeseries fetch hook | VERIFIED | fetchTimeseries called; re-fetches on from/to ISO string change |
| `frontend/hooks/useUrlState.ts` | URL search param read/write hook | VERIFIED (with TS error) | useSearchParams + router.replace present; TS error on line 45 |
| `frontend/hooks/useLayerData.ts` | Extended with optional timestamp param | VERIFIED | Third param `timestamp?: Date \| null`; passes ?at= to fetchLayer; polling disabled when timestamp set |
| `frontend/lib/api.ts` | fetchKpi, fetchTimeseries, extended fetchLayer | VERIFIED | All 3 functions exported; fetchLayer accepts optional `at` param |
| `frontend/components/dashboard/KpiTile.tsx` | KpiTile with activeDomain ring | VERIFIED | ring-2 ring-primary when active; "Kein aktueller Messwert" null state |
| `frontend/components/dashboard/TrendArrow.tsx` | TrendArrow component | VERIFIED | TrendingUp/Down icons; "Unverändert" for <1% |
| `frontend/components/dashboard/DashboardPanel.tsx` | 320px right column with KPI tiles | VERIFIED | w-[320px] hidden lg:flex; children slot below Separator |
| `frontend/components/dashboard/DateRangePicker.tsx` | Preset buttons + Zeitraum popover | VERIFIED | 3 presets (24h, 7 Tage, 30 Tage); Zeitraum... popover; Uebernehmen/Abbrechen |
| `frontend/components/dashboard/TimeSeriesChart.tsx` | AreaChart + LineChart via shadcn ChartContainer | VERIFIED (with TS errors) | Both domain branches implemented; correct empty/error states; isAnimationActive={false} |
| `frontend/components/dashboard/DomainDetailPanel.tsx` | Detail panel with back button | VERIFIED | "Zurueck" button; useTimeseries wired; attribution rendered |
| `frontend/components/dashboard/TimeSlider.tsx` | 96-step scrubber with "Live" label | VERIFIED | SLIDER_STEPS = 96; 300ms debounce; "Zurueck zu Live" button |
| `frontend/components/map/MapView.tsx` | historicalTimestamp prop + historical badge | VERIFIED | `historicalTimestamp?: Date \| null` in MapViewProps; badge overlay renders when non-null |
| `frontend/app/page.tsx` | Fully wired page with Suspense | VERIFIED | Suspense > HomeInner pattern; all 5 Phase 5 components imported; useUrlState as single source of truth |
| `backend/tests/test_layers_at_param.py` | 4 tests for ?at= param | VERIFIED | All 4 test cases present with correct assertions |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| layers.py air_quality LATERAL | air_quality_readings WHERE time <= :at | conditional SQL | WIRED | Line 94: `AND (:at IS NULL OR time <= :at)` confirmed |
| useKpi.ts | /api/kpi?town=aalen | fetchKpi() in lib/api.ts | WIRED | fetchKpi imported and called; setInterval(load, 60_000) present |
| useTimeseries.ts | /api/timeseries/{domain} | fetchTimeseries() in lib/api.ts | WIRED | fetchTimeseries imported and called |
| useUrlState.ts | URL search params | useSearchParams + router.replace | WIRED | Both present; router.replace called on update() |
| DashboardPanel.tsx | useKpi hook | import { useKpi } from '@/hooks/useKpi' | WIRED | useKpi(town) called inside component |
| KpiTile.tsx | shadcn Card | import { Card } from '@/components/ui/card' | WIRED | Card and CardContent used |
| TimeSeriesChart.tsx | components/ui/chart.tsx | ChartContainer import | WIRED | ChartContainer used as chart wrapper |
| TimeSeriesChart.tsx | useTimeseries hook | props (data.points passed in) | WIRED | Points passed from DomainDetailPanel via useTimeseries |
| DateRangePicker.tsx | components/ui/popover + calendar | Popover + Calendar imports | WIRED | Both used in render |
| TimeSlider.tsx | components/ui/slider.tsx | import { Slider } | WIRED | Slider rendered with correct props |
| MapView.tsx | useLayerData with timestamp | historicalTimestamp prop | WIRED | page.tsx passes historicalTimestamp to both useLayerData calls and to MapView |
| page.tsx | useUrlState hook | Suspense > HomeInner > useUrlState() | WIRED | HomeInner calls useUrlState(); outer Home wraps in Suspense |
| page.tsx DashboardPanel | DomainDetailPanel or TimeSeriesChart | activeDomain state (chartSlot) | WIRED | chartSlot conditional renders DomainDetailPanel when activeDomain non-null |
| page.tsx TimeSlider | useLayerData(domain, town, historicalTimestamp) | historicalTimestamp state | WIRED | transit and airQuality hooks receive historicalTimestamp as third arg |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| DashboardPanel.tsx | data (KPIResponse) | useKpi() → fetchKpi() → GET /api/kpi | Yes — DB-backed (backend KPI router queries hypertables) | FLOWING |
| TimeSeriesChart.tsx | points (TimeseriesPoint[]) | useTimeseries() → fetchTimeseries() → GET /api/timeseries/{domain} | Yes — DB-backed timeseries router | FLOWING |
| MapView.tsx (historical) | transitData / airQualityData | useLayerData(domain, town, timestamp) → fetchLayer() with ?at= | Yes — layers router uses LATERAL join with at filter | FLOWING |

---

## Behavioral Spot-Checks

Step 7b: PARTIAL — backend tests are runnable but need DB; frontend requires a browser.

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| layers.py syntax valid | `python -c "import ast; ast.parse(...)"` | OK | PASS |
| at param present in layers.py | grep assertions on source text | All pass | PASS |
| TypeScript compilation | `pnpm exec tsc --noEmit` | 3 errors | FAIL |
| recharts installed | grep `package.json` | `"recharts": "^3.8.0"` | PASS |
| All shadcn ui components exist | ls components/ui/ | chart.tsx, calendar.tsx, popover.tsx, slider.tsx all present | PASS |
| test_layers_at_param.py exists and has 4 tests | file read | 4 test functions confirmed | PASS |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| DASH-01 | 05-03, 05-04 | KPI summary tiles per domain | SATISFIED | DashboardPanel renders 3 KpiTiles from useKpi; AQI, weather, transit wired |
| DASH-02 | 05-03, 05-05 | Time-series charts with date range picker | SATISFIED | DateRangePicker + TimeSeriesChart + useTimeseries all present and wired |
| DASH-03 | 05-04, 05-05 | Per-domain detail panels | SATISFIED | DomainDetailPanel with back button, extended chart, attribution |
| DASH-04 | 05-03, 05-07 | Permalink URLs encoding view state | SATISFIED | useUrlState encodes 9 params; router.replace on every change; Suspense wrapper |
| DASH-05 | 05-07 | Responsive layout desktop + tablet | SATISFIED | DashboardPanel uses `hidden lg:flex`; no horizontal scroll at 768px (human verify needed for visual confirmation) |
| MAP-06 | 05-01, 05-06 | Time slider for historical map snapshots | SATISFIED | Backend ?at= param wired; TimeSlider with 96 steps; MapView historicalTimestamp prop; useLayerData polling disabled on historical |

All 6 requirements for Phase 5 are structurally satisfied. DASH-05 visual correctness and MAP-06 end-to-end behavior require human verification.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| frontend/components/dashboard/TimeSeriesChart.tsx | 77, 119 | TypeScript error: chartData union type rejected by ChartContainer generic | Warning | Prevents clean `tsc --noEmit`; does not block runtime (JS transpiles correctly) |
| frontend/hooks/useUrlState.ts | 45 | TypeScript error: `params.set(k, v)` where v is `string \| undefined` | Warning | Prevents clean `tsc --noEmit`; runtime safe (else branch guarantees v is non-null at runtime) |

No placeholder comments, empty return stubs, or hardcoded empty data found in any dashboard component. All components have real data flow paths.

---

## Human Verification Required

### 1. KPI tiles display real data from backend

**Test:** Start the full stack (`docker-compose up`), open http://localhost:4000, observe the Dashboard panel on the right.
**Expected:** Three tiles show: Luftqualitaet (numeric AQI value), Wetter (temperature in degC), OEPNV (route count in Linien). Values update every 60 seconds.
**Why human:** Requires populated TimescaleDB with actual connector data.

### 2. Time slider historical navigation

**Test:** Open the app with data loaded. Drag the time slider left from the rightmost position.
**Expected:** Label changes from "Live" to "HH:mm Uhr". Air quality sensor marker colors update to reflect historical readings. "Zurueck zu Live" button appears. Slider URL param ?ts= updates.
**Why human:** Requires running full stack and populated air_quality_readings data.

### 3. URL permalink round-trip

**Test:** Load the app, click a KPI tile to open a detail panel, change the date range to 7 Tage. Copy the URL. Open a new browser tab, paste the URL.
**Expected:** New tab loads with same domain detail panel open and same 7-day date range selected.
**Why human:** Browser interaction required; URL state round-trip through Next.js router cannot be simulated statically.

### 4. Responsive layout at 768px

**Test:** Open the app, use browser DevTools to resize to 768px width. Verify no horizontal scroll.
**Expected:** DashboardPanel is hidden (invisible); map and sidebar fill the viewport; no content overflows horizontally.
**Why human:** Visual CSS verification requires browser at specific viewport width.

---

## Gaps Summary

The phase goal is structurally achieved: all components exist, are substantive (not stubs), are wired to real data sources, and data flows from backend queries through to rendering. The 3 TypeScript errors are the only actionable gap:

**Gap 1: TimeSeriesChart.tsx chartData type mismatch (2 errors)**
The `chartData` variable is typed as a union of `{time, pm25, pm10}[]` and `{time, temperature}[]`. Recharts' `ChartContainer` infers the generic from the first branch and rejects the second because it does not have the `pm25`/`pm10` properties. The runtime behavior is correct (each branch renders independently) but TypeScript cannot verify this statically. Fix: cast `chartData` to `Record<string, unknown>[]` at the point of passing to `AreaChart`/`LineChart`, or define a shared union type.

**Gap 2: useUrlState.ts params.set argument type (1 error)**
`URLSearchParams.set(key, value)` requires `value: string`. Inside the `else` branch of `if (v === null)`, TypeScript infers `v: string | undefined` rather than narrowing to `string`. The `Partial<Record<string, string | null>>` type allows undefined values from `Object.entries`. Fix: change the patch parameter to `Partial<Record<string, string | null | undefined>>` and add an explicit check for undefined, or cast `v` to `string`.

Both errors are non-blocking at runtime (JavaScript transpiles correctly) but block a clean CI `tsc --noEmit` pass and are genuine type safety gaps that could hide future bugs.

---

_Verified: 2026-04-05_
_Verifier: Claude (gsd-verifier)_
