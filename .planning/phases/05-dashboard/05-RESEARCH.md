# Phase 5: Dashboard - Research

**Researched:** 2026-04-05
**Domain:** React dashboard with KPI tiles, Recharts time-series charts, date range picker, time slider, URL permalink state
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Right panel alongside map — split view (left=map, right=dashboard)
- KPI tiles as compact shadcn Cards — icon + value + label + trend arrow
- Recharts for all charts (line, area, bar) — shadcn chart components
- Time slider below the map — horizontal scrubber, full width
- URL state via search params: `?town=aalen&layers=transit,aqi&zoom=13&lat=48.84&lng=10.09&from=...&to=...`
- Date range picker: preset buttons (24h / 7d / 30d / custom) + shadcn DatePicker for custom
- Click KPI tile → expand panel replaces chart area with domain-specific detail
- Time slider scrub updates map layers to show historical snapshot at selected timestamp

### Claude's Discretion
- Exact KPI metrics per domain
- Chart types per domain (line vs area vs bar)
- Animation/transition details
- Responsive breakpoint behavior for dashboard panel

### Deferred Ideas (OUT OF SCOPE)
- Cross-domain correlation views (v2)
- Time-lapse animations (v2)
- Export to PDF/CSV (v2)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DASH-01 | KPI summary tiles showing key metrics per domain (AQI, weather, transit) | KPIResponse schema confirmed: `air_quality`, `weather`, `transit` sub-objects. `/api/kpi?town=aalen` already implemented. shadcn Card + lucide icons pattern ready. |
| DASH-02 | Time-series charts with configurable date range picker | `/api/timeseries/{domain}` fully implemented (air_quality and weather). Recharts 3.8.1 + shadcn chart add command. `react-day-picker` 9.14 available; `date-fns` 4.1 already installed. |
| DASH-03 | Per-domain detail panels accessible from dashboard or map | KPI tile click → `activeDomain` state → `DomainDetailPanel` replaces chart area. Pattern defined in UI-SPEC. |
| DASH-04 | Shareable/permalink URLs that encode current view, time, and active layers | `useSearchParams` + `router.replace` pattern (Next.js 16 App Router). Must wrap in `<Suspense>` or build will fail. |
| DASH-05 | Responsive layout — usable on desktop and tablet (768px+) | Tailwind breakpoints: `lg:` (1024px+) = side panel, tablet = bottom drawer. Pattern same as existing Sidebar mobile drawer. |
| MAP-06 | Time slider to view historical data snapshots on map | `@base-ui/react` Slider already installed. Backend layers router needs `at` query param for historical snapshot (not yet implemented — needs Wave 0 backend task). |
</phase_requirements>

---

## Summary

Phase 5 adds a dashboard panel to the right of the existing map, implementing KPI tiles, time-series charts, a date range picker, a time slider, and permalink URL state. All backend endpoints (`/api/kpi`, `/api/timeseries/{domain}`) are already implemented from Phase 3. The frontend needs new components and three new shadcn components (chart, calendar, popover) plus one new npm package (recharts 3.x).

The critical backend gap is that the `/api/layers/{domain}` endpoint does not accept a `?at=` timestamp query parameter. The time slider (MAP-06) requires the layers router to return "the reading closest to timestamp T" rather than "the latest reading". This is a one-query-change on the backend but must happen before the frontend time slider can be wired up.

URL state management via Next.js `useSearchParams` + `router.replace` is the correct pattern, but it requires `<Suspense>` wrapping in production builds or the build will fail with a hard error.

**Primary recommendation:** Build in wave order: (1) install recharts + add shadcn components, (2) KPI tiles + KPI hook, (3) date range picker + charts, (4) detail panels, (5) add `?at=` param to backend layers, (6) time slider, (7) URL permalink sync.

---

## Project Constraints (from CLAUDE.md)

Directives that constrain Phase 5 implementation:

