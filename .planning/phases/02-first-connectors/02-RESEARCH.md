# Phase 2: First Connectors - Research

**Researched:** 2026-04-05
**Domain:** Python data connectors — GTFS/GTFS-RT transit, UBA air quality, Sensor.community, Bright Sky weather
**Confidence:** HIGH (APIs verified live; library versions confirmed from PyPI)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
All implementation choices are at Claude's discretion — infrastructure/data ingestion phase. Use ROADMAP phase goal, success criteria, and codebase conventions.

Key constraints from Phase 1:
- BaseConnector pattern defined in backend/app/connectors/base.py
- Town config via towns/aalen.yaml with ConnectorConfig entries
- TimescaleDB hypertables: air_quality_readings, transit_positions, water_readings, energy_readings
- PostGIS features table for spatial data (stops, routes)
- APScheduler for periodic polling (from stack research)
- Pydantic 2.x for data validation
- httpx for async HTTP
- Frontend runs on port 4000 (not 3000)

Data sources (from user research):
- NVBW GTFS: bwgesamt feed — 3,688 routes, 55,284 stops, DL-DE-BY-2.0 license
- GTFS-RT: realtime.gtfs.de — CC BY-SA 4.0
- UBA air quality API: luftqualitaet.api.bund.dev — no API key needed, station in Aalen
- Sensor.community: JSON API, ~2.5 min updates
- Bright Sky: brightsky.dev — DWD data via clean JSON API, no API key, query by coordinates (48.84°N, 10.09°E)

### Claude's Discretion
All implementation choices are Claude's discretion within the constraints above.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TRAF-01 | Public transport routes and stops on map (NVBW GTFS — 3,688 routes, 55,284 stops) | GTFSConnector: gtfs-kit parses stops/routes/shapes from bwgesamt.zip; writes Point geometries (stops) and LineString geometries (shapes) to features table |
| TRAF-02 | Real-time transit positions/delays where available (GTFS-RT via gtfs.de) | GTFSRealtimeConnector: gtfs-realtime-bindings parses binary protobuf; VehiclePosition → transit_positions hypertable; TripUpdate.delay → transit_positions.delay_seconds |
| WAIR-01 | Current weather conditions for configured town (DWD via Bright Sky — no API key) | WeatherConnector: GET /current_weather?lat=48.84&lon=10.09; all weather fields verified against live API |
| WAIR-02 | Weather forecast overlay (MOSMIX point forecasts from DWD) | WeatherConnector: GET /weather?lat=48.84&lon=10.09&date=TODAY&last_date=TODAY+2d; forecast entries have source.observation_type="forecast" (MOSMIX) |
| WAIR-03 | Air quality readings from UBA station in Aalen (PM10, PM2.5, NO₂, O₃) | UBAConnector: station ID 238 (DEBW029), at Bahnhofstraße 115 Aalen; GET /airquality/json?station=238; writes to air_quality_readings hypertable |
| WAIR-04 | Citizen-science air quality sensors (Sensor.community — multiple sensors in Ostalbkreis) | SensorCommunityConnector: GET /airrohr/v1/filter/?area=48.84,10.09,25; filters SDS011/SPS30 sensors for PM10/PM2.5 within 25km; writes to air_quality_readings hypertable |
</phase_requirements>

---

## Summary

Phase 2 implements four concrete connectors that follow the BaseConnector abstract class established in Phase 1. The primary challenge is wiring the `persist()` no-op into real database writes using the existing `AsyncSessionLocal` from `db.py`, then building each connector's domain-specific fetch/normalize logic.

The data sources are all public, require no API keys, and return JSON (Bright Sky, UBA, Sensor.community) or binary protobuf (GTFS-RT) or zip file (GTFS Static). The UBA Aalen station has been confirmed: numeric ID **238**, code **DEBW029**, at Bahnhofstraße 115 Aalen. Bright Sky serves MOSMIX forecasts via the same `/weather` endpoint — forecast entries are identified by `source.observation_type = "forecast"`.

The three new packages required are: `gtfs-kit==12.0.3` (GTFS static parsing), `gtfs-realtime-bindings==2.0.0` (protobuf parsing), and `apscheduler==3.11.2` (scheduler). None are currently in `pyproject.toml`. The `persist()` method on BaseConnector needs to be implemented in Phase 2 as decided in Phase 1 (it is currently a no-op).

**Primary recommendation:** Wire persist() with AsyncSessionLocal first (shared infrastructure), then implement connectors in this order: UBAConnector (simplest JSON REST), WeatherConnector (Bright Sky current + forecast), SensorCommunityConnector (area filter + sensor dedup), GTFSConnector (static zip + large dataset), GTFSRealtimeConnector (protobuf + requires GTFS-RT feed URL).

