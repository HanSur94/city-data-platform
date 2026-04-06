# Phase 7: Traffic & Energy Connectors — Research

**Researched:** 2026-04-06
**Domain:** German open data APIs — BASt traffic counts, Autobahn API, MobiData BW, SMARD electricity, MaStR renewable registry
**Confidence:** MEDIUM-HIGH (all API shapes verified; BASt CSV column names require download validation at implementation time)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Traffic Data Sources & Scope**
- "Near Aalen" for BASt stations means stations within the Aalen bbox + 20km buffer — covers A7 and B29
- Use BASt CSV data (free, no registration) as primary traffic count source — MDM/Mobilithek may need registration per STATE.md blocker
- MobiData BW: prioritize traffic count stations + bike counting stations — sharing/bike-rental data is fragmented near Aalen
- Autobahn API scope: A7 + A6 (Crailsheim junction) roadworks and closures within 50km of Aalen

**Energy Data Sources & Dashboard**
- SMARD electricity mix KPI tile: stacked bar showing current % by source (solar, wind, gas, coal, nuclear, hydro, biomass, other), color-coded renewable vs fossil
- MaStR registry: clustered circles color-coded by type (solar=yellow, wind=blue, battery=green); solar on buildings gets distinct roof icon
- Use SMARD as the single energy data source — Energy-Charts pulls from SMARD anyway; avoids maintaining two scrapers
- Poll intervals: SMARD every 15 min (matches resolution), MaStR daily (registry changes slowly)

**Map Layer Presentation**
- Traffic flow: colored circles at station locations, sized by flow rate, colored green→yellow→red by congestion level — follows AQI layer pattern
- Autobahn roadworks: warning triangle icons (⚠) for roadworks, red X (✗) for closures, clickable popup with detour info
- Sidebar groups: "Traffic" (BASt counts, Autobahn warnings, MobiData BW) and "Energy" (electricity mix, renewables map) as separate toggle groups
- MaStR layer load: clustered GeoJSON with server-side bbox filtering — follows GTFS stops pattern

**Dashboard Integration**
- Energy KPI tile: current renewable % + generation mix mini-bar + wholesale price — click opens energy detail panel
- Traffic KPI tile: active roadworks count + average flow status indicator (normal/busy/congested) — click opens traffic detail panel
- Energy detail panel: generation mix stacked area chart (time-series) + wholesale price line chart — date range picker applies
- Traffic detail panel: per-station flow chart (line) + roadworks list sorted by proximity

### Claude's Discretion
No items deferred to Claude's discretion — all grey areas resolved.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TRAF-03 | Traffic count stations on map with flow data (BASt permanent counters near Aalen) | BASt CSV download verified; connector follows PegelonlineConnector pattern (feature upsert + observation persist); `traffic_readings` hypertable needed in migration 003 |
| TRAF-04 | Autobahn roadworks, warnings, and closures for nearby A7 (Autobahn API) | API endpoints confirmed at `verkehr.autobahn.de/o/autobahn/{road}/services/roadworks|closure|warning`; response fields documented; stored as features, not time-series |
| TRAF-05 | MobiData BW traffic counts and sharing/bike data integration | MobiData BW hourly CSV format confirmed (same BASt format, BW-filtered); connector shares normalize logic with BASt connector |
| ENRG-01 | Current German electricity generation mix by source (SMARD — 15-min resolution) | SMARD API filter codes confirmed for all 8 sources; `quarterhour` resolution param verified; `energy_readings` hypertable already exists in migration 001 |
| ENRG-02 | Regional renewable energy installations on map (MaStR — solar, wind, batteries) | MaStR bulk XML download confirmed; open-mastr Python library for parsing; daily update cadence; Ostalbkreis filter via Landkreis field; stored as features |
| ENRG-03 | Electricity wholesale price trend (SMARD) | SMARD filter code 4169 (Deutschland/Luxemburg day-ahead price) confirmed; same API pattern as generation mix |
| ENRG-04 | Energy statistics dashboard (Fraunhofer Energy-Charts data) | Decision: use SMARD only — Energy-Charts pulls from SMARD anyway; detail panel shows generation mix stacked area + wholesale price line |
</phase_requirements>

---

## Summary

Phase 7 adds two new data domains — traffic and energy — by integrating five external data sources via new backend connectors, then surfacing the data through new map layers, KPI tiles, and detail panel charts. All five data sources are German federal open data with no API key requirements.

The backend work requires one new Alembic migration (003) to add a `traffic_readings` hypertable and extend the `persist()` method in `BaseConnector` for the `traffic` domain. The existing `energy_readings` hypertable from migration 001 is already present. Five new connectors follow the established `PegelonlineConnector` run-override pattern: upsert features, then persist observations. The Autobahn and MaStR connectors are features-only (no time-series observations).

