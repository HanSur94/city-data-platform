# Roadmap: City Data Platform

## Overview

Ten phases build from an immovable foundation (schema + town config + Docker) through a first complete vertical slice (transit + air quality ingestion, query API, map, dashboard), then expand outward to all data domains in waves of related connectors (weather/environment, traffic/energy, community/infrastructure), deepen the geospatial experience, and close with operator features and multi-town validation. Every data domain feeds the same pipeline; every phase delivers something runnable and verifiable.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Docker environment, TimescaleDB/PostGIS schema, town config, BaseConnector abstraction (completed 2026-04-05)
- [ ] **Phase 2: First Connectors** - Transit (GTFS) and air quality connectors writing validated data to hypertables
- [ ] **Phase 3: Query API** - FastAPI routers serving GeoJSON, time-series, and KPI responses for first two domains
- [ ] **Phase 4: Map Frontend** - Next.js + MapLibre map with transit and air quality layers, layer toggle, freshness indicators
- [ ] **Phase 5: Dashboard** - KPI tiles, time-series charts, date range picker, and permalink URLs alongside the map
- [ ] **Phase 6: Weather & Environment Connectors** - Weather, AQI visualization, water levels, flood/noise/env overlays
- [ ] **Phase 7: Traffic & Energy Connectors** - Road traffic counts, Autobahn warnings, MobiData BW, SMARD energy mix
- [ ] **Phase 8: Community & Infrastructure Connectors** - Waste, schools, healthcare, parks, EV charging, roadworks, solar
- [ ] **Phase 9: Geospatial Enrichment** - Cadastral data, 3D buildings, elevation, orthophotos, satellite imagery
- [ ] **Phase 10: Operator & Multi-Town** - Admin health dashboard, demographics data, second-town validation, theming

## Phase Details

### Phase 1: Foundation
**Goal**: A running local environment with correct schema, town config, and connector abstraction that all future work builds on
**Depends on**: Nothing (first phase)
**Requirements**: PLAT-01, PLAT-02, PLAT-06, PLAT-07, PLAT-08, GEO-06
**Success Criteria** (what must be TRUE):
  1. `docker-compose up` starts PostgreSQL + TimescaleDB + PostGIS + FastAPI with no errors
  2. Alembic migration creates all domain hypertables, the `features` spatial table, and the `towns`/`sources` config tables with retention policies applied
  3. `towns/aalen.yaml` and `towns/example.yaml` exist with all required fields; loading either via the config loader produces a validated Town object with no code changes between them
  4. BaseConnector abstract class is defined; a stub connector that inherits it passes the test suite
  5. Administrative boundary polygons for Aalen are loaded into PostGIS via the BKG VG250 source
**Plans**: 4 plans

Plans:
- [x] 01-01-PLAN.md — Docker Compose + project structure + Alembic scaffold + test conftest
- [x] 01-02-PLAN.md — Alembic migration: hypertables, PostGIS spatial table, retention policies
- [x] 01-03-PLAN.md — Town YAML config + Pydantic loader + BaseConnector + StubConnector
- [x] 01-04-PLAN.md — FastAPI lifespan wiring + BKG VG250 boundary import script

### Phase 2: First Connectors
**Goal**: Transit and air quality data flow continuously from upstream sources through validated Pydantic models into TimescaleDB hypertables with staleness tracking
**Depends on**: Phase 1
**Requirements**: TRAF-01, TRAF-02, WAIR-01, WAIR-02, WAIR-03, WAIR-04
**Success Criteria** (what must be TRUE):
  1. GTFSConnector downloads NVBW GTFS feed, parses stops and route shapes, and writes them to the `features` table on scheduler run; GTFS-RT positions/delays write to the transit hypertable where feed is available
  2. AQI connectors (UBA + Sensor.community) fetch current readings and write PM10, PM2.5, NO2, O3 values to the air quality hypertable on their configured cron intervals
  3. DWD/Bright Sky weather connector writes current conditions and MOSMIX forecasts to the weather hypertable
  4. Every connector records `last_successful_fetch` and validation error counts; a fetch that returns HTTP 200 with empty payload is treated as failure
  5. Running `pytest tests/connectors/` passes with live-endpoint integration tests for both connectors