---

## Standard Stack

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.28.1 (installed) | Async HTTP client | All REST API calls; async-native |
| pydantic | 2.12.5 (installed) | Data validation models | Validates every external API response |
| sqlalchemy | 2.0.49 (installed) | Async DB writes | Already wired in db.py |
| asyncpg | 0.31.0 (installed) | PostgreSQL async driver | Required by SQLAlchemy async |
| geoalchemy2 | 0.18.4 (installed) | PostGIS geometry types | features table geometry column |

### New dependencies required
| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| gtfs-kit | 12.0.3 | GTFS static feed parsing | Standard Python GTFS library; pandas DataFrames for stops/routes/shapes |
| gtfs-realtime-bindings | 2.0.0 | GTFS-RT protobuf parsing | Official MobilityData library; parses VehiclePosition, TripUpdate |
| apscheduler | 3.11.2 | Periodic connector polling | Embedded in FastAPI via AsyncIOScheduler; no broker dependency |

**Installation:**
```bash
cd backend
uv add gtfs-kit==12.0.3 gtfs-realtime-bindings==2.0.0 apscheduler==3.11.2
```

**Version verification (confirmed 2026-04-05):**
- gtfs-kit: 12.0.3 (latest on PyPI)
- gtfs-realtime-bindings: 2.0.0 (latest on PyPI)
- apscheduler: 3.11.2 (latest stable 3.x on PyPI)

---

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── connectors/
│   ├── base.py          # BaseConnector (Phase 1, complete)
│   ├── stub.py          # StubConnector (Phase 1, complete)
│   ├── gtfs.py          # GTFSConnector (TRAF-01)
│   ├── gtfs_rt.py       # GTFSRealtimeConnector (TRAF-02)
│   ├── uba.py           # UBAConnector (WAIR-03)
│   ├── sensor_community.py  # SensorCommunityConnector (WAIR-04)
│   └── weather.py       # WeatherConnector (WAIR-01, WAIR-02)
├── models/              # NEW: Pydantic validation models for external APIs
│   ├── uba.py
│   ├── sensor_community.py
│   ├── weather.py
│   └── gtfs_rt.py
├── scheduler.py         # NEW: APScheduler integration
├── config.py            # (Phase 1, complete)
├── db.py                # (Phase 1, complete)
└── main.py              # (Phase 1, update lifespan to start scheduler)
tests/
└── connectors/          # NEW: integration tests per connector
    ├── conftest.py
    ├── test_uba.py
    ├── test_sensor_community.py
    ├── test_weather.py
    ├── test_gtfs.py
    └── test_gtfs_rt.py
```

### Pattern 1: persist() implementation via SQLAlchemy insert

**What:** BaseConnector.persist() needs to be upgraded from no-op to real DB writes. Use SQLAlchemy core INSERT (not ORM) for performance on hypertables. Session is injected into the connector at construction time in Phase 2.

**When to use:** All connectors call `await self.persist(observations)` — persist() handles routing to the correct hypertable based on `observation.domain`.

**Key decision:** Inject `AsyncSession` at connector construction time (stored as `self.session`), not passed per-call. The scheduler creates connectors fresh per run, so session lifetime matches job lifetime.

```python
# Revised BaseConnector constructor signature (Phase 2 update)
class BaseConnector(ABC):
    def __init__(self, config: ConnectorConfig, town: Town, session: AsyncSession) -> None:
        self.config = config
        self.town = town
        self.session = session  # injected in Phase 2

    async def persist(self, observations: list[Observation]) -> None:
        # Route to correct hypertable by domain
        for obs in observations:
            if obs.domain == "air_quality":
                await self._insert_air_quality(obs)
            elif obs.domain == "transit":
                await self._insert_transit(obs)
        await self.session.commit()
```

### Pattern 2: APScheduler integration in FastAPI lifespan

**What:** `AsyncIOScheduler` from APScheduler 3.x runs within the same asyncio event loop as FastAPI. Register connector jobs in the lifespan startup.

**When to use:** All connectors are scheduled via APScheduler — no separate worker process.

```python
# backend/app/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

scheduler = AsyncIOScheduler()

def setup_scheduler(town: Town) -> None:
    for connector_cfg in town.connectors:
        if not connector_cfg.enabled:
            continue
        # resolve connector class by name
        connector_class = _resolve_connector(connector_cfg.connector_class)
        trigger = IntervalTrigger(seconds=connector_cfg.poll_interval_seconds)
        scheduler.add_job(
            _run_connector,
            trigger=trigger,
            args=[connector_class, connector_cfg, town],
            max_instances=1,  # prevent overlap
            coalesce=True,
        )