The frontend work adds two new map layer groups (Verkehr, Energie), two new KPI tiles, and two extended detail panels. All follow established patterns from `AQILayer.tsx`/`TransitLayer.tsx` and `KpiTile.tsx`/`DomainDetailPanel.tsx`. The only genuinely new component is `EnergyMixBar.tsx` — a horizontal stacked bar for the generation mix that has no direct precedent in the existing codebase.

**Primary recommendation:** Implement in three waves — (1) DB migration + backend connectors, (2) API endpoint extensions, (3) frontend layers/tiles/panels.

---

## Standard Stack

### Core (unchanged from project stack)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.135.x | Connector orchestration + REST endpoints | Already in use |
| SQLAlchemy (async) | 2.x | DB access in connectors | Already in use |
| httpx | 0.27.x | Async HTTP for all API fetches | Already in use |
| Pydantic | 2.x | Input validation for API responses | Already in use |
| TimescaleDB | PG 17 + TSDBv2.23 | Hypertable storage for traffic readings | Already in use |
| MapLibre / react-map-gl | 5.x / 8.x | Map layer rendering | Already in use |
| Recharts (via shadcn chart) | 2.x | AreaChart + LineChart for detail panels | Already in use |

### New Dependencies This Phase
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| open-mastr | latest (PyPI) | Parse MaStR bulk XML download into structured data | MaStR XML format is complex; hand-rolling the parser is high-risk |
| lxml (transitive) | — | XML parsing, pulled by open-mastr | Automatic dependency |

**Installation (backend):**
```bash
uv add open-mastr
```

**Version verification:**
```bash
npm view recharts version    # already installed
pip show open-mastr          # or: uv run pip show open-mastr
```

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| open-mastr | Hand-rolled XML parser | MaStR XML structure changes; open-mastr tracks schema updates; not worth hand-rolling |
| BASt CSV + MobiData BW CSV | MDM/Mobilithek live feed | MDM may require registration per STATE.md blocker; BASt CSV is free, no auth |
| SMARD API | Fraunhofer Energy-Charts | Energy-Charts pulls from SMARD; single source eliminates duplicate scraping |

---

## Architecture Patterns

### Connector Pattern (established — follow exactly)

All five new connectors follow `PegelonlineConnector.run()` override pattern:

```python
# Source: /backend/app/connectors/pegelonline.py (verified)
async def run(self) -> None:
    raw = await self.fetch()
    for item in raw:
        feature_id = await self.upsert_feature(
            source_id=f"bast:{item['station_id']}",
            domain="traffic",
            geometry_wkt=f"POINT({item['lon']} {item['lat']})",
            properties={"station_name": ..., "road": ..., "attribution": ...},
        )
        self._feature_ids[item['station_id']] = feature_id
    observations = self.normalize(raw)
    await self.persist(observations)
    await self._update_staleness()
```

BASt and MobiData BW connectors: feature upsert + traffic_readings persist.
Autobahn connector: feature upsert only (roadworks are current-state, not time-series — overwrite properties on each poll).
MaStR connector: feature upsert only (static registry, daily refresh — update geometry+properties).
SMARD connector: persist to energy_readings only (no point features — national grid data has no map coordinates).

### Domain Extension Points

1. **`VALID_DOMAINS`** in `backend/app/schemas/geojson.py` — add `"traffic"` (energy already listed)
2. **`CONNECTOR_ATTRIBUTION`** in `backend/app/schemas/geojson.py` — add 5 new connector entries
3. **`BaseConnector.persist()`** in `backend/app/connectors/base.py` — add `elif obs.domain == "traffic"` branch
4. **`backend/app/routers/layers.py`** — add traffic-specific query (LATERAL join on `traffic_readings` like air_quality_readings) and energy-specific query (LATERAL join on `energy_readings`)
5. **`backend/app/routers/kpi.py`** — add TrafficKPI and EnergyKPI query + response fields
6. **`backend/app/routers/timeseries.py`** — add `elif domain == "traffic"` and `elif domain == "energy"` branches
7. **`backend/app/schemas/responses.py`** — add `TrafficKPI`, `EnergyKPI` Pydantic models; extend `KPIResponse`
8. **`towns/aalen.yaml`** — add 5 new connector entries

### New Alembic Migration (003)

```python
# Pattern: backend/alembic/versions/002_schema_additions.py
# New migration: 003_traffic_readings.py
op.create_table(
    "traffic_readings",
    sa.Column("time", sa.TIMESTAMP(timezone=True), nullable=False),
    sa.Column("feature_id", postgresql.UUID(as_uuid=True), ...),
    sa.Column("vehicle_count_total", sa.Integer, nullable=True),   # Kfz/h
    sa.Column("vehicle_count_hgv", sa.Integer, nullable=True),     # SV/h heavy goods
    sa.Column("speed_avg_kmh", sa.Float, nullable=True),
    sa.Column("congestion_level", sa.String, nullable=True),       # "free"|"moderate"|"congested"
)
op.execute("SELECT create_hypertable('traffic_readings', 'time', ...)")
op.execute("SELECT add_retention_policy('traffic_readings', drop_after => INTERVAL '2 years', ...)")
```

