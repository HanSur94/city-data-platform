# Phase 1: Foundation - Research

**Researched:** 2026-04-05
**Domain:** Docker Compose + TimescaleDB/PostGIS schema + Alembic migrations + Pydantic YAML config + BaseConnector pattern + BKG VG250 boundary loading
**Confidence:** HIGH (core stack verified; VG250 attribute details MEDIUM)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
All implementation choices are at Claude's discretion — pure infrastructure phase. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key constraints from PROJECT.md:
- Hybrid architecture: own FastAPI backend + TimescaleDB/PostGIS + NGSI-LD compatible API
- Town-config-driven from the start (PLAT-01)
- Docker Compose self-hosted deployment (PLAT-02)
- Plugin-based connector architecture with BaseConnector pattern (PLAT-06)
- TimescaleDB for time-series (PLAT-07), PostGIS for spatial (PLAT-08)
- Frontend runs on port 4000 (not 3000 — Grafana occupies 3000 on target system)
- Smart Data Models schemas for NGSI-LD compatibility (PLAT-03 — Phase 3)

### Claude's Discretion
All implementation choices are at Claude's discretion for this infrastructure phase.

### Deferred Ideas (OUT OF SCOPE)
None — infrastructure phase.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PLAT-01 | Town-config-driven architecture — add a new town via config file, no code changes | Pydantic BaseSettings + YAML loading; `towns/` directory with per-town YAML validated by Pydantic BaseModel |
| PLAT-02 | Docker Compose self-hosted deployment — single `docker-compose up` | Docker Compose v5.1.1 available; timescale/timescaledb-ha image includes both TimescaleDB and PostGIS |
| PLAT-06 | Plugin-based connector architecture (BaseConnector pattern) | Abstract base class with fetch/normalize/persist methods; stub connector for testing |
| PLAT-07 | Time-series storage with retention policies (TimescaleDB) | `create_hypertable()` + `add_retention_policy()` via Alembic `op.execute()` |
| PLAT-08 | Spatial query support (PostGIS) | PostGIS available in timescaledb-ha image; `features` table with GEOMETRY column |
| GEO-06 | Administrative boundaries (BKG VG250) | VG250 Shapefile/GeoPackage download from BKG; filter by AGS=08136088 for Aalen; load via geopandas + sync SQLAlchemy |
</phase_requirements>

---

## Summary

Phase 1 is a pure infrastructure phase. All external tooling (Docker, Docker Compose, Python 3.11, pytest) is confirmed available on the developer machine. The core challenge is wiring together six independent concerns — Docker Compose service orchestration, Alembic migration with TimescaleDB-specific DDL, Pydantic YAML config loading, the BaseConnector abstract class, PostGIS spatial table setup, and one-time BKG VG250 data import — in a way that leaves future phases with clean extension points.

The key Docker image decision is **`timescale/timescaledb-ha`** rather than the older `timescale/timescaledb-postgis` image, which is no longer maintained. The ha image bundles both TimescaleDB and PostGIS in a single container. Alembic cannot use autogenerate for hypertable indexes cleanly — the migration must call `create_hypertable()` and `add_retention_policy()` via raw `op.execute()`. For VG250, GeoPandas with a synchronous SQLAlchemy engine is the correct path; `to_postgis()` does not support async engines.

**Primary recommendation:** Build the Docker Compose stack first (establishes the running environment), then schema via Alembic (everything else depends on it), then YAML config loader + BaseConnector (they share the ConnectorConfig dataclass), then BKG VG250 import as a one-shot script.

---

## Project Constraints (from CLAUDE.md)

| Constraint | Details |
|------------|---------|
| No Grafana | Port 3000 in use on target system; frontend on port 4000 |
| No paid APIs | Open data only — DL-DE-BY-2.0 attribution required |
| No Aalen hardcoding | All town-specific config in YAML files |
| No Mapbox GL JS | Use MapLibre GL JS (open-source fork) |
| No GraphQL | REST via FastAPI only |
| No create-react-app | Use Next.js App Router |
| No Leaflet | Use MapLibre GL JS |
| Python package manager | Use `uv`, not pip/poetry |
| JS package manager | Use `pnpm`, not npm |
| Linting/formatting | Biome (replaces ESLint + Prettier) |
| Testing | pytest + pytest-asyncio for Python |
| NGSI-LD | Compatible API layer required (Phase 3 scope, but schema must support it) |

---

## Standard Stack