# In main.py lifespan:
# scheduler.start()
# yield
# scheduler.shutdown()
```

### Pattern 3: Pydantic validation models for external APIs

**What:** Every external API response is parsed through a Pydantic model before values are written to DB. Use `model_validate()` on the parsed JSON dict. Mark nullable fields with `float | None`.

**When to use:** UBA, Sensor.community, Bright Sky all return JSON; validate before touching DB.

```python
# backend/app/models/uba.py
from pydantic import BaseModel, field_validator
from datetime import datetime

class UBAMeasurement(BaseModel):
    station_id: int
    component_id: int
    date_end: datetime
    value: float | None
    index: int | None  # AQI index 1-6

    @field_validator("value", mode="before")
    @classmethod
    def reject_negative(cls, v):
        if v is not None and v < 0:
            return None
        return v
```

### Pattern 4: HTTP 200 with empty payload treated as failure

Per CONTEXT.md requirement, all connectors must raise `ValueError` when fetch() returns HTTP 200 but an empty body. This prevents silent data gaps from being recorded as successful fetches.

```python
async def fetch(self) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.get(self.url, headers=self.headers)
        r.raise_for_status()
        data = r.json()
        if not data:  # empty dict or empty list
            raise ValueError(f"Empty payload from {self.url} (HTTP 200 with no data)")
        return data
```

### Pattern 5: features table upsert for spatial data

GTFS stops and route shapes must be written to the `features` table. Use PostgreSQL `INSERT ... ON CONFLICT (source_id, town_id, domain) DO UPDATE` to avoid duplicates on re-download.

The `features` table uses `source_id` (string, e.g., GTFS stop_id) to allow idempotent upserts. Add a unique constraint on `(town_id, domain, source_id)` via an Alembic migration in Wave 0.

### Pattern 6: staleness tracking (last_successful_fetch)

The `sources` table already has `enabled` but not `last_successful_fetch`. A migration must add this column plus `validation_error_count` as Phase 2 Wave 0 schema work.

```sql
-- Alembic migration 002
ALTER TABLE sources
  ADD COLUMN last_successful_fetch TIMESTAMPTZ,
  ADD COLUMN validation_error_count INTEGER DEFAULT 0;
```

### Anti-Patterns to Avoid

- **Starting scheduler before DB is ready:** Connectors that write to DB must only start after the DB engine/migrations are verified. Use lifespan ordering: validate DB connection → start scheduler.
- **One httpx.AsyncClient per request:** Create a single shared `httpx.AsyncClient` per connector instance (or use `httpx.AsyncClient` as an async context manager per job run), not per HTTP call.
- **Storing GTFS stop geometries as raw lat/lon floats:** Use `geoalchemy2.elements.WKTElement("POINT(lon lat)", srid=4326)` for the features table geometry column.
- **Parsing GTFS-RT synchronously:** `gtfs_realtime_pb2.FeedMessage.ParseFromString()` is synchronous (CPU-bound); call it directly without `await` — it is fast enough for typical feed sizes.
- **Assuming UBA returns PM2.5 for Aalen:** The UBA API returns all available components per station; not every station measures all pollutants. Station 238 (Aalen) coverage must be confirmed at fetch time by checking which component IDs are present in the response.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GTFS zip parsing | Custom CSV parser | gtfs-kit 12.x | Handles feed validation, timezone, calendar.txt join, shape geometry generation |
| GTFS-RT protobuf decode | Manual protobuf parser | gtfs-realtime-bindings 2.0.0 | Official MobilityData bindings; handles proto schema versioning |
| Cron-style scheduling | asyncio.sleep loop | APScheduler 3.x AsyncIOScheduler | Handles missed runs, coalescing, max_instances, error recovery |
| UBA station discovery | Screen scraping | GET /meta/json?use=airquality — Aalen is station 238 | Already confirmed; station code DEBW029 |
| Protobuf binaries | protoc compilation | `pip install gtfs-realtime-bindings` | Pre-compiled bindings from MobilityData |

**Key insight:** The GTFS Static feed (bwgesamt.zip) is 55,284 stops across 3,688 routes. Do not load the entire feed into memory as raw dicts. Use gtfs-kit's DataFrame API which loads lazily and allows bbox filtering before writing to DB.

---

## Data Source Reference

### GTFS Static (TRAF-01)
- **URL:** `https://www.nvbw.de/fileadmin/user_upload/service/open_data/fahrplandaten_mit_liniennetz/bwgesamt.zip`
- **Update frequency:** Weekly (Wednesdays–Fridays)
- **License:** DL-DE-BY-2.0 (attribution required)
- **Poll interval recommendation:** Daily (86400s) — no need to poll more often than weekly updates
- **Key tables:** `stops.txt` (stop_id, stop_name, stop_lat, stop_lon), `routes.txt` (route_id, route_short_name, route_type), `shapes.txt` (shape_id, shape_pt_lat, shape_pt_lon, shape_pt_sequence)
- **Aalen bbox filter:** lon 9.97–10.22, lat 48.76–48.90 (from aalen.yaml) — filter stops by lat/lon before writing to DB to avoid loading all 55,284 stops

