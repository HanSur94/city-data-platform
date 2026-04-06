# Phase 18: Data Transparency UI - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Add data provenance badges (LIVE/SCRAPED/INTERPOLATED/MODELED/STATIC) to every layer, metadata popups with source/license/freshness info, stale data warnings, and widget footer annotations.

</domain>

<decisions>
## Implementation Decisions

### Data Type Badges
- Every layer gets a visible badge: LIVE / SCRAPED / INTERPOLATED / MODELED / STATIC
- Badge colors: LIVE=green, SCRAPED=yellow, INTERPOLATED=blue, MODELED=purple, STATIC=gray
- Displayed in layer toggle panel next to layer name

### Layer Metadata Popup
- Info icon (i) in layer toggle panel
- Click opens popup with: source name+URL, data type badge, last updated, update interval, license
- If data stale (last update > 2x expected interval), show warning badge

### Dashboard Widget Footers
- Each KPI widget footer shows: source abbreviation + last updated timestamp + data type badge
- Format: "SMARD . 14:30 . LIVE" or "KEA-BW . 2025 . MODELED"

### Feature Popup Data Source Section
- Every feature popup includes "Datenquelle" section at bottom
- Full source name and link, data type badge, timestamp
- For computed/modeled data: brief methodology explanation

### Backend Support
- Layer metadata endpoint: GET /api/metadata/layers returning per-layer metadata
- Each layer metadata includes: source_name, source_url, data_type, update_interval_seconds, license, last_updated

### Claude's Discretion
- Exact UI component design for badges and metadata popup
- How to wire metadata into existing layer components without refactoring all layers
- Backend metadata registry structure

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- CONNECTOR_ATTRIBUTION dict in routers (maps connector_class to attribution)
- Connector health endpoint already tracks last_successful_fetch per connector
- FreshnessIndicator component exists for staleness display
- shadcn/ui Popover for metadata popups

### Integration Points
- Add /api/metadata/layers endpoint to backend
- Create LayerMetadata registry mapping domains to metadata
- Create DataTypeBadge component
- Modify Sidebar layer toggles to include badge + info icon
- Modify KpiTile to show footer with source info
- Modify all popup components to include data source section

</code_context>

<specifics>
Per-layer classification from AalenPulse requirements:
- Traffic flow: LIVE (TomTom)
- Construction sites: LIVE+SCRAPED
- Bus positions: INTERPOLATED
- Air quality sensors: LIVE, Air quality heatmap: INTERPOLATED
- Energy mix/CO2/price: LIVE (SMARD)
- Solar production: MODELED
- Parking: SCRAPED
- EV charging: LIVE (OCPDB)
- Weather: LIVE (DWD)
- Kocher water: LIVE (LHP)
- Buildings, terrain, roads: STATIC
- Heat demand: MODELED (KEA-BW)
- Noise map: MODELED (LUBW)
- Demographics: STATIC (Zensus)
- Cycling: STATIC (OSM)
</specifics>

<deferred>
## Deferred Ideas
- Methodology explanation tooltips for MODELED data types
- Data quality scoring per source
</deferred>