**Plans**: 5 plans

Plans:
- [x] 02-01-PLAN.md — Wave 0 foundation: migration 002, BaseConnector persist(), scheduler.py, test scaffolding, new packages
- [x] 02-02-PLAN.md — UBA + Sensor.community air quality connectors (WAIR-03, WAIR-04)
- [x] 02-03-PLAN.md — Bright Sky weather connector (WAIR-01, WAIR-02)
- [x] 02-04-PLAN.md — GTFS static connector: stops + route shapes to features table (TRAF-01)
- [x] 02-05-PLAN.md — GTFS-RT connector + aalen.yaml wiring + FastAPI scheduler startup (TRAF-02)

### Phase 3: Query API
**Goal**: FastAPI exposes clean, town-scoped GeoJSON, time-series, and KPI endpoints that the frontend can consume without ever touching the database directly
**Depends on**: Phase 2
**Requirements**: PLAT-03, PLAT-04, PLAT-05
**Success Criteria** (what must be TRUE):
  1. `GET /api/layers/transit?town=aalen` returns a valid GeoJSON FeatureCollection of stops and route polylines
  2. `GET /api/layers/air_quality?town=aalen` returns a GeoJSON FeatureCollection with current AQI readings and health-tier color values
  3. `GET /api/timeseries/air_quality?town=aalen&start=...&end=...` returns time-ordered readings for the requested window
  4. `GET /api/kpi?town=aalen` returns current AQI, latest weather summary, and transit coverage metrics in a structured JSON response
  5. Every endpoint response includes `attribution` and `last_updated` fields; requests for an unknown town return a 404 with a clear error
**Plans**: 3 plans

Plans:
- [x] 03-01-PLAN.md — Foundation: dependencies.py, schemas package, test stubs (RED state), geojson-pydantic install
- [ ] 03-02-PLAN.md — Layers + connectors routers: GET /api/layers/{domain} and GET /api/connectors/health
- [x] 03-03-PLAN.md — Timeseries + KPI routers + main.py wiring: GET /api/timeseries/{domain} and GET /api/kpi

### Phase 4: Map Frontend
**Goal**: Citizens can open the app, see Aalen on a map, toggle transit and air quality layers, and know how fresh the data is
**Depends on**: Phase 3
**Requirements**: MAP-01, MAP-02, MAP-03, MAP-04, MAP-05, MAP-07, MAP-08
**Success Criteria** (what must be TRUE):
  1. App loads at port 4000 showing Aalen centered on a MapLibre GL JS map with OpenStreetMap/basemap.de tiles
  2. Transit layer renders bus/train stops and route polylines as vector tiles via Martin; clustering activates at city scale and dissolves to individual stops at street scale
  3. Air quality layer renders sensor locations color-coded by AQI health tier with a visible legend
  4. Each layer has a toggle switch; turning a layer off removes it from the map without a page reload
  5. Clicking or hovering a map feature opens a detail popup showing current readings and a data freshness timestamp
  6. Layout is responsive and usable on a 768px-wide tablet screen
**Plans**: 3 plans

Plans:
- [x] 04-01-PLAN.md — Next.js scaffold: dependencies, types, hooks, lib utilities, Dockerfile, docker-compose frontend service
- [x] 04-02-PLAN.md — Map shell + sidebar: MapView with PMTiles base, layout, layer toggles, legends
- [x] 04-03-PLAN.md — Data layers + popups + checkpoint: TransitLayer, AQILayer, FeaturePopup, FreshnessIndicator, human verify
**UI hint**: yes