### Core (Phase 1 relevant)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| timescale/timescaledb-ha | pg17 tag | PostgreSQL 17 + TimescaleDB 2.23 + PostGIS in one image | Official Timescale image that bundles both extensions; `timescale/timescaledb-postgis` is deprecated |
| FastAPI | 0.135.x | Python HTTP API + startup event handler | Async-native; Pydantic v2 integration; lifespan events for startup validation |
| Alembic | 1.18.x | Database migration management | Standard SQLAlchemy migration tool; `op.execute()` used for TimescaleDB-specific DDL |
| SQLAlchemy | 2.x | ORM + connection pool | Async-compatible; `create_async_engine` for FastAPI; sync engine for geopandas import |
| Pydantic | 2.x | Data validation and config models | `BaseModel` for Town config; strict validation of YAML fields |
| PyYAML | 6.x | YAML file parsing | Load `towns/*.yaml` into dict before Pydantic validation |
| psycopg2-binary | 2.9.x | Sync PostgreSQL driver | Required by geopandas `to_postgis()`; used in migration context |
| asyncpg | 0.30.x | Async PostgreSQL driver | Used by SQLAlchemy async engine for FastAPI routes |
| geopandas | 1.x | Shapefile reading + PostGIS writing | `read_file()` for VG250 shapefile; `to_postgis()` for loading into PostGIS |
| GeoAlchemy2 | 0.15.x | SQLAlchemy PostGIS types | Required by geopandas `to_postgis()` for geometry column type mapping |
| httpx | 0.27.x | Async HTTP client | Used by connectors to fetch external APIs |
| pytest | 9.x | Test framework | Confirmed available: `pytest 9.0.2` |
| pytest-asyncio | 0.24.x | Async test support | Required for testing async FastAPI code |

### Infrastructure

| Technology | Purpose | Notes |
|------------|---------|-------|
| Docker Compose v5 | Service orchestration | Confirmed available: `Docker Compose version v5.1.1` |
| Docker 29.x | Container runtime | Confirmed available: `Docker version 29.3.1` |
| uv 0.9.x | Python package manager | Confirmed available: `uv 0.9.30` |

### Installation

```bash
# Backend Python environment (from project root)
uv init backend
cd backend
uv add fastapi uvicorn alembic sqlalchemy asyncpg psycopg2-binary \
       pydantic pyyaml httpx geopandas geoalchemy2 shapely
uv add --dev pytest pytest-asyncio
```

### Version verification (confirmed 2026-04-05)

```bash
# Check current versions before writing pyproject.toml
uv pip index versions fastapi
uv pip index versions timescale  # for docker image tags
```

---

## Architecture Patterns

### Recommended Project Structure

```
city-data-platform/
├── backend/                      # Python FastAPI application
│   ├── pyproject.toml            # uv-managed dependencies
│   ├── alembic.ini               # Alembic config
│   ├── alembic/
│   │   ├── env.py                # Migration environment
│   │   └── versions/
│   │       └── 001_initial_schema.py  # Creates all tables + hypertables
│   ├── app/
│   │   ├── main.py               # FastAPI app factory + lifespan
│   │   ├── config.py             # Town config loader (YAML -> Pydantic)
│   │   ├── db.py                 # SQLAlchemy async engine + session
│   │   └── connectors/
│   │       ├── base.py           # BaseConnector abstract class
│   │       └── stub.py           # Stub connector for testing
│   └── scripts/
│       └── load_vg250.py         # One-shot BKG VG250 import script
├── towns/
│   ├── aalen.yaml                # Aalen reference config
│   └── example.yaml              # Template for new towns
├── docker-compose.yml            # db, backend services
└── tests/
    ├── conftest.py               # Shared fixtures (DB, config)
    ├── test_config.py            # YAML config loading tests
    └── test_connector.py         # BaseConnector stub tests
```

### Pattern 1: Docker Compose with timescaledb-ha

**What:** Use `timescale/timescaledb-ha:pg17` as the single database image — it ships PostgreSQL 17, TimescaleDB 2.23, and PostGIS together. No need to enable extensions manually in migrations.

**When to use:** Always for this project.

```yaml
# docker-compose.yml
version: "3.9"
services:
  db:
    image: timescale/timescaledb-ha:pg17
    environment:
      POSTGRES_DB: citydata
      POSTGRES_USER: citydata
      POSTGRES_PASSWORD: citydata
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U citydata -d citydata"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+asyncpg://citydata:citydata@db:5432/citydata
      TOWN: aalen
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./towns:/app/towns:ro

volumes:
  pgdata:
```

### Pattern 2: Alembic Migration with TimescaleDB DDL

**What:** Create tables normally using `op.create_table()`, then immediately call `create_hypertable()` and `add_retention_policy()` via `op.execute()`. Alembic cannot autogenerate these — always hand-write the TimescaleDB calls.

**Critical gotcha:** Alembic autogenerate will attempt to DROP the index TimescaleDB creates on the time column. Fix by adding a `include_object` filter in `alembic/env.py`.