```python
import gtfs_kit
feed = gtfs_kit.read_feed(zip_url_or_path, dist_units="km")
# feed.stops is a pandas DataFrame
aalen_stops = feed.stops[
    (feed.stops.stop_lat.between(48.76, 48.90)) &
    (feed.stops.stop_lon.between(9.97, 10.22))
]
```

### GTFS-RT (TRAF-02)
- **Feed URL:** Needs verification at implementation time via gtfs.de or NVBW open data portal. The CONTEXT.md references `realtime.gtfs.de` but the specific feed path for bwgesamt/NVBW must be confirmed.
- **Format:** Binary protobuf (application/x-protobuf)
- **Update frequency:** ~30 seconds typical for GTFS-RT
- **Poll interval recommendation:** 30s (`poll_interval_seconds: 30`)
- **Parser:** `gtfs_realtime_bindings` (pip package `gtfs-realtime-bindings`)

```python
from google.transit import gtfs_realtime_pb2

feed_msg = gtfs_realtime_pb2.FeedMessage()
response = await client.get(gtfs_rt_url, headers={"Accept": "application/x-protobuf"})
feed_msg.ParseFromString(response.content)  # synchronous, fast
for entity in feed_msg.entity:
    if entity.HasField("vehicle"):
        lat = entity.vehicle.position.latitude
        lon = entity.vehicle.position.longitude
        trip_id = entity.vehicle.trip.trip_id
    if entity.HasField("trip_update"):
        delay = entity.trip_update.delay  # seconds
        trip_id = entity.trip_update.trip.trip_id
```

### UBA Air Quality (WAIR-03)
- **Base URL:** `https://luftdaten.umweltbundesamt.de/api-proxy/` (v2 proxy) or `https://www.umweltbundesamt.de/api/air_data/v2/`
- **Aalen station:** ID **238**, code **DEBW029**, address Bahnhofstraße 115 Aalen (HIGH confidence — confirmed from live API)
- **Endpoint:** `GET /airquality/json?station=238&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&time_from=1&time_to=24&lang=de`
- **Pollutants available:** PM10, NO2, O3, SO2, CO; PM2.5 availability at station 238 must be confirmed at runtime
- **Update frequency:** Hourly measurements
- **Poll interval recommendation:** 3600s (1 hour)
- **No API key required**

### Sensor.community (WAIR-04)
- **Endpoint:** `GET https://data.sensor.community/airrohr/v1/filter/?area=48.84,10.09,25`
  - `area` = `{lat},{lon},{radius_km}` — 25km covers Aalen urban area and Ostalbkreis
- **Update frequency:** ~5 minutes
- **Poll interval recommendation:** 300s (5 minutes)
- **Required header:** `User-Agent: city-data-platform/0.1 (contact@example.com)` — explicitly required by API terms
- **Response:** JSON array of sensor measurements; each element has `sensor.sensor_type.name` (e.g., "SDS011", "SPS30"), `sensordatavalues` array with `value_type` and `value`
- **Relevant value_types:** `P1` = PM10 (µg/m³), `P2` = PM2.5 (µg/m³)
- **Deduplication:** Multiple sensors per location; store `sensor.id` as `source_id` in features table to uniquely identify each sensor

### Bright Sky / DWD Weather (WAIR-01, WAIR-02)
- **Base URL:** `https://api.brightsky.dev`
- **Current weather:** `GET /current_weather?lat=48.84&lon=10.09&tz=Europe/Berlin`
- **Forecast (includes MOSMIX):** `GET /weather?lat=48.84&lon=10.09&date=YYYY-MM-DD&last_date=YYYY-MM-DD&tz=Europe/Berlin`
  - MOSMIX forecast entries have `source.observation_type = "forecast"`
  - Forecasts cover up to ~240 hours ahead
- **No API key required; no rate limits documented**
- **Poll interval recommendation:** 3600s current weather (1 hour); 21600s forecast (6 hours)
- **Key response fields (current_weather):** `temperature`, `dew_point`, `pressure_msl`, `wind_speed`, `wind_direction`, `condition`, `icon`, `precipitation_*`, `sunshine_*`, `cloud_cover`, `relative_humidity`
- **Note:** The existing schema does not have a dedicated `weather_readings` hypertable. Weather data will be stored in a new hypertable or in the generic pattern using `features` + a new hypertable. **This is a schema gap that requires a Wave 0 migration.**

