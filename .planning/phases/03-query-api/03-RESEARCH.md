# Phase 3: Query API - Research

**Researched:** 2026-04-05
**Domain:** FastAPI routers, GeoJSON responses, PostGIS spatial queries, TimescaleDB analytics, NGSI-LD compatibility
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None — all implementation choices are at Claude's discretion.

### Claude's Discretion
All implementation choices. Key constraints derived from CONTEXT.md:
- NGSI-LD compatible API layer (PLAT-03) — responses should follow Smart Data Models schemas where applicable
- Data source attribution in every response (PLAT-04) — Datenlizenz Deutschland compliance
- Connector health/staleness exposed (PLAT-05) — last_successful_fetch, validation_error_count from sources table
- FastAPI already running on port 8000 with /health endpoint
- TimescaleDB hypertables: air_quality_readings, transit_positions, water_readings, energy_readings, weather_readings
- PostGIS features table with spatial data
- Town-scoped queries via town_id parameter

### Deferred Ideas (OUT OF SCOPE)
None listed.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PLAT-03 | NGSI-LD compatible API layer (Smart Data Models schemas) | GeoJSON FeatureCollection responses with @context-compatible structure; NGSI-LD "compatible" does not require a full FIWARE Orion deployment — own REST endpoints with GeoJSON output and proper typing is the hybrid approach chosen at project init |
| PLAT-04 | Data source attribution display (Datenlizenz Deutschland compliance) | Every response must include attribution metadata drawn from the sources table; sources.domain + connector_class + a static license map gives DL-DE-BY-2.0 fields |
| PLAT-05 | Connector health monitoring — staleness detection, last-update timestamps | sources.last_successful_fetch and sources.validation_error_count already populated by BaseConnector._update_staleness(); a /api/health/sources endpoint can expose these directly |
</phase_requirements>

---

## Summary