| Directive | Impact on This Phase |
|-----------|----------------------|
| No Grafana | Dashboard must be custom Next.js — already planned |
| Port 4000 (not 3000) for frontend | Affects dev server and links; no code change needed |
| No Mapbox GL JS | MapLibre already in use — time slider must use react-map-gl/maplibre APIs |
| Tailwind CSS 4.x (no config file) | `@theme inline` CSS variable approach only; no `tailwind.config.js` |
| shadcn base-nova / neutral / cssVariables | Chart must use `--chart-1` through `--chart-5` CSS variable tokens (already in globals.css) |
| German copy only | All UI text in German; no i18n layer |
| No WebSocket / SSE | Polling (60s interval) only; already established in useLayerData |
| `use client` on page.tsx | Map page is a client component; URL state from `useSearchParams` is compatible |
| Read-only platform | No write-back endpoints needed |
| `next/dynamic` with `ssr: false` for MapView | Time slider must also avoid SSR if it references `window`; wrap in dynamic or use `useEffect` guard |

---

## Standard Stack

### Core (already installed)

| Library | Installed Version | Purpose | Status |
|---------|------------------|---------|--------|
| Next.js | 16.2.2 | App Router, useSearchParams, router.replace | Installed |
| React | 19.2.4 | UI layer | Installed |
| TypeScript | 5.x | Type safety | Installed |
| shadcn/ui CLI | 4.1.2 | Component installer | Installed |
| Tailwind CSS | 4.x | Utility CSS | Installed |
| lucide-react | 1.7.0 | Icons (wind, thermometer, bus, etc.) | Installed |
| date-fns | 4.1.0 | Date formatting for chart axes, date picker | Installed |
| @base-ui/react | 1.3.0 | Slider component (has `Slider.Root`, `Thumb`, `Track`, etc.) | Installed |

### To Install (Phase 5 Wave 0)

| Library | Version | Purpose | Install Command |
|---------|---------|---------|----------------|
| recharts | 3.8.1 | Time-series charts (AreaChart, LineChart) | `npm install recharts` |

**Version note:** Recharts 3.8.1 is the latest stable (verified 2026-04-05). shadcn chart component requires Recharts v3 (confirmed: "The chart component now uses Recharts v3"). Recharts v3 is compatible with React 19.

### shadcn Components to Add (Wave 0)

```bash
npx shadcn@latest add chart
npx shadcn@latest add calendar
npx shadcn@latest add popover
npx shadcn@latest add slider
```

Note: `popover` and `slider` from shadcn wrap Radix UI primitives, not `@base-ui/react`. The time slider uses the shadcn `Slider` (Radix-based), not `@base-ui/react`'s Slider directly. Both are installed — use shadcn's `Slider` for consistency with the existing component system.

### Already-Present shadcn Components (no install needed)

- `card`, `button`, `separator`, `switch`, `badge`, `label`, `tooltip` — already in `components/ui/`

---

## Architecture Patterns

### Recommended Project Structure

```
frontend/
├── app/
│   └── page.tsx              # Extend: add <Suspense> wrapper, DashboardPanel, TimeSlider
├── components/
│   ├── dashboard/
│   │   ├── DashboardPanel.tsx       # Right panel container
│   │   ├── KpiTile.tsx              # shadcn Card + icon + value + trend
│   │   ├── TrendArrow.tsx           # Up/down/flat chevron + percent
│   │   ├── DateRangePicker.tsx      # Preset buttons + Popover+Calendar
│   │   ├── TimeSeriesChart.tsx      # Recharts AreaChart/LineChart wrapper
│   │   ├── DomainDetailPanel.tsx    # Expanded per-domain view
│   │   └── TimeSlider.tsx           # shadcn Slider below map
│   ├── map/
│   │   └── MapView.tsx              # Extend: accept historicalTimestamp prop
│   ├── sidebar/
│   │   └── Sidebar.tsx              # Unchanged from Phase 4
│   └── ui/                          # shadcn components (add chart, calendar, popover, slider)
├── hooks/
│   ├── useLayerData.ts              # Extend: accept optional timestamp param
│   ├── useKpi.ts                    # New: polls /api/kpi every 60s
│   ├── useTimeseries.ts             # New: fetches /api/timeseries/{domain}
│   ├── useUrlState.ts               # New: reads/writes URL search params
│   └── useRelativeTime.ts           # Unchanged
├── types/
│   ├── geojson.ts                   # Unchanged
│   ├── kpi.ts                       # New: TypeScript types for KPIResponse
│   └── timeseries.ts                # New: TypeScript types for TimeseriesResponse
└── lib/
    └── api.ts                       # Extend: add fetchKpi(), fetchTimeseries()
```