```python
# alembic/versions/001_initial_schema.py

def upgrade() -> None:
    # --- Config tables (standard relational) ---
    op.create_table(
        "towns",
        sa.Column("id", sa.String, primary_key=True),  # "aalen"
        sa.Column("display_name", sa.String, nullable=False),
        sa.Column("country", sa.String, nullable=False, server_default="DE"),
        sa.Column("bbox", postgresql.JSONB, nullable=True),  # [lon_min, lat_min, lon_max, lat_max]
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "sources",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("town_id", sa.String, sa.ForeignKey("towns.id"), nullable=False),
        sa.Column("domain", sa.String, nullable=False),   # "transit", "air_quality", etc.
        sa.Column("connector_class", sa.String, nullable=False),
        sa.Column("config", postgresql.JSONB, nullable=True),
        sa.Column("poll_interval_seconds", sa.Integer, server_default="300"),
        sa.Column("enabled", sa.Boolean, server_default="true"),
    )

    # --- Spatial table (PostGIS) ---
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    op.create_table(
        "features",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("town_id", sa.String, sa.ForeignKey("towns.id"), nullable=False),
        sa.Column("domain", sa.String, nullable=False),
        sa.Column("source_id", sa.String, nullable=True),
        sa.Column("geometry", ga.Geometry("GEOMETRY", srid=4326), nullable=False),
        sa.Column("properties", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_features_town_domain", "features", ["town_id", "domain"])
    op.create_index("idx_features_geometry", "features", ["geometry"], postgresql_using="gist")

    # --- Domain hypertables ---
    # Air quality readings
    op.create_table(
        "air_quality_readings",
        sa.Column("time", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("feature_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("features.id"), nullable=False),
        sa.Column("pm25", sa.Float, nullable=True),
        sa.Column("pm10", sa.Float, nullable=True),
        sa.Column("no2", sa.Float, nullable=True),
        sa.Column("o3", sa.Float, nullable=True),
        sa.Column("aqi", sa.Float, nullable=True),
    )
    op.execute(
        "SELECT create_hypertable('air_quality_readings', 'time', "
        "chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE)"
    )
    op.execute(
        "SELECT add_retention_policy('air_quality_readings', "
        "drop_after => INTERVAL '2 years', if_not_exists => TRUE)"
    )

    # Transit vehicle positions
    op.create_table(
        "transit_positions",
        sa.Column("time", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("feature_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("features.id"), nullable=False),
        sa.Column("trip_id", sa.String, nullable=True),
        sa.Column("route_id", sa.String, nullable=True),
        sa.Column("delay_seconds", sa.Integer, nullable=True),
        sa.Column("geometry", ga.Geometry("POINT", srid=4326), nullable=True),
    )
    op.execute(
        "SELECT create_hypertable('transit_positions', 'time', "
        "chunk_time_interval => INTERVAL '1 hour', if_not_exists => TRUE)"
    )
    op.execute(
        "SELECT add_retention_policy('transit_positions', "
        "drop_after => INTERVAL '90 days', if_not_exists => TRUE)"
    )

    # Water level readings
    op.create_table(
        "water_readings",
        sa.Column("time", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("feature_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("features.id"), nullable=False),
        sa.Column("level_cm", sa.Float, nullable=True),
        sa.Column("flow_m3s", sa.Float, nullable=True),
    )
    op.execute(
        "SELECT create_hypertable('water_readings', 'time', "
        "chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE)"
    )
    op.execute(
        "SELECT add_retention_policy('water_readings', "
        "drop_after => INTERVAL '5 years', if_not_exists => TRUE)"
    )

    # Energy readings
    op.create_table(
        "energy_readings",
        sa.Column("time", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("feature_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("features.id"), nullable=False),
        sa.Column("value_kw", sa.Float, nullable=True),
        sa.Column("source_type", sa.String, nullable=True),  # "solar", "wind", "grid"
    )
    op.execute(
        "SELECT create_hypertable('energy_readings', 'time', "
        "chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE)"
    )
    op.execute(
        "SELECT add_retention_policy('energy_readings', "
        "drop_after => INTERVAL '5 years', if_not_exists => TRUE)"
    )


def downgrade() -> None:
    for table in ["energy_readings", "water_readings", "transit_positions",
                  "air_quality_readings", "features", "sources", "towns"]:
        op.drop_table(table)
```

**Fix for Alembic autogenerate dropping TimescaleDB indexes:**

```python
# alembic/env.py — add this filter to exclude timescaledb internal objects

def include_object(object, name, type_, reflected, compare_to):
    # Skip TimescaleDB internal schema tables
    if type_ == "table" and hasattr(object, "schema") and object.schema == "_timescaledb_internal":
        return False
    # Skip the auto-created index on the time column that TimescaleDB manages
    if type_ == "index" and name and name.startswith("_hyper_"):
        return False
    return True

# In run_migrations_online():
context.configure(
    ...
    include_object=include_object,
)
```

### Pattern 3: Town Config via YAML + Pydantic BaseModel

**What:** Each town has a YAML file in `towns/`. A config loader reads the YAML, validates it through a Pydantic model, and returns a `Town` object. No code changes are needed when switching towns.