Phase 3 builds the read side of the FastAPI application: three families of endpoints (layers, timeseries, kpi) that the Phase 4+ frontend will consume. The database schema is already fully defined by migrations 001 and 002; no schema changes are required here. The main engineering challenges are (1) converting PostGIS geometry to GeoJSON cleanly in an async SQLAlchemy context, (2) composing correct attribution metadata from the sources table into every response, and (3) shaping responses to be "NGSI-LD compatible" without requiring a full FIWARE Orion deployment (per the project's Out of Scope decision).

The standard pattern in this stack is: `APIRouter` per endpoint family → `get_db` + `get_current_town` dependencies injected → raw SQL via `session.execute(text(...))` → manual assembly of Pydantic response models. `geojson-pydantic 2.1.0` provides RFC 7946-compliant `FeatureCollection` and `Feature` Pydantic types that integrate cleanly with FastAPI's `response_model`. PostGIS's `ST_AsGeoJSON()` is the right tool for geometry → GeoJSON string conversion inside SQL queries. TimescaleDB's `last(value, time)` aggregate gives the most-recent reading per station for KPI endpoints.

**Primary recommendation:** Use three `APIRouter` files (`layers.py`, `timeseries.py`, `kpi.py`) mounted on the existing FastAPI app. Each router depends on `get_db` + `get_current_town` (both already established in the codebase). `geojson-pydantic` for response shapes. Raw SQL via `text()` for all queries — no ORM models needed given the text-based pattern already established in `base.py`. Add a fourth router `connectors.py` for PLAT-05 health exposure.

---

## Project Constraints (from CLAUDE.md)

All of these are binding for this phase:

| Directive | Impact on Phase 3 |
|-----------|-------------------|
| NGSI-LD compatible API layer, Smart Data Models schemas | GeoJSON responses must include `@context` or at minimum be structurally compatible; use FIWARE SmartDataModels AirQualityObserved, TransportStop entity shapes where applicable |
| Data sources: only freely available / open data | No impact on API layer |
| Datenlizenz Deutschland (DL-DE-BY-2.0) attribution required | Every endpoint response body must include `attribution` field; not just headers |
| REST via FastAPI (not GraphQL) | Already the pattern; confirmed |
| Docker Compose self-hosted | No impact on API layer itself |
| Frontend on port 4000 | API remains on 8000; no change needed |
| Town config YAML, never hardcoded town | All queries use `town.id` from `get_current_town()` dependency |
| Async SQLAlchemy with AsyncSessionLocal | Established pattern; use throughout |
| Pydantic 2.x | Already in use; `geojson-pydantic` 2.1.0 requires `pydantic~=2.0` — compatible |
| pytest + pytest-asyncio for testing | Test all routers with `httpx.AsyncClient` + `ASGITransport` (FastAPI's recommended async test pattern) |
| Biome for TS/JS linting | No impact (backend-only phase) |

---

## Standard Stack

### Core (already installed, no new additions needed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.135.3 | Web framework + OpenAPI | Already running; APIRouter pattern for modular endpoints |
| SQLAlchemy (async) | 2.0.x | Async DB queries | `AsyncSessionLocal` + `text()` — established pattern in `base.py` |
| asyncpg | 0.31.x | Async PostgreSQL driver | Already the configured driver in DATABASE_URL |
| Pydantic | 2.12.x | Response model validation | Already in use throughout; v2 required |

### New Dependency (must be added)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| geojson-pydantic | 2.1.0 | RFC 7946 GeoJSON response models | De facto standard for typed GeoJSON in Python/FastAPI ecosystem; 575+ dependents; Pydantic v2 native; provides `FeatureCollection`, `Feature`, all geometry types |

### Supporting (no install needed — PostGIS functions)
| Tool | Purpose |
|------|---------|
| PostGIS `ST_AsGeoJSON(geometry)` | Convert stored WKB geometry to GeoJSON string in-query; eliminates Python-side WKB parsing |
| TimescaleDB `last(value, time)` | Most-recent reading per feature_id for KPI endpoint — avoids `ORDER BY ... LIMIT 1` per-group subquery |

**Installation (add to pyproject.toml):**
```bash
uv add geojson-pydantic
```

**Version verification (confirmed 2026-04-05):**
- `geojson-pydantic`: 2.1.0 (latest on PyPI as of research date)
- Pydantic compatibility: `geojson-pydantic~=2.0` requires pydantic ~2.x — project uses pydantic 2.12.5 — compatible

---

## Architecture Patterns

### Recommended Project Structure

```
backend/app/
├── routers/
│   ├── __init__.py
│   ├── layers.py          # GET /api/layers/{domain}?town={town}
│   ├── timeseries.py      # GET /api/timeseries/{domain}?town={town}&start=...&end=...
│   ├── kpi.py             # GET /api/kpi?town={town}
│   └── connectors.py      # GET /api/connectors/health?town={town}  (PLAT-05)
├── schemas/
│   ├── __init__.py
│   ├── geojson.py         # Extended FeatureCollection with attribution + last_updated
│   └── responses.py       # TimeseriesResponse, KPIResponse, ConnectorHealthResponse
├── queries/
│   ├── __init__.py
│   ├── layers.py          # SQL for features + latest reading join
│   ├── timeseries.py      # SQL for hypertable range queries
│   └── kpi.py             # SQL for last() aggregates
├── main.py                # Mount routers here
└── ...existing files
```

### Pattern 1: Router Registration on Existing App

Mount all routers in `main.py` after existing `/health` endpoint:

```python
# backend/app/main.py (additions only)
from app.routers import layers, timeseries, kpi, connectors

app.include_router(layers.router, prefix="/api")
app.include_router(timeseries.router, prefix="/api")
app.include_router(kpi.router, prefix="/api")
app.include_router(connectors.router, prefix="/api")
```

Each router file uses:
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.main import get_current_town
from app.config import Town

router = APIRouter(tags=["layers"])

@router.get("/layers/{domain}")
async def get_layer(
    domain: str,
    db: AsyncSession = Depends(get_db),
    town: Town = Depends(get_current_town),
) -> dict:
    ...
```

### Pattern 2: Town Validation — 404 on Unknown Town

The `get_current_town()` dependency loads a single town at startup; the `town` query param must match `town.id`. Unknown town → 404:

```python
@router.get("/layers/{domain}")
async def get_layer(
    domain: str,
    town_param: str = Query(..., alias="town"),
    db: AsyncSession = Depends(get_db),
    current_town: Town = Depends(get_current_town),
):
    if town_param != current_town.id:
        raise HTTPException(status_code=404, detail=f"Unknown town: {town_param!r}")
```

### Pattern 3: PostGIS Geometry → GeoJSON in SQL

Use `ST_AsGeoJSON()` inside the SELECT to get geometry as a JSON string. Cast with `::text` for asyncpg compatibility. Then `json.loads()` in Python:

```python
# Source: PostGIS docs + GeoAlchemy2 pattern
result = await db.execute(
    text("""
        SELECT
            f.id::text,
            ST_AsGeoJSON(f.geometry)::text AS geometry,
            f.properties,
            f.source_id,
            f.domain
        FROM features f
        WHERE f.town_id = :town_id
          AND f.domain = :domain
    """),
    {"town_id": town.id, "domain": domain},
)
rows = result.mappings().all()
```

Then build `Feature` objects:
```python
import json
from geojson_pydantic import Feature, FeatureCollection

features = [
    Feature(
        type="Feature",
        id=str(row["id"]),
        geometry=json.loads(row["geometry"]),
        properties=row["properties"] or {},
    )
    for row in rows
]
```

### Pattern 4: Joining Latest Reading to Features (Layers Endpoint)

For `GET /api/layers/air_quality`, join the most recent reading per feature from the hypertable using `DISTINCT ON` (cleaner than subquery for small feature counts):

```python
# Source: PostgreSQL DISTINCT ON pattern + TimescaleDB docs
text("""
    SELECT
        f.id::text,
        ST_AsGeoJSON(f.geometry)::text AS geometry,
        f.properties,
        r.pm25, r.pm10, r.no2, r.o3, r.aqi,
        r.time AS reading_time
    FROM features f
    LEFT JOIN LATERAL (
        SELECT pm25, pm10, no2, o3, aqi, time
        FROM air_quality_readings
        WHERE feature_id = f.id
        ORDER BY time DESC
        LIMIT 1
    ) r ON true
    WHERE f.town_id = :town_id
      AND f.domain = 'air_quality'
""")
```

For transit layers, features table already contains stop/shape geometries — no hypertable join needed for static layer.

### Pattern 5: TimescaleDB LAST() for KPI Endpoint

```sql
-- Source: TimescaleDB docs https://docs.timescale.com/api/latest/hyperfunctions/last/
SELECT
    last(aqi, time) AS current_aqi,
    last(pm25, time) AS current_pm25,
    last(pm10, time) AS current_pm10,
    last(no2, time) AS current_no2,
    MAX(time) AS last_updated
FROM air_quality_readings r
JOIN features f ON r.feature_id = f.id
WHERE f.town_id = :town_id
  AND r.time > NOW() - INTERVAL '24 hours'
```

### Pattern 6: Response Schema with Attribution

Every response must include `attribution` and `last_updated`. Define a base response Pydantic model:

```python
# backend/app/schemas/geojson.py
from datetime import datetime
from typing import Any
from pydantic import BaseModel
from geojson_pydantic import FeatureCollection as BaseFeatureCollection

class Attribution(BaseModel):
    source_name: str           # e.g. "Umweltbundesamt (UBA)"
    license: str               # "Datenlizenz Deutschland – Namensnennung – Version 2.0"
    license_url: str           # "https://www.govdata.de/dl-de/by-2-0"
    url: str | None = None     # upstream data URL

class LayerResponse(BaseModel):
    type: str = "FeatureCollection"
    features: list[dict]       # GeoJSON Feature dicts
    attribution: list[Attribution]
    last_updated: datetime | None
    town: str
    domain: str
```

### Pattern 7: NGSI-LD Compatibility (PLAT-03)

Per the project's Out of Scope decision ("Full FIWARE Orion deployment"), NGSI-LD compatible means:
- GeoJSON output uses `application/geo+json` content type
- Properties follow Smart Data Models naming conventions where practical (e.g., `pm25` → `atmosphericPressure`, `no2` → `no2`)
- Responses can include an optional `@context` field pointing to Smart Data Models JSON-LD context URL
- No full entity management API required; read-only GET endpoints are sufficient for "compatible" designation

Minimal NGSI-LD compatibility pattern:
```python
NGSI_CONTEXT = "https://uri.fiware.org/ns/data-models/context.jsonld"

class LayerResponse(BaseModel):
    context: str = Field(default=NGSI_CONTEXT, alias="@context")
    type: str = "FeatureCollection"
    ...

    class Config:
        populate_by_name = True
```

### Anti-Patterns to Avoid

- **ORM models for read queries:** The codebase uses raw `text()` SQL throughout; do not introduce SQLAlchemy ORM mapped classes for Phase 3 queries — it adds complexity without benefit for read-only SQL.
- **Fetching all rows then Python-side geometry parsing:** Always use `ST_AsGeoJSON()` in the SQL query; never read raw WKB geometry bytes into Python and use shapely to convert — this is slower and adds a dependency.
- **Hard-coding domain list in router:** Domain is a URL path parameter; validate against an allowed set (`air_quality`, `transit`, `weather`, `water`, `energy`) and return 404 for unknown domains — prevents empty result confusion.
- **Separate session per row:** The existing pattern opens one session per operation; for queries returning many features, fetch all rows in one query execution, not per-row round trips.
- **Missing timezone on datetime:** All TimescaleDB timestamps are `TIMESTAMP WITH TIME ZONE`; always return ISO 8601 with UTC `Z` suffix in responses.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GeoJSON response types | Custom dict schemas | `geojson-pydantic` FeatureCollection/Feature | RFC 7946 compliance, FastAPI schema generation, validation |
| Geometry → JSON conversion | shapely/WKB parsing in Python | `ST_AsGeoJSON()` in SQL | Database-side, zero Python overhead, always correct CRS |
| Latest-value-per-group query | Python loop over ordered rows | `LATERAL ... ORDER BY time DESC LIMIT 1` or `last(val, time)` | Set-based, uses TimescaleDB/PG indexes |
| Town validation middleware | Custom middleware class | Query param check + `HTTPException(404)` in each handler | Simple, explicit, testable |
| Attribution field lookup | Static dict in code | Query `sources` table by `town_id + domain` | Sources table already populated; stays in sync with connector config |

**Key insight:** PostGIS does geometry serialization better than any Python library. Push the `ST_AsGeoJSON()` call into SQL, return a JSON string, `json.loads()` it once — that's the entire geometry conversion pipeline.

---

## Common Pitfalls

### Pitfall 1: asyncpg returns geometry as bytes, not string
**What goes wrong:** Selecting a `geometry` column directly with asyncpg returns raw WKB bytes, not a string. Passing those to `json.loads()` raises a TypeError.
**Why it happens:** asyncpg maps PostGIS geometry types to bytes by default.
**How to avoid:** Always cast the result of `ST_AsGeoJSON()` explicitly to text: `ST_AsGeoJSON(geometry)::text`. The `::text` cast forces asyncpg to return a Python `str`.
**Warning signs:** `TypeError: a bytes-like object cannot be interpreted as str` when processing geometry.

### Pitfall 2: geojson-pydantic v2.x FeatureCollection is generic
**What goes wrong:** `FeatureCollection(features=[...])` may fail with type errors if features are passed as plain dicts rather than `Feature` objects in v2.
**Why it happens:** v2.0 changed collection classes to be generic — `FeatureCollection[Feature[Geometry, Properties]]`. Direct dict passing may not validate.
**How to avoid:** Either construct `Feature` objects explicitly, or return plain dicts and use `response_model=None` with a manually defined Pydantic model for the envelope (attribution, last_updated) wrapping the GeoJSON dict.
**Warning signs:** Pydantic `ValidationError` when constructing FeatureCollection from query results.

### Pitfall 3: `get_current_town()` not importable from `main.py`
**What goes wrong:** Circular import: `routers/layers.py` imports from `app.main`, which imports from `app.routers.layers`.
**Why it happens:** `get_current_town()` is defined in `main.py` alongside the `_current_town` module-level variable.
**How to avoid:** Move `_current_town` state and `get_current_town()` dependency to a new `app/dependencies.py` module. Import from there in both `main.py` and all routers. This is the standard FastAPI pattern for shared dependencies.
**Warning signs:** `ImportError: cannot import name...` or `ImportError: circular import`.

### Pitfall 4: Missing domain validation returns empty FeatureCollection silently
**What goes wrong:** `GET /api/layers/typo?town=aalen` returns a valid-looking 200 with 0 features instead of 404.
**Why it happens:** The SQL `WHERE domain = :domain` simply matches nothing — no error.
**How to avoid:** Add an explicit domain allowlist: `VALID_DOMAINS = {"air_quality", "transit", "weather", "water", "energy"}`. Return `HTTPException(404)` for unknown domains.

### Pitfall 5: Time range queries without index hint on hypertable
**What goes wrong:** Timeseries queries with very wide date ranges scan too many chunks.
**Why it happens:** TimescaleDB chunks by time; queries covering years scan all historical chunks.
**How to avoid:** Always include `AND r.time > :start AND r.time < :end` with timestamps as `datetime` objects (not strings). Asyncpg handles Python `datetime` → PostgreSQL `timestamptz` correctly. Add reasonable default and maximum range limits (e.g., max 90 days per request).

### Pitfall 6: sources table may not have rows for all connectors
**What goes wrong:** The health endpoint returns empty list or crashes when joining `features` to `sources` by domain.
**Why it happens:** `sources` rows are only created if the connector's `config` included a corresponding INSERT (Phase 2 implementation detail). `_update_staleness()` does an UPDATE, not INSERT.
**How to avoid:** The health endpoint should query `sources` directly for all rows where `town_id = :town_id`; do not JOIN to features. If no rows exist, return empty health list with a clear `message` field.

---

## Code Examples

### Router file skeleton

```python
# backend/app/routers/layers.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json

from app.db import get_db
from app.dependencies import get_current_town  # moved from main.py
from app.config import Town

router = APIRouter(tags=["layers"])

VALID_DOMAINS = {"air_quality", "transit", "weather", "water", "energy"}

@router.get("/layers/{domain}")
async def get_layer(
    domain: str,
    town: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_town: Town = Depends(get_current_town),
):
    if town != current_town.id:
        raise HTTPException(status_code=404, detail=f"Unknown town: {town!r}")
    if domain not in VALID_DOMAINS:
        raise HTTPException(status_code=404, detail=f"Unknown domain: {domain!r}")
    # ... query and assemble response
```

### PostGIS geometry query (verified pattern)

```python
# Source: PostGIS ST_AsGeoJSON docs + asyncpg casting requirement
result = await db.execute(
    text("""
        SELECT
            f.id::text            AS id,
            ST_AsGeoJSON(f.geometry)::text AS geometry,
            f.properties,
            f.source_id
        FROM features f
        WHERE f.town_id = :town_id
          AND f.domain   = :domain
    """),
    {"town_id": current_town.id, "domain": domain},
)
rows = result.mappings().all()

features = []
for row in rows:
    geom = json.loads(row["geometry"])
    props = dict(row["properties"] or {})
    features.append({
        "type": "Feature",
        "id": row["id"],
        "geometry": geom,
        "properties": props,
    })
```

### TimescaleDB KPI query (verified pattern)

```python
# Source: TimescaleDB last() docs https://docs.timescale.com/api/latest/hyperfunctions/last/
result = await db.execute(
    text("""
        SELECT
            last(aqi,  time) AS current_aqi,
            last(pm25, time) AS current_pm25,
            last(pm10, time) AS current_pm10,
            last(no2,  time) AS current_no2,
            last(o3,   time) AS current_o3,
            MAX(time)        AS last_updated
        FROM air_quality_readings r
        JOIN features f ON r.feature_id = f.id
        WHERE f.town_id = :town_id
          AND r.time > NOW() - INTERVAL '24 hours'
    """),
    {"town_id": current_town.id},
)
```

### Attribution from sources table

```python
# Source: migration 002 — sources table has last_successful_fetch, validation_error_count
result = await db.execute(
    text("""
        SELECT id, domain, connector_class, last_successful_fetch, validation_error_count
        FROM sources
        WHERE town_id = :town_id
          AND domain  = :domain
    """),
    {"town_id": current_town.id, "domain": domain},
)
```

Map `connector_class` to DL-DE-BY-2.0 attribution using a static dict in the router (source names don't change at runtime):

```python
CONNECTOR_ATTRIBUTION = {
    "UBAConnector": {
        "source_name": "Umweltbundesamt (UBA)",
        "license": "Datenlizenz Deutschland – Namensnennung – Version 2.0",
        "license_url": "https://www.govdata.de/dl-de/by-2-0",
        "url": "https://www.umweltbundesamt.de/",
    },
    "SensorCommunityConnector": {
        "source_name": "Sensor.Community",
        "license": "Open Data Commons Open Database License (ODbL)",
        "license_url": "https://opendatacommons.org/licenses/odbl/",
        "url": "https://sensor.community/",
    },
    "GTFSConnector": {
        "source_name": "MobiData BW / NVBW GTFS",
        "license": "Datenlizenz Deutschland – Namensnennung – Version 2.0",
        "license_url": "https://www.govdata.de/dl-de/by-2-0",
        "url": "https://www.mobidata-bw.de/",
    },
    "WeatherConnector": {
        "source_name": "Deutscher Wetterdienst (DWD) via Bright Sky",
        "license": "Datenlizenz Deutschland – Zero – Version 2.0",
        "license_url": "https://www.govdata.de/dl-de/zero-2-0",
        "url": "https://brightsky.dev/",
    },
}
```

---

## Runtime State Inventory

> SKIPPED — this is a greenfield API layer phase, not a rename/refactor phase.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| PostgreSQL + TimescaleDB | All query endpoints | Docker only (not running at research time) | PG 17 + TSDB per docker-compose.yml | Run `docker compose up db` before testing |
| PostGIS extension | layers endpoint geometry | Docker only | Installed via migration 001 | — |
| Python 3.11+ | Backend runtime | ✓ (confirmed by pytest pyc files: cpython-311) | 3.11 | — |
| uv | Dependency management | Unknown (not checked) | — | pip install directly |

**Missing dependencies with no fallback:**
- TimescaleDB must be running for endpoint integration tests; unit tests (mocked DB) work offline.

**Missing dependencies with fallback:**
- Docker services not running during research — all integration tests require `docker compose up` first.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | `backend/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cd backend && python -m pytest tests/test_api_layers.py tests/test_api_timeseries.py tests/test_api_kpi.py -x -m "not slow"` |
| Full suite command | `cd backend && python -m pytest tests/ -m "not slow"` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PLAT-03 | GET /api/layers/transit returns valid GeoJSON FeatureCollection | unit (mocked DB) | `pytest tests/test_api_layers.py::test_layers_transit_returns_geojson -x` | Wave 0 |
| PLAT-03 | GET /api/layers/air_quality returns GeoJSON with AQI and health-tier colors in properties | unit (mocked DB) | `pytest tests/test_api_layers.py::test_layers_air_quality_properties -x` | Wave 0 |
| PLAT-03 | All layer responses include `type: FeatureCollection` and valid feature geometry | unit | `pytest tests/test_api_layers.py::test_layer_geojson_structure -x` | Wave 0 |
| PLAT-04 | Every layer response body contains attribution list with license field | unit | `pytest tests/test_api_layers.py::test_layer_attribution_present -x` | Wave 0 |
| PLAT-04 | Every response includes last_updated field | unit | `pytest tests/test_api_timeseries.py::test_timeseries_last_updated -x` | Wave 0 |
| PLAT-05 | GET /api/connectors/health returns last_successful_fetch and validation_error_count | unit | `pytest tests/test_api_connectors.py::test_connector_health -x` | Wave 0 |
| PLAT-03 | GET /api/timeseries/air_quality returns time-ordered readings | unit | `pytest tests/test_api_timeseries.py::test_timeseries_ordered -x` | Wave 0 |
| PLAT-03 | GET /api/kpi returns current AQI, weather summary, transit metrics | unit | `pytest tests/test_api_kpi.py::test_kpi_fields -x` | Wave 0 |
| PLAT-03 | Unknown town → 404 | unit | `pytest tests/test_api_layers.py::test_unknown_town_404 -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_api_layers.py tests/test_api_timeseries.py tests/test_api_kpi.py tests/test_api_connectors.py -x -m "not slow"`
- **Per wave merge:** `cd backend && python -m pytest tests/ -m "not slow"`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_api_layers.py` — covers PLAT-03 layers, PLAT-04 attribution
- [ ] `backend/tests/test_api_timeseries.py` — covers PLAT-03 timeseries, PLAT-04 last_updated
- [ ] `backend/tests/test_api_kpi.py` — covers PLAT-03 KPI endpoint
- [ ] `backend/tests/test_api_connectors.py` — covers PLAT-05 health endpoint
- [ ] `backend/app/dependencies.py` — extract `get_current_town` to break circular import (needed before any router can be tested)
- [ ] `backend/app/routers/__init__.py` and router files

**Test approach for router unit tests:** Use `httpx.AsyncClient` with `ASGITransport(app=app)` plus `unittest.mock.AsyncMock` to mock `get_db` and `get_current_town` dependencies — avoids requiring a live database for unit tests. This is FastAPI's recommended async testing pattern.

```python
# Wave 0 fixture pattern
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch
from app.main import app

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Mapbox GL JS (proprietary) | MapLibre GL JS (OSS fork) | 2020 | Confirmed in CLAUDE.md; no impact on backend |
| Pydantic v1 | Pydantic v2 | 2023 | Already on v2; geojson-pydantic 2.x requires v2 |
| geojson-pydantic v1.x | geojson-pydantic v2.x (generic FeatureCollection) | Oct 2025 | v2 breaking change: no `__iter__`/`__len__` on collections; access via `.features` |
| FastAPI TestClient (sync) | `httpx.AsyncClient` + `ASGITransport` | FastAPI docs update ~2024 | Required for async route testing; `TestClient` works but blocks |

**Deprecated/outdated:**
- `from starlette.testclient import TestClient` for async routes: use `httpx.AsyncClient(transport=ASGITransport(app=app))` instead for proper async testing.
- `geojson_pydantic.FeatureCollection.__iter__()`: removed in v2.0 — iterate via `.features` attribute.

---

## Open Questions

1. **AQI health-tier color logic (success criterion 2)**
   - What we know: Success criterion says "returns GeoJSON with AQI readings and health-tier colors"
   - What's unclear: Where does health-tier color assignment live? In the API response (computed at query time) or in the frontend? There is no AQI tier color config in the codebase yet.
   - Recommendation: Compute and inject `aqi_tier` and `aqi_color` as properties in the GeoJSON Feature at query time in the layers endpoint. Use a static AQI tier lookup (WHO/UBA thresholds) defined in `app/routers/layers.py`. This is simpler than frontend-side computation and enables correct NGSI-LD property typing.

2. **sources table rows: guaranteed to exist for all connectors?**
   - What we know: `_update_staleness()` does `UPDATE sources ... WHERE connector_class = :class AND town_id = :town_id` — it does NOT insert rows.
   - What's unclear: Phase 2 may not have inserted rows into `sources` for all connectors. The health endpoint (PLAT-05) could return empty results.
   - Recommendation: The connectors health router should query `sources` and gracefully return an empty list with a note if no rows found. If Phase 2 did not insert into sources, the planner should add a Wave 0 task to verify and document whether sources rows must be seeded by migration or by the scheduler setup.

3. **Transit layer: stops vs. shapes vs. positions**
   - What we know: GTFSConnector writes transit stops and shapes into `features` (static). GTFSRealtimeConnector writes live positions into `transit_positions` hypertable.
   - What's unclear: Should `GET /api/layers/transit` return only static stops/routes (from features), or also current vehicle positions from the hypertable?
   - Recommendation: For Phase 3, return static stops/shapes from the `features` table (simpler, always available). Vehicle positions are real-time data better suited to a separate endpoint or Phase 5+ streaming feature. Document this scope decision.

---

## Sources

### Primary (HIGH confidence)
- PostGIS docs — `ST_AsGeoJSON()` function signature and `::text` cast requirement — https://postgis.net/docs/ST_AsGeoJSON.html
- TimescaleDB docs — `last(value, time)` aggregate function — https://docs.timescale.com/api/latest/hyperfunctions/last/
- FastAPI official docs — APIRouter pattern, bigger applications — https://fastapi.tiangolo.com/tutorial/bigger-applications/
- geojson-pydantic PyPI / release notes — version 2.1.0, Pydantic 2.x requirement — https://developmentseed.org/geojson-pydantic/release-notes/
- Project codebase — `base.py` (text() query pattern), `db.py` (AsyncSessionLocal), `main.py` (get_current_town), migration files (schema) — direct read

### Secondary (MEDIUM confidence)
- FastAPI + PostGIS + GeoAlchemy integration examples — https://medium.com/@notarious2/working-with-spatial-data-using-fastapi-and-geoalchemy-797d414d2fe7
- NGSI-LD GeoJSON content type (`application/geo+json`) — https://ngsi-ld.org/ and fiware-datamodels.readthedocs.io
- TimescaleDB 5 ways to query last point — https://forum.tigerdata.com/forum/t/5-ways-to-efficiently-query-last-point-data-in-postgresql-and-timescaledb-hypertables/199

### Tertiary (LOW confidence)
- Smart Data Models AirQualityObserved property naming conventions — https://fiware.github.io/data-models/specs/ngsi-ld_faq.html (not verified against actual schema files)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — existing packages confirmed via pyproject.toml; geojson-pydantic version confirmed via PyPI API
- Architecture: HIGH — patterns derived directly from existing codebase conventions in base.py, db.py, main.py
- SQL patterns: HIGH — ST_AsGeoJSON and LAST() confirmed via official PostGIS/TimescaleDB docs
- NGSI-LD compatibility: MEDIUM — "compatible" scope is deliberately minimal per project Out of Scope; exact Smart Data Models property names not verified against individual schema files
- Pitfalls: HIGH — asyncpg WKB/text pitfall verified from direct knowledge of asyncpg behavior; circular import pitfall derived from observed codebase structure

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (stable stack; geojson-pydantic and FastAPI versions unlikely to change significantly in 30 days)
