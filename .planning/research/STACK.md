# Stack Research

**Domain:** Open-source city data platform — map + dashboard, public data ingestion, self-hosted
**Researched:** 2026-04-05
**Confidence:** MEDIUM-HIGH (core choices HIGH, German open data specifics MEDIUM)

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Next.js | 16.x | Full-stack React framework | App Router enables server components for data fetching; API routes handle backend without a separate service for simple read endpoints; React 19 support built-in; biggest ecosystem for this domain |
| React | 19.x | UI layer | Required by Next.js 16; server components reduce JS bundle for map/chart-heavy pages |
| TypeScript | 5.x | Type safety across entire codebase | Prevents coordinate type errors, API shape mismatches; critical when consuming heterogeneous open data APIs |
| FastAPI | 0.135.x | Data ingestion service + periodic polling | Python is where the open data ecosystem lives (GTFS parsers, CKAN clients, geo libs); async-native; Pydantic models for validating messy open data; separate from Next.js to keep concerns clean |
| PostgreSQL + TimescaleDB | PG 17 + TSDBv2.23 | Primary datastore for all time-series city data | TimescaleDB is a PG extension — no new query language to learn; hypertables handle time-partitioned traffic/sensor data efficiently; PostGIS for spatial queries; single database covers both relational config and time-series measurements |
| MapLibre GL JS | 5.x | Interactive vector tile map rendering | Open-source fork of Mapbox GL JS (Mapbox switched to proprietary license in 2020); WebGL rendering handles large datasets; works with PMTiles/OSM tiles — fully self-hostable; the standard for open-source web maps in 2025 |
| react-map-gl | 8.x | React bindings for MapLibre | Official vis.gl wrapper; makes MapLibre work as controlled React components; deck.gl integration built-in |

### Data Visualization Layer

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| deck.gl | 9.x | WebGL data overlays on the map | Traffic flow, particle animations, hex-bin aggregations — things that need GPU rendering of thousands of points |
| Recharts | 2.x | Dashboard charts (line, bar, area, donut) | Standard KPI charts and trend lines in the dashboard panel; shadcn/ui uses it as base; good enough for city metrics |
| shadcn/ui | latest | Copy-paste UI component system | Provides KPI cards, data tables, tabs, layout primitives — all unstyled-but-styled, fully owned in codebase; Tailwind-native |
| Tailwind CSS | 4.x | Utility CSS | Co-designed with shadcn/ui; zero-overhead for city official UI polish; v4 drops config file |

### Map Tiles — Self-Hosted

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Protomaps / PMTiles | latest | Single-file OSM vector tile archive | Serve Germany OSM tiles from a static file — no tile server process needed, just HTTP range requests; weekly builds available from protomaps.com |
| Martin | 0.x (Rust) | On-the-fly vector tiles from PostGIS | When dynamic city-specific layers (e.g. traffic polygons stored in PostGIS) need to be served as tiles; complements PMTiles for base map |

### Data Ingestion Layer

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| APScheduler | 3.x | Periodic polling of open data APIs | Embedded in FastAPI process; cron-style jobs for each data domain (traffic every 5 min, transport every 30 sec); no Redis/broker dependency for modest scale |
| httpx | 0.27.x | Async HTTP client for Python | Fetching CKAN APIs, REST endpoints, open data portals; async-native unlike requests |
| gtfs-kit | 7.x | GTFS feed parsing | German transport authorities (VVS, SWEG, DB) publish GTFS; gtfs-kit is the standard Python library |
| python-ckan | 0.8.x | CKAN API client | GovData / mCLOUD portals use CKAN; structured client prevents reimplementing CKAN paging |
| Pydantic | 2.x | Data validation models | Validates every external API response before it touches the database; critical for messy open data |

### Infrastructure

| Technology | Purpose | Notes |
|------------|---------|-------|
| Docker Compose | Orchestrate all services locally and on server | Single `docker-compose.yml` for postgres+timescaledb, fastapi-ingestor, next.js frontend, martin tile server; restart policies for unattended operation |
| Redis | Job result caching + pub/sub for live updates | Optional: only add if APScheduler + polling proves insufficient; avoids premature complexity |
| Nginx | Reverse proxy | Terminates TLS, routes `/api/ingest` to FastAPI, `/` to Next.js, `/tiles` to Martin; standard pattern |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Python package manager | Faster than pip/poetry for FastAPI service; lockfile for reproducible ingestion builds |
| pnpm | Node package manager | Faster installs than npm; workspace support if monorepo grows |
| Biome | Linting + formatting (TypeScript/JS) | Replaces ESLint + Prettier in one tool; ~100× faster than ESLint |
| pytest + pytest-asyncio | FastAPI/ingestion testing | Essential for validating data transformation logic before hitting real APIs |

