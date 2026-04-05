# Requirements: City Data Platform

**Defined:** 2026-04-05
**Core Value:** Citizens and city officials can see all publicly available city data in one place, on a map, updated live — no technical expertise required.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Map & Visualization

- [ ] **MAP-01**: Interactive map centered on configured town with pan/zoom
- [ ] **MAP-02**: Toggleable data layers per domain (transport, air, energy, water, etc.)
- [ ] **MAP-03**: Vector tile rendering for performant display (not raw GeoJSON)
- [ ] **MAP-04**: Layer legend with color coding and icons per data type
- [ ] **MAP-05**: Zoom-appropriate detail levels (cluster at city scale, detail at street scale)
- [ ] **MAP-06**: Time slider to view historical data snapshots on map
- [ ] **MAP-07**: Click/hover on map features shows detail popup with current readings
- [ ] **MAP-08**: Base map with OpenStreetMap / basemap.de tiles

### Dashboard

- [ ] **DASH-01**: KPI summary tiles showing key metrics per domain (e.g., current AQI, transit delays, energy mix)
- [ ] **DASH-02**: Time-series charts with configurable date range picker
- [ ] **DASH-03**: Per-domain detail panels accessible from dashboard or map
- [ ] **DASH-04**: Shareable/permalink URLs that encode current view, time, and active layers
- [ ] **DASH-05**: Responsive layout — usable on desktop and tablet

### Transport & Traffic

- [ ] **TRAF-01**: Public transport routes and stops on map (NVBW GTFS — 3,688 routes, 55,284 stops)
- [ ] **TRAF-02**: Real-time transit positions/delays where available (GTFS-RT via gtfs.de)
- [ ] **TRAF-03**: Traffic count stations on map with flow data (BASt permanent counters near Aalen)
- [ ] **TRAF-04**: Autobahn roadworks, warnings, and closures for nearby A7 (Autobahn API)
- [ ] **TRAF-05**: MobiData BW traffic counts and sharing/bike data integration

### Weather & Air Quality

- [ ] **WAIR-01**: Current weather conditions for configured town (DWD via Bright Sky — no API key)
- [ ] **WAIR-02**: Weather forecast overlay (MOSMIX point forecasts from DWD)
- [ ] **WAIR-03**: Air quality readings from UBA station in Aalen (PM10, PM2.5, NO₂, O₃)
- [ ] **WAIR-04**: Citizen-science air quality sensors (Sensor.community — multiple sensors in Ostalbkreis)
- [ ] **WAIR-05**: Air quality index (AQI) visualization with health-based color scale
- [ ] **WAIR-06**: Historical air quality trends (time-series from UBA + Sensor.community)

### Energy

- [ ] **ENRG-01**: Current German electricity generation mix by source (SMARD — 15-min resolution)
- [ ] **ENRG-02**: Regional renewable energy installations on map (MaStR — every solar panel, wind turbine, battery in Ostalbkreis)
- [ ] **ENRG-03**: Electricity wholesale price trend (SMARD)
- [ ] **ENRG-04**: Energy statistics dashboard (Fraunhofer Energy-Charts data)

### Water & Environment

- [ ] **WATR-01**: Real-time water levels at nearby gauging stations (PEGELONLINE REST API)
- [ ] **WATR-02**: State waterway monitoring — Kocher and tributaries (HVZ Baden-Württemberg)
- [ ] **WATR-03**: Flood hazard map overlay (LUBW Hochwassergefahrenkarten — HQ10 to HQextrem via WMS)
- [ ] **WATR-04**: Noise map overlay (LUBW road noise + EBA railway noise via WMS)
- [ ] **WATR-05**: LUBW environmental data layers (water quality, nature conservation via WFS)

### Demographics & Statistics

- [ ] **DEMO-01**: Population and demographic data for configured town (Statistik BW via GENESIS API)
- [ ] **DEMO-02**: Zensus 2022 data at municipal level + 100m grid (REST API + WMS)
- [ ] **DEMO-03**: Wegweiser Kommune indicators (700+ indicators, CC0 license)
- [ ] **DEMO-04**: Employment/unemployment data (Bundesagentur für Arbeit)

### Geospatial & 3D