---

## Common Pitfalls

### Pitfall 1: Missing weather_readings hypertable
**What goes wrong:** The schema (001_initial_schema.py) has hypertables for `air_quality_readings`, `transit_positions`, `water_readings`, `energy_readings` — but NOT `weather_readings`. Weather data cannot be stored without a new migration.
**Why it happens:** Weather was not in the initial schema planning.
**How to avoid:** Wave 0 of Phase 2 must add a migration `002_weather_hypertable.py` before any connector code runs.
**Warning signs:** Import error or SQLAlchemy `ProgrammingError: relation "weather_readings" does not exist` at first connector run.

### Pitfall 2: features table has no unique constraint on source_id
**What goes wrong:** GTFS stops re-downloaded weekly will duplicate rows in `features` table.
**Why it happens:** The initial schema has no UNIQUE constraint on `(town_id, domain, source_id)`.
**How to avoid:** Wave 0 migration must add this unique constraint before GTFSConnector runs. Use `INSERT ... ON CONFLICT DO UPDATE SET geometry=EXCLUDED.geometry, properties=EXCLUDED.properties`.
**Warning signs:** features table row count doubles every weekly GTFS re-download.

### Pitfall 3: GTFS bwgesamt feed loads 55,284 stops into memory
**What goes wrong:** Loading the full bwgesamt feed without bbox filtering writes stops from all of Baden-Württemberg to the database. This is wasteful and pollutes the map layer.
**Why it happens:** gtfs-kit loads all stops from the zip into a DataFrame.
**How to avoid:** After `feed = gtfs_kit.read_feed(...)`, immediately apply bbox filter using Aalen bounds from `self.town.bbox` before iterating over stops/shapes.

### Pitfall 4: GTFS-RT feed URL unconfirmed
**What goes wrong:** The CONTEXT.md references `realtime.gtfs.de` but the exact protobuf endpoint URL for NVBW bwgesamt is not documented in a freely-accessible location.
**Why it happens:** GTFS-RT feeds in Germany often require registration or have per-operator URLs.
**How to avoid:** Store the GTFS-RT URL in `aalen.yaml` connector config (not hardcoded). The connector reads `self.config.config["gtfs_rt_url"]`. If the URL is empty or returns 404, the connector logs a warning and skips. This makes the connector resilient while the URL is being confirmed.

### Pitfall 5: UBA station 238 may not measure PM2.5
**What goes wrong:** Code assumes PM2.5 is available at station 238 and raises KeyError when it is absent from the API response.
**Why it happens:** Not every UBA station measures all pollutants. The API returns only measured components.
**How to avoid:** Use `response_data.get("pm25")` (not `response_data["pm25"]`). The Pydantic model for UBA should have all pollutant fields as `float | None`.

### Pitfall 6: Sensor.community requires User-Agent header
**What goes wrong:** Requests without a User-Agent header may be rate-limited or rejected.
**Why it happens:** API documentation explicitly states: "the user agent string should give us a chance to contact the source of excessive requests."
**How to avoid:** Always set `User-Agent: city-data-platform/0.1 (+https://github.com/your-org/city-data-platform)` in `httpx` default headers for the SensorCommunityConnector.

### Pitfall 7: APScheduler 4.x vs 3.x API break
**What goes wrong:** APScheduler 4.x (currently in development) has a completely different API (`AsyncScheduler`, no `add_job` method). PyPI may resolve to 4.x if version is not pinned.
**Why it happens:** APScheduler 4.x is on PyPI and `uv add apscheduler` may pick it up.
**How to avoid:** Pin to `apscheduler==3.11.2` explicitly. Use `AsyncIOScheduler` from `apscheduler.schedulers.asyncio`.

### Pitfall 8: persist() session lifetime mismatch
**What goes wrong:** If `AsyncSession` is held open across multiple connector runs (across scheduler invocations), connection pool exhaustion occurs.
**Why it happens:** Sessions are not closed between scheduler job runs if shared at class level.
**How to avoid:** Create a fresh `AsyncSession` per connector job run using `async with AsyncSessionLocal() as session:` inside the scheduler's `_run_connector` wrapper, not at connector construction time.

---

## Code Examples

### UBA connector fetch
```python
# Source: live API verification + schnittstellenbeschreibung_luftdaten_api_v4.pdf
import httpx
from datetime import date, timedelta

BASE_URL = "https://luftdaten.umweltbundesamt.de/api-proxy"
AALEN_STATION_ID = 238  # DEBW029, confirmed 2026-04-05

async def fetch(self) -> dict:
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    url = f"{BASE_URL}/airquality/json"
    params = {
        "station": AALEN_STATION_ID,
        "date_from": yesterday,
        "date_to": today,
        "time_from": 1,
        "time_to": 24,
        "lang": "de",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
        if not data:
            raise ValueError(f"Empty payload from UBA API (station {AALEN_STATION_ID})")
        return data
```

