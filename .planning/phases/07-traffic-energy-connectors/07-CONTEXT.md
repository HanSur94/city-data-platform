# Phase 7: Traffic & Energy Connectors - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Road traffic flow, highway warnings, MobiData BW data, and the German electricity mix are visible on map and dashboard. Requirements: TRAF-03, TRAF-04, TRAF-05, ENRG-01, ENRG-02, ENRG-03, ENRG-04.

Backend: new connectors for BASt traffic counts, Autobahn API, MobiData BW, SMARD energy data, and MaStR renewable installations registry. Frontend: new Traffic and Energy map layer groups, KPI tiles, detail panels, and time-series charts.

</domain>

<decisions>
## Implementation Decisions

### Traffic Data Sources & Scope
- "Near Aalen" for BASt stations means stations within the Aalen bbox + 20km buffer — covers A7 and B29
- Use BASt CSV data (free, no registration) as primary traffic count source — MDM/Mobilithek may need registration per STATE.md blocker
- MobiData BW: prioritize traffic count stations + bike counting stations — sharing/bike-rental data is fragmented near Aalen
- Autobahn API scope: A7 + A6 (Crailsheim junction) roadworks and closures within 50km of Aalen

### Energy Data Sources & Dashboard
- SMARD electricity mix KPI tile: stacked bar showing current % by source (solar, wind, gas, coal, nuclear, hydro, biomass, other), color-coded renewable vs fossil
- MaStR registry: clustered circles color-coded by type (solar=yellow, wind=blue, battery=green); solar on buildings gets distinct roof icon
- Use SMARD as the single energy data source — Energy-Charts pulls from SMARD anyway; avoids maintaining two scrapers
- Poll intervals: SMARD every 15 min (matches resolution), MaStR daily (registry changes slowly)

### Map Layer Presentation
- Traffic flow: colored circles at station locations, sized by flow rate, colored green→yellow→red by congestion level — follows AQI layer pattern
- Autobahn roadworks: warning triangle icons (⚠) for roadworks, red X (✗) for closures, clickable popup with detour info
- Sidebar groups: "Traffic" (BASt counts, Autobahn warnings, MobiData BW) and "Energy" (electricity mix, renewables map) as separate toggle groups
- MaStR layer load: clustered GeoJSON with server-side bbox filtering — follows GTFS stops pattern

### Dashboard Integration
- Energy KPI tile: current renewable % + generation mix mini-bar + wholesale price — click opens energy detail panel
- Traffic KPI tile: active roadworks count + average flow status indicator (normal/busy/congested) — click opens traffic detail panel
- Energy detail panel: generation mix stacked area chart (time-series) + wholesale price line chart — date range picker applies
- Traffic detail panel: per-station flow chart (line) + roadworks list sorted by proximity

### Claude's Discretion
No items deferred to Claude's discretion — all grey areas resolved.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- backend/app/connectors/base.py — BaseConnector with persist(), upsert_feature(), _update_staleness()
- backend/app/connectors/uba.py, sensor_community.py, weather.py, pegelonline.py — connector patterns for various data sources
- frontend/components/map/AQILayer.tsx, TransitLayer.tsx, WaterLayer.tsx — layer component patterns (colored circles, clustering, popups)
- frontend/hooks/useLayerData.ts — data fetching with polling
- frontend/hooks/useKpi.ts, useTimeseries.ts — dashboard data hooks
- frontend/components/dashboard/KpiTile.tsx, DomainDetailPanel.tsx, TimeSeriesChart.tsx — dashboard component patterns
- backend/app/routers/layers.py — GeoJSON layer endpoint with ?at= param
- backend/app/routers/kpi.py — KPI endpoint pattern

### Established Patterns
- Connectors register in towns/aalen.yaml with connector_class, poll_interval_seconds, config
- Domain enum: "air_quality", "transit", "water", "weather" — extend with "traffic", "energy"
- Map layers follow: useLayerData hook → GeoJSON source → MapLibre layer spec → popup component
- Dashboard follows: useKpi/useTimeseries hooks → KpiTile → DomainDetailPanel with charts

### Integration Points
- New connectors register in towns/aalen.yaml
- New domains added to backend/app/schemas/ and routers
- New layers toggle in frontend sidebar with domain grouping
- KPI endpoint extended for traffic and energy domains

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond ROADMAP success criteria.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
