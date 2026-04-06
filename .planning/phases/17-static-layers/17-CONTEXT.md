# Phase 17: Static Data Layers Expansion - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Add remaining static/semi-static data layers: heat demand per building (KEA-BW), Fernwaerme coverage, cycling infrastructure, demographics grid visualization, road noise WMS.

</domain>

<decisions>
## Implementation Decisions

### Heat Demand (KEA-BW Waermeatlas)
- Source: KEA-BW download (GeoPackage/Shapefile), one-time load
- Color buildings by kWh/m2/y: blue <50, light blue 50-100, green 100-150, yellow 150-200, orange 200-250, red >250
- Display on building footprints (2D) and building faces (3D)

### Fernwaerme Coverage
- Known neighborhoods: Schlossaecker, Weisse Steige, Maiergasse/Talschule, Ostalbklinikum
- Polygon overlay on map, color connected buildings
- Static data, manually defined polygons

### Cycling Infrastructure
- Source: OSM cycling tags (already in road network data)
- Color road segments by infrastructure type
- Dark green = separated cycleway, light green = cycle lane, yellow = advisory, orange = shared, red = none on major road

### Demographics Grid (Zensus 2022)
- ZensusConnector already exists, but no grid visualization
- 100m grid cell choropleth on map
- Toggle between metrics: population density, age, rent, heating type

### Road Noise (LUBW WMS)
- LUBW Umgebungslaermkartierung 2022 WMS
- LDEN and LNight toggle
- Colored bands: green <55dB -> yellow 55-65 -> orange 65-70 -> red 70-75 -> purple >75

### Claude's Discretion
- Whether to use WMS overlay or download vector data for each layer
- How to integrate heat demand data without actual KEA-BW download available
- Fernwaerme polygon coordinates

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- WmsOverlayLayer component for WMS layers
- BuildingsLayer for 3D building coloring
- ZensusConnector + demographics_readings hypertable
- WaterLegend pattern for additional legends
- Existing road network from OSM via OverpassCommunityConnector

### Integration Points
- Add WMS layers for noise map
- Create CyclingLayer component
- Create DemographicsGridLayer component
- Extend BuildingsLayer with heat demand coloring mode
- Add Fernwaerme polygon overlay

</code_context>

<specifics>
Since some data sources require actual downloads (KEA-BW, Fernwaerme), use placeholder/simulated data where downloads are not available at implementation time. The connectors and frontend components should be fully functional, with data loading paths documented for when data becomes available.
</specifics>

<deferred>
## Deferred Ideas
- Vegetation/tree canopy layer (nDOM data)
- Terrain mesh (DGM1)
- Solar potential per roof face (LUBW WMS sampling)
</deferred>