### Phase 5: Dashboard
**Goal**: Citizens and officials can view KPI tiles, trend charts, and a time slider alongside the map, and share a specific view via URL
**Depends on**: Phase 4
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, MAP-06
**Success Criteria** (what must be TRUE):
  1. KPI summary tiles show current AQI, latest weather summary, and transit domain metrics alongside the map without navigation
  2. A date range picker lets the user select a custom window; time-series charts update to reflect the selection using continuous-aggregate backed queries
  3. Clicking a domain KPI tile opens a per-domain detail panel with extended charts and source attribution
  4. A time slider on the map moves historical data snapshots; the map layers reflect the selected timestamp
  5. The current view state (active layers, time range, map viewport) is encoded in the URL; pasting that URL into a new browser tab restores the exact same view
  6. Layout is usable on desktop and tablet (768px+) with no horizontal scroll
**Plans**: 8 plans

Plans:
- [x] 05-01-PLAN.md — Backend: add ?at= timestamp param to /api/layers/{domain}
- [x] 05-02-PLAN.md — Frontend: install recharts + add shadcn chart/calendar/popover/slider
- [x] 05-03-PLAN.md — Frontend: TypeScript types + useKpi/useTimeseries/useUrlState hooks
- [x] 05-04-PLAN.md — Frontend: KpiTile + TrendArrow + DashboardPanel container
- [x] 05-05-PLAN.md — Frontend: DateRangePicker + TimeSeriesChart + DomainDetailPanel
- [x] 05-06-PLAN.md — Frontend: TimeSlider + MapView historicalTimestamp prop
- [x] 05-07-PLAN.md — Frontend: page.tsx full wiring + URL permalink state
- [ ] 05-08-PLAN.md — Human verify: all 6 Phase 5 requirements
**UI hint**: yes

### Phase 6: Weather & Environment Connectors
**Goal**: Weather forecasts, full AQI visualization, water levels, and environmental overlays are live on the map and in the dashboard
**Depends on**: Phase 5
**Requirements**: WAIR-05, WAIR-06, WATR-01, WATR-02, WATR-03, WATR-04, WATR-05
**Success Criteria** (what must be TRUE):
  1. Air quality index is displayed with EU/WHO health-based color scale; toggling the AQI layer shows all sensor locations color-coded by tier
  2. Historical AQI trend charts show at least 90 days of UBA and Sensor.community data with no missing-data gaps beyond expected upstream outages
  3. Real-time water level gauge readings from PEGELONLINE appear on the map for Neckar stations near Aalen (note: Kocher is a state river not in PEGELONLINE; WATR-02 scope is Neckar federal stations)
  4. Flood hazard map (HQ100 + statutory USG zones) and railway noise map (EBA Lden) are available as toggleable WMS overlay layers
  5. LUBW environmental WFS layers (Naturschutzgebiet, Wasserschutzgebiet) can be toggled on the map
**Plans**: 5 plans

Plans:
- [ ] 06-01-PLAN.md — Backend: base.py water branch + PegelonlineConnector + scheduler + aalen.yaml (WATR-01, WATR-02)
- [ ] 06-02-PLAN.md — AQI: EEA EAQI 6-tier scale in geojson.py + layers.py + AQILayer.tsx + AQILegend (WAIR-05)
- [ ] 06-03-PLAN.md — Backend: LubwWfsConnector fetching nature/water protection zones to features table (WATR-05)
- [ ] 06-04-PLAN.md — Frontend: WaterLayer + WmsOverlayLayer + Sidebar toggles + MapView + page.tsx wiring (WATR-01/03/04/05)
- [ ] 06-05-PLAN.md — 90-day AQI backfill script + human verify checkpoint (WAIR-06)
**UI hint**: yes

### Phase 7: Traffic & Energy Connectors
**Goal**: Road traffic flow, highway warnings, MobiData BW data, and the German electricity mix are visible on map and dashboard
**Depends on**: Phase 6
**Requirements**: TRAF-03, TRAF-04, TRAF-05, ENRG-01, ENRG-02, ENRG-03, ENRG-04
**Success Criteria** (what must be TRUE):
  1. BASt permanent traffic count stations near Aalen appear on the map with current vehicle flow rates; historical hourly counts are accessible in the detail panel
  2. Active Autobahn roadworks and closures on the nearby A7 appear on the map with detour information from the Autobahn API
  3. MobiData BW traffic counts and bike/sharing data are ingested and visible as a toggleable map layer
  4. Current German electricity generation mix by source (SMARD, 15-min resolution) is displayed as a KPI tile and trend chart on the dashboard
  5. Renewable energy installations in Ostalbkreis (MaStR registry — solar, wind, batteries) render on the map; existing solar installations on buildings are distinguishable from other renewables
  6. Electricity wholesale price trend (SMARD) and Fraunhofer Energy-Charts statistics are shown in the energy domain detail panel