**Note:** Use plain `pydantic.BaseModel` (not `pydantic_settings.BaseSettings`). `BaseSettings` is for env-var-driven config; town YAML is data config. Load YAML manually then call `Town.model_validate()`.

```python
# app/config.py
from pathlib import Path
from typing import Optional
import yaml
from pydantic import BaseModel, field_validator

class ConnectorConfig(BaseModel):
    connector_class: str
    poll_interval_seconds: int = 300
    enabled: bool = True
    config: dict = {}

class TownBbox(BaseModel):
    lon_min: float
    lat_min: float
    lon_max: float
    lat_max: float

class Town(BaseModel):
    id: str                          # "aalen" — used as DB key
    display_name: str                # "Aalen (Württemberg)"
    country: str = "DE"
    timezone: str = "Europe/Berlin"
    bbox: TownBbox
    connectors: list[ConnectorConfig] = []

    @field_validator("id")
    @classmethod
    def id_must_be_slug(cls, v: str) -> str:
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Town id must be alphanumeric slug")
        return v.lower()


def load_town(town_id: str, towns_dir: Path = Path("towns")) -> Town:
    """Load and validate a town config from YAML. Raises ValidationError on bad config."""
    yaml_path = towns_dir / f"{town_id}.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"Town config not found: {yaml_path}")
    raw = yaml.safe_load(yaml_path.read_text())
    return Town.model_validate(raw)
```

```yaml
# towns/aalen.yaml
id: aalen
display_name: "Aalen (Württemberg)"
country: DE
timezone: Europe/Berlin
bbox:
  lon_min: 9.9700
  lat_min: 48.7600
  lon_max: 10.2200
  lat_max: 48.9000

connectors:
  - connector_class: StubConnector
    poll_interval_seconds: 300
    enabled: true
    config: {}
```

```yaml
# towns/example.yaml
id: example
display_name: "Example Town"
country: DE
timezone: Europe/Berlin
bbox:
  lon_min: 0.0
  lat_min: 0.0
  lon_max: 1.0
  lat_max: 1.0

connectors: []
```

### Pattern 4: BaseConnector Abstract Class

**What:** All connectors inherit from `BaseConnector`. The constructor receives a `ConnectorConfig` and a `Town`. Subclasses must implement `fetch()` and `normalize()`. `persist()` is provided in the base class.

```python
# app/connectors/base.py
from abc import ABC, abstractmethod
from typing import Any
from app.config import Town, ConnectorConfig


class Observation:
    """Internal normalized observation. Matches DB schema."""
    def __init__(self, feature_id: str, domain: str, values: dict, timestamp=None):
        self.feature_id = feature_id
        self.domain = domain
        self.values = values
        self.timestamp = timestamp


class BaseConnector(ABC):
    def __init__(self, config: ConnectorConfig, town: Town) -> None:
        self.config = config
        self.town = town

    @abstractmethod
    async def fetch(self) -> Any:
        """Fetch raw data from external source. Return raw payload."""
        ...

    @abstractmethod
    def normalize(self, raw: Any) -> list[Observation]:
        """Transform raw data into list of Observations."""
        ...

    async def run(self) -> None:
        """Full pipeline: fetch -> normalize -> persist."""
        raw = await self.fetch()
        observations = self.normalize(raw)
        await self.persist(observations)

    async def persist(self, observations: list[Observation]) -> None:
        """Write observations to DB. Implemented in base; subclasses should not override."""
        # Phase 1: stub implementation (no-op or log)
        # Real implementation wires to SQLAlchemy session in later phases
        pass
```

```python
# app/connectors/stub.py
from app.connectors.base import BaseConnector, Observation
from app.config import ConnectorConfig, Town


class StubConnector(BaseConnector):
    """No-op connector for testing the base class contract."""

    async def fetch(self) -> dict:
        return {"status": "ok", "town": self.town.id}

    def normalize(self, raw: dict) -> list[Observation]:
        return []  # No observations from stub
```

### Pattern 5: BKG VG250 Administrative Boundary Import

**What:** One-shot import script. Downloads VG250 GeoPackage from BKG, filters to Aalen (AGS=08136088), reprojects to WGS84 (EPSG:4326), inserts into the `features` table as domain=`administrative`.

**VG250 key facts (verified):**
- Source: `https://daten.gdz.bkg.bund.de/produkte/vg/vg250_ebenen_0101/aktuell/vg250_01-01.gk3.shape.ebenen.zip`
- Also available as GeoPackage (UTM32s): preferred for Python (fewer encoding issues)
- Municipality layer name: `VG250_GEM` (Gemeinden)
- Key attribute: `AGS` (8-digit Amtlicher Gemeindeschlüssel)
- Aalen AGS: **`08136088`** (08=BW, 1=Stuttgart region, 36=Ostalbkreis, 088=Aalen)
- Default CRS: GK3 (EPSG:31467) for shapefile version; UTM32s (EPSG:25832) for GeoPackage
- Geometry type: MultiPolygon
- `GEN` column: geographic name (e.g., "Aalen")