The existing `energy_readings` schema (`value_kw`, `source_type`) needs extension to store the full SMARD generation mix. Rather than altering it, SMARD data can use `source_type` as the generation source (e.g., `"solar"`, `"wind_onshore"`) and `value_kw` for MW value — the schema already fits.

### Map Layer Pattern

Follow `AQILayer.tsx` for circle layers, `TransitLayer.tsx` for clustered layers.

```typescript
// Source: /frontend/components/map/AQILayer.tsx (verified)
// TrafficLayer: same pattern, color driven by congestion_level property
const trafficCircleLayer: CircleLayerSpecification = {
  id: 'traffic-circles',
  type: 'circle',
  source: 'traffic',
  paint: {
    'circle-color': [
      'match', ['get', 'congestion_level'],
      'free',      '#22c55e',
      'moderate',  '#eab308',
      'congested', '#ef4444',
      '#9ca3af',  // unknown/default
    ],
    'circle-radius': ['interpolate', ['linear'], ['get', 'vehicle_count_total'], 0, 6, 2000, 16],
    'circle-stroke-width': 1,
    'circle-stroke-color': '#ffffff',
  },
};
```

### SMARD API Pattern

SMARD requires two-step fetch: index → data. The connector must call the index endpoint first to get the latest available timestamp, then fetch that chunk.

```python
# Verified from bundesAPI/smard-api openapi.yaml
BASE = "https://www.smard.de/app/chart_data"
# Step 1: get available timestamps
index_url = f"{BASE}/{filter_code}/DE/index_quarterhour.json"
# Step 2: fetch latest chunk
data_url = f"{BASE}/{filter_code}/DE/{filter_code}_DE_quarterhour_{timestamp}.json"
# Response: {"series": [[unix_ms, value_mw_or_null], ...]}
```

Generation mix requires one fetch per source type. Batch 8 filter codes:

| Source | Filter Code |
|--------|-------------|
| Solar | 4068 |
| Wind Onshore | 4067 |
| Wind Offshore | 1225 |
| Natural Gas | 4071 |
| Lignite (Braunkohle) | 1223 |
| Hard Coal (Steinkohle) | 4069 |
| Nuclear | 1224 |
| Hydro (Wasserkraft) | 1226 |
| Biomass | 4066 |
| Other Renewables | 1228 |
| Wholesale Price DE/LU | 4169 |

### Autobahn API Pattern

Base URL: `https://verkehr.autobahn.de/o/autobahn`
No authentication required. Roads supported: A1–A9, etc. No query filtering by location — fetch all roadworks for A7, then filter by coordinate proximity.

```python
# GET /{road}/services/roadworks  →  {"roadworks": [{...}, ...]}
# Response fields: identifier, coordinate (lat, long), title, subtitle,
#                  description, startTimestamp, isBlocked, future, extent
# Detail endpoint for full description:
# GET /details/roadworks/{roadworkId}  (base64-encoded ID)
```

For Autobahn features, use `source_id=f"autobahn:{roadwork['identifier']}"` — this lets `upsert_feature` overwrite stale entries when roadworks resolve.

### MaStR Pattern

The open-mastr library downloads the full BNetzA XML bulk dump and parses it into a local SQLite database. For Phase 7, use the bulk method filtered to `solar_extended` and `wind_extended` technology types, then post-filter by `Landkreis = "Ostalbkreis"` in Python.

```python
# Verified from open-mastr docs
from open_mastr import Mastr
db = Mastr()
db.download(data=["solar_extended", "wind_extended", "storage_units"])
# Returns pandas DataFrame with columns including:
# Breitengrad (lat), Laengengrad (lon), Nettonennleistung (capacity kW),
# Inbetriebnahmedatum (commissioning date), Standort (location/municipality),
# Landkreis (district), Lage (roof-top="Aufdach" vs ground="Freifläche")
```

The `Lage` field distinguishes rooftop solar (`Aufdach`) from ground-mounted (`Freifläche`) — this drives the distinct roof icon decision from CONTEXT.md.

### Frontend KPI Extension Pattern

The `KPIResponse` Pydantic model and `useKpi` hook must be extended:

```typescript
// Extend /frontend/types/kpi.ts (existing file)
// Add to KPIResponse:
traffic: TrafficKPI | null
energy: EnergyKPI | null

// TrafficKPI:
active_roadworks: number
flow_status: 'normal' | 'elevated' | 'congested' | null
last_updated: string | null

// EnergyKPI:
renewable_percent: number | null
generation_mix: Record<string, number>  // source → MW
wholesale_price_eur_mwh: number | null
last_updated: string | null
```

### EnergyMixBar Component Pattern