### Pattern 1: URL State with useSearchParams + router.replace

**What:** Read URL search params on mount to restore view state; write on every state change with `router.replace` (no history entry).
**When to use:** All stateful dashboard interactions — date range, active domain, time slider position, layer visibility.

**Critical pitfall:** `useSearchParams` MUST be wrapped in `<Suspense>` in production. The Next.js build fails hard with "Missing Suspense boundary with useSearchParams" without it.

```tsx
// Source: frontend/node_modules/next/dist/docs/01-app/03-api-reference/04-functions/use-search-params.md
'use client'
import { useSearchParams, useRouter } from 'next/navigation'
import { Suspense } from 'react'

function DashboardInner() {
  const searchParams = useSearchParams()
  const router = useRouter()

  const from = searchParams.get('from') // 'YYYY-MM-DD' or null
  const to = searchParams.get('to')
  const ts = searchParams.get('ts')     // ISO8601 or null (live when null)

  function updateParams(updates: Record<string, string | null>) {
    const params = new URLSearchParams(searchParams.toString())
    for (const [k, v] of Object.entries(updates)) {
      if (v === null) params.delete(k)
      else params.set(k, v)
    }
    router.replace(`?${params.toString()}`, { scroll: false })
  }

  // ...
}

export default function Dashboard() {
  return (
    <Suspense fallback={null}>
      <DashboardInner />
    </Suspense>
  )
}
```

### Pattern 2: shadcn Chart (Recharts 3 wrapper)

**What:** `ChartContainer` wraps a Recharts chart and provides CSS variable-based color config. `ChartTooltip` and `ChartTooltipContent` add hover behavior.
**When to use:** All time-series charts — AQI AreaChart and Weather LineChart.

```tsx
// Source: https://ui.shadcn.com/docs/components/base/chart
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid } from 'recharts'

const chartConfig = {
  pm25: { label: 'PM2.5', color: 'var(--chart-2)' },
  pm10: { label: 'PM10', color: 'var(--chart-4)' },
}

<ChartContainer config={chartConfig} className="min-h-[200px] w-full">
  <AreaChart data={points}>
    <CartesianGrid strokeDasharray="3 3" />
    <XAxis dataKey="time" />
    <YAxis width="auto" />
    <ChartTooltip content={<ChartTooltipContent />} />
    <Area dataKey="pm25" stroke="var(--color-pm25)" fill="var(--color-pm25)" fillOpacity={0.3} />
    <Area dataKey="pm10" stroke="var(--color-pm10)" fill="var(--color-pm10)" fillOpacity={0.3} />
  </AreaChart>
</ChartContainer>
```

Note: `var(--color-pm25)` is auto-generated by ChartContainer from the `config` prop. The `--chart-1` through `--chart-5` tokens are already defined in `globals.css`.

### Pattern 3: Date Range Picker (Presets + Calendar)

**What:** Preset buttons for 24h / 7d / 30d, plus a Popover+Calendar for custom range.
**When to use:** DASH-02 date range selection that drives chart queries.