### Bright Sky current weather fetch
```python
# Source: live API test GET https://api.brightsky.dev/current_weather?lat=48.84&lon=10.09
async def fetch(self) -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(
            "https://api.brightsky.dev/current_weather",
            params={"lat": 48.84, "lon": 10.09, "tz": "Europe/Berlin"},
        )
        r.raise_for_status()
        data = r.json()
        if not data.get("weather"):
            raise ValueError("Empty weather payload from Bright Sky (HTTP 200 no data)")
        return data
```

### Sensor.community fetch with area filter
```python
# Source: https://github.com/opendata-stuttgart/meta/wiki/EN-APIs
async def fetch(self) -> list:
    bbox = self.town.bbox
    lat = (bbox.lat_min + bbox.lat_max) / 2
    lon = (bbox.lon_min + bbox.lon_max) / 2
    radius_km = 25
    async with httpx.AsyncClient(
        timeout=30.0,
        headers={"User-Agent": "city-data-platform/0.1 (open-source city dashboard)"},
    ) as client:
        r = await client.get(
            "https://data.sensor.community/airrohr/v1/filter/",
            params={"area": f"{lat},{lon},{radius_km}"},
        )
        r.raise_for_status()
        data = r.json()
        if not data:
            raise ValueError("Empty sensor list from Sensor.community")
        return data
```

### GTFS static feed loading with bbox filter
```python
# Source: gtfs_kit docs; https://mrcagney.github.io/gtfs_kit_docs/
import gtfs_kit

def normalize(self, raw: bytes) -> list[Observation]:
    import io
    feed = gtfs_kit.read_feed(io.BytesIO(raw), dist_units="km")
    bbox = self.town.bbox
    stops = feed.stops[
        feed.stops.stop_lat.between(bbox.lat_min, bbox.lat_max) &
        feed.stops.stop_lon.between(bbox.lon_min, bbox.lon_max)
    ]
    observations = []
    for _, row in stops.iterrows():
        observations.append(Observation(
            feature_id=row.stop_id,  # used as source_id for upsert
            domain="transit",
            values={
                "stop_name": row.stop_name,
                "geometry_type": "Point",
                "lon": row.stop_lon,
                "lat": row.stop_lat,
            },
            source_id=row.stop_id,
        ))
    return observations
```