No direct precedent in codebase. Use shadcn `chart` component (Recharts-based) for the mini stacked bar in the KPI tile, and a full `AreaChart` with multiple data series for the detail panel.

```typescript
// EnergyMixBar: horizontal stacked bar, 8 sources
// Uses CSS variables from shadcn chart color system (--chart-1 through --chart-8)
// Override with domain-specific colors per UI-SPEC.md
```

### Anti-Patterns to Avoid

- **Storing Autobahn roadworks as time-series**: They are current-state events. Store as features only; overwrite on each poll. Do NOT insert into any hypertable.
- **Storing MaStR installations as time-series**: Static registry. Feature upsert only, daily poll updates geometry+properties in place.
- **Fetching all German SMARD data**: Only fetch latest 15-min window per source type. The index endpoint returns the most-recent timestamp chunk — use that, not a full historical pull.
- **Fetching all MaStR data without Landkreis filter**: Full Germany MaStR is 100k+ rows. Filter to `Landkreis = "Ostalbkreis"` (roughly 8,000-person-municipality, ~2k solar installs likely) before upsert.
- **Skipping the two-step SMARD index→data fetch**: The SMARD API has no "latest" endpoint — you must always call the index first to discover the latest chunk's timestamp.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MaStR XML parsing | Custom XML parser | `open-mastr` (PyPI) | MaStR XML schema has 40+ entity types; schema evolves; open-mastr handles it and runs a tested download pipeline |
| SMARD timestamp discovery | Custom index scraping | SMARD index endpoint (`index_quarterhour.json`) | The index JSON is the only machine-readable way to find the latest available chunk |
| Autobahn coordinate filtering | Bounding box math | Server-side: fetch all A7/A6 roadworks, filter by distance in Python using haversine | Autobahn API returns all roadworks per road — API has no geographic filter; client-side Python filter is trivial |
| Congestion level computation | Custom thresholds | Backend: compute in `normalize()` based on capacity data from BASt station metadata | BASt provides lane count + historical baseline; congestion = current / capacity ratio |
| EnergyMixBar chart | Custom SVG | shadcn `chart` wrapper over Recharts BarChart | Recharts stacked bar handles color mapping + tooltip; matches existing chart patterns |

**Key insight:** MaStR is the only data source in this phase that requires a third-party Python library. All others (BASt, Autobahn, SMARD) are plain HTTP + JSON/CSV — use httpx directly.

---

## Common Pitfalls

### Pitfall 1: SMARD "Null Island" values
**What goes wrong:** SMARD returns `null` entries in the series array for time slots with no data (e.g., solar at night). The array is `[[timestamp_ms, value_or_null], ...]`. If you `sum()` without filtering `None`, you get `None` propagating into all calculations.
**Why it happens:** SMARD preserves the 15-min grid even when no measurement exists.
**How to avoid:** Filter `None` values in `normalize()` before computing renewable percentage. `total = sum(v for v in values.values() if v is not None)`.
**Warning signs:** Renewable % shows as `null` in the KPI tile even during daytime.

### Pitfall 2: BASt CSV Encoding
**What goes wrong:** BASt CSV files use Windows-1252 (ANSI) encoding, not UTF-8. Python's `open()` defaults to UTF-8 and raises `UnicodeDecodeError`.
**Why it happens:** Legacy German federal IT systems. Confirmed in BASt documentation reference to "ANSI data sets."
**How to avoid:** `open(path, encoding='windows-1252')` or use `chardet` to detect. Add encoding detection to `BastConnector.normalize()`.
**Warning signs:** `UnicodeDecodeError: 'utf-8' codec can't decode byte` during first parse.

### Pitfall 3: Autobahn API Rate Limiting
**What goes wrong:** The Autobahn API returns HTTP 429 if polled too frequently. The default poll interval for roadworks connectors might be too aggressive.
**Why it happens:** The API is a public free service with undocumented rate limits (observed ~10 req/min).
**How to avoid:** Set poll interval to 300s (5 min) in `aalen.yaml`. Space A7 and A6 fetches within the same connector run (not separate connectors). Add retry with exponential backoff in `fetch()`.
**Warning signs:** HTTP 429 errors appearing in connector health dashboard.

### Pitfall 4: MaStR Download Size
**What goes wrong:** `open-mastr`'s full bulk download is several GB and takes 10-30 minutes. Running it on every poll cycle (daily) means the connector blocks for a long time.
**Why it happens:** The bulk download is a full Germany snapshot.
**How to avoid:** Download to a local path and check the file modification timestamp. Only re-download if the file is older than 24h. Alternatively, use `open-mastr`'s built-in SQLite caching — it persists the last download and only re-fetches on explicit call.
**Warning signs:** APScheduler job timeout, connector health showing `never_fetched` for MaStR.

