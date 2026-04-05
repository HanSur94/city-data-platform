# Project Research Summary

**Project:** City Data Platform
**Domain:** Open-source city data aggregation and visualization (German municipalities, self-hosted)
**Researched:** 2026-04-05
**Confidence:** MEDIUM-HIGH

## Executive Summary

This is an open-source, self-hosted city data platform for small German municipalities — aggregating six public data domains (traffic, public transport, air quality, water, electricity, wastewater) into a unified map + dashboard UI. Research across comparable platforms (Sentilo, FIWARE, CKAN portals, Grafana smart city deployments) shows this product fills a genuine gap: existing tools cover one domain at a time and are either developer-facing (CKAN) or infrastructure-focused (Grafana). The recommended approach is a vertically-integrated stack with a Python FastAPI ingestion service feeding a PostgreSQL + TimescaleDB + PostGIS database, and a Next.js frontend rendering MapLibre GL JS maps alongside shadcn/ui dashboard components. The architecture is explicitly split into four layers — ingestion, storage, query API, frontend — enabling independent scaling and clear ownership boundaries.

The single highest-leverage architectural decision is making the platform town-configuration-driven from the first line of code. Aalen serves as the reference deployment, but every API URL, bounding box, data source credential, and connector parameter must be read from a `towns/aalen.yaml` config — never hardcoded. Research shows that skipping this discipline on the first connector cascades into a 40-file refactor when a second town attempts to onboard. The second highest-leverage decision is building connector health and data staleness tracking into the database schema before any connector goes to production; German open data APIs have no SLA and will silently stop working.

The primary risks are (1) Aalen-specific hardcoding blocking multi-town adoption, (2) silent upstream API failures eroding dashboard trust, (3) schema drift from unversioned German municipal APIs writing nulls to the database, and (4) map rendering collapse at real data volumes if GeoJSON is served raw instead of as vector tiles. All four are avoidable with upfront architectural discipline — they are not difficult to prevent but very costly to fix retroactively.

## Key Findings

### Recommended Stack

The stack is Python + TypeScript with a clean service boundary: FastAPI handles all data ingestion and serves the query API; Next.js 16 with App Router handles the frontend. The Python backend is non-negotiable because the German open data ecosystem (GTFS parsing, CKAN clients, geo libraries) lives in Python. TimescaleDB is the correct time-series store because it speaks standard PostgreSQL SQL, extends PostGIS in the same container, and handles the expected data volumes (under ~100M rows per table per domain) with continuous aggregates for dashboard performance. MapLibre GL JS 5.x is the only viable open-source WebGL map renderer after Mapbox went proprietary in 2020.

**Core technologies:**
- Next.js 16 + React 19: full-stack framework; server components reduce JS bundle on map-heavy pages
- FastAPI 0.135 + Python: ingestion service; Python is required for GTFS/CKAN/geo ecosystem
- PostgreSQL 17 + TimescaleDB 2.23 + PostGIS: unified time-series + spatial storage; one engine, one query language
- MapLibre GL JS 5.x + react-map-gl 8.x: open-source WebGL map rendering; Mapbox alternative
- deck.gl 9.x: WebGL overlays for city-scale data density (traffic flow, heatmaps, hex-bins)
- Recharts 2.x + shadcn/ui: dashboard charts and KPI components; Tailwind 4.x native
- PMTiles (Protomaps) + Martin (Rust): self-hosted vector tiles; PMTiles for OSM base, Martin for dynamic PostGIS layers
- APScheduler 3.x: embedded cron scheduler in FastAPI; sufficient for ~8 data domains without Redis/broker overhead
- Docker Compose: single-file orchestration for all services; targets modest hardware (4GB RAM, 2-core, 50GB SSD)

**Critical version constraints:** Never use PostgreSQL 17.1/16.5/15.9 (TimescaleDB binary interface breakage — use 17.2+); Next.js 16 requires React 19 (do not mix React 18); MapLibre 5 requires react-map-gl 8; FastAPI 0.100+ requires Pydantic v2.

### Expected Features

The MVP needs to prove multi-domain aggregation, the time-series dimension, and the map + dashboard interaction model simultaneously. Starting with public transport (GTFS) and air quality is recommended — both have reliable, well-documented German data sources — before expanding to the remaining four domains.

