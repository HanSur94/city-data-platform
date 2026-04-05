# Phase 5: Dashboard - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

KPI tiles, time-series charts, date range picker, time slider, and permalink URLs alongside the map. Requirements: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, MAP-06.

</domain>

<decisions>
## Implementation Decisions

### Dashboard Layout
- Right panel alongside map — split view (left=map, right=dashboard)
- KPI tiles as compact shadcn Cards — icon + value + label + trend arrow
- Recharts for all charts (line, area, bar) — shadcn chart components
- Time slider below the map — horizontal scrubber, full width

### Interactions & Permalinks
- URL state via search params: ?town=aalen&layers=transit,aqi&zoom=13&lat=48.84&lng=10.09&from=...&to=...
- Date range picker: preset buttons (24h / 7d / 30d / custom) + shadcn DatePicker for custom
- Click KPI tile → expand panel replaces chart area with domain-specific detail
- Time slider scrub updates map layers to show historical snapshot at selected timestamp

### Claude's Discretion
- Exact KPI metrics per domain
- Chart types per domain (line vs area vs bar)
- Animation/transition details
- Responsive breakpoint behavior for dashboard panel

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- frontend/app/page.tsx — current map page with sidebar
- frontend/hooks/useLayerData.ts — data fetching hook with polling
- frontend/components/sidebar/ — sidebar components to extend
- backend/app/routers/kpi.py — GET /api/kpi endpoint
- backend/app/routers/timeseries.py — GET /api/timeseries/{domain} endpoint

### Established Patterns
- shadcn/ui components, Tailwind CSS
- react-map-gl for map control
- useLayerData hook pattern for API calls

### Integration Points
- Dashboard panel mounts alongside existing map in page.tsx
- Time slider controls both map layers and charts
- URL params sync with map viewport + dashboard state

</code_context>

<specifics>
## Specific Ideas

- KPI tiles should feel like a "city vital signs" dashboard — quick scan, not data overload
- Time slider should feel like scrubbing a video timeline

</specifics>

<deferred>
## Deferred Ideas

- Cross-domain correlation views (v2)
- Time-lapse animations (v2)
- Export to PDF/CSV (v2)

</deferred>