**CRITICAL:** `geopandas.to_postgis()` does NOT support async SQLAlchemy engines. Use `create_engine()` (sync), not `create_async_engine()`.

```python
# scripts/load_vg250.py
"""One-shot BKG VG250 boundary import for a town."""

import os
import sys
import zipfile
from pathlib import Path
import httpx
import geopandas as gpd
from sqlalchemy import create_engine, text

VG250_GPKG_URL = (
    "https://daten.gdz.bkg.bund.de/produkte/vg/vg250_ebenen_0101/aktuell/"
    "vg250_01-01.utm32s.gpkg.ebenen.zip"
)

def load_town_boundary(town_id: str, ags: str, db_url: str) -> None:
    """Download VG250, filter to AGS, insert into features table."""
    # 1. Download
    tmp = Path("/tmp/vg250")
    tmp.mkdir(exist_ok=True)
    zip_path = tmp / "vg250.zip"
    gpkg_path = tmp / "vg250.gpkg"

    if not zip_path.exists():
        print("Downloading VG250 GeoPackage...")
        with httpx.Client() as client:
            r = client.get(VG250_GPKG_URL, follow_redirects=True, timeout=120)
            r.raise_for_status()
            zip_path.write_bytes(r.content)

    if not gpkg_path.exists():
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                if name.endswith(".gpkg"):
                    with open(gpkg_path, "wb") as f:
                        f.write(zf.read(name))
                    break

    # 2. Load and filter
    print(f"Loading VG250_GEM layer, filtering AGS={ags}...")
    gdf = gpd.read_file(gpkg_path, layer="VG250_GEM")
    town_gdf = gdf[gdf["AGS"] == ags].copy()

    if town_gdf.empty:
        raise ValueError(f"No municipality found for AGS={ags}")

    # 3. Reproject to WGS84 (EPSG:4326)
    town_gdf = town_gdf.to_crs(epsg=4326)

    # 4. Prepare for features table
    town_gdf["id"] = [str(__import__("uuid").uuid4()) for _ in range(len(town_gdf))]
    town_gdf["town_id"] = town_id
    town_gdf["domain"] = "administrative"
    town_gdf["source_id"] = "bkg_vg250"
    town_gdf["properties"] = town_gdf.apply(
        lambda r: {"gen": r["GEN"], "ags": r["AGS"]}, axis=1
    )

    insert_gdf = town_gdf[["id", "town_id", "domain", "source_id", "geometry", "properties"]]

    # 5. Write to PostGIS (SYNC engine — to_postgis() does not support async)
    sync_url = db_url.replace("+asyncpg", "")
    engine = create_engine(sync_url)
    insert_gdf.to_postgis(
        name="features",
        con=engine,
        if_exists="append",
        index=False,
        dtype={"properties": __import__("sqlalchemy.dialects.postgresql", fromlist=["JSONB"]).JSONB},
    )
    print(f"Loaded {len(insert_gdf)} boundary features for town_id={town_id}")


if __name__ == "__main__":
    db_url = os.environ.get("DATABASE_URL", "postgresql://citydata:citydata@localhost:5432/citydata")
    load_town_boundary(
        town_id=sys.argv[1] if len(sys.argv) > 1 else "aalen",
        ags=sys.argv[2] if len(sys.argv) > 2 else "08136088",
        db_url=db_url,
    )
```

### Anti-Patterns to Avoid

- **Hardcoded Aalen constants in Python code:** All town references must come from `Town.id`, not from `if town == "aalen":` branches.
- **One fat measurements table with JSONB values:** Each domain gets its own typed hypertable. `JSONB value` columns resist indexing.
- **Using `timescale/timescaledb-postgis` image:** It is deprecated. Use `timescale/timescaledb-ha:pg17` instead.
- **Alembic autogenerate after hypertable creation:** TimescaleDB creates internal indexes that confuse autogenerate. Always add `include_object` filter.
- **`create_async_engine()` passed to `geopandas.to_postgis()`:** This raises `ValueError: Unknown Connectable`. Use sync engine for the VG250 import script.
- **Enabling extensions inside application code:** Enable `postgis` and `timescaledb` in the migration (`op.execute("CREATE EXTENSION IF NOT EXISTS postgis")`), not in app startup.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Database migrations | Custom SQL runner scripts | Alembic | Rollback support, version history, team-safe |
| YAML validation | Manual dict key checks | Pydantic BaseModel | Automatic type coercion, field-level error messages, IDE support |
| Shapefile loading | Raw psycopg2 + WKB encoding | geopandas + to_postgis() | Handles CRS reprojection, geometry serialization, batch inserts |
| PostgreSQL connection pooling | Manual psycopg2 pool | SQLAlchemy + asyncpg | Async-safe, reconnect logic, connection health checks |
| CRS reprojection | Manual coordinate math | geopandas.to_crs() (uses pyproj) | Edge cases in datum shifts, antimeridian crossing |

