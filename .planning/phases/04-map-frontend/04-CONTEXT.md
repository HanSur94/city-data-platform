# Phase 4: Map Frontend - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Citizens can open the app, see Aalen on a map, toggle transit and air quality layers, and know how fresh the data is. Next.js frontend on port 4000 with MapLibre GL JS, consuming the Phase 3 API endpoints. Requirements: MAP-01, MAP-02, MAP-03, MAP-04, MAP-05, MAP-07, MAP-08.

</domain>

<decisions>
## Implementation Decisions

### Map Layout & Controls
- Left sidebar panel for layer toggles — collapsible on mobile, standard map UI pattern
- Legend displayed inside the sidebar, below toggles — always visible when sidebar open
- Base map: OpenStreetMap via Protomaps PMTiles — self-hostable, no API key needed
- Light theme — better readability for officials, standard for map apps

### Data Visualization
- Air quality: **Heatmap overlay** — interpolated color field across the city (like weather radar), health-tier colors (green/yellow/orange/red/purple)
- Transit stops: Small dots with clustering — cluster at zoom <14, individual stops at street level
- Route polylines: Colored lines by route type — bus=blue, train=red, tram=green
- Popup content: Compact card — value + unit + freshness timestamp, 200px max width

### Technical Approach
- Next.js with App Router + TypeScript — `create-next-app` standard setup
- react-map-gl + MapLibre GL JS for map integration
- State management: React useState + URL params — simple enough for map state
- Styling: Tailwind CSS + shadcn/ui as per stack research
- Port 4000 (not 3000 — Grafana conflict on target system)

### Claude's Discretion
- Component file structure within the Next.js app
- Exact PMTiles base map URL/file
- Clustering algorithm parameters
- Heatmap interpolation radius and intensity settings
- Responsive breakpoints for tablet layout

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- backend/app/routers/layers.py — GET /api/layers/{domain} returns GeoJSON
- backend/app/routers/kpi.py — GET /api/kpi returns summary data
- backend/app/routers/connectors.py — GET /api/connectors/health
- backend/app/schemas/geojson.py — aqi_tier() color function, VALID_DOMAINS

### Established Patterns
- FastAPI backend on port 8000
- GeoJSON FeatureCollection responses with attribution field
- Town-scoped queries via ?town= parameter

### Integration Points
- Frontend fetches from http://localhost:8000/api/*
- docker-compose.yml needs frontend service added
- Reverse proxy (nginx) not needed yet for dev

</code_context>

<specifics>
## Specific Ideas

- The heatmap should feel like a weather radar — smooth interpolated colors, not individual points
- Transit routes should be visually distinct by type (bus vs train vs tram)
- Freshness timestamp in popups should show relative time ("2 min ago") not absolute

</specifics>

<deferred>
## Deferred Ideas

- 3D building extrusion (Phase 9)
- Time slider for historical data (Phase 5)
- Shareable permalink URLs (Phase 5)
- deck.gl overlays for high-density data (future optimization)

</deferred>