**Must have (table stakes):**
- Interactive map with per-layer toggle — the core interaction model; users orient spatially first
- Public transport layer (GTFS static: stops + route polylines) — GTFS is the best-documented German open data source
- Air quality layer with AQI color coding — widely understood by the public; EU/WHO thresholds as annotations
- KPI summary tiles per active domain — proves the dashboard dimension alongside the map
- Time range selector with at least one week of historical data — proves the platform is more than a live snapshot
- Per-layer data freshness indicator — non-negotiable for user trust with no-SLA upstream sources
- Mobile-responsive layout — citizens use phones; officials use tablets in meetings
- Traffic flow / congestion layer — most citizens' primary data curiosity

**Should have (competitive differentiators):**
- Generic multi-town configuration — any German town self-hosts by editing one YAML file
- Remaining data domains (water, electricity, wastewater) — once the connector pattern is proven
- Permalink / shareable URLs — encode active layers + time range + viewport in URL query params
- Data export (CSV / GeoJSON) — for journalists and researchers
- Data source health dashboard (operator-facing) — visibility into upstream API health
- Town-specific theming (logo, colors) — low-friction adoption by a second town

**Defer (v2+):**
- Multi-town comparison view — requires normalized cross-town data model; needs real adoption first
- GTFS-RT live departures — static timetable sufficient for v1; real-time adds significant complexity
- Embed snippet — stable embed API contract is hard to commit to before core is stable
- i18n / multi-language — no concrete non-German user; defer until there is one

**Anti-features to avoid:** User accounts/auth (not needed for public open data; breaks embed capability), WebSockets for all layers (upstream sources update at 1–15 min intervals; HTTP polling is invisible to users), 3D building visualization (heavy rendering cost, distracts from data content), and native mobile apps (responsive web covers the use case).

### Architecture Approach

The architecture is a four-layer pipeline: ingestion connectors → TimescaleDB + PostGIS storage → FastAPI query API → Next.js + MapLibre frontend. Connectors implement a shared `BaseConnector` abstract class (`fetch() / normalize() / persist()`) so each new data source is a self-contained file, not a framework modification. Storage uses domain-partitioned TimescaleDB hypertables (one per domain, e.g. `air_quality_readings`, `traffic_flow`) — not a single catch-all measurements table — to keep queries fast and schema evolution independent. The frontend never touches the database directly; all reads go through the FastAPI query API which enforces town scoping, computes KPIs, and shapes responses to GeoJSON FeatureCollections.

**Major components:**
1. Connector Registry (Python, `connectors/`) — one class per data domain; inherits BaseConnector; reads all config from town YAML
2. Scheduler (`scheduler/`) — APScheduler job definitions with per-connector cron intervals; isolated from the HTTP API process
3. Storage (PostgreSQL + PostGIS + TimescaleDB) — spatial `features` table + domain-specific hypertables + town/source config metadata tables
4. Query API (FastAPI, `api/`) — one router per domain; serves GeoJSON, time-series, and KPI aggregations; enforces town scoping
5. Map View (Next.js + MapLibre + react-map-gl) — vector tile rendering with layer toggle; deck.gl for GPU-rendered overlays
6. Dashboard View (Next.js + Recharts + shadcn/ui) — KPI tiles, sparklines, time range selector
7. Town Config (`towns/*.yaml`) — the single source of truth for all town-specific parameters; loaded at scheduler startup

**Build order mandated by dependencies:** storage schema → one connector end-to-end → query API for that domain → map frontend with one layer → remaining connectors → dashboard/KPI layer → multi-town config validation.

### Critical Pitfalls

1. **Aalen-specific hardcoding** — Treat Aalen as `CITY_ID=aalen` from line one; every URL, bounding box, and label must come from the town config object. Build a stub second-town config in parallel to prove genericism before it costs a sprint to retrofit.

2. **Upstream APIs silently stopping** — Store `last_successful_fetch` in the DB schema from the start; display data age on every panel; treat HTTP 200 with empty payload as failure; implement staleness thresholds per domain (traffic >15 min = yellow; air quality >1 hour = red).

3. **Schema drift writing silent nulls** — Every connector must validate against a Pydantic model before touching the database; fail loudly at the connector boundary; log validation failures to a monitoring table; write CI tests against live endpoints.

4. **Map performance collapse at real data volumes** — Serve all spatial data as vector tiles (PMTiles base + Martin for dynamic layers), never raw GeoJSON dumps; implement zoom-level clustering; use deck.gl WebGL rendering for layers exceeding ~5,000 points; load-test with 12 months of realistic synthetic data before any map milestone is signed off.

5. **Storage exhaustion on self-hosted hardware** — Define retention policies per domain before schema design (e.g., raw traffic: 90 days; hourly aggregates: 5 years); enable TimescaleDB compression (10-20x reduction); build automatic downsampling pipelines; document disk estimates in deployment guide.