### Pitfall 5: VALID_DOMAINS missing "traffic"
**What goes wrong:** Layer endpoint returns HTTP 404 for `domain=traffic` because `VALID_DOMAINS` frozenset in `geojson.py` does not include it yet.
**Why it happens:** `energy` was pre-added in migration 001 but `traffic` was not added to `VALID_DOMAINS`.
**How to avoid:** Add `"traffic"` to `VALID_DOMAINS` in `backend/app/schemas/geojson.py` as part of migration 003 wave.
**Warning signs:** 404 on `GET /api/layers/traffic?town=aalen`.

### Pitfall 6: BaseConnector.persist() missing "traffic" branch
**What goes wrong:** Traffic observations silently drop — `persist()` has no `elif obs.domain == "traffic"` branch, so observations are accepted but never written.
**Why it happens:** `persist()` is domain-aware and has explicit branches per domain.
**How to avoid:** Add the `traffic` branch to `persist()` alongside the migration 003 work. This is a coordinated change: migration + persist branch must both land before the connector runs.
**Warning signs:** `traffic_readings` table stays empty; no error raised.

### Pitfall 7: Recharts AreaChart with null series values
**What goes wrong:** Recharts `AreaChart` with stacked areas renders incorrectly or throws when a data series has `undefined`/`null` for some time slots (e.g., nuclear generation = 0 during daytime renewable periods).
**Why it happens:** Recharts stacked area requires consistent series presence per data point.
**How to avoid:** Normalize all data points to have all source keys present, substituting `0` for missing values. `const normalized = points.map(p => ({time: p.time, solar: p.solar ?? 0, wind: p.wind ?? 0, ...}))`.
**Warning signs:** Area chart gaps or console errors from Recharts during energy detail panel render.

---

## Code Examples

### SMARD Two-Step Fetch Pattern
```python
# Source: Verified from bundesAPI/smard-api openapi.yaml + Python forum example
import httpx
from datetime import datetime, timezone

SMARD_BASE = "https://www.smard.de/app/chart_data"
GENERATION_FILTERS = {
    "solar": 4068,
    "wind_onshore": 4067,
    "wind_offshore": 1225,
    "gas": 4071,
    "lignite": 1223,
    "hard_coal": 4069,
    "nuclear": 1224,
    "hydro": 1226,
    "biomass": 4066,
}
PRICE_FILTER = 4169  # Deutschland/Luxemburg day-ahead

async def fetch_smard_latest(filter_code: int) -> list[tuple[int, float | None]]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: get available timestamps
        idx_resp = await client.get(
            f"{SMARD_BASE}/{filter_code}/DE/index_quarterhour.json"
        )
        idx_resp.raise_for_status()
        timestamps: list[int] = idx_resp.json().get("timestamps", [])
        if not timestamps:
            raise ValueError(f"SMARD returned no timestamps for filter {filter_code}")
        latest_ts = timestamps[-1]
        # Step 2: fetch latest chunk
        data_resp = await client.get(
            f"{SMARD_BASE}/{filter_code}/DE/{filter_code}_DE_quarterhour_{latest_ts}.json"
        )
        data_resp.raise_for_status()
        return data_resp.json().get("series", [])
```

### Autobahn Roadworks Fetch + Proximity Filter
```python
# Source: Verified from autobahn.api.bund.dev/openapi.yaml
import httpx, math

AUTOBAHN_BASE = "https://verkehr.autobahn.de/o/autobahn"
AALEN_LAT, AALEN_LON = 48.840, 10.093

def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

async def fetch_roadworks(roads: list[str], radius_km: float = 50.0) -> list[dict]:
    results = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for road in roads:
            for service in ("roadworks", "closure", "warning"):
                resp = await client.get(f"{AUTOBAHN_BASE}/{road}/services/{service}")
                if resp.status_code == 404:
                    continue  # road has no active items
                resp.raise_for_status()
                items = resp.json().get(service, [])
                for item in items:
                    coord = item.get("coordinate", {})
                    lat = float(coord.get("lat", 0))
                    lon = float(coord.get("long", 0))
                    if haversine_km(AALEN_LAT, AALEN_LON, lat, lon) <= radius_km:
                        item["_service_type"] = service
                        results.append(item)
    return results
```

### MapLibre SymbolLayer for Autobahn Markers
```typescript
// Source: Verified from UI-SPEC.md + react-map-gl/maplibre docs pattern
// Autobahn layer uses SymbolLayerSpecification for icon markers
import type { SymbolLayerSpecification } from 'react-map-gl/maplibre';

const autobahnSymbolLayer: SymbolLayerSpecification = {
  id: 'autobahn-markers',
  type: 'symbol',
  source: 'autobahn',
  layout: {
    'icon-image': [
      'match', ['get', 'service_type'],
      'roadworks', 'roadworks-icon',
      'closure',   'closure-icon',
      'warning-icon',
    ],
    'icon-size': 1.0,
    'icon-allow-overlap': true,
    visibility: 'visible',
  },
};
// Note: icons must be added to MapLibre style via map.addImage() in MapView useEffect
```