```tsx
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui/popover'
import { Calendar } from '@/components/ui/calendar'
import { Button } from '@/components/ui/button'
import { addDays, startOfDay } from 'date-fns'
import type { DateRange } from 'react-day-picker'

function DateRangePicker({ value, onChange }) {
  const [open, setOpen] = useState(false)
  const [range, setRange] = useState<DateRange | undefined>()

  const presets = [
    { label: '24h', days: 1 },
    { label: '7 Tage', days: 7 },
    { label: '30 Tage', days: 30 },
  ]

  return (
    <div className="flex gap-2 items-center">
      {presets.map(p => (
        <Button
          key={p.label}
          variant={isActivePreset(p.days) ? 'default' : 'outline'}
          onClick={() => onChange({ from: addDays(new Date(), -p.days), to: new Date() })}
        >
          {p.label}
        </Button>
      ))}
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button variant="outline">Zeitraum...</Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            mode="range"
            selected={range}
            onSelect={setRange}
            numberOfMonths={2}
          />
          <div className="flex gap-2 p-3 border-t">
            <Button onClick={() => { onChange(range); setOpen(false) }}>Übernehmen</Button>
            <Button variant="outline" onClick={() => setOpen(false)}>Abbrechen</Button>
          </div>
        </PopoverContent>
      </Popover>
    </div>
  )
}
```

Note: `react-day-picker` 9.14 is the current version (verified 2026-04-05). shadcn Calendar wraps it. `DateRange` type from `react-day-picker` is `{ from?: Date; to?: Date }`.

### Pattern 4: Time Slider (shadcn Slider)

**What:** shadcn Slider (Radix UI based) with timestamp display. Debounce scrub to avoid excessive API calls.
**When to use:** MAP-06 — historical map snapshot.

```tsx
import { Slider } from '@/components/ui/slider'
import { format } from 'date-fns'

const SLIDER_STEPS = 24 * 4  // 24h × 4 per hour = 15-min steps

function TimeSlider({ onChange }) {
  const [value, setValue] = useState([SLIDER_STEPS])  // rightmost = live
  const isLive = value[0] === SLIDER_STEPS

  const timestampAt = (step: number) => {
    const msPerStep = 15 * 60 * 1000
    return new Date(Date.now() - (SLIDER_STEPS - step) * msPerStep)
  }

  const handleChange = useDebouncedCallback((v: number[]) => {
    const ts = v[0] === SLIDER_STEPS ? null : timestampAt(v[0])
    onChange(ts)
  }, 300)

  return (
    <div className="w-full px-4 py-2">
      <Slider
        min={0}
        max={SLIDER_STEPS}
        step={1}
        value={value}
        onValueChange={(v) => { setValue(v); handleChange(v) }}
      />
      {!isLive && (
        <span className="text-sm text-muted-foreground">
          {format(timestampAt(value[0]), 'HH:mm')} Uhr
        </span>
      )}
    </div>
  )
}
```

Note: No `use-debounce` package is currently installed. The debounce can be implemented with `useRef` + `setTimeout` inline, or `use-debounce` can be added (`npm install use-debounce`).

### Pattern 5: Backend Layers with Historical Timestamp (MAP-06)

**What:** `/api/layers/{domain}` needs an optional `?at=ISO8601` query param that changes `ORDER BY time DESC LIMIT 1` to `WHERE time <= :at ORDER BY time DESC LIMIT 1`.
**When to use:** Time slider scrub — map shows sensor readings at a specific past time.

```python
# In layers.py — extend the air_quality LATERAL join
@router.get("/layers/{domain}")
async def get_layer(
    domain: str,
    town: str = Query(...),
    at: datetime | None = Query(None),  # NEW: optional historical timestamp
    ...
):
    # For air_quality LATERAL join, add WHERE clause:
    # WHERE feature_id = f.id
    #   AND (:at IS NULL OR time <= :at)
    # ORDER BY time DESC LIMIT 1
```

This is a minimal backend change — one condition added to two LATERAL subqueries (air_quality). Transit and weather layers don't have time-indexed readings in the same way.

### Anti-Patterns to Avoid