**Plans**: TBD
**UI hint**: yes

### Phase 8: Community & Infrastructure Connectors
**Goal**: Citizens can use the map to find waste collection, schools, healthcare, parks, EV charging, roadworks, and solar potential
**Depends on**: Phase 7
**Requirements**: COMM-01, COMM-02, COMM-03, COMM-04, INFR-01, INFR-02, INFR-03, INFR-04
**Success Criteria** (what must be TRUE):
  1. Waste collection schedules and Wertstoffhof locations are visible on the map with pickup day information in the feature popup
  2. Schools (Kita and Schule), healthcare facilities (doctors, pharmacies, hospitals, emergency services), and public spaces (parks, playgrounds, sports facilities) are each a separate toggleable map layer
  3. Active construction sites and roadworks with detour information appear on the map from a live data source
  4. EV charging stations from the Bundesnetzagentur Ladesäulenregister render on the map with plug type and power rating in the popup
  5. Roof solar potential map (where BW/municipal data is available) is displayed as a raster overlay; buildings with existing solar installations from MaStR are highlighted distinctly
**Plans**: TBD
**UI hint**: yes

### Phase 9: Geospatial Enrichment
**Goal**: The map gains high-resolution cadastral data, 3D building footprints, elevation context, aerial photos, and satellite imagery as optional base layers
**Depends on**: Phase 8
**Requirements**: GEO-01, GEO-02, GEO-03, GEO-04, GEO-05
**Success Criteria** (what must be TRUE):
  1. Cadastral and topographic data from LGL Baden-Württemberg is available as a toggleable overlay layer
  2. LoD1/LoD2 3D building models from LGL render on the map with extrusion height; buildings are visually distinguishable from the flat base map
  3. The 1m digital elevation model from LGL is available as a hillshade or contour overlay option
  4. LGL aerial orthophotos are available as an optional base layer that replaces the OSM base map when selected
  5. Copernicus Sentinel-2 satellite imagery (10m resolution) is available as an optional base layer
**Plans**: TBD
**UI hint**: yes

### Phase 10: Operator & Multi-Town
**Goal**: An operator can monitor connector health, a second town can be onboarded via a single YAML file, and demographic statistics complete the data offering
**Depends on**: Phase 9
**Requirements**: PLAT-09, DEMO-01, DEMO-02, DEMO-03, DEMO-04
**Success Criteria** (what must be TRUE):
  1. The admin health dashboard shows each connector's last-fetch timestamp, error rate, and staleness status (green/yellow/red thresholds per domain); an operator can diagnose a silent upstream failure without reading logs
  2. A second town (e.g., a stub Ulm config) can be added by creating a new YAML file in `towns/`; running `docker-compose up` with `TOWN=ulm` serves that town's data with zero code changes
  3. Population and demographic data (Statistik BW, Zensus 2022, Wegweiser Kommune, Bundesagentur) are available in a demographics domain detail panel with time-series indicators
  4. Data source attribution is displayed in the UI per active layer, compliant with Datenlizenz Deutschland requirements
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 4/4 | Complete   | 2026-04-05 |
| 2. First Connectors | 0/5 | Not started | - |
| 3. Query API | 2/3 | In Progress|  |
| 4. Map Frontend | 2/3 | In Progress|  |
| 5. Dashboard | 7/8 | In Progress|  |
| 6. Weather & Environment Connectors | 0/5 | Not started | - |
| 7. Traffic & Energy Connectors | 0/TBD | Not started | - |
| 8. Community & Infrastructure Connectors | 0/TBD | Not started | - |
| 9. Geospatial Enrichment | 0/TBD | Not started | - |
| 10. Operator & Multi-Town | 0/TBD | Not started | - |