### MaStR Filter + Upsert Pattern
```python
# Source: Verified from open-mastr docs + CONTEXT.md decisions
from open_mastr import Mastr

async def load_mastr_ostalbkreis(self) -> list[dict]:
    db = Mastr()
    db.download(data=["solar_extended", "wind_extended", "storage_units"])
    solar_df = db.get_power_plant_in_region(
        technology="solar",
        additional_data=["extended"]
    )
    # Filter by Landkreis
    local = solar_df[solar_df["Landkreis"] == "Ostalbkreis"]
    results = []
    for _, row in local.iterrows():
        results.append({
            "type": "solar_rooftop" if row.get("Lage") == "Aufdach" else "solar_ground",
            "lat": row["Breitengrad"],
            "lon": row["Laengengrad"],
            "capacity_kw": row["Nettonennleistung"],
            "commissioned": str(row.get("Inbetriebnahmedatum", "")),
        })
    return results
```

---

## Data Source API Reference

### BASt Permanent Traffic Counters

**Data type:** Monthly ZIP archives, hourly CSV per station
**URL pattern:**
```
https://files.bast.de/...DZ_{YYYY}_{MM}_Rohdaten.zip
```
Contains per-station CSVs (`BW_XXXXXXXX_YYMM.csv`) and a station metadata CSV.

**Key CSV fields (verified from BASt documentation):**
- Station ID (Zählstellennummer), Road name, Direction, Lane count
- Hourly vehicle counts by type: `Kfz` (total), `Pkw` (cars), `Lfw` (lorries), `SV` (heavy traffic total)
- **Encoding:** Windows-1252 (ANSI), not UTF-8
- **Coordinates:** Included in station metadata CSV (lat/lon in WGS84)

**License:** Datenlizenz Deutschland – Namensnennung – Version 2.0
**Registration required:** None

**Aalen bbox + 20km buffer:** approx `[9.67, 48.57, 10.47, 49.10]` — expect ~5-15 BASt stations (A7 near Aalen has confirmed stations).

### MobiData BW Traffic Counts

**Data type:** Same BASt-format hourly CSV, filtered to Baden-Württemberg
**URL pattern:**
```
https://mobidata-bw.de/vm/Stundenwerte_Dauerzaehlstellen_BW/Stundenwerte_{YYYYMM}/BW_{STATION_ID}_{YYMM}.csv
```
**Vehicle classification:** 8+1 types (Mot, Pkw, Lfw, PmA, Bus, LoA, LmA, Sat, Son), same as BASt format.
**License:** Datenlizenz Deutschland – Namensnennung – Version 2.0

### Autobahn GmbH API

**Base URL:** `https://verkehr.autobahn.de/o/autobahn`
**No authentication required.**

| Endpoint | Returns |
|----------|---------|
| `GET /{road}/services/roadworks` | Active roadworks list |
| `GET /{road}/services/closure` | Road closures |
| `GET /{road}/services/warning` | Traffic warnings |
| `GET /details/roadworks/{id}` | Full description + detour text |

**Response fields per item:** `identifier`, `coordinate.lat`, `coordinate.long`, `title`, `subtitle`, `description`, `startTimestamp`, `isBlocked`, `future`
**Roads for this phase:** `A7`, `A6`
**No API key, no rate-limit documentation** — be conservative (300s poll interval).

### SMARD API

**Base URL:** `https://www.smard.de/app/chart_data`
**No authentication required.**

Two-endpoint pattern (index → data). Resolution: `quarterhour` for 15-min data.

**Filter codes:**
| Source | Code | Use |
|--------|------|-----|
| Solar PV | 4068 | ENRG-01 generation mix |
| Wind Onshore | 4067 | ENRG-01 |
| Wind Offshore | 1225 | ENRG-01 |
| Biomass | 4066 | ENRG-01 |
| Other Renewables | 1228 | ENRG-01 |
| Natural Gas | 4071 | ENRG-01 |
| Lignite | 1223 | ENRG-01 |
| Hard Coal | 4069 | ENRG-01 |
| Nuclear | 1224 | ENRG-01 |
| Hydro | 1226 | ENRG-01 |
| Day-ahead price DE/LU | 4169 | ENRG-03 wholesale price |

**Response format:** `{"series": [[unix_ms, value_or_null], ...], "object_meta": {...}}`
Generation values in MW. Price values in EUR/MWh.
**License:** CC BY 4.0 (SMARD data use terms confirm free commercial and non-commercial use with attribution).

### MaStR Bulk Download

**Source:** `https://www.marktstammdatenregister.de/MaStR/Datendownload`
**Format:** Daily ZIP of XML files (full Germany, multi-GB)
**Python library:** `open-mastr` (PyPI) — download + parse + cache locally in SQLite