6. **License non-compliance** — Every data source requires attribution under Datenlizenz Deutschland or CC-BY; store `license` and `attribution` in the connector config schema; render attribution overlay in the map UI per active layer from day one.

## Implications for Roadmap

Based on research, the architecture's explicit build-order guidance and the pitfall dependency mapping both point to the same phase structure. The schema and connector abstractions must be locked before any data flows. A single end-to-end vertical slice must be validated before expanding to six domains. The dashboard can only be built after time-series data exists.

### Phase 1: Foundation — Storage Schema, Town Config, and Docker Environment

**Rationale:** Everything downstream depends on the storage schema and town-config abstraction being correct. This is the phase where the most expensive pitfalls (hardcoding, wrong DB choice, missing retention policy, missing attribution schema, missing health metadata) are either prevented or baked in permanently.
**Delivers:** Docker Compose environment with PostgreSQL + TimescaleDB + PostGIS running; Alembic migrations for the `features` table, domain hypertables, and `towns`/`sources` config tables; `towns/aalen.yaml` and `towns/example.yaml` schema; retention policy documented; BaseConnector abstract class defined.
**Addresses:** Town configuration file (FEATURES.md table stakes prerequisite); multi-town generic architecture precondition.
**Avoids:** Aalen hardcoding, wrong DB selection, storage exhaustion, license non-compliance (attribution field in source schema).
**Research flag:** Standard patterns — well-documented PostgreSQL/TimescaleDB setup; skip phase research.

### Phase 2: Data Ingestion — First Connector End-to-End (Transit + Air Quality)

**Rationale:** Validates the full pipeline (scheduler → connector → DB) before building any UI. Transit (GTFS) and air quality (LUBW API) are the best-documented German sources — use them to prove the BaseConnector pattern works before tackling less-documented domains.
**Delivers:** GTFSConnector and AirQualityConnector writing to hypertables; APScheduler job definitions with per-connector cron intervals; Pydantic schema validation on both connectors; `last_successful_fetch` metadata; connector health visible in logs.
**Uses:** FastAPI + APScheduler + httpx + gtfs-kit + Pydantic (STACK.md); MobiData BW and LUBW as upstream sources.
**Avoids:** Schema drift silent nulls, upstream API silence (staleness tracking), connector cross-contamination (isolated async workers per source).
**Research flag:** Needs research — GTFS-RT feed quality and specific LUBW API endpoint structure; verify before implementation.

### Phase 3: Query API — FastAPI Routers for Ingested Domains

**Rationale:** Proves the read path exists and shapes responses correctly before building any frontend. The GeoJSON layer API pattern must be established here; retrofitting it later breaks the frontend contract.
**Delivers:** `/api/layers/transit`, `/api/layers/air_quality`, `/api/kpi`, `/api/timeseries/air_quality` endpoints; GeoJSON FeatureCollection responses; town-scoped queries; PostGIS spatial queries.
**Implements:** Query API component; GeoJSON Layer API pattern (ARCHITECTURE.md Pattern 3).
**Avoids:** Frontend directly querying the database (anti-pattern 4 in ARCHITECTURE.md).
**Research flag:** Standard patterns — FastAPI routers and PostGIS GeoJSON queries are well-documented; skip phase research.

### Phase 4: Map Frontend — MapLibre with First Two Layers

**Rationale:** Validates the complete vertical slice from external source to browser before adding more connectors. Must confirm vector tile strategy and layer toggle work at this phase — retrofitting the tile architecture later is expensive (PITFALLS.md: map performance pitfall).
**Delivers:** Next.js frontend at port 4000 (Grafana is on 3000 on target system); MapLibre GL JS with PMTiles OSM base; transit and air quality layers as vector tiles via Martin; layer toggle UI; data freshness indicator per layer; mobile-responsive layout.
**Addresses:** Interactive map with layer toggle, public transport layer, air quality layer, mobile-responsive layout, data freshness indicator (all P1 features from FEATURES.md).
**Avoids:** Map performance collapse, no data freshness display (UX pitfall).
**Research flag:** Needs research — Martin tile server integration with MapLibre and dynamic PostGIS layers; verify configuration patterns.

### Phase 5: Dashboard — KPI Tiles and Time-Series Charts

