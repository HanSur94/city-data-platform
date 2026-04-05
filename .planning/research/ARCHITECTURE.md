# Architecture Research

**Domain:** Open city data aggregation and visualization platform
**Researched:** 2026-04-05
**Confidence:** MEDIUM (core patterns well-established; specific German open data API specifics LOW due to limited doc coverage)

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          FRONTEND LAYER                             │
│  ┌─────────────────────────┐  ┌──────────────────────────────────┐  │
│  │     Map View            │  │       Dashboard / KPI View       │  │
│  │  (MapLibre GL JS)       │  │   (charts, tiles, time series)   │  │
│  └────────────┬────────────┘  └────────────────┬─────────────────┘  │
│               │  REST / GeoJSON / SSE            │                   │
└───────────────┼──────────────────────────────────┼───────────────────┘
                │                                  │
┌───────────────┼──────────────────────────────────┼───────────────────┐
│                          API GATEWAY LAYER                          │
│  ┌────────────▼──────────────────────────────────▼──────────────┐   │
│  │              Query API (FastAPI / Python)                     │   │
│  │  /api/layers/{domain}  /api/kpi  /api/timeseries  /api/tiles  │   │
│  └────────────────────────────┬─────────────────────────────────┘   │
└───────────────────────────────┼─────────────────────────────────────┘
                                │