**Key fields available (verified from open-mastr docs):**
| Field | German Name | Notes |
|-------|------------|-------|
| Latitude | `Breitengrad` | WGS84 |
| Longitude | `Laengengrad` | WGS84 |
| Capacity kW | `Nettonennleistung` | Nameplate capacity |
| Type/Location | `Lage` | `"Aufdach"` = rooftop, `"Freifläche"` = ground |
| District | `Landkreis` | Filter: `"Ostalbkreis"` |
| Municipality | `Standort` | City name |
| Commission date | `Inbetriebnahmedatum` | ISO date string |

**Technologies:** `solar_extended`, `wind_extended`, `storage_units`
**License:** Datenlizenz Deutschland – Namensnennung – Version 2.0 (BNetzA open data)

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SMARD CSV download | SMARD JSON API (`chart_data` endpoint) | 2019+ | API is faster, no file parsing needed |
| MaStR SOAP API (registration required) | MaStR bulk XML download (no auth) | 2021 | Bulk is preferred for full regional downloads |
| BASt annual archives only | BASt monthly rolling archives | 2022 | Current-month data available after month-end |

**Deprecated/outdated:**
- `mdm.vdv.de` (Mobilitätsdaten-Marktplatz): Requires registration and approval for live traffic feeds. Per STATE.md blocker, use BASt CSV fallback for Phase 7.
- SMARD download CSV: JSON API is the standard approach now; CSV is for bulk historical exports only.

---

## Open Questions

1. **BASt CSV column names exact format**
   - What we know: Files contain `Kfz`, `Pkw`, `SV` counts + station metadata with coordinates
   - What's unclear: Exact header row names in the CSV (may be German abbreviations; BASt documentation PDF is the authoritative source)
   - Recommendation: In Wave 0, download one sample ZIP from BASt files server and log the CSV header before writing `normalize()`. Add a `test_bast_csv_format.py` smoke test.

2. **MaStR open-mastr `Lage` field values for rooftop vs ground**
   - What we know: `Lage` distinguishes installation location; "Aufdach" confirmed in research
   - What's unclear: Whether `Lage` is consistently populated across all MaStR solar entries (some older entries may be NULL)
   - Recommendation: Handle `Lage is None` → default to `"solar_ground"` in normalize; treat NULL as ground mount.