### GTFS-RT vehicle position parsing
```python
# Source: https://gtfs.org/documentation/realtime/language-bindings/python/
from google.transit import gtfs_realtime_pb2
from datetime import datetime, timezone

def normalize(self, raw: bytes) -> list[Observation]:
    feed_msg = gtfs_realtime_pb2.FeedMessage()
    feed_msg.ParseFromString(raw)
    observations = []
    ts = datetime.now(timezone.utc)
    for entity in feed_msg.entity:
        if entity.HasField("vehicle"):
            vp = entity.vehicle
            observations.append(Observation(
                feature_id=vp.trip.trip_id or entity.id,
                domain="transit",
                values={
                    "lat": vp.position.latitude,
                    "lon": vp.position.longitude,
                    "trip_id": vp.trip.trip_id,
                    "route_id": vp.trip.route_id,
                    "delay_seconds": None,
                },
                timestamp=ts,
                source_id=entity.id,
            ))
        if entity.HasField("trip_update"):
            tu = entity.trip_update
            observations.append(Observation(
                feature_id=tu.trip.trip_id or entity.id,
                domain="transit",
                values={
                    "trip_id": tu.trip.trip_id,
                    "route_id": tu.trip.route_id,
                    "delay_seconds": tu.delay,
                    "lat": None,
                    "lon": None,
                },
                timestamp=ts,
                source_id=entity.id,
            ))
    return observations
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| APScheduler 3.x job API | APScheduler 4.x AsyncScheduler | 2024 (4.x released) | 3.x API is still correct for this project; do NOT use 4.x — different API |
| gtfs-realtime-bindings 0.0.x (pip) | 2.0.0 (MobilityData maintained) | 2023 | Use `gtfs-realtime-bindings==2.0.0`; old 0.x versions are deprecated |
| UBA v2 direct API | UBA luftdaten.umweltbundesamt.de v4 API | 2022 | Both work; v2 proxy URL `luftdaten.umweltbundesamt.de/api-proxy/` is stable |
| Sensor.community global data dump (data.json) | Area-filtered endpoint `/airrohr/v1/filter/` | n/a | Use area filter — global dump is 10MB+; area filter returns only local sensors |
| Bright Sky v1 | Bright Sky v2.2.8 (current) | 2024 | `/current_weather` + `/weather` endpoints unchanged; new fields added but backward compatible |

**Deprecated/outdated:**
- `luftdaten.info` domain: Now redirects to Sensor.community. Use `data.sensor.community` directly.
- GTFS-Kit 7.x: Referenced in STACK.md; current version is 12.0.3. API is compatible but use `12.0.3`.

---

## Open Questions

1. **GTFS-RT feed URL for NVBW bwgesamt**
   - What we know: CONTEXT.md references `realtime.gtfs.de`; gtfs.de offers GTFS-RT feeds but specific paths are behind a portal
   - What's unclear: Whether NVBW publishes GTFS-RT at all for bwgesamt, and if so, the exact URL and whether registration is required
   - Recommendation: Store `gtfs_rt_url: ""` in `aalen.yaml` initially; GTFSRealtimeConnector checks `self.config.config.get("gtfs_rt_url")` and skips gracefully if empty. Planner should include a task to investigate and fill in the URL.

2. **UBA station 238 PM2.5 availability**
   - What we know: Station 238 (DEBW029 Aalen) measures PM10, NO2, O3, SO2, CO per the metadata API
   - What's unclear: Whether PM2.5 component ID is available at this station
   - Recommendation: UBA connector must handle missing PM2.5 gracefully (nullable field). Do a live API call during connector testing to confirm component IDs.

3. **weather_readings schema: new hypertable or reuse existing?**
   - What we know: No weather_readings table exists in 001_initial_schema.py
   - What's unclear: Whether to add a dedicated weather_readings hypertable or store weather as features+generic readings
   - Recommendation: Add a dedicated `weather_readings` hypertable in migration 002, similar to `air_quality_readings`. Weather data is time-series by nature and fits hypertable pattern.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | Backend runtime | ✓ | 3.11.5 (venv) | — |
| Docker | Container DB | ✓ | 29.3.1 | — |
| TimescaleDB (Docker) | Hypertables | ✓ | pg17 (running, port 5432) | — |
| httpx | All connectors | ✓ | 0.28.1 (installed) | — |
| pydantic | Validation models | ✓ | 2.12.5 (installed) | — |
| sqlalchemy + asyncpg | DB writes | ✓ | 2.0.49 / 0.31.0 (installed) | — |
| geoalchemy2 | PostGIS geometry | ✓ | 0.18.4 (installed) | — |
| gtfs-kit | GTFS static parsing | ✗ | — (not in pyproject.toml) | Manual CSV parsing (do not hand-roll) |
| gtfs-realtime-bindings | GTFS-RT protobuf | ✗ | — (not in pyproject.toml) | protobuf library (complex, avoid) |
| apscheduler | Scheduled polling | ✗ | — (not in pyproject.toml) | asyncio.sleep loop (fragile, avoid) |
| pytest-asyncio | Async tests | ✓ | 1.3.0 (installed) | — |

**Missing dependencies with no fallback:**
- `gtfs-kit`, `gtfs-realtime-bindings`, `apscheduler` — must be added to pyproject.toml in Wave 0 before implementation

**Missing dependencies with fallback:**
- None. All three missing libraries have no acceptable hand-rolled alternative at this scope.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | `backend/pyproject.toml` → `[tool.pytest.ini_options]` with `asyncio_mode = "auto"` |
| Quick run command | `cd backend && uv run pytest tests/connectors/ -x -q` |
| Full suite command | `cd backend && uv run pytest tests/ -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TRAF-01 | GTFSConnector fetches bwgesamt zip, bbox-filters stops, writes to features | integration (live URL) | `uv run pytest tests/connectors/test_gtfs.py -x` | ❌ Wave 0 |
| TRAF-02 | GTFSRealtimeConnector parses protobuf VehiclePosition + TripUpdate | unit (fixture protobuf) + integration | `uv run pytest tests/connectors/test_gtfs_rt.py -x` | ❌ Wave 0 |
| WAIR-01 | WeatherConnector fetches current conditions, writes to weather_readings | integration (live API) | `uv run pytest tests/connectors/test_weather.py::test_current_weather -x` | ❌ Wave 0 |
| WAIR-02 | WeatherConnector fetches MOSMIX forecast entries | integration (live API) | `uv run pytest tests/connectors/test_weather.py::test_forecast -x` | ❌ Wave 0 |
| WAIR-03 | UBAConnector fetches PM10/NO2/O3 for station 238 | integration (live API) | `uv run pytest tests/connectors/test_uba.py -x` | ❌ Wave 0 |
| WAIR-04 | SensorCommunityConnector fetches sensors within 25km of Aalen | integration (live API) | `uv run pytest tests/connectors/test_sensor_community.py -x` | ❌ Wave 0 |