**Rationale:** Requires time-series data already in the database from Phase 2. The dashboard is a second viewport on the same data, not a separate product — build it after the map layer is validated.
**Delivers:** KPI summary tiles (current readings per domain); sparkline charts via Recharts; time range selector driving time-filtered queries; 7-day, 30-day, 90-day chart views tested at realistic data volumes; shadcn/ui layout alongside map view.
**Addresses:** KPI summary panel, charts/trend visualizations, time range selector (P1 table stakes from FEATURES.md).
**Avoids:** Dashboard query performance degradation (continuous aggregates for 30/90-day views); frontend fetching full historical datasets for sparklines.
**Research flag:** Standard patterns — Recharts + shadcn/ui are well-documented; skip phase research. Continuous aggregate queries are standard TimescaleDB.

### Phase 6: Remaining Connectors — Traffic, Water, Electricity, Wastewater

**Rationale:** Once the BaseConnector pattern is proven by Phase 2, adding four more domains is mechanical. Traffic is the highest user value of the four (P1 in FEATURES.md); the others are P2.
**Delivers:** TrafficConnector (MDM / BASt data), WaterConnector, ElectricityConnector, WastewaterConnector; corresponding FastAPI routers; map layers for each; updated KPI tiles.
**Addresses:** Traffic flow/congestion (P1), water/electricity/wastewater layers (P2).
**Avoids:** Polling frequency mismatch (each connector gets its own cron interval from town YAML); connector cross-contamination.
**Research flag:** Needs research — MDM/Mobilithek traffic feed format (DATEX II XML), Stadtwerke API availability for Aalen (may require direct inquiry), WFS endpoints for water/wastewater; verify before implementation.

### Phase 7: Multi-Town Genericism Validation and Operator Features

**Rationale:** The generic architecture was designed in from Phase 1, but must be explicitly validated by running the full stack against a second town config (even a stub). Operator-facing features (health dashboard, data export, shareable URLs) become relevant once the platform is running in production.
**Delivers:** Second town YAML config (e.g., stub Ulm); verified zero-code-change town onboarding; data source health dashboard (internal); permalink / shareable URLs; data export (CSV / GeoJSON); town-specific theming via CSS variables.
**Addresses:** Generic multi-town configuration, permalink URLs, data export, health dashboard, town theming (all P2 differentiators from FEATURES.md).
**Avoids:** Multi-city genericism failure ("generic" means one config file with Aalen values — verify with real second town).
**Research flag:** Standard patterns — URL state encoding and CSV export are straightforward; skip phase research.

### Phase Ordering Rationale

- Storage schema must precede connectors because hypertable design is non-reversible at production data volumes; choosing the wrong schema or omitting retention policies requires a full migration.
- BaseConnector abstraction must precede any connector implementation; the first connector sets the pattern all six follow.
- The transit + air quality vertical slice (Phases 2-4) must complete as a unit before adding more domains; it validates every layer of the stack with the best-documented sources.
- Dashboard (Phase 5) explicitly requires time-series data; it cannot move earlier.
- Remaining connectors (Phase 6) are deliberately late because they are higher-risk (less-documented sources, some requiring registration) and should not block the validated core.
- Multi-town validation (Phase 7) is last because it verifies all preceding phases held to the town-config discipline.

### Research Flags

Phases needing deeper research during planning:
- **Phase 2 (Ingestion):** GTFS-RT feed quality issues are well-documented but specific MobiData BW endpoint behavior and LUBW API structure need verification before connector implementation.
- **Phase 4 (Map Frontend):** Martin tile server dynamic PostGIS layer configuration with MapLibre GL JS; pmtiles format specifics for Germany OSM extract.
- **Phase 6 (Remaining Connectors):** MDM/Mobilithek traffic feed access (some feeds require registration); Stadtwerke API availability for water/electricity is highly fragmented and may require per-town manual investigation; WFS endpoint parsing for wastewater.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Foundation):** PostgreSQL + TimescaleDB + PostGIS setup via Docker Compose is thoroughly documented; Alembic migrations are standard.
- **Phase 3 (Query API):** FastAPI routers + PostGIS GeoJSON responses are well-documented with official sources.
- **Phase 5 (Dashboard):** Recharts + shadcn/ui + TimescaleDB continuous aggregates are all standard documented patterns.
- **Phase 7 (Operator Features):** URL state encoding, CSV export, and theming via CSS variables are low-complexity standard patterns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Core technology choices (MapLibre, TimescaleDB, FastAPI, Next.js) verified against official documentation; version compatibility explicitly confirmed |
| Features | MEDIUM | Table stakes and differentiators derived from analysis of comparable platforms; no direct user research; inferred from comparable smart city deployments |
| Architecture | MEDIUM-HIGH | Core patterns (connector registry, domain-partitioned hypertables, GeoJSON layer API) well-established; specific German API integration details are LOW confidence |
| Pitfalls | MEDIUM-HIGH | Seven critical pitfalls identified; all backed by multiple sources; German GTFS quality issues backed by a live GitHub issue tracker; time-series DB pitfalls have post-mortems |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Stadtwerke APIs for water/electricity/wastewater:** Highly fragmented; no national standard. Connector implementation for these domains will require per-Aalen investigation before any code is written. Flag Phase 6 for a dedicated discovery spike.
- **MDM/Mobilithek registration:** Some traffic feeds require registration. Verify access before committing to MDM-based traffic data in the roadmap; have BASt count data as fallback.
- **GTFS-RT from MobiData BW:** German GTFS-RT quality issues are well-documented. Budget a validation step (GTFS Canonical Validator) as a formal gate before the transit connector is marked complete.
- **Aalen-specific data source confirmation:** LUBW coverage of Aalen (sensor station locations and IDs are city-specific); confirm coverage before air quality connector scope is finalized.
- **Storage sizing estimate for Aalen specifically:** Research provides formulas; a concrete estimate for Aalen (6 domains, expected sensor count, chosen poll intervals) should be produced during Phase 1 to right-size the target hardware.