**Key insight:** The geo tooling (geopandas/pyproj/shapely) wraps GDAL and handles coordinate system edge cases that are extremely painful to reimplement. Always install the full geo stack in the data loader environment, even if it's a one-off script.

---

## Common Pitfalls

### Pitfall 1: timescaledb-ha image tag confusion

**What goes wrong:** Developer uses `timescale/timescaledb-ha:latest` which may pull an unexpected version, or uses the deprecated `timescale/timescaledb-postgis` image which is no longer maintained.

**Why it happens:** Multiple images exist; the official docs sometimes still reference the old image name.

**How to avoid:** Pin the tag explicitly: `timescale/timescaledb-ha:pg17`. This maps to PostgreSQL 17 with TimescaleDB bundled.

**Warning signs:** `docker pull` succeeds but `CREATE EXTENSION timescaledb` fails — wrong image.

### Pitfall 2: Alembic autogenerate drops TimescaleDB indexes

**What goes wrong:** Running `alembic revision --autogenerate` after the initial migration generates a new revision that drops `_hyper_*` indexes managed by TimescaleDB internally.

**Why it happens:** Alembic reflects the database schema and sees indexes it didn't create, so it generates DROP INDEX statements.

**How to avoid:** Add an `include_object` filter to `alembic/env.py` that returns `False` for any index whose name starts with `_hyper_`.

**Warning signs:** Autogenerated migration contains `op.drop_index("_hyper_1_1_chunk_time_idx", ...)`.

### Pitfall 3: PostGIS extension not enabled before geometry column creation

**What goes wrong:** `op.create_table()` with a `ga.Geometry` column fails with `type "geometry" does not exist`.

**Why it happens:** PostGIS extension creates the `geometry` type; if the extension isn't enabled before the table is created, the type is unknown.

**How to avoid:** Always run `op.execute("CREATE EXTENSION IF NOT EXISTS postgis")` before any table with geometry columns in the migration's `upgrade()`.

**Warning signs:** `ProgrammingError: type "geometry" does not exist` during migration.

### Pitfall 4: geopandas not available in the backend container

**What goes wrong:** The VG250 import script fails inside Docker because geopandas/GDAL aren't in the backend's Python environment.

**Why it happens:** geopandas requires GDAL, which has native binary dependencies. If not installed during Docker build, it fails at import time.

**How to avoid:** Either (a) add geopandas to the backend's uv dependencies and ensure the Dockerfile installs GDAL system packages (`apt-get install libgdal-dev`), or (b) run the VG250 import script locally (outside Docker) pointing at the exposed database port.

**Warning signs:** `ModuleNotFoundError: No module named 'fiona'` or `ImportError: libgdal.so.x not found`.

### Pitfall 5: AGS field is a string, not integer

**What goes wrong:** Filtering VG250 by `gdf["AGS"] == 8136088` (integer) returns zero rows.

**Why it happens:** The AGS column in VG250 is a zero-padded 8-character string. Leading zero matters: `"08136088"`, not `8136088`.

**How to avoid:** Always quote the AGS value: `gdf["AGS"] == "08136088"`.

**Warning signs:** Filter returns empty GeoDataFrame even though the town exists.

### Pitfall 6: VG250 CRS mismatch with PostGIS EPSG:4326

**What goes wrong:** Boundaries load but are visually offset or invisible on the map because the geometry is in GK3 (EPSG:31467) or UTM32s (EPSG:25832) instead of WGS84 (EPSG:4326).

**Why it happens:** VG250 is distributed in German national CRS; PostGIS and MapLibre both expect WGS84 for standard map display.

**How to avoid:** Always call `gdf.to_crs(epsg=4326)` before `to_postgis()`. Verify with `gdf.crs` before and after.

**Warning signs:** Boundaries appear in the North Atlantic or completely off-screen.

---

## Code Examples

### Start DB and run migration

```bash
# Start database only
docker compose up db -d

# Run Alembic migration
cd backend
DATABASE_URL="postgresql://citydata:citydata@localhost:5432/citydata" \
  alembic upgrade head

# Verify hypertables created
psql postgresql://citydata:citydata@localhost:5432/citydata \
  -c "SELECT hypertable_name FROM timescaledb_information.hypertables;"
```

### Verify PostGIS and TimescaleDB extensions

```sql
SELECT name, default_version, installed_version
FROM pg_available_extensions
WHERE name IN ('postgis', 'timescaledb');
-- Both should show installed_version = non-null
```

### Load town config in FastAPI lifespan