- **No `useSearchParams` without `<Suspense>`:** Causes production build failure. Dev mode silently works; production fails with a hard error. The entire page.tsx needs the URL-reading component wrapped.
- **No recharts v2 API with v3:** Recharts v3 removed `CategoricalChartState` from event handlers and `Customized` component. Don't use internal recharts state props.
- **No `window.history.pushState` directly:** Use `router.replace` from `next/navigation` — keeps React hydration consistent.
- **No chart rendering without `min-h-*` on ChartContainer:** ResponsiveContainer collapses to height 0 without a height constraint.
- **No time slider with SSR:** Slider value based on `Date.now()` — must be client-only. Use `useEffect` to initialize or wrap in `next/dynamic` with `ssr: false`.
- **No polling on chart data:** Chart data is historical and stable. Only KPI tiles poll (60s). Chart fetches on mount and date range change only.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Responsive chart sizing | Custom resize observer | Recharts `ResponsiveContainer` (via ChartContainer) | Already handles ResizeObserver, debounce, 0-height guard |
| Date range calendar UI | Custom calendar grid | shadcn `Calendar` (react-day-picker 9) | Keyboard nav, range selection, timezone handling, accessibility |
| Slider accessibility | Custom range input | shadcn `Slider` (Radix UI) | ARIA roles, keyboard step, touch target sizing built in |
| Color config propagation | Passing color props through chart tree | shadcn `ChartContainer` config system | Auto-generates CSS vars (`--color-{key}`) from config object |
| URL serialization | Custom param encoding | Native `URLSearchParams` | No library needed; already available in browser |
| Debounce | Custom timer ref | `use-debounce` npm package (or simple useRef pattern) | Time slider scrub — prevents API floods |
| Date formatting for German locale | Custom format strings | `date-fns` (already installed) with `de` locale | `date-fns` 4.x is already a dependency; `formatDistanceToNow` already used in `useRelativeTime` |

**Key insight:** shadcn's chart wrapper (`ChartContainer`) is thin but critical — it solves the CSS variable color injection problem that makes recharts work with design tokens. Do not bypass it.

---

## Common Pitfalls

### Pitfall 1: useSearchParams without Suspense
**What goes wrong:** Production build (`next build`) fails with "Missing Suspense boundary with useSearchParams" error. Works fine in development.
**Why it happens:** Next.js 16 App Router requires `useSearchParams` (a dynamic API) to be wrapped in Suspense for static-prerendering compatibility.
**How to avoid:** Always wrap the component that calls `useSearchParams` in `<Suspense fallback={null}>` at the `page.tsx` level.
**Warning signs:** Works in `npm run dev`, fails in `npm run build`.

### Pitfall 2: ChartContainer needs explicit height
**What goes wrong:** Chart renders invisible (0px height) — looks like recharts is broken but it isn't.
**Why it happens:** `ChartContainer` uses `ResponsiveContainer` internally which reads its parent's height. Without `min-h-[200px]` or `aspect-video`, height is 0.
**How to avoid:** Always set `className="min-h-[200px] w-full"` or `className="aspect-video w-full"` on `ChartContainer`.
**Warning signs:** Chart area is empty, no error in console, but DevTools shows 0px height div.

### Pitfall 3: recharts v3 breaking changes from v2
**What goes wrong:** Code copied from shadcn v2 chart examples fails because `CategoricalChartState` is no longer accessible.
**Why it happens:** Recharts v3 removed internal state exposure from event handlers and the `Customized` component.
**How to avoid:** Use standard Recharts v3 event props (`onClick`, `onMouseEnter`) on chart components directly. Don't use `<Customized />` to read recharts internals.
**Warning signs:** TypeScript errors on `CategoricalChartState` import, or runtime errors about undefined state.

### Pitfall 4: Time slider initializing with server-rendered Date.now()
**What goes wrong:** Hydration mismatch — server renders a timestamp, client renders a different one (time passed).
**Why it happens:** `Date.now()` returns different values on server and client.
**How to avoid:** Initialize slider value in `useEffect` (runs only on client), not in component body or `useState` initializer.
**Warning signs:** React hydration warning in console: "Expected server HTML to contain...".

