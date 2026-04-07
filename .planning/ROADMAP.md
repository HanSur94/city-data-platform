# Roadmap: City Data Platform

## Completed Milestones

<details>
<summary>v1.0 — Full Platform (shipped 2026-04-06)</summary>

10 phases, 46 plans, 241 files, ~47,700 lines. Foundation through operator dashboard + multi-town.

See: [v1.0 Archive](.planning/milestones/v1.0-ROADMAP.md) | [v1.0 Requirements](.planning/milestones/v1.0-REQUIREMENTS.md) | [v1.0 Audit](.planning/milestones/v1.0-MILESTONE-AUDIT.md)

</details>

## Current Milestone: v2.0 — AalenPulse Feature Parity

Implement all missing features from the AalenPulse requirements document to reach full 30-layer parity with the specification.

### Phase 11: Traffic Flow — TomTom Integration
- **Goal:** Add real-time traffic flow visualization using TomTom Flow Segment Data API with road segment coloring by congestion ratio
- **Requirements:**
  - REQ-TRAFFIC-01: TomTom connector polling ~35 sample points on Aalen arterial roads (B29, B19, Friedrichstr., Gmunder Str.)
  - REQ-TRAFFIC-02: Road segments colored by congestion ratio (currentSpeed/freeFlowSpeed): green >=0.75, yellow 0.50-0.75, orange 0.25-0.50, red <0.25
  - REQ-TRAFFIC-03: Poll interval 10min rush hours (06-09, 16-19), 30min off-peak
  - REQ-TRAFFIC-04: Store every poll result in traffic_readings for trend analysis
  - REQ-TRAFFIC-05: Frontend TrafficFlowLayer showing colored road segments on map (2D + 3D)
- **Success Criteria:**
  - [ ] TomTom connector fetches speed data for Aalen road segments
  - [ ] Road segments render with congestion-based color gradient on map
  - [ ] Traffic readings stored in TimescaleDB
  - [ ] Dashboard traffic KPI updated with flow status
- **Plans:** 2/2 plans complete
  - [x] 11-01-PLAN.md -- TomTom connector with adaptive polling and road segment storage
  - [x] 11-02-PLAN.md -- Frontend TrafficFlowLayer with sidebar toggle and popup
- **Status:** Planning Complete

### Phase 12: Kocher Water Level — LHP Integration
- **Goal:** Add Kocher river water level monitoring via LHP API with dashboard gauge widget and river visualization
- **Requirements:**
  - REQ-KOCHER-01: LHP connector polling Huttlingen gauge every 15 min via lhpapi
  - REQ-KOCHER-02: Dashboard gauge widget: current cm reading, color-coded bar (green <80, yellow 80-120, orange 120-160, red >160)
  - REQ-KOCHER-03: Trend arrow (rising/falling/stable) + sparkline last 7 days
  - REQ-KOCHER-04: Warning badge when flood stage >= 1
  - REQ-KOCHER-05: Kocher river line on map colored by warning stage
- **Success Criteria:**
  - [ ] LHP connector fetches water level, flow, stage for Huttlingen gauge
  - [ ] Water readings stored in water_readings hypertable
  - [ ] Dashboard shows Kocher gauge widget with color-coded level
  - [ ] Map shows Kocher river colored by warning stage
- **Plans:** 2/2 plans complete
  - [x] 12-01-PLAN.md -- LHP connector with Huttlingen gauge polling and water KPI endpoint
  - [x] 12-02-PLAN.md -- KocherGaugeWidget dashboard + KocherLayer map visualization
- **Status:** Planning Complete

### Phase 13: Parking Occupancy — Stadtwerke Scraper
- **Goal:** Add live parking garage occupancy by scraping sw-aalen.de and displaying on map + dashboard
- **Requirements:**
  - REQ-PARKING-01: Scraper for sw-aalen.de parking page
  - REQ-PARKING-02: Scrape every 5-10 min, extract fill level per parking garage
  - REQ-PARKING-03: Map pins colored green (free) -> yellow (filling) -> red (full)
  - REQ-PARKING-04: Dashboard KPI widget showing parking availability summary
  - REQ-PARKING-05: Click popup: "Parkhaus Stadtmitte: 45/120 frei"
- **Success Criteria:**
  - [ ] Parking scraper extracts occupancy from Stadtwerke website
  - [ ] Parking features created with correct locations
  - [ ] Map shows parking pins with occupancy coloring
  - [ ] Dashboard shows parking KPI tile
