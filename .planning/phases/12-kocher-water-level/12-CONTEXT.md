# Phase 12: Kocher Water Level — LHP Integration - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning
**Mode:** Auto-generated from AalenPulse requirements document

<domain>
## Phase Boundary

Add Kocher river water level monitoring via LHP API (Landeruebergreifendes Hochwasserportal). Dashboard gauge widget with color-coded level, trend arrow, sparkline. River visualization on map colored by warning stage.

</domain>

<decisions>
## Implementation Decisions

### Data Source
- Use lhpapi Python library (pip install lhpapi) for Huttlingen gauge
- LHP ident needs lookup at implementation (BW_XXXXX format)
- Poll every 15 minutes
- Data: Wasserstand (cm), Abfluss (m3/s), warning stage 0-4, trend

### Connector Design
- Follow BaseConnector pattern
- Domain: "water" (existing, reuse water_readings hypertable which has level_cm, flow_m3s)
- Feature: single gauge point at Huttlingen location
- Values: {level_cm, flow_m3s, stage, trend}

### Dashboard Widget
- Kocher gauge widget: current cm with color bar
- Green <80cm, Yellow 80-120, Orange 120-160, Red >160
- Trend arrow (rising/falling/stable)
- Sparkline last 7 days from water_readings time-series

### Map Visualization
- Kocher river line colored by warning stage
- Gauge pin at Huttlingen with level readout
- Warning badge when stage >= 1

### Claude's Discretion
- Exact LHP gauge identifier lookup approach
- Sparkline chart library choice (Recharts mini or custom SVG)
- River line geometry source (OSM Kocher way or manual GeoJSON)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- PegelonlineConnector exists for federal waterway gauges (different API but same domain)
- water_readings hypertable: time, feature_id, level_cm, flow_m3s
- WaterLayer.tsx exists showing PEGELONLINE gauges
- KpiTile component for dashboard widgets
- TrendArrow component for directional indicators

### Established Patterns
- Water domain connectors use upsert_feature for gauge location
- KPI queries use TimescaleDB last() for current values
- Dashboard tiles use shadcn/ui Card with optional children slot

### Integration Points
- Add LhpConnector to backend/app/connectors/
- Add to aalen.yaml connectors list
- Extend KPI endpoint with Kocher-specific data
- Add KocherGauge widget to DashboardPanel
- Extend WaterLayer or create KocherLayer for river visualization

</code_context>

<specifics>
## Specific Ideas

- Normal Kocher level ~50cm, flood alert threshold ~120+cm
- Huttlingen gauge ~3km downstream from Aalen center
- Combine with precipitation radar for rain-river correlation (future)
- Store readings for trend analysis, seasonal patterns

</specifics>

<deferred>
## Deferred Ideas

- Flood risk zone overlay correlation with current level
- Rain-river correlation with precipitation radar
- Historical flood event archive

</deferred>