---

## Installation

```bash
# Frontend (Next.js)
pnpm create next-app@latest frontend --typescript --tailwind --app

# shadcn/ui setup
pnpm dlx shadcn@latest init

# Map + chart libraries
pnpm add maplibre-gl react-map-gl @deck.gl/react @deck.gl/layers recharts

# Backend (Python)
uv init ingestor
cd ingestor
uv add fastapi uvicorn apscheduler httpx pydantic psycopg2-binary sqlalchemy gtfs-kit

# Dev dependencies
uv add --dev pytest pytest-asyncio
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| FastAPI (Python) | tRPC (TypeScript) | Only if you never need Python geo/GTFS libs and want a pure TypeScript monorepo. tRPC can't use the Python open data ecosystem. |
| FastAPI (Python) | Next.js API routes only | Only if data sources are simple REST JSON — no GTFS, no spatial processing. Won't scale for 8 data domains. |
| TimescaleDB | InfluxDB | If you're already deep in InfluxDB/Flux; TimescaleDB wins here because it speaks standard SQL and combines with PostGIS in one container |
| TimescaleDB | plain PostgreSQL | Fine for MVP but you lose automatic time-partitioning; query performance degrades as historical data grows |
| MapLibre GL JS | Leaflet | Leaflet is raster-tile-era tech; no WebGL, no 3D, no GPU-rendered overlays. Use Leaflet only for the simplest possible map. |
| MapLibre GL JS | Mapbox GL JS | Mapbox requires an API key and is proprietary since 2020. Not viable for a fully open-source, self-hosted project. |
| deck.gl | Leaflet plugins | deck.gl handles 100k+ point datasets via WebGL; Leaflet DOM-based overlays break at city-scale traffic data |
| PMTiles + Martin | Tegola / pg_tileserv | Both work but PMTiles + Martin is the current community consensus for simple self-hosted stacks |
| APScheduler | Celery + Redis | Celery adds broker complexity (Redis or RabbitMQ, worker processes). APScheduler embedded in FastAPI is sufficient for polling ~8 data domains at city scale. Add Celery if jobs become long-running or distributed. |
| shadcn/ui + Recharts | Tremor | Tremor is now also shadcn-based and uses Recharts underneath — functionally equivalent. Prefer raw shadcn/ui for more control; Tremor for faster bootstrapping. |
| Docker Compose | Kubernetes | K8s is overengineering for a single-city, self-hosted deployment on modest hardware. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Mapbox GL JS | Proprietary license since Dec 2020; requires API key; costs money; defeats "fully open source" goal | MapLibre GL JS (the open-source fork) |
| Google Maps API | Paid, proprietary, data leaves EU, not open-source | MapLibre GL JS + Protomaps OSM tiles |
| Grafana | Port 3000 conflict with Grafana already on target system per project context; designed for infrastructure metrics not citizen-facing city dashboards; poor map integration | Custom Next.js dashboard with shadcn/ui + Recharts |
| CouchDB / MongoDB | Document stores don't fit time-series data well; lose time-partitioning and PostGIS spatial capabilities | PostgreSQL + TimescaleDB (handles both relational config and time-series in one engine) |
| GraphQL | Overkill for a city data read-heavy API with stable schemas; adds schema maintenance overhead | REST via FastAPI (simple, cacheable, easy to document) |
| Webpack (manually) | Next.js 16 bundles Turbopack; configuring raw Webpack causes version conflicts | Let Next.js manage its bundler |
| Leaflet | Raster-tile era; no WebGL; DOM-based overlays collapse under city-scale data volumes | MapLibre GL JS |
| create-react-app | Deprecated, unmaintained since 2022 | Next.js App Router |

---

## Stack Patterns by Variant

**For the MVP (single city, Aalen):**
- Run everything via `docker-compose up`
- FastAPI polls 8 data domains on schedule, writes to TimescaleDB
- Next.js server components fetch from TimescaleDB directly via Postgres connection (no extra REST layer for reads)
- MapLibre renders Protomaps PMTiles base + deck.gl overlays for data layers
- No Redis, no Nginx yet (dev mode)

**For multi-town configuration:**
- Add a `towns` table with CKAN portal URL, GTFS feed URL, bounding box per town
- FastAPI reads town config and creates per-town scheduled jobs dynamically
- MapLibre bbox comes from town config, not hardcoded
- This is the generic architecture — no Aalen hardcoding

**If live data push is needed (< 60 sec updates):**
- Add Server-Sent Events (SSE) in FastAPI for streaming sensor data
- FastAPI 0.135+ supports SSE natively
- Skip WebSockets for read-only display — SSE is simpler, proxied by Nginx trivially

**For self-hosting on modest hardware (e.g. a mini PC or small VPS):**
- TimescaleDB compression reduces storage ~90% for time-series columns
- PMTiles for base map requires zero tile server compute
- Martin tile server is Rust — extremely low memory footprint
- Target: runs on 4GB RAM, 2-core, 50GB SSD

---

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| MapLibre GL JS 5.x | react-map-gl 8.x | react-map-gl 8 dropped Mapbox-specific APIs; pairs correctly with MapLibre 5 |
| deck.gl 9.x | react-map-gl 8.x | deck.gl uses react-map-gl's `useControl` hook for overlay integration |
| Next.js 16.x | React 19.x | Next.js 16 requires React 19; do not mix React 18 |
| TimescaleDB 2.23.x | PostgreSQL 15, 16, 17, 18 | Avoid PG 17.1/16.5/15.9 specifically — binary interface breakage; use 17.2+ |
| FastAPI 0.135.x | Pydantic 2.x | FastAPI 0.100+ requires Pydantic v2; do not use Pydantic v1 |
| Tailwind CSS 4.x | shadcn/ui latest | shadcn/ui requires Tailwind 4+ for its new CSS variable system |

---

## German Open Data Notes

These are domain specifics that affect ingestion design — not library choices, but architectural constraints:

- **GovData (govdata.de)**: National CKAN portal. REST API at `https://www.govdata.de/ckan/api/3/`. ~120k datasets, many state-level.
- **mCLOUD (mcloud.de)**: Federal transport/mobility open data hub. 1500+ datasets. Has its own API separate from GovData.
- **GTFS**: Public transport timetables. German operators (VVS for Stuttgart region, SWEG, DB) publish GTFS Static; GTFS-Realtime (GTFS-RT) is available from some operators for live departures. MobilityDatabase (transitfeeds.com) is the global catalog. DELFI e.V. aggregates national GTFS.
- **Luftqualität (air quality)**: Umweltbundesamt (UBA) publishes an open REST API at `luftdaten.info` / `sensor.community` for citizen sensors; official UBA station data is also open.
- **Verkehr (traffic)**: BASt (Bundesanstalt für Straßenwesen) publishes traffic count data. Some Länder publish live road sensor data.
- **Energie**: SMARD.de (Bundesnetzagentur) for electricity grid data; municipality-level data is scarce — depends on the Stadtwerk publishing.
- **Wasser/Abwasser**: Highly fragmented — no national standard; each Stadtwerk decides. Check for INSPIRE-compliant WFS endpoints.