┌───────────────────────────────┼─────────────────────────────────────┐
│                          STORAGE LAYER                              │
│  ┌─────────────────────────────▼──────────────────────────────────┐ │
│  │   PostgreSQL + PostGIS + TimescaleDB                           │ │
│  │   - Spatial tables (point, line, polygon features)             │ │
│  │   - Time-series hypertables (measurements, readings)          │ │
│  │   - Metadata tables (towns, sources, connector configs)       │ │
│  └────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────┼─────────────────────────────────────┐
│                      INGESTION LAYER                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ Traffic  │  │ Transit  │  │   Air    │  │  Water/  │           │
│  │Connector │  │Connector │  │ Quality  │  │  Power   │           │
│  │ (MDVU,   │  │ (GTFS,   │  │Connector │  │Connector │           │
│  │  TomTom) │  │GTFS-RT)  │  │(LUBW API)│  │(Stadt API│           │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘           │
│       │              │              │              │                 │
│  ┌────▼──────────────▼──────────────▼──────────────▼─────────────┐ │
│  │            Scheduler / Job Runner (APScheduler / Celery)       │ │
│  │   - Per-connector cron schedule (e.g. every 5 min for GTFS-RT) │ │
│  │   - Retry logic, dead-letter queue                             │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘

External Open Data Sources (upstream, outside platform):
  MobiData BW (GTFS, GTFS-RT), LUBW (Luftqualität), daten.bw, GovData,
  Stadtwerke APIs, MDM (Mobilitätsdatenmarktplatz), OpenStreetMap
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|---------------|------------------------|
| Connector | Fetches raw data from one external source, normalizes to internal schema, writes to DB | Python class per data source type |
| Scheduler | Triggers connectors on a cron schedule; handles retries and error logging | APScheduler (in-process) or Celery Beat |
| Storage (PostGIS + TimescaleDB) | Persists spatial features and time-series measurements; serves spatial queries | Single PostgreSQL instance with two extensions |
| Query API | Reads from DB, computes aggregations, serves GeoJSON, time series, KPI tiles to frontend | FastAPI; one router per domain (traffic, transit, etc.) |
| Map View | Renders vector/GeoJSON layers, user can toggle domains on/off | React + MapLibre GL JS (react-map-gl) |
| Dashboard View | Shows KPI tiles, charts, sparklines alongside the map | React + Recharts or Chart.js |
| Town Config | YAML/JSON file declaring which connectors run, with what parameters, for which town | Loaded at startup; no hardcoded town data |

## Recommended Project Structure

```
city-data-platform/
├── connectors/               # One module per data domain
│   ├── base.py               # Abstract Connector class (fetch, normalize, persist)
│   ├── traffic.py            # Traffic connector (MDM / TomTom open layer)
│   ├── transit.py            # GTFS + GTFS-RT connector (MobiData BW)
│   ├── air_quality.py        # Air quality connector (LUBW)
│   ├── water.py              # Water supply connector
│   ├── electricity.py        # Grid / electricity connector
│   └── wastewater.py         # Wastewater connector
├── scheduler/                # Job runner and schedule definitions
│   ├── jobs.py               # APScheduler job definitions
│   └── runner.py             # Startup entrypoint for scheduler process
├── api/                      # FastAPI application
│   ├── main.py               # App factory, CORS, startup
│   ├── routers/
│   │   ├── traffic.py
│   │   ├── transit.py
│   │   ├── air_quality.py
│   │   ├── water.py
│   │   ├── kpi.py
│   │   └── layers.py         # Generic GeoJSON layer endpoint
│   └── db.py                 # SQLAlchemy / asyncpg connection pool
├── db/
│   ├── migrations/           # Alembic migrations
│   └── schema.sql            # Reference schema (spatial + time-series tables)
├── frontend/                 # React SPA
│   ├── src/
│   │   ├── components/
│   │   │   ├── Map/          # MapLibre GL wrapper, layer controls
│   │   │   └── Dashboard/    # KPI tiles, charts
│   │   ├── hooks/            # useLayerData, useKPI, etc.
│   │   └── config/           # Layer registry (label, color, API endpoint per domain)
│   └── public/
├── towns/                    # Per-town configuration
│   ├── aalen.yaml            # Aalen: which connectors, which API endpoints
│   └── example.yaml          # Template for a new town
├── docker-compose.yml        # Postgres, scheduler, API, frontend
└── docs/
    └── adding-a-town.md
```

### Structure Rationale

- **connectors/**: Each connector is isolated — a new data source means a new file that inherits from `base.py`. No coupling between domains.
- **towns/**: YAML config per town is the key mechanism for genericity. Connectors read their endpoint URLs, credentials, and schedule from this config, not from hardcoded values.
- **scheduler/ separate from api/**: The scheduler is a long-running background process. Keeping it separate from the HTTP API prevents coupling and allows independent restart.
- **db/migrations/**: Alembic-managed schema means reproducible deployments on any new town's server.

## Architectural Patterns

### Pattern 1: Connector Registry with Base Class

**What:** All connectors inherit from a shared `BaseConnector` with a standard interface (`fetch() -> RawData`, `normalize(RawData) -> List[Observation]`, `persist(List[Observation])`). The scheduler and town config reference connectors by name.

**When to use:** Always — this is what enables plugging in new data sources without touching core code.

**Trade-offs:** Adds a small layer of abstraction overhead; pays off immediately when adding a second data source.

**Example:**
```python
class BaseConnector:
    def __init__(self, config: ConnectorConfig): ...
    def fetch(self) -> dict: raise NotImplementedError
    def normalize(self, raw: dict) -> list[Observation]: raise NotImplementedError
    def persist(self, observations: list[Observation]): ...  # shared DB write logic

class GTFSRealtimeConnector(BaseConnector):
    def fetch(self) -> dict:
        return requests.get(self.config.url).json()
    def normalize(self, raw) -> list[Observation]:
        # parse GTFS-RT protobuf, return list of vehicle positions
        ...
```

### Pattern 2: Domain-Partitioned Storage Tables

**What:** Each data domain (traffic, air quality, transit, etc.) gets its own time-series hypertable in TimescaleDB, with a shared spatial reference table of features (stops, road segments, sensors). Measurements reference features by ID.

**When to use:** Always for time-series data. Avoid one giant `measurements` table with a `domain` column — it makes queries slow and schema evolution painful.

**Trade-offs:** More tables, but queries stay fast and domain schemas stay independent.

**Example:**
```sql
-- Shared spatial features
CREATE TABLE features (
    id UUID PRIMARY KEY,
    town_id TEXT NOT NULL,
    domain TEXT NOT NULL,       -- 'traffic', 'transit', 'air_quality'
    geometry GEOMETRY(Point, 4326),
    properties JSONB
);

-- Domain-specific time series (TimescaleDB hypertable)
CREATE TABLE air_quality_readings (
    time TIMESTAMPTZ NOT NULL,
    feature_id UUID REFERENCES features(id),
    pm25 FLOAT, pm10 FLOAT, no2 FLOAT
);
SELECT create_hypertable('air_quality_readings', 'time');
```

### Pattern 3: GeoJSON Layer API

**What:** The frontend doesn't know about database schemas. The Query API exposes one endpoint per domain (`GET /api/layers/air_quality?town=aalen&bbox=...`) that returns GeoJSON FeatureCollection. The frontend treats all layers uniformly.

**When to use:** Always — decouples map rendering from storage internals, and makes adding a new domain as simple as a new router + connector.

**Trade-offs:** Some data transformation on every API call (DB rows → GeoJSON); acceptable at city scale. Add a Redis cache layer if response times become an issue.

## Data Flow

### Ingestion Flow (background, scheduled)

```
Scheduler (cron trigger)
    ↓
Connector.fetch()  →  External API (MobiData BW, LUBW, Stadt API, ...)
    ↓
Connector.normalize()  →  List[Observation] (internal schema)
    ↓
BaseConnector.persist()  →  PostgreSQL + PostGIS + TimescaleDB
```

### Query Flow (user-triggered)

```
User opens map / dashboard
    ↓
React frontend  →  GET /api/layers/{domain}?town=aalen
    ↓
FastAPI router  →  SQL query (PostGIS ST_AsGeoJSON, TimescaleDB last())
    ↓
GeoJSON FeatureCollection  →  MapLibre layer source
    ↓
Map re-renders with updated data
```

### Key Data Flows

1. **GTFS-RT vehicle positions:** Connector polls GTFS-RT feed every 30 seconds, writes vehicle positions to `transit_vehicles` hypertable. Query API returns current positions as GeoJSON points. Frontend renders as animated bus/train icons on map.

2. **Air quality time series:** Connector polls LUBW (Landesanstalt für Umwelt Baden-Württemberg) API every 30 minutes. Query API serves `GET /api/timeseries/air_quality?station=X&range=7d` for sparklines in dashboard.

3. **Traffic congestion:** Connector fetches road segment flow data. Stored as a time-series with segment geometry. Map layer colors segments by congestion level via PostGIS join.

4. **Town bootstrap:** On first run, connector reads `towns/aalen.yaml`, creates `features` rows for all static locations (bus stops, sensor stations, etc.) from GTFS stops.txt or static API responses.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1 town, dev machine | Single Docker Compose: Postgres, FastAPI, scheduler in one process, Vite dev server |
| 3-10 towns, VPS | Same Docker Compose stack; add TimescaleDB continuous aggregates for dashboard KPIs to reduce query cost |
| 10+ towns, team use | Split scheduler into separate container; add Redis cache for GeoJSON layer responses; consider read replica for Postgres |
| 50+ towns | Move to managed Postgres (e.g. Timescale Cloud or self-hosted cluster); town configs loaded from DB rather than YAML files |

### Scaling Priorities

1. **First bottleneck:** Database query time for time-series aggregations. Fix with TimescaleDB continuous aggregates (pre-computed hourly/daily rollups).
2. **Second bottleneck:** GeoJSON serialization on every API call for large feature sets. Fix with response caching (Redis or HTTP Cache-Control headers — data changes at most every few minutes).

## Anti-Patterns

### Anti-Pattern 1: Hardcoded Town Data

**What people do:** Write `if city == "Aalen": url = "https://..."` or commit Aalen-specific SQL seed data into the main codebase.

**Why it's wrong:** Every new town requires a code change. Makes the platform a one-city tool.

**Do this instead:** All town-specific configuration (API URLs, connector parameters, bounding box, display name) lives in `towns/<townname>.yaml`. Connectors are parameterized, not specialized.

### Anti-Pattern 2: One Fat Measurements Table

**What people do:** Create `measurements(time, domain, feature_id, value JSONB)` as a single catch-all table.

**Why it's wrong:** Queries across millions of rows with a `WHERE domain = 'air_quality'` filter are slow. JSONB value columns resist indexing. Schema changes for one domain affect all.

**Do this instead:** One hypertable per domain (`air_quality_readings`, `traffic_flow`, etc.) with typed columns. TimescaleDB partitions each independently.

### Anti-Pattern 3: Polling Frequency Mismatch

**What people do:** Poll all sources at the same interval (e.g. every minute) regardless of data freshness.

**Why it's wrong:** GTFS static files change weekly; polling them every minute hammers the source for no benefit. Air quality updates hourly; a 5-minute interval adds noise without value.

**Do this instead:** Configure poll interval per connector in the town YAML. GTFS-RT: 30s. Air quality: 15 min. GTFS static: daily. Water/electricity: hourly.

### Anti-Pattern 4: Frontend Directly Queries Database

**What people do:** Expose a direct PostgREST interface to the frontend for simplicity.

**Why it's wrong:** Leaks schema details, makes it hard to aggregate or transform data before display, and bypasses the town-scoping logic.

**Do this instead:** All frontend queries go through the FastAPI Query API which enforces town scoping, computes KPIs, and shapes responses to GeoJSON or chart-ready formats.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| MobiData BW (GTFS, GTFS-RT) | HTTP poll on schedule, parse protobuf (GTFS-RT) or ZIP (GTFS static) | Free, no auth required for open feeds; BW state-level, covers Aalen |
| LUBW (air quality) | REST API poll | Landesanstalt für Umwelt BW; free public data |
| daten-bw.de / GovData CKAN | CKAN API (`/api/3/action/package_search`) to discover datasets, then fetch resource URLs | Acts as metadata catalog; actual data is at source URLs |
| MDM (Mobilitätsdatenmarktplatz) | REST / DATEX II for traffic data | Federal platform; some feeds require registration but are free |
| Stadtwerke APIs | HTTP poll, format varies per utility | Least standardized; may require per-town investigation |
| OpenStreetMap (base tiles) | PMTiles (self-hosted) or tileserver-gl | Never depend on third-party tile providers for self-hosted installs |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Connector → Database | Direct asyncpg / psycopg3 write | Connectors write to DB directly; no message bus needed at this scale |
| Scheduler → Connector | In-process function call (APScheduler) | Celery adds operational overhead not justified until 10+ towns |
| API → Database | Async SQLAlchemy or raw asyncpg | Use async drivers to avoid blocking FastAPI event loop |
| Frontend → API | REST (JSON / GeoJSON), polling | Frontend polls `/api/layers` every N seconds for live data; SSE optional for GTFS-RT vehicles |
| Town Config → Connectors | Loaded at scheduler startup from YAML | Connectors receive a `ConnectorConfig` dataclass; never read YAML themselves |

## Build Order Implications

The component dependencies dictate a clear build sequence:

1. **Storage schema first** — Everything else depends on it. Define `features` table, hypertables, and migrations before writing connectors or API.
2. **One connector end-to-end** — Wire up the full pipeline (scheduler → connector → DB) for one domain (transit is best: GTFS is well-documented). Validates the base class and town config mechanism.
3. **Query API for that domain** — Prove the read path works. One router, one GeoJSON endpoint.
4. **Map frontend with one layer** — Validate the full vertical slice (external source → DB → API → map).
5. **Remaining connectors** — Each follows the same pattern. Parallelize once base class is stable.
6. **Dashboard / KPI layer** — Requires time-series data to already exist in DB. Build after connectors are running.
7. **Multi-town configuration** — Validate by running the same connectors with a second town YAML.

## Sources

- Urban Intelligence Architecture (Fraunhofer / PMC): https://pmc.ncbi.nlm.nih.gov/articles/PMC11014012/
- FROST-Server / OGC SensorThings API (Fraunhofer IOSB): https://fraunhoferiosb.github.io/FROST-Server/
- MobiData BW open data platform (NVBW): https://mobidata-bw.de/
- CKAN open data management system: https://ckan.org/
- MapLibre GL JS documentation: https://maplibre.org/maplibre-gl-js/docs/
- TimescaleDB + PostGIS spatial time-series: https://medium.com/@marcoscedenillabonet/optimizing-geospatial-and-time-series-queries-with-timescaledb-and-postgis-4978ea2ef8af
- Stackable Urban Data Platform (open source): https://stackable.tech/en/urbandataplatforms/
- MDPI Smart City multi-layer architecture: https://www.mdpi.com/1424-8220/24/7/2376
- Mobility Database (GTFS catalog): https://mobilitydatabase.org/

---
*Architecture research for: Open-source city data aggregation and visualization platform*
*Researched: 2026-04-05*