### Pitfall 5: date-fns v4 breaking changes from v3
**What goes wrong:** Import paths like `import { format } from 'date-fns'` still work, but some locale imports changed.
**Why it happens:** `date-fns` 4.x (installed: 4.1.0) has minor breaking changes from v3. The `de` locale already used in `useRelativeTime.ts` (`import { de } from 'date-fns/locale'`) is unchanged.
**How to avoid:** Follow the pattern already established in `useRelativeTime.ts`. Import format utilities from `'date-fns'` and locales from `'date-fns/locale'`.
**Warning signs:** TypeScript errors on locale imports.

### Pitfall 6: API timeseries endpoint 10,000-row limit
**What goes wrong:** For 30-day range with 15-min sensor data, row count can approach the 10,000-row limit, truncating chart data silently.
**Why it happens:** `timeseries.py` has `LIMIT 10000` hardcoded.
**How to avoid:** For 30-day ranges, the frontend should request `air_quality` data with a coarser interval. In Phase 5, this can be mitigated by displaying a note when count equals 10,000. A downsampling query param is a v2 concern.
**Warning signs:** Chart shows abrupt end at a round number of points.

### Pitfall 7: Backend layers missing `?at=` param (MAP-06 blocker)
**What goes wrong:** Time slider changes frontend state but map layers always show live data.
**Why it happens:** `/api/layers/{domain}` currently uses `ORDER BY time DESC LIMIT 1` with no time filter — always returns the latest reading.
**How to avoid:** Add `?at=ISO8601` query param to `layers.py` before wiring up the time slider frontend. This is a Wave 0 backend task.
**Warning signs:** Time slider moves visually but map doesn't change.

---

## Code Examples

### useKpi hook (polls /api/kpi)
```typescript
// Pattern mirrors existing useLayerData.ts
'use client'
import { useState, useEffect } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export function useKpi(town = 'aalen') {
  const [data, setData] = useState<KPIResponse | null>(null)
  const [error, setError] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/kpi?town=${town}`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const json = await res.json()
        if (!cancelled) { setData(json); setError(false); setLoading(false) }
      } catch {
        if (!cancelled) { setError(true); setLoading(false) }
      }
    }
    load()
    const id = setInterval(load, 60_000)
    return () => { cancelled = true; clearInterval(id) }
  }, [town])

  return { data, error, loading }
}
```

### useTimeseries hook (fetches on demand)
```typescript
'use client'
import { useState, useEffect } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export function useTimeseries(domain: string, from: Date, to: Date, town = 'aalen') {
  const [data, setData] = useState<TimeseriesResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    const url = `${API_BASE}/api/timeseries/${domain}?town=${town}`
      + `&start=${from.toISOString()}&end=${to.toISOString()}`
    fetch(url)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
      .then(json => { if (!cancelled) { setData(json); setLoading(false) } })
      .catch(() => { if (!cancelled) { setError(true); setLoading(false) } })
    return () => { cancelled = true }
  }, [domain, from.toISOString(), to.toISOString(), town])

  return { data, loading, error }
}
```

### Extend useLayerData for historical timestamp
```typescript
// Add optional timestamp param to existing hook
export function useLayerData(domain: string, town = 'aalen', at?: Date | null) {
  // ... existing state ...
  useEffect(() => {
    const url = at
      ? `${API_BASE}/api/layers/${domain}?town=${town}&at=${at.toISOString()}`
      : `${API_BASE}/api/layers/${domain}?town=${town}`
    // ... existing fetch logic ...
    // Disable auto-poll when historical mode is active
    if (!at) {
      const id = setInterval(load, 60_000)
      return () => { cancelled = true; clearInterval(id) }
    }
    return () => { cancelled = true }
  }, [domain, town, at?.toISOString()])
  // ...
}
```

### Backend: add `?at=` to layers router (air_quality domain)
```python
# In backend/app/routers/layers.py
@router.get("/layers/{domain}", response_model=None)
async def get_layer(
    domain: str,
    town: str = Query(...),
    at: datetime | None = Query(None),  # NEW param
    db: AsyncSession = Depends(get_db),
    current_town: Town = Depends(get_current_town),
) -> dict:
    # ...
    # In air_quality LATERAL join, change to:
    # SELECT pm25, pm10, no2, o3, aqi, time
    # FROM air_quality_readings
    # WHERE feature_id = f.id
    #   AND (:at IS NULL OR time <= :at)   -- NEW condition
    # ORDER BY time DESC LIMIT 1
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Recharts v2 (shadcn default) | Recharts v3 (shadcn chart current) | shadcn chart updated ~2025 | Must use v3 API; v2 `CategoricalChartState` removed |
| `next/router` from `next/router` | `useRouter` from `next/navigation` | Next.js 13+ App Router | Already using correct import |
| Radix UI Slider | shadcn Slider (wraps Radix @1.3.6) | N/A | Use shadcn for design system consistency |
| react-day-picker v8 | react-day-picker v9.14 | 2024 | `DateRange` type and `mode="range"` API is same |