---

## Sources

- MapLibre GL JS official docs — https://maplibre.org/maplibre-gl-js/docs/ — HIGH confidence
- react-map-gl official docs — https://visgl.github.io/react-map-gl/docs — HIGH confidence
- deck.gl + MapLibre integration — https://deck.gl/docs/developer-guide/base-maps/using-with-maplibre — HIGH confidence
- Protomaps / PMTiles — https://protomaps.com/ — HIGH confidence
- TimescaleDB releases — https://github.com/timescale/timescaledb/releases — HIGH confidence
- FastAPI release notes — https://fastapi.tiangolo.com/release-notes/ — HIGH confidence
- Next.js 15/16 releases — https://nextjs.org/blog — HIGH confidence (16.x confirmed)
- GovData CKAN portal — https://github.com/GovDataOfficial/GovDataPortal — MEDIUM confidence
- GTFS Germany via DELFI — mentioned in public transport research — MEDIUM confidence (verify specific feed URLs at implementation time)
- APScheduler vs Celery comparison — https://leapcell.io/blog/scheduling-tasks-in-python-apscheduler-vs-celery-beat — MEDIUM confidence
- shadcn/ui charts (Recharts-based) — https://www.shadcn.io/charts — HIGH confidence

---

*Stack research for: open-source city data platform (map + dashboard, German open data, self-hosted)*
*Researched: 2026-04-05*