## Sources

### Primary (HIGH confidence)
- MapLibre GL JS official docs — https://maplibre.org/maplibre-gl-js/docs/ — map rendering, PMTiles integration
- react-map-gl official docs — https://visgl.github.io/react-map-gl/docs — React bindings, MapLibre compatibility
- deck.gl + MapLibre integration — https://deck.gl/docs/developer-guide/base-maps/using-with-maplibre — overlay rendering
- TimescaleDB releases — https://github.com/timescale/timescaledb/releases — version compatibility, PG 17 constraint
- FastAPI release notes — https://fastapi.tiangolo.com/release-notes/ — Pydantic v2 requirement
- Next.js blog — https://nextjs.org/blog — 16.x / React 19 requirement confirmed
- shadcn/ui charts — https://www.shadcn.io/charts — Recharts integration
- GovData CKAN portal — https://github.com/GovDataOfficial/GovDataPortal — German open data structure
- GTFS Germany (gtfs.de) — https://gtfs.de/en/ — German GTFS feed catalog
- DELFI national GTFS — https://gtfs.de/en/realtime/ — national aggregation
- GovData licenses (Datenlizenz Deutschland) — https://www.govdata.de/informationen/lizenzen — license compliance requirements
- GitHub: mfdz/GTFS-Issues — https://github.com/mfdz/GTFS-Issues — German GTFS feed quality tracking
- GitHub: graphhopper/open-traffic-collection — German traffic data sources
- Mobilithek.info — https://mobilithek.info/ — German mobility data platform (MDM replacement)
- Schema evolution best practices — https://datalakehousehub.com/blog/2026-02-de-best-practices-05-schema-evolution/
- Open data quality pipeline — https://datalakehousehub.com/blog/2026-02-de-best-practices-03-data-quality-first/

### Secondary (MEDIUM confidence)
- Grafana smart city blog (Sentilo/Timescale) — feature comparison baseline
- APScheduler vs Celery comparison — https://leapcell.io/blog/scheduling-tasks-in-python-apscheduler-vs-celery-beat
- QuestDB DB comparison — https://questdb.com/blog/comparing-influxdb-timescaledb-questdb-time-series-databases/ (vendor source)
- Fraunhofer urban intelligence architecture — https://pmc.ncbi.nlm.nih.gov/articles/PMC11014012/
- TimescaleDB + PostGIS spatial queries — https://medium.com/@marcoscedenillabonet/optimizing-geospatial-and-time-series-queries-with-timescaledb-and-postgis-4978ea2ef8af
- MDPI smart city multi-layer architecture — https://www.mdpi.com/1424-8220/24/7/2376
- Dashboard staleness trust issues — https://www.optijara.ai/en/blog/hidden-cost-of-caching-2-line-api-fix-hts-dashboard
- Heavy map visualization fundamentals — https://advena.hashnode.dev/heavy-map-visualizations-fundamentals-for-web-developers

### Tertiary (LOW confidence)
- Smart city dashboard EDAG reference — marketing material; used only for feature landscape, not technical decisions
- Open data citizen engagement (The Hill) — opinion piece; supports feature prioritization rationale only

---
*Research completed: 2026-04-05*
*Ready for roadmap: yes*
