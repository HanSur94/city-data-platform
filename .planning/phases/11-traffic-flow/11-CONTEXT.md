# Phase 11: Traffic Flow — TomTom Integration - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning
**Mode:** Auto-generated from AalenPulse requirements document

<domain>
## Phase Boundary

Add real-time traffic flow visualization using TomTom Flow Segment Data API. Road segments on the map are colored by congestion ratio (currentSpeed/freeFlowSpeed): green >= 0.75, yellow 0.50-0.75, orange 0.25-0.50, red < 0.25. Poll 10min rush, 30min off-peak. Store readings for trend analysis.

</domain>

<decisions>
## Implementation Decisions

### Data Source
- Use TomTom Flow Segment Data API (free tier: 2,500 calls/day)
- ~35 sample points on arterial roads (B29, B19, Friedrichstr., Gmunder Str.)
- API key stored in connector config (aalen.yaml)

### Connector Design
- Follow BaseConnector pattern (fetch → normalize → persist)
- Override run() to upsert road segment features first, then store speed observations
- Domain: "traffic" (existing domain, reuse traffic_readings hypertable)
- Values: {speed_kmh, freeflow_kmh, congestion_ratio, confidence}
- Feature type: road segments with LineString geometry from TomTom response

### Map Layer
- New TrafficFlowLayer component (LineLayerSpecification, not circles)
- Road segments as colored lines, NOT circles like BASt stations
- Color by congestion_ratio using MapLibre data-driven styling
- Line width proportional to road importance

### Claude's Discretion
- Exact TomTom API endpoint URL and parameter choices
- How to define the 35 sample road segments (pre-configured coordinates or dynamic discovery)
- Differentiation from existing BaSt TrafficLayer (rename existing to TrafficCountLayer?)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- BaseConnector with fetch/normalize/persist pipeline
- traffic_readings hypertable already exists (vehicle_count_total, speed_avg_kmh, congestion_level)
- TrafficLayer.tsx exists but shows BASt count stations as circles
- useLayerData() hook for fetching GeoJSON
- KPI traffic section in kpi.py

### Established Patterns
- Connectors return Observation(feature_id, domain="traffic", values={...})
- Map layers use Source + Layer from react-map-gl/maplibre
- Town config in aalen.yaml with connector_class + poll_interval + config dict

### Integration Points
- Add TomTomConnector to backend/app/connectors/
- Register in CONNECTOR_REGISTRY
- Add config to towns/aalen.yaml
- Add TrafficFlowLayer to frontend/components/map/
- Wire into MapView.tsx
- Add layer toggle in sidebar

</code_context>

<specifics>
## Specific Ideas

From AalenPulse requirements:
- Congestion ratio = currentSpeed / freeFlowSpeed
- Color bands: green >= 0.75, yellow 0.50-0.75, orange 0.25-0.50, red < 0.25
- Historical baseline after 2+ weeks: compare current to historical median per weekday+timeslot

</specifics>

<deferred>
## Deferred Ideas

- Historical baseline comparison (requires 2+ weeks of data)
- WebSocket push for real-time traffic updates
- Traffic trend charts per road segment (Phase 4 of original spec)

</deferred>