- **Plans:** 2/2 plans complete
  - [x] 13-01-PLAN.md -- ParkingConnector scraper, KPI endpoint, TypeScript types
  - [x] 13-02-PLAN.md -- ParkingLayer map component, popup, sidebar toggle, dashboard KPI tile
- **Status:** Planning Complete

### Phase 14: Bus Position Interpolation
- **Goal:** Implement interpolated bus positions from GTFS schedule + GTFS-RT delays, showing moving bus icons on routes
- **Requirements:**
  - REQ-BUS-01: Interpolation engine: for each active trip, calculate position along route shape based on schedule + delay offset
  - REQ-BUS-02: Bus icons moving along route geometry, colored by delay (green <2min, yellow 2-5min, orange 5-10min, red >10min)
  - REQ-BUS-03: Click/hover popup: line number, destination, current delay, next stop
  - REQ-BUS-04: Faint route lines shown when bus layer active
  - REQ-BUS-05: Handle edge cases: dwelling at stop, no delay data, trip not departed, trip completed
  - REQ-BUS-06: Update every 30 seconds with smooth animation between updates
- **Success Criteria:**
  - [ ] Interpolation engine produces lat/lon positions for active OstalbMobil trips
  - [ ] Frontend shows moving bus icons along routes
  - [ ] Bus icons colored by delay status
  - [ ] Popup shows trip details on click
- **Plans:** 2/2 plans complete
  - [x] 14-01-PLAN.md -- BusInterpolationConnector with shape-walking algorithm and scheduler registration
  - [x] 14-02-PLAN.md -- BusPositionLayer, BusRouteLayer, BusPopup frontend components and wiring
- **Status:** Planning Complete

### Phase 15: Air Quality Heatmap — IDW Interpolation
- **Goal:** Create continuous air quality surface across Aalen using IDW spatial interpolation from sensor points
- **Requirements:**
  - REQ-AIR-01: IDW interpolation on 50m x 50m grid from UBA + sensor.community readings
  - REQ-AIR-02: 2D view: translucent color overlay (green -> yellow -> orange -> red -> purple)
  - REQ-AIR-03: Toggle between pollutants: PM2.5 / PM10 / NO2 / O3
  - REQ-AIR-04: Sensor points as pulsing dots with live readings
  - REQ-AIR-05: Click sensor -> time-series popup chart
  - REQ-AIR-06: Recalculate every 5 minutes
- **Success Criteria:**
  - [ ] IDW computation worker produces grid cell values
  - [ ] Heatmap overlay renders on map with correct color ramp
  - [ ] Pollutant toggle switches between PM2.5/PM10/NO2/O3
  - [ ] Sensor point popups show time-series chart
- **Plans:** 2/2 plans complete
  - [x] 15-01-PLAN.md -- AirQualityGridConnector with IDW interpolation algorithm and grid layer filter
  - [x] 15-02-PLAN.md -- AirQualityHeatmapLayer, pollutant toggle, pulsing sensors, time-series popup
- **Status:** Planning Complete

### Phase 16: Live Solar Production & EV Charging Status
- **Goal:** Add computed live solar production per building and real-time EV charger availability
- **Requirements:**
  - REQ-SOLAR-01: Solar production computation: installed_kW (MaStR) x current_irradiance_factor (Bright Sky)
  - REQ-SOLAR-02: 3D view: solar-equipped buildings glow proportional to current output
  - REQ-SOLAR-03: Click building popup with potential vs installed vs current production
  - REQ-EV-01: MobiData BW OCPDB connector for real-time charger status (AVAILABLE/OCCUPIED/INOPERATIVE)
  - REQ-EV-02: Map pins: green=available, red=occupied, gray=offline
  - REQ-EV-03: Icon size proportional to power (11kW AC small, 150kW DC large)
- **Success Criteria:**
  - [ ] Solar production computation runs every 15 min
  - [ ] Buildings with solar show glow/badge in 3D view
  - [ ] EV charger pins show real-time availability status
  - [ ] Click popup shows connector types, operator, live status
- **Plans:** 2/2 plans complete
  - [x] 16-01-PLAN.md -- SolarProductionConnector + EvChargingConnector backend with tests and scheduler registration
  - [x] 16-02-PLAN.md -- SolarGlowLayer, EvChargingLiveLayer frontend components, popups, sidebar wiring
- **Status:** Planning Complete