```python
# app/main.py
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from app.config import load_town

@asynccontextmanager
async def lifespan(app: FastAPI):
    town_id = os.environ.get("TOWN", "aalen")
    app.state.town = load_town(town_id, Path("/app/towns"))
    yield

app = FastAPI(lifespan=lifespan)
```

### Test stub connector

```python
# tests/test_connector.py
import pytest
from app.connectors.stub import StubConnector
from app.config import ConnectorConfig, Town, TownBbox

@pytest.fixture
def town():
    return Town(
        id="test",
        display_name="Test Town",
        bbox=TownBbox(lon_min=9.0, lat_min=48.0, lon_max=10.0, lat_max=49.0),
    )

@pytest.fixture
def config():
    return ConnectorConfig(connector_class="StubConnector")

@pytest.mark.asyncio
async def test_stub_connector_run(town, config):
    connector = StubConnector(config=config, town=town)
    raw = await connector.fetch()
    assert raw["town"] == "test"
    observations = connector.normalize(raw)
    assert isinstance(observations, list)

def test_stub_connector_is_subclass_of_base():
    from app.connectors.base import BaseConnector
    assert issubclass(StubConnector, BaseConnector)
```

---

## Runtime State Inventory

Step 2.5: SKIPPED — This is a greenfield phase with no existing runtime state. Empty git repository; no databases, services, or OS registrations exist yet.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Docker | All containers | Yes | 29.3.1 | — |
| Docker Compose | Service orchestration | Yes | v5.1.1 | — |
| Python 3.11 | Backend runtime | Yes | 3.11.5 | — |
| uv | Python package manager | Yes | 0.9.30 | pip (slower) |
| pytest | Test runner | Yes | 9.0.2 | — |
| psycopg2 | Sync DB driver (migration context) | Yes | in system Python | — |
| Node.js | Frontend (Phase 4) | Yes | v22.22.1 | — |
| pnpm | JS package manager | No | — | npm (available: 10.9.4) |
| curl | HTTP downloads | Yes | 8.2.1 | httpx in Python |
| ogr2ogr / GDAL CLI | Shapefile conversion | No | — | geopandas (Python) |
| geopandas | VG250 shapefile loading | No (not in system Python) | — | Install via uv |
| psql CLI | DB inspection | No | — | Docker exec into db container |
| PostgreSQL server | Database | No (Docker only) | — | Run via docker compose up db |

**Missing dependencies with no fallback:**
- None that block execution — all gaps have workable alternatives.

**Missing dependencies with fallback:**
- `pnpm`: Use npm (available) for Phase 4 frontend work, or install pnpm via `npm install -g pnpm`
- `ogr2ogr/GDAL CLI`: Use geopandas Python library (same underlying GDAL, cleaner Python API)
- `geopandas`: Not in system Python 3.11, but will be installed via `uv add geopandas` in the backend environment
- `psql CLI`: Use `docker compose exec db psql -U citydata citydata` for interactive queries

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio |
| Config file | `backend/pyproject.toml` ([tool.pytest.ini_options]) — Wave 0 gap |
| Quick run command | `cd backend && uv run pytest tests/ -x -q` |
| Full suite command | `cd backend && uv run pytest tests/ -v` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PLAT-01 | `load_town("aalen")` returns valid Town object | unit | `uv run pytest tests/test_config.py -x` | Wave 0 |
| PLAT-01 | `load_town("example")` returns valid Town object without code changes | unit | `uv run pytest tests/test_config.py -x` | Wave 0 |
| PLAT-01 | Invalid YAML raises ValidationError with clear message | unit | `uv run pytest tests/test_config.py::test_invalid_config -x` | Wave 0 |
| PLAT-02 | `docker compose up` starts with no errors | smoke | `docker compose up -d && docker compose ps` | manual |
| PLAT-06 | StubConnector is subclass of BaseConnector | unit | `uv run pytest tests/test_connector.py::test_stub_connector_is_subclass_of_base -x` | Wave 0 |
| PLAT-06 | StubConnector.run() completes without exception | unit (async) | `uv run pytest tests/test_connector.py::test_stub_connector_run -x` | Wave 0 |
| PLAT-07 | Alembic migration creates hypertables | integration | `alembic upgrade head && psql -c "SELECT hypertable_name FROM timescaledb_information.hypertables;"` | manual |
| PLAT-07 | Retention policies applied to hypertables | integration | `psql -c "SELECT * FROM timescaledb_information.jobs WHERE proc_name='policy_retention';"` | manual |
| PLAT-08 | `features` table has PostGIS geometry column | integration | `psql -c "SELECT type FROM geometry_columns WHERE f_table_name='features';"` | manual |
| GEO-06 | Aalen boundary rows exist in `features` table after script | integration | `psql -c "SELECT COUNT(*) FROM features WHERE town_id='aalen' AND domain='administrative';"` | manual |

### Sampling Rate