- [ ] **GEO-01**: Cadastral and topographic base data from LGL Baden-Württemberg
- [ ] **GEO-02**: 3D building models (LoD1/LoD2) from LGL — visualized on map
- [ ] **GEO-03**: Digital elevation model (1m DEM from LGL)
- [ ] **GEO-04**: Aerial orthophotos from LGL as optional base layer
- [ ] **GEO-05**: Satellite imagery layer (Copernicus Sentinel-2, 10m resolution)
- [ ] **GEO-06**: Administrative boundaries (BKG VG250)

### Community & Services

- [ ] **COMM-01**: Waste collection schedules and recycling locations/Wertstoffhöfe on map
- [ ] **COMM-02**: Schools and childcare (Kita/Schule) — locations, types on map
- [ ] **COMM-03**: Healthcare facilities — doctors, pharmacies, hospitals, emergency services on map
- [ ] **COMM-04**: Public spaces — parks, playgrounds, sports facilities on map

### Infrastructure & Construction

- [ ] **INFR-01**: Active construction sites and roadworks with detour info
- [ ] **INFR-02**: EV charging stations on map (Bundesnetzagentur Ladesäulenregister)
- [ ] **INFR-03**: Roof solar potential map (where available from BW/municipal data)
- [ ] **INFR-04**: Existing solar installations on buildings (from MaStR registry — shows which buildings already have solar)

### Platform & Infrastructure

- [ ] **PLAT-01**: Town-config-driven architecture — add a new town via config file, no code changes
- [ ] **PLAT-02**: Docker Compose self-hosted deployment — single `docker-compose up`
- [ ] **PLAT-03**: NGSI-LD compatible API layer (Smart Data Models schemas)
- [ ] **PLAT-04**: Data source attribution display (Datenlizenz Deutschland compliance)
- [ ] **PLAT-05**: Connector health monitoring — staleness detection, last-update timestamps
- [ ] **PLAT-06**: Plugin-based connector architecture (BaseConnector pattern)
- [ ] **PLAT-07**: Time-series storage with retention policies (TimescaleDB)
- [ ] **PLAT-08**: Spatial query support (PostGIS)
- [ ] **PLAT-09**: Admin health dashboard — connector status, data freshness, error rates

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Advanced Visualization

- **VIZ-01**: Full 3D digital twin view (CesiumJS-based)
- **VIZ-02**: Cross-domain correlation views (e.g., traffic vs. air quality)
- **VIZ-03**: Time-lapse animations of historical data

### Citizen Engagement

- **CIT-01**: Klimawatch integration — municipal climate goal tracking
- **CIT-02**: Citizen feedback / reporting layer
- **CIT-03**: Participatory budgeting integration (Decidim)

### Extended Data

- **EXT-01**: Real-time parking occupancy (when Aalen publishes this as open data)
- **EXT-02**: Municipal budget data (currently PDF-only, not machine-readable)
- **EXT-03**: Construction permits and building activity
- **EXT-04**: Crime statistics (only available at Kreis level, not municipal)
- **EXT-05**: Stadtwerke utility data (water/electricity/wastewater — API availability unconfirmed)

### Multi-Town

- **MULTI-01**: Zero-code second-town onboarding workflow
- **MULTI-02**: Multi-town comparison dashboard
- **MULTI-03**: daten.bw portal integration (CKAN harvesting)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Mobile native app | Web-first, responsive design covers mobile use |
| User accounts / auth | Public data, public access — no login needed |
| IoT sensor deployment | Consume existing APIs only, don't manage hardware |
| Predictive analytics / AI | Show what IS, not what MIGHT BE (v1 is observational) |
| Full FIWARE Orion deployment | Hybrid approach — own backend with NGSI-LD compat instead |
| Real-time websocket push | Upstream data refreshes in minutes, not seconds — polling sufficient |
| Multi-language (i18n) | German first, internationalize later |
| Data editing / write-back | Read-only platform — display data, don't modify sources |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| (populated by roadmapper) | | |

**Coverage:**
- v1 requirements: 53 total
- Mapped to phases: 0
- Unmapped: 53 ⚠️

---
*Requirements defined: 2026-04-05*
*Last updated: 2026-04-05 after initial definition*