3. **Autobahn API A6 road ID**
   - What we know: A7 roadworks endpoint is `GET /A7/services/roadworks`; CONTEXT.md adds A6 (Crailsheim junction)
   - What's unclear: Whether A6 is the correct Autobahn ID in the API's road enumeration (it may return 404 if A6 has no active roadworks in the API's coverage area)
   - Recommendation: In `fetch()`, handle HTTP 404 gracefully (the API returns 404, not empty list, when a road has no active events). Confirm A6 coverage at implementation time.

4. **SMARD API data freshness lag**
   - What we know: SMARD publishes 15-min resolution data; poll interval set to 900s
   - What's unclear: Whether the API has a publication delay (e.g., 15-30 min lag from real-time)
   - Recommendation: When computing "current renewable %" in the KPI, use the latest non-null timestamp from the series, not the wall clock. Accept up to 30-min lag as normal.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python / uv | BASt/SMARD/MaStR connectors | Assumed present (existing backend) | 3.11+ | — |
| httpx | All API fetches | Yes (already installed) | 0.27.x | — |
| open-mastr (PyPI) | MaStR connector | Not yet installed | latest | None — must install |
| PostgreSQL + TimescaleDB | traffic_readings hypertable | Yes (existing) | PG17 + TSDBv2.23 | — |
| Internet access to SMARD, Autobahn, BASt | Connector fetch | Required | — | None (data sources are external) |

**Missing dependencies with no fallback:**
- `open-mastr` package: run `uv add open-mastr` as part of Wave 1 setup.

**Missing dependencies with fallback:**
- None other than open-mastr.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio 9.x |
| Config file | `backend/pyproject.toml` (`asyncio_mode = "auto"`, `asyncio_default_fixture_loop_scope = "session"`) |
| Quick run command | `cd backend && pytest tests/connectors/ -x -q` |
| Full suite command | `cd backend && pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TRAF-03 | BASt connector normalizes CSV to Observations with traffic domain | unit | `pytest tests/connectors/test_bast.py -x` | ❌ Wave 0 |
| TRAF-04 | Autobahn connector fetches A7 roadworks and upserts features | unit | `pytest tests/connectors/test_autobahn.py -x` | ❌ Wave 0 |
| TRAF-05 | MobiData BW connector normalizes BW CSV to Observations | unit | `pytest tests/connectors/test_mobidata_bw.py -x` | ❌ Wave 0 |
| ENRG-01 | SMARD connector fetches generation mix, computes renewable % | unit | `pytest tests/connectors/test_smard.py -x` | ❌ Wave 0 |
| ENRG-02 | MaStR connector filters Ostalbkreis, upserts features with correct type | unit | `pytest tests/connectors/test_mastr.py -x` | ❌ Wave 0 |
| ENRG-03 | SMARD wholesale price included in energy KPI response | unit | `pytest tests/test_api_kpi.py -x` | ✅ (extend) |
| ENRG-04 | Energy timeseries endpoint returns generation mix points for date range | unit | `pytest tests/test_api_timeseries.py -x` | ✅ (extend) |
| TRAF-03/04 | Layer endpoint returns GeoJSON for traffic domain | unit | `pytest tests/test_api_layers.py -x` | ✅ (extend) |
| ENRG-01/02 | Layer endpoint returns GeoJSON for energy domain with readings | unit | `pytest tests/test_api_layers.py -x` | ✅ (extend) |

### Sampling Rate
- **Per task commit:** `cd backend && pytest tests/connectors/ -x -q`
- **Per wave merge:** `cd backend && pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/connectors/test_bast.py` — covers TRAF-03: CSV parse, normalize, congestion level computation
- [ ] `tests/connectors/test_autobahn.py` — covers TRAF-04: mock API response, feature upsert structure
- [ ] `tests/connectors/test_mobidata_bw.py` — covers TRAF-05: BW CSV same format as BASt, verify normalize reuse
- [ ] `tests/connectors/test_smard.py` — covers ENRG-01/03: mock two-step index+data, null value filtering, renewable % calc
- [ ] `tests/connectors/test_mastr.py` — covers ENRG-02: mock open-mastr output, Landkreis filter, Lage field mapping

---

## Project Constraints (from CLAUDE.md)

| Constraint | Impact on Phase 7 |
|------------|-------------------|
| Only freely available / open data — no paid APIs or restricted feeds | BASt CSV: no auth. Autobahn API: no auth. SMARD: no auth. MaStR bulk: no auth. MDM/Mobilithek: deferred if registration required. |
| Must run on modest hardware (self-hostable, not cloud-dependent) | MaStR open-mastr download (multi-GB) is an I/O concern on 4GB RAM, 50GB SSD. Cache locally; do not re-download on every poll. |
| Generic architecture — no Aalen-specific hardcoding | Autobahn roads list (`["A7", "A6"]`), bbox buffer (`20km`), and Landkreis filter (`"Ostalbkreis"`) must be config-driven in `aalen.yaml`, not hardcoded in connector code. |
| NGSI-LD compatible API layer, Smart Data Models schemas | New `traffic` domain features should include NGSI-LD type annotations in properties (follow existing pattern in `layers.py`). |
| Datenlizenz Deutschland attribution required | All 5 new connectors need entries in `CONNECTOR_ATTRIBUTION` dict with correct license strings. |
| Frontend on port 4000 | No impact on this phase — port is already set. |

---

## Sources

### Primary (HIGH confidence)
- Autobahn API OpenAPI spec — `https://autobahn.api.bund.dev/openapi.yaml` — endpoint paths, response fields, base URL
- SMARD API openapi.yaml (bundesAPI/smard-api) — filter codes, resolution parameter, URL format
- Existing codebase — `BaseConnector`, `PegelonlineConnector`, `AQILayer.tsx`, `TransitLayer.tsx`, `KpiTile.tsx`, `DomainDetailPanel.tsx`, `layers.py`, `kpi.py`, `timeseries.py`, migration 001/002

### Secondary (MEDIUM confidence)
- MobiData BW dataset page — `mobidata-bw.de/dataset/stundenwerte_dauerzaehlstellen` — CSV URL pattern, vehicle classification fields, license
- BASt website — `www.bast.de/DE/Publikationen/Daten/Verkehrstechnik/DZ.html` — download structure, monthly ZIP pattern, encoding note (ANSI)
- open-mastr PyPI / GitHub — `https://github.com/OpenEnergyPlatform/open-MaStR` — bulk download API, field names
- MaStR data download page — confirmed bulk XML download availability, daily updates

### Tertiary (LOW confidence — validate at implementation)
- BASt CSV exact column header names: not enumerated in web documentation; require a sample download to confirm
- open-mastr `Lage` field completeness: documented as available, but real-world null rate unknown
- Autobahn API A6 coverage: road exists in Germany but API coverage for eastern Baden-Württemberg unconfirmed

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use or well-documented PyPI packages
- Architecture patterns: HIGH — all follow verified existing codebase patterns
- Data source APIs: MEDIUM-HIGH — Autobahn and SMARD APIs fully confirmed; BASt CSV column names require sample validation
- Pitfalls: MEDIUM — encoding pitfall and SMARD null handling are common patterns; MaStR download size is an estimate

**Research date:** 2026-04-06
**Valid until:** 2026-07-06 (stable German federal APIs; SMARD filter codes unlikely to change; MaStR XML schema may evolve)