### Phase 17: Static Data Layers Expansion
- **Goal:** Add remaining static data layers: heat demand, Fernwaerme coverage, cycling infrastructure, demographics grid, road noise map
- **Requirements:**
  - REQ-HEAT-01: Heat demand per building from KEA-BW Waermeatlas, color by kWh/m2/y (blue->green->yellow->orange->red)
  - REQ-FERN-01: Fernwaerme coverage polygons for known neighborhoods
  - REQ-CYCLE-01: Cycling infrastructure overlay from OSM tags (separated/lane/advisory/shared/none)
  - REQ-DEMO-01: Zensus 2022 100m grid cell visualization on map (population density, age, rent, heating)
  - REQ-NOISE-01: LUBW road noise WMS overlay (LDEN/LNight toggle)
- **Success Criteria:**
  - [ ] Heat demand coloring on buildings in 3D view
  - [ ] Fernwaerme polygons visible on map
  - [ ] Cycling infrastructure colors road segments
  - [ ] Demographics grid cells render with choropleth colors
  - [ ] Road noise bands visible from LUBW WMS
- **Plans:** 3/3 plans complete
  - [x] 17-01-PLAN.md -- HeatDemandConnector + CyclingInfraConnector backend with tests
  - [x] 17-02-PLAN.md -- NoiseWmsLayer, FernwaermeLayer, DemographicsGridLayer frontend
  - [x] 17-03-PLAN.md -- HeatDemandLayer + CyclingLayer frontend with popups and legends
- **Status:** Planning Complete

### Phase 18: Data Transparency UI
- **Goal:** Add data provenance badges, metadata popups, and freshness indicators per layer
- **Requirements:**
  - REQ-TRANS-01: Data type badges on every layer: LIVE / SCRAPED / INTERPOLATED / MODELED / STATIC
  - REQ-TRANS-02: Layer toggle panel info icon -> metadata popup with source, data type, last updated, interval, license
  - REQ-TRANS-03: Stale data warning badge when last update > 2x expected interval
  - REQ-TRANS-04: Dashboard widget footer format: "SMARD . 14:30 . LIVE"
  - REQ-TRANS-05: Per-feature popup includes data source section with full source name, link, data type badge, timestamp
- **Success Criteria:**
  - [ ] Every active layer shows data type badge
  - [ ] Info icon opens metadata popup with 5 required fields
  - [ ] Stale layers show warning indicator
  - [ ] Widget footers show source + timestamp + badge
  - [ ] Feature popups include data source section
- **Plans:** 2/2 plans complete
  - [x] 18-01-PLAN.md -- Backend metadata endpoint, frontend metadata registry, DataTypeBadge and DataSourceSection components
  - [x] 18-02-PLAN.md -- Sidebar badges + info icons, KPI widget footers, popup DataSourceSection wiring
- **Status:** Planning Complete

### Phase 19: Feature Registry & Clickable Buildings
- **Goal:** Implement unified feature registry with semantic IDs, cross-domain data attachment, and make every building/infrastructure object clickable in 2D and 3D views with a unified data card
- **Requirements:**
  - REQ-REGISTRY-01: Semantic feature_id scheme (bldg_{gml_id}, road_osm_{way_id}, stop_{gtfs_id}, etc.) replacing UUIDs
  - REQ-REGISTRY-02: Unified observations table (or cross-domain join view) so all data layers attach to features by feature_id
  - REQ-REGISTRY-03: Spatial matching at ingestion — MaStR solar, heat demand, Fernwaerme matched to nearest building
  - REQ-REGISTRY-04: Per-building data stack API: GET /api/features/{feature_id}/observations returns all attached data
  - REQ-REGISTRY-05: Every building clickable in 2D (footprint) and 3D (extruded block) — click opens unified data card
  - REQ-REGISTRY-06: Unified BuildingPopup showing all attached layers: heat demand, solar potential, solar installed, solar production, Fernwaerme, demographics, energy class
  - REQ-REGISTRY-07: Infrastructure objects (EV chargers, parking, bus stops, sensors) also clickable with unified popup
  - REQ-REGISTRY-08: Feature search — type address or feature name to fly-to and open popup
- **Success Criteria:**
  - [ ] Features table uses semantic IDs instead of random UUIDs
  - [ ] Cross-domain query returns all data for a single building
  - [ ] Buildings clickable in both 2D and 3D views
  - [ ] Unified BuildingPopup shows all attached data layers
  - [ ] Infrastructure objects clickable with data card
- **Plans:** 2/3 plans executed
  - [x] 19-01-PLAN.md — Semantic ID migration, cross-domain observations VIEW, feature data API
  - [x] 19-02-PLAN.md — Clickable buildings with UnifiedBuildingPopup in 2D/3D
  - [ ] 19-03-PLAN.md — Infrastructure popup enhancements and feature search
- **Status:** Planning Complete