**Deprecated/outdated:**
- `window.history.pushState`: Works but bypasses React. Use `router.replace` from `next/navigation` instead.
- Recharts `<Customized />` for reading internal state: Removed in v3. Use standard event handlers.

---

## Open Questions

1. **Debounce utility for time slider**
   - What we know: No debounce library currently installed. `use-debounce` is the standard (~2M weekly downloads).
   - What's unclear: Whether the planner should add `use-debounce` as a dependency or inline a simple `useRef` + `setTimeout` approach.
   - Recommendation: Add `npm install use-debounce` in Wave 0. The package is tiny and avoids brittle manual debounce implementations.

2. **Weather layer historical snapshots via time slider**
   - What we know: Weather readings are in `weather_readings` table, served via the generic "plain features" path in layers.py (no LATERAL join with time). The `?at=` param would require adding a LATERAL join for weather too.
   - What's unclear: Whether MAP-06 scope includes weather or only air quality in Phase 5.
   - Recommendation: Scope MAP-06 to air quality only in Phase 5 (the one domain with actual time-series data). Weather time slider support can be added when the weather domain's layer query gets upgraded.

3. **KPI trend arrow: "vs 24h ago" requires a second API call or backend change**
   - What we know: `/api/kpi` returns only the current value. Trend requires comparing to a past value.
   - What's unclear: Whether the plan should add `previous_aqi` / `previous_temperature` to the KPI endpoint or use a separate `/api/timeseries` fetch.
   - Recommendation: Add `previous_aqi` and `previous_temperature` fields to `KPIResponse` (queried as `last()` over `time > NOW() - INTERVAL '48 hours' AND time < NOW() - INTERVAL '24 hours'`). This avoids a separate frontend call. Alternatively, derive from timeseries data already fetched for charts — use timeseries if charts are shown, fall back to "no trend" if not.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | npm install, next build | Yes | 22.22.1 | — |
| npm | Package installation | Yes | 10.9.4 | — |
| recharts | Charts (DASH-02) | No (not installed) | 3.8.1 (latest) | — (required, no fallback) |
| react-day-picker | Calendar component | No (not installed, pulled by shadcn add calendar) | 9.14 | — (required) |
| @radix-ui/react-slider | shadcn Slider | No (not installed, pulled by shadcn add slider) | 1.3.6 | @base-ui/react Slider (already installed) |
| @radix-ui/react-popover | shadcn Popover | No (not installed, pulled by shadcn add popover) | 1.1.15 | @base-ui/react Popover (already installed) |
| use-debounce | Time slider | No | 10.x | Inline useRef/setTimeout debounce |

**Missing dependencies with no fallback:**
- `recharts` — must be installed before chart components can be built

