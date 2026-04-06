# Phase 9: Geospatial Enrichment - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

The map gains high-resolution cadastral data, 3D building footprints, elevation context, aerial photos, and satellite imagery as optional base layers. Requirements: GEO-01, GEO-02, GEO-03, GEO-04, GEO-05.

Backend: minimal — WMS/WMTS layers are consumed directly by the frontend. Possibly a small connector for 3D building data if WFS processing needed. Frontend: base layer switcher (radio), geospatial overlay toggles, 3D building extrusion, new Geospatial sidebar group.

</domain>

<decisions>
## Implementation Decisions

### Data Sources & Access
- GEO-01 Cadastral: LGL WMS/WMTS at maps.lgl-bw.de — ALKIS cadastral layer, free for non-commercial use
- GEO-02 3D Buildings: MapLibre fill-extrusion from LGL 3D building WFS or pre-processed GeoJSON — LoD1 with building height
- GEO-03 Elevation: LGL hillshade WMS as raster overlay — pre-rendered, simpler than raw DEM processing
- GEO-04 Orthophotos: LGL DOP WMS as alternative base layer replacing OSM tiles
- GEO-05 Satellite: Copernicus Browser WMS (free, no API key) or ESA Sentinel Hub trial. Defer with "Demnächst verfügbar" if no reliable free WMS found

### Base Layer Switching UX
- Sidebar "Basiskarte" radio group: OSM (default), Orthophoto, Satellit — only one base layer active at a time
- Overlays (cadastral, hillshade) are independent toggles coexisting with any base layer
- 3D buildings toggle enables fill-extrusion on current base. Map auto-tilts slightly when 3D active

### Layer Organization & Performance
- New "Geospatial" sidebar group with sub-sections: Basiskarte (radio), Overlays (toggles), 3D (toggle)
- Lazy-load WMS tiles only when toggled on — reuse raster-opacity toggle pattern from Phase 6 WmsOverlayLayer
- Sentinel-2: defer gracefully if no free WMS available

### Claude's Discretion
No items deferred to Claude's discretion — all grey areas resolved.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- frontend/components/map/WmsOverlayLayer.tsx — WMS raster overlay pattern with opacity toggle
- frontend/components/sidebar/Sidebar.tsx — toggle group pattern with radio/checkbox variants
- frontend/components/map/MapView.tsx — conditional layer rendering, base map style switching

### Established Patterns
- WMS layers use MapLibre raster source with raster-opacity toggle (Phase 6 pattern)
- Sidebar groups: radio for exclusive selection, checkbox for toggles
- page.tsx useUrlState for layer visibility persistence

### Integration Points
- MapView base style switching (replace PMTiles source with WMS raster)
- Sidebar Geospatial group with radio + toggle sub-sections
- page.tsx URL state for base layer selection + overlay visibility

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond ROADMAP success criteria.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
