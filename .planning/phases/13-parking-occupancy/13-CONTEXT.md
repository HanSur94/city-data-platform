# Phase 13: Parking Occupancy — Stadtwerke Scraper - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Add live parking garage occupancy by scraping sw-aalen.de parking page. Display on map as colored pins and in dashboard as KPI widget.

</domain>

<decisions>
## Implementation Decisions

### Data Source
- Scrape sw-aalen.de/privatkunden/dienstleistungen/parken/parkhausbelegung
- HTML parsing with BeautifulSoup4 or similar
- Poll every 5-10 minutes
- Extract: garage name, free spots, total capacity

### Connector Design
- Follow BaseConnector pattern, override run() for scraping
- Domain: "infrastructure" (new parking features)
- Values: {free_spots, total_spots, occupancy_pct}
- Feature type: point per parking garage with known coordinates
- Data type: SCRAPED

### Map Display
- Point/pin per parking garage
- Color: green (>50% free) -> yellow (20-50% free) -> red (<20% free)
- Label: "Parkhaus Name: 45/120 frei"
- Click popup with details

### Dashboard
- KPI tile showing aggregate parking availability
- "X/Y Parkplatze frei" summary

### Claude's Discretion
- Exact HTML parsing approach for the Stadtwerke page
- Fallback behavior if scrape fails (show stale data with warning)
- Parking garage coordinates (manually geocoded or from OSM)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- BaseConnector with fetch/normalize/persist pipeline
- httpx for async HTTP requests
- KpiTile component for dashboard
- InfrastructureLayer exists for infrastructure domain

### Integration Points
- Add ParkingConnector to backend/app/connectors/
- Add to aalen.yaml
- Create ParkingLayer map component or extend InfrastructureLayer
- Add parking KPI to dashboard

</code_context>

<specifics>
## Specific Ideas

- Stadtwerke operates multiple Parkhauser in Aalen center
- Scraping stability depends on website structure — may break on redesign
- Consider graceful degradation with "Daten nicht verfugbar" on scrape failure

</specifics>

<deferred>
## Deferred Ideas

- Real-time parking prediction
- Historical parking patterns by time of day

</deferred>
