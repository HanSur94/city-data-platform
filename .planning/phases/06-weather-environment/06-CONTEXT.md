# Phase 6: Weather & Environment Connectors - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning
**Mode:** Auto-generated (connector expansion phase — discuss skipped)

<domain>
## Phase Boundary

AQI visualization with EU/WHO health-based color scale, historical AQI trends (90+ days), real-time water levels from PEGELONLINE, HVZ BW state waterway monitoring (Kocher), flood hazard map WMS overlay, noise map WMS overlay, LUBW environmental WFS layers. Requirements: WAIR-05, WAIR-06, WATR-01, WATR-02, WATR-03, WATR-04, WATR-05.

Backend: new connectors for PEGELONLINE and HVZ BW. Frontend: new map layers for water/flood/noise/environment + AQI enhancements.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion. Follow established patterns:
- BaseConnector pattern for new connectors
- Existing map layer pattern (TransitLayer/AQILayer) for new frontend layers
- WMS layers can be added directly to MapLibre as raster sources
- PEGELONLINE REST API (free, no key): pegelonline.wsv.de
- HVZ BW: hvz.lubw.baden-wuerttemberg.de
- LUBW flood/noise maps: WMS endpoints
- AQI visualization enhancement: EU/WHO color scale already exists in schemas/geojson.py

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- backend/app/connectors/base.py — BaseConnector with persist(), upsert_feature(), _update_staleness()
- backend/app/connectors/uba.py, sensor_community.py, weather.py — air quality connector patterns
- frontend/components/map/AQILayer.tsx, TransitLayer.tsx — layer component patterns
- frontend/hooks/useLayerData.ts — data fetching with polling
- backend/app/routers/layers.py — GeoJSON layer endpoint with ?at= param

### Integration Points
- New connectors register in towns/aalen.yaml
- New layers toggle in frontend sidebar
- WMS layers use MapLibre raster source (no backend connector needed)

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond ROADMAP success criteria.

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>
