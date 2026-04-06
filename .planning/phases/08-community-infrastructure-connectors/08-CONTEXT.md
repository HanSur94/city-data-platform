# Phase 8: Community & Infrastructure Connectors - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Citizens can use the map to find waste collection, schools, healthcare, parks, EV charging, roadworks, and solar potential. Requirements: COMM-01, COMM-02, COMM-03, COMM-04, INFR-01, INFR-02, INFR-03, INFR-04.

Backend: new connectors for Overpass API (OSM POIs), Bundesnetzagentur Ladesäulenregister (EV charging CSV), and Energieatlas BW solar potential WMS. Frontend: new Community and Infrastructure map layer groups with category-specific layers and popups.

</domain>

<decisions>
## Implementation Decisions

### Data Sources & Scope
- Waste collection: Overpass API (OSM) for Wertstoffhof locations + iCal feed from Aalen GWA for pickup schedules if available
- Schools/healthcare/parks: Overpass API with amenity tags — schools (amenity=school/kindergarten), healthcare (amenity=pharmacy/hospital/doctors), parks (leisure=park/playground/sports_centre)
- Construction sites/roadworks: Autobahn API (already Phase 7) for Autobahn + OSM construction notes for local roadworks — no Aalen-specific construction API available
- EV charging: Bundesnetzagentur Ladesäulenregister CSV (open data, updated monthly) — official German EV charging registry

### Map Layer Organization & Presentation
- Two new sidebar groups: "Gemeinwesen" (Community: waste, schools, healthcare, parks) and "Infrastruktur" (Infrastructure: roadworks, EV charging, solar)
- Icon strategy: colored circles with category-specific colors — Schools=blue, Healthcare=red, Parks=green, Waste=brown, EV=purple. Consistent with existing layer pattern
- Solar potential: WMS overlay from Energieatlas BW if available; if no WMS endpoint found, defer to Phase 9
- MaStR solar distinction: Phase 7 EnergyLayer already renders with yellow/amber icons — solar potential raster overlays underneath

### Popup Content & Dashboard
- Community POI popups: name, address, category, opening hours (where available), distance from map center. German labels
- EV charging popup: operator, address, plug types (CCS/Type2/CHAdeMO), max power kW, number of points, status if available
- No new KPI tiles — these are spatial/POI layers, not time-series. Add a "Community" count summary in existing dashboard area
- Waste collection popup: next pickup date per waste type (Restmüll, Biomüll, Papier, Gelber Sack) if iCal feed available, otherwise Wertstoffhof hours

### Claude's Discretion
No items deferred to Claude's discretion — all grey areas resolved.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- backend/app/connectors/base.py — BaseConnector with persist(), upsert_feature()
- backend/app/connectors/lubw_wfs.py — WFS connector pattern (similar to Overpass queries)
- frontend/components/map/TrafficLayer.tsx, EnergyLayer.tsx — circle layer patterns with clustering
- frontend/components/map/WmsOverlayLayer.tsx — WMS raster overlay pattern (for solar potential)
- frontend/components/sidebar/Sidebar.tsx — sidebar toggle group pattern (Verkehr, Energie groups from Phase 7)

### Established Patterns
- Connectors register in towns/aalen.yaml
- New domains use features table (spatial POIs are features, not time-series)
- Map layers: useLayerData hook -> GeoJSON source -> MapLibre layer spec -> popup
- WMS overlays: WmsOverlayLayer component with raster-opacity toggle

### Integration Points
- New connectors in aalen.yaml
- New sidebar toggle groups in Sidebar.tsx
- New layer components in MapView.tsx conditional renders
- page.tsx wiring for new layer visibility state

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond ROADMAP success criteria.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