**Missing dependencies with fallback:**
- `@radix-ui/react-slider` — `@base-ui/react` Slider is already installed and has equivalent API; the plan can choose either
- `@radix-ui/react-popover` — `@base-ui/react` Popover is already installed; the plan can choose either
- Note: shadcn `add popover` and `add slider` will install the Radix primitives anyway; the fallback is moot if we use `shadcn add`

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (backend) |
| Config file | `backend/pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `cd backend && uv run pytest tests/test_api_kpi.py tests/test_api_timeseries.py -x -q` |
| Full suite command | `cd backend && uv run pytest -x -q` |
| Frontend framework | None currently installed — no vitest/jest found |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DASH-01 | KPI endpoint returns air_quality, weather, transit fields | unit (backend) | `cd backend && uv run pytest tests/test_api_kpi.py -x -q` | Yes (test_api_kpi.py) |
| DASH-02 | Timeseries returns time-ordered readings within date range | unit (backend) | `cd backend && uv run pytest tests/test_api_timeseries.py -x -q` | Yes (test_api_timeseries.py) |
| DASH-03 | Detail panel shows per-domain chart on KPI click | manual-only | N/A | N/A — UI interaction, no headless test infra |
| DASH-04 | Permalink URL restores view state | manual-only | N/A | N/A — requires browser |
| DASH-05 | Layout usable at 768px+ | manual-only | N/A | N/A — requires browser resize |
| MAP-06 | Layers endpoint accepts `?at=` param and returns historical reading | unit (backend) | `cd backend && uv run pytest tests/test_api_layers.py -x -q` | Yes (test_api_layers.py) — needs new test case |

### Sampling Rate

- **Per task commit:** `cd backend && uv run pytest tests/test_api_kpi.py tests/test_api_timeseries.py tests/test_api_layers.py -x -q`
- **Per wave merge:** `cd backend && uv run pytest -x -q`
- **Phase gate:** Full backend suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/test_api_layers.py` needs a new test case: `test_layers_at_param_returns_historical` — covers MAP-06 backend change
- [ ] Frontend: no test framework installed — DASH-03, DASH-04, DASH-05 are manual-verification only

*(No new test files needed for DASH-01 and DASH-02 — existing test files cover those endpoints already.)*

---

## Sources

### Primary (HIGH confidence)
- `frontend/node_modules/next/dist/docs/` — Next.js 16.2.2 built-in docs (useSearchParams, useRouter, Suspense requirement)
- `frontend/package.json` — Installed package versions (exact)
- `frontend/components.json` — shadcn preset (base-nova, neutral, cssVariables)
- `frontend/app/globals.css` — Confirmed `--chart-1` through `--chart-5` CSS variable definitions
- `backend/app/routers/kpi.py` — KPIResponse shape confirmed
- `backend/app/routers/timeseries.py` — TimeseriesResponse shape, 90-day MAX_RANGE, 10K row limit
- `backend/app/routers/layers.py` — Confirmed no `?at=` param exists (MAP-06 gap identified)
- `https://ui.shadcn.com/docs/components/base/chart` — Recharts v3 confirmed, ChartContainer pattern
- `https://ui.shadcn.com/docs/components/calendar` — react-day-picker, mode="range" API
- Node.js `require('@base-ui/react')` — Confirmed Slider and Popover are available

### Secondary (MEDIUM confidence)
- `https://github.com/recharts/recharts/releases/tag/v3.0.0` — Breaking changes: CategoricalChartState removed
- `https://ui.shadcn.com/docs/components/slider` — Slider wraps Radix UI, install command
- `https://ui.shadcn.com/docs/components/popover` — Popover pattern for date picker

### Tertiary (LOW confidence)
- None — all critical findings were verified with primary sources.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified all versions via npm view and package.json inspection
- Architecture: HIGH — based on existing codebase patterns (useLayerData, Sidebar, MapView) + Next.js official docs
- Pitfalls: HIGH — useSearchParams/Suspense pitfall verified in official Next.js docs; chart height pitfall verified in shadcn docs; recharts v3 breaking changes from GitHub releases
- Backend gap (MAP-06): HIGH — confirmed by reading layers.py source directly

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (shadcn/recharts evolve; re-verify versions if planning is delayed more than 30 days)
