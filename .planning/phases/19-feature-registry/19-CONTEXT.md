# Phase 19: Feature Registry & Clickable Buildings - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement the unified feature registry from AalenPulse spec Section 5.2. Every spatial object (building, road, stop, sensor, charger, gauge) gets a permanent semantic feature_id. All data attaches to these IDs. Buildings and infrastructure become clickable in 2D/3D with unified data cards showing all attached layers.

This is an architectural refactor touching the database schema, all connectors, the API layer, and the frontend popup system.

</domain>

<decisions>
## Implementation Decisions

### Approach: Additive, Not Destructive
- Do NOT drop existing UUID features table or rename columns
- Add a new `semantic_id` TEXT column to features table (nullable initially)
- Create a cross-domain observations VIEW that unions all 7 hypertables
- Connectors gradually populate semantic_id during their normal upsert flow
- Frontend uses semantic_id when available, falls back to UUID
- This avoids breaking existing functionality during migration

### Semantic ID Scheme
- Buildings: bldg_{source_id} where source_id comes from LoD2 CityGML gml:id or OSM building way_id
- Road segments: road_{source_id} (OSM way ID or TomTom segment ID)
- Bus stops: stop_{gtfs_stop_id}
- Sensors: sensor_{domain}_{source_id} (e.g., sensor_air_uba_238)
- Parking: parking_{slug}
- EV chargers: evcharger_{source_id}
- Gauges: gauge_{source_id}
- Grid cells: grid_{domain}_{lat}_{lon}

### Cross-Domain View
- CREATE VIEW feature_observations AS
  SELECT feature_id, 'air_quality' as domain, time as timestamp, ... FROM air_quality_readings
  UNION ALL SELECT feature_id, 'traffic', time, ... FROM traffic_readings
  UNION ALL ... (all 7 hypertables)
- API endpoint: GET /api/features/{feature_id}/data returns latest per domain

### Clickable Buildings
- BuildingsLayer already renders 3D extrusions
- Add interactiveLayerIds to MapView for building layer
- On click: lookup building feature_id -> fetch /api/features/{id}/data -> show UnifiedBuildingPopup
- UnifiedBuildingPopup sections: Gebaeude-Info, Waerme, Solar, Fernwaerme, Demografie

### Clickable Infrastructure
- EV chargers, parking, bus stops, sensors already have popups
- Enhance existing popups to also query feature observations endpoint for cross-domain data
- Add interactiveLayerIds for all infrastructure layers

### Feature Search
- Search bar in sidebar or top bar
- Queries features table by properties->name, properties->address, semantic_id
- Results as dropdown list, click flies to location and opens popup

### Claude's Discretion
- Exact SQL for the cross-domain view (column mapping across hypertables)
- Migration strategy (Alembic migration vs runtime schema update)
- Search implementation (simple ILIKE vs full-text search)
- How to handle buildings without attached data (show "Keine Daten verfuegbar")

</decisions>

<code_context>
## Existing Code Insights

### Current Schema
- features table: id (UUID PK), town_id, domain, source_id, geometry, properties (JSONB)
- 7 hypertables: air_quality_readings, traffic_readings, water_readings, energy_readings, weather_readings, transit_positions, demographics_readings
- All hypertables have: time, feature_id (UUID FK to features.id), plus domain-specific columns
- Alembic for migrations

### Existing Popups
- ~15 popup components, each domain-specific
- MapView routes clicks to domain-specific popups based on layer source
- BuildingsLayer exists with fill-extrusion-height for 3D

### Integration Points
- Alembic migration to add semantic_id column
- Modify BaseConnector.upsert_feature() to compute and store semantic_id
- New API endpoint /api/features/{feature_id}/data
- New UnifiedBuildingPopup component
- Modify MapView click handling for buildings
- New FeatureSearch component in sidebar

</code_context>

<specifics>
## Specific Ideas

From AalenPulse spec Section 5.4 — per-building query example:
SELECT layer, value, data_type, source, timestamp
FROM observations
WHERE feature_id = 'bldg_DEBWAL330000aBcD'
Result: heat_demand_kwh=187, solar_potential_kwh=1420, solar_installed_kw=8.2, etc.

The frontend popup renders this as a unified building info card. Zero extra API calls.
</specifics>

<deferred>
## Deferred Ideas
- Full migration of all UUIDs to semantic IDs (do additive first)
- Graph relationships between features (building contains solar installation)
- Feature versioning / change history
</deferred>