All tests are integration tests hitting live endpoints. Per success criteria: "Running pytest tests/connectors/ passes with live-endpoint integration tests."

### Sampling Rate
- **Per task commit:** `cd backend && uv run pytest tests/connectors/ -x -q -k "not slow"`
- **Per wave merge:** `cd backend && uv run pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/connectors/__init__.py` — package init
- [ ] `backend/tests/connectors/conftest.py` — shared fixtures (db session, town config, aalen bbox)
- [ ] `backend/tests/connectors/test_uba.py` — covers WAIR-03
- [ ] `backend/tests/connectors/test_sensor_community.py` — covers WAIR-04
- [ ] `backend/tests/connectors/test_weather.py` — covers WAIR-01, WAIR-02
- [ ] `backend/tests/connectors/test_gtfs.py` — covers TRAF-01
- [ ] `backend/tests/connectors/test_gtfs_rt.py` — covers TRAF-02 (with fixture protobuf binary)
- [ ] `backend/alembic/versions/002_weather_hypertable.py` — adds weather_readings hypertable
- [ ] `backend/alembic/versions/002_schema_additions.py` — adds features unique constraint, sources staleness columns
- [ ] Dependency install: `uv add gtfs-kit==12.0.3 gtfs-realtime-bindings==2.0.0 apscheduler==3.11.2`

---

## Project Constraints (from CLAUDE.md)

All directives from CLAUDE.md are binding. Key ones for this phase:

- **No paid APIs or restricted feeds** — All four connectors use free, open APIs (confirmed)
- **No Aalen-specific hardcoding** — Station ID 238 and coordinates must come from town config YAML, not hardcoded in connector class
- **NGSI-LD compatible API layer** — Not in scope for Phase 2, deferred to Phase 3
- **DL-DE-BY-2.0 attribution** — NVBW GTFS data requires attribution; store in `sources` table `config` JSONB field
- **Town-config-driven** — All connector URLs, station IDs, bbox go in `aalen.yaml` `config:` block, read via `self.config.config["key"]`
- **uv for package management** — Use `uv add` not `pip install`
- **pytest + pytest-asyncio** — `asyncio_mode = "auto"` already set in pyproject.toml
- **TDD** — Write failing test first, then implement connector
- **GSD Workflow Enforcement** — All code changes through GSD execute-phase; no direct edits outside workflow

---

## Sources

### Primary (HIGH confidence)
- Live API test: `https://api.brightsky.dev/current_weather?lat=48.84&lon=10.09` — response fields verified 2026-04-05
- Live API test: `https://api.brightsky.dev/openapi.json` — all endpoints and parameters
- Live API test: `https://luftdaten.umweltbundesamt.de/api/air-data/v2/meta/json` — Aalen station 238 confirmed
- Official GTFS-RT Python bindings: https://gtfs.org/documentation/realtime/language-bindings/python/
- Sensor.community API wiki: https://github.com/opendata-stuttgart/meta/wiki/EN-APIs
- UBA API spec PDF: https://www.umweltbundesamt.de/system/files/medien/358/dokumente/schnittstellenbeschreibung_luftdaten_api_v4.pdf
- PyPI verified versions: gtfs-kit 12.0.3, apscheduler 3.11.2, gtfs-realtime-bindings 2.0.0

### Secondary (MEDIUM confidence)
- NVBW bwgesamt download URL: https://busmaps.com/en/germany/Nahverkehrsgesellschaft-Baden-Wurttemberg/bwgesamt — confirms `bwgesamt.zip` URL and weekly update cycle
- gtfs-kit documentation: https://mrcagney.github.io/gtfs_kit_docs/ (404 at research time; API confirmed from GitHub source)
- APScheduler FastAPI integration: https://www.nashruddinamin.com/blog/running-scheduled-jobs-in-fastapi

### Tertiary (LOW confidence)
- GTFS-RT URL for NVBW: not found — marked as open question, URL must be confirmed before GTFSRealtimeConnector is finalized

---

## Metadata

**Confidence breakdown:**
- Standard stack (new packages): HIGH — versions confirmed from PyPI 2026-04-05
- UBA API + station ID: HIGH — confirmed from live API response
- Bright Sky API: HIGH — confirmed from live OpenAPI spec + live API call
- Sensor.community API: HIGH — confirmed from official wiki
- GTFS static URL: MEDIUM — confirmed from secondary source, should be verified before first download
- GTFS-RT URL: LOW — not found; must be discovered at implementation time
- Weather hypertable gap: HIGH — verified by reading 001_initial_schema.py

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (stable APIs); GTFS-RT URL remains LOW confidence until confirmed