- **Per task commit:** `cd backend && uv run pytest tests/ -x -q`
- **Per wave merge:** `cd backend && uv run pytest tests/ -v`
- **Phase gate:** Full suite green + manual integration checks before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/conftest.py` — shared fixtures (Town, ConnectorConfig)
- [ ] `backend/tests/test_config.py` — covers PLAT-01 (load_town, validation)
- [ ] `backend/tests/test_connector.py` — covers PLAT-06 (BaseConnector, StubConnector)
- [ ] `backend/pyproject.toml` — pytest config section (`[tool.pytest.ini_options]` with `asyncio_mode = "auto"`)
- [ ] Framework install: `cd backend && uv add --dev pytest pytest-asyncio`

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `timescale/timescaledb-postgis` Docker image | `timescale/timescaledb-ha:pg17` | ~2023 | Must use ha image; old one unmaintained |
| Pydantic v1 (`class Config:` inner class) | Pydantic v2 (`model_config = ConfigDict(...)`) | 2023 | FastAPI 0.100+ requires Pydantic v2 |
| SQLAlchemy 1.x (`Session`) | SQLAlchemy 2.x (`async_sessionmaker`) | 2023 | Async session API changed; 2.x required |
| `geopandas.to_postgis()` with raw psycopg2 connection | `geopandas.to_postgis()` with SQLAlchemy `create_engine()` | 2021+ | Raw connections deprecated; must pass engine |

**Deprecated/outdated:**
- `timescale/timescaledb-postgis`: No longer maintained; PostGIS support moved to `timescaledb-ha`
- Pydantic v1 `BaseSettings` with `class Config`: Use `model_config = SettingsConfigDict(...)` in v2
- `alembic autogenerate` with TimescaleDB: Still works for regular tables; must filter internal objects

---

## Open Questions

1. **Which specific timescaledb-ha tag to pin**
   - What we know: `pg17` tag exists and maps to PostgreSQL 17 with TimescaleDB
   - What's unclear: Exact TimescaleDB version bundled in `pg17` tag (STACK.md says 2.23 — verify at implementation time)
   - Recommendation: At Docker pull time, run `docker exec db psql -U citydata -c "SELECT extversion FROM pg_extension WHERE extname='timescaledb';"` to confirm

2. **VG250 GeoPackage layer name**
   - What we know: VG250 Shapefile contains `VG250_GEM` layer for municipalities; GeoPackage should have same layer names
   - What's unclear: Whether GeoPackage layer is named `VG250_GEM` or uses a different naming convention
   - Recommendation: After download, list layers with `geopandas.io.file.fiona.listlayers("vg250.gpkg")` and adjust if needed

3. **uv run inside Docker vs direct uvicorn invocation**
   - What we know: uv is available on the dev machine
   - What's unclear: Whether the Dockerfile should use `uv run` or install to a venv and call uvicorn directly
   - Recommendation: Use `uv sync --frozen && uv run uvicorn ...` pattern in Dockerfile for reproducibility

---

## Sources

### Primary (HIGH confidence)
- TimescaleDB create_hypertable API (docs.tigerdata.com mirrors timescale docs) — create_hypertable syntax, add_retention_policy
- Docker Hub timescale/timescaledb-ha — confirmed PostGIS included, timescaledb-postgis deprecated
- Pydantic v2 official docs (docs.pydantic.dev) — BaseModel, model_validate, field_validator
- Pydantic Settings docs — YamlConfigSettingsSource confirmed available
- BKG GDZ portal (gdz.bkg.bund.de) — VG250 download links, formats (Shapefile + GeoPackage), CRS options
- Statistik BW / Statistikportal.de — Aalen AGS confirmed as `08136088`
- geopandas docs — to_postgis() async limitation confirmed (GitHub issue #2160)
- Alembic GitHub discussions — TimescaleDB index autogenerate conflict confirmed (#1465)

### Secondary (MEDIUM confidence)
- WebSearch: timescaledb-ha includes PostGIS — multiple sources confirm, no official doc URL retrieved
- WebSearch: VG250_GEM layer name for municipalities — confirmed via ArcGIS Hub layer listing
- BKG VG250 English documentation PDF (binary, unreadable) — layer names inferred from search results

### Tertiary (LOW confidence)
- VG250 GeoPackage specific layer names — assumed same as shapefile naming convention; needs verification at download time
- Exact timescaledb-ha:pg17 TimescaleDB version — assumed ~2.23 per STACK.md; verify at implementation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tools verified available in environment; Docker images confirmed
- Architecture: HIGH — patterns follow verified ARCHITECTURE.md and STACK.md decisions
- TimescaleDB DDL: HIGH — syntax verified via official API docs and search
- VG250 import: MEDIUM — AGS for Aalen confirmed; GeoPackage layer names inferred (verify at download)
- Alembic/TimescaleDB integration: MEDIUM — known issue and fix documented via GitHub discussions

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (stable ecosystem; Docker image tags change slowly)
