# Phase 6: Weather & Environment Connectors - Research

**Researched:** 2026-04-06
**Domain:** Water/environment data connectors (PEGELONLINE, HVZ BW, LUBW WMS/WFS, EBA noise WMS) + AQI visualization enhancement
**Confidence:** MEDIUM — PEGELONLINE REST API is HIGH confidence (live-verified). LUBW WMS/WFS endpoints are MEDIUM (URLs verified via GetCapabilities). HVZ BW machine-readable access is LOW (no confirmed public API found). AQI thresholds are HIGH (EEA official).

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None specified — all implementation choices are at Claude's discretion.

### Claude's Discretion
All implementation choices. Follow established patterns:
- BaseConnector pattern for new connectors
- Existing map layer pattern (TransitLayer/AQILayer) for new frontend layers
- WMS layers can be added directly to MapLibre as raster sources (no backend connector needed)
- PEGELONLINE REST API (free, no key): pegelonline.wsv.de
- HVZ BW: hvz.lubw.baden-wuerttemberg.de
- LUBW flood/noise maps: WMS endpoints
- AQI visualization enhancement: EU/WHO color scale already exists in schemas/geojson.py

### Deferred Ideas (OUT OF SCOPE)
None.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WAIR-05 | AQI visualization with EU/WHO health-based color scale | EEA EAQI thresholds verified (6-tier, PM2.5/PM10/NO2/O3/SO2). Existing `aqi_tier()` in geojson.py uses 5 generic thresholds — needs replacement with official EEA breakpoints per-pollutant. AQILayer.tsx heatmap uses gradient; circle layers need per-sensor color coding. |
| WAIR-06 | Historical AQI trends: 90+ days from UBA + Sensor.community | UBA API supports `date_from`/`date_to` range queries (verified). Sensor.community historical data available via their archive API. Existing `air_quality_readings` hypertable with 2-year retention covers storage. Frontend `useTimeseries` hook exists. |
| WATR-01 | Real-time water levels at PEGELONLINE gauging stations | PEGELONLINE REST API confirmed free, no auth. Critical finding: Kocher is a state (Land) river — NOT on PEGELONLINE (federal waterways only). Nearest federal stations are on Neckar (~80km away). Plan must use Neckar stations OR use HVZ BW for Kocher. |
| WATR-02 | State waterway monitoring — Kocher and tributaries (HVZ BW) | HVZ BW (hvz.lubw.baden-wuerttemberg.de) has no confirmed public machine-readable API. Site is a web portal only. Data may need to be scraped from HTML or obtained via the WFS service. This is a significant risk. |
| WATR-03 | Flood hazard map overlay (LUBW HQ10 to HQextrem via WMS) | Confirmed public WMS: `UIS_0100000003900001` serves HQ100 + ÜSG layers. Full HWGK service with HQ10/HQextrem appears restricted to state intranet. Public substitute: ÜSG (statutory flood zones) available. |
| WATR-04 | Noise map overlay (LUBW road noise + EBA railway noise via WMS) | EBA WMS confirmed: `geoinformation.eisenbahn-bundesamt.de/wms/isophonen` with Lden/Lnight layers. LUBW road noise metadata found but WMS URL requires GetCapabilities probe. |
| WATR-05 | LUBW environmental WFS layers (water quality, nature conservation) | Confirmed WFS endpoints for Wasserschutzgebiet and Naturschutzgebiet (rips-gdi.lubw.baden-wuerttemberg.de). WFS returns GeoJSON (supported output format). No auth required. |
</phase_requirements>

---

## Summary

Phase 6 adds water/environment layers to the city data platform. The work splits into three distinct categories: (1) backend data connectors writing to TimescaleDB, (2) static WMS overlay layers loaded directly in MapLibre (no backend needed), and (3) enhancement of the existing AQI visualization.

The most significant finding is that **PEGELONLINE covers federal waterways only** — the Kocher river near Aalen is managed by Baden-Württemberg state, not the federal WSV, and returns no results from the PEGELONLINE API. Nearby Neckar stations (Neckarsulm, Kochendorf ~40km west) are available. For Kocher-specific data, HVZ BW is the correct source but exposes no documented public REST API — only a web portal. This creates a scope decision: use available Neckar PEGELONLINE stations for WATR-01, and for WATR-02 either implement HVZ BW scraping or defer Kocher data to a later phase.

The flood hazard WMS (WATR-03) has a split: the statutory ÜSG flood zone layer (HQ100 + formal designations) is publicly accessible via `UIS_0100000003900001`. The full HWGK with HQ10/HQ50/HQextrem inundation zones is documented as requiring UIS state intranet access. The practical approach is to use the ÜSG service for WATR-03 and clearly document what's available vs. intranet-only.

AQI enhancement (WAIR-05) requires replacing the current generic 5-tier scale in `schemas/geojson.py` with the official EEA 6-tier per-pollutant breakpoints, updating the AQILayer heatmap colors, and adding individual sensor color-coding based on their AQI tier.

**Primary recommendation:** Use PEGELONLINE REST API for Neckar stations (WATR-01), implement HVZ BW connector as HTML-scrape (WATR-02), add WMS raster layers directly to MapLibre without backend (WATR-03/04), implement LUBW WFS fetch with PostGIS storage (WATR-05), and update AQI to EEA 6-tier standard.

---

## Standard Stack

### Core (Backend — new connectors)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.28.x | Async HTTP for PEGELONLINE/HVZ REST calls | Already in pyproject.toml |
| pydantic | 2.12.x | Response model validation | Already in pyproject.toml |
| BaseConnector | (project) | fetch/normalize/persist/upsert_feature pattern | All Phase 2+ connectors use this |

### Core (Frontend — new map layers)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react-map-gl/maplibre | 8.x | Source + Layer components for WMS raster layers | Already in use (AQILayer, TransitLayer) |
| MapLibre GL JS | 5.x | `raster` source type for WMS overlays | Native support, no extra lib |

### No New Dependencies Needed
All new backend connectors follow the existing pattern (httpx + pydantic + BaseConnector). All new frontend layers follow the Source/Layer pattern. WMS layers in MapLibre use `type: "raster"` sources — no OGC library needed.

---

## Architecture Patterns

### Pattern 1: New Backend Connector (PEGELONLINE / HVZ BW)

Follows UBAConnector pattern exactly:

```python
# Source: backend/app/connectors/uba.py — follow this structure
class PegelonlineConnector(BaseConnector):
    async def run(self) -> None:
        # 1. Upsert station features (one per station UUID)
        # 2. Fetch current measurements
        # 3. Normalize to Observation(domain="water", values={"level_cm": ...})
        # 4. persist()
        # 5. _update_staleness()
```

Key: `upsert_feature()` is called in `run()`, not in `normalize()`. Feature UUIDs are cached on the connector instance after first upsert.

**Water observation schema** (already in `water_readings` hypertable from migration 001):
```sql
-- Existing table — no migration needed
CREATE TABLE water_readings (
    time    TIMESTAMPTZ NOT NULL,
    feature_id UUID REFERENCES features(id),
    level_cm   FLOAT,
    flow_m3s   FLOAT
);
```

**persist() extension** — `base.py` persist() currently handles `air_quality`, `weather`, `transit` domains. A `water` branch must be added:
```python
elif obs.domain == "water":
    await session.execute(
        text("INSERT INTO water_readings (time, feature_id, level_cm, flow_m3s) "
             "VALUES (:time, :feature_id, :level_cm, :flow_m3s)"),
        {"time": ts, "feature_id": obs.feature_id,
         "level_cm": obs.values.get("level_cm"),
         "flow_m3s": obs.values.get("flow_m3s")},
    )
```

### Pattern 2: PEGELONLINE REST API Call

```python
# Source: PEGELONLINE REST API docs (verified 2026-04-06)
# Base: https://www.pegelonline.wsv.de/webservices/rest-api/v2

# Get station metadata + current measurement for a known UUID:
GET /stations/{uuid}.json?includeTimeseries=true&includeCurrentMeasurement=true

# Get historical measurements (last N days, ISO 8601 duration):
GET /stations/{uuid}/W/measurements.json?start=P90D

# Search stations near a point (radius in km):
GET /stations.json?latitude=48.84&longitude=10.09&radius=50
```

Response format (verified):
```json
{
  "uuid": "be7ce40e-...",
  "shortname": "PLOCHINGEN",
  "water": {"longname": "NECKAR"},
  "latitude": 48.707,
  "longitude": 9.419,
  "timeseries": [{
    "shortname": "W",
    "unit": "cm",
    "currentMeasurement": {
      "timestamp": "2026-04-06T01:30:00+02:00",
      "value": 159.0
    }
  }]
}
```

**CRITICAL FINDING:** PEGELONLINE only covers federal waterways (Bundeswasserstraßen). The Kocher river is a state river managed by Baden-Württemberg and returns **empty results** from PEGELONLINE. The nearest available federal stations are on the Neckar river: Neckarsulm (UUID: lookup required, ~40km from Aalen), Kochendorf, Plochingen.

Verified Neckar stations within 100km of Aalen (48.84°N, 10.09°E): Plochingen, Deizisau, Oberesslingen, Esslingen, Neckarsulm, Kochendorf, Gundelsheim, and others. At runtime, `stations.json?waters=NECKAR` returns the full list.

### Pattern 3: WMS Raster Layer in MapLibre

WMS overlays require no backend connector. They load directly in MapLibre as raster sources:

```typescript
// Source: MapLibre GL JS docs — raster source + layer pattern
// Used for: flood hazard overlay, noise overlay, LUBW layers

<Source
  id="flood-hazard"
  type="raster"
  tiles={[
    "https://rips-gdi.lubw.baden-wuerttemberg.de/arcgis/services/wms/" +
    "UIS_0100000003900001/MapServer/WMSServer?" +
    "SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap" +
    "&LAYERS=0,1&STYLES=&FORMAT=image/png&TRANSPARENT=true" +
    "&CRS=EPSG:3857&BBOX={bbox-epsg-3857}&WIDTH=256&HEIGHT=256"
  ]}
  tileSize={256}
>
  <Layer
    id="flood-hazard-layer"
    type="raster"
    paint={{ "raster-opacity": 0.7 }}
    layout={{ visibility: visible ? "visible" : "none" }}
  />
</Source>
```

**MapLibre WMS URL template note:** Use `{bbox-epsg-3857}` as the BBOX placeholder — MapLibre replaces this automatically. Use `CRS=EPSG:3857` (WMS 1.3.0) or `SRS=EPSG:3857` (WMS 1.1.1).

### Pattern 4: LUBW WFS → Backend Storage

For WATR-05 (nature conservation, water quality zones), the WFS data is static/slow-changing. Fetch as GeoJSON on startup, store in `features` table using `upsert_feature()`:

```python
# WFS GetFeature as GeoJSON:
GET https://rips-gdi.lubw.baden-wuerttemberg.de/arcgis/services/wfs/
    Naturschutzgebiet/MapServer/WFSServer
    ?service=WFS&version=2.0.0&request=GetFeature
    &typeNames=Naturschutzgebiet&outputFormat=application/json
    &BBOX=9.97,48.76,10.22,48.90,EPSG:4326

# Coordinate system note: WFS returns EPSG:25832 by default.
# Request EPSG:4326 via srsName=urn:ogc:def:crs:EPSG::4326
```

### Pattern 5: AQI Enhancement — EU EAQI Scale

Current `schemas/geojson.py` uses 5 generic tiers (0-20-40-60-80-∞). Replace with official EEA 6-tier per-pollutant thresholds:

```python
# Source: EEA European Air Quality Index (verified 2026-04-06)
# https://airindex.eea.europa.eu/AQI/index.html

EAQI_TIERS = [
    ("good",         "#50F0E6"),  # teal
    ("fair",         "#50CCAA"),  # green
    ("moderate",     "#F0E641"),  # yellow
    ("poor",         "#FF5050"),  # red
    ("very_poor",    "#960032"),  # dark red
    ("extremely_poor","#7D2181"), # purple
]

# Per-pollutant breakpoints (µg/m³, upper bounds per tier):
EAQI_BREAKPOINTS = {
    "pm25": [5,   15,   25,   50,  75,  float("inf")],
    "pm10": [10,  20,   50,  100, 150,  float("inf")],
    "no2":  [10,  20,   50,  100, 200,  float("inf")],
    "o3":   [50,  100,  130, 240, 380,  float("inf")],
    "so2":  [100, 200,  350, 500, 750,  float("inf")],
}

def eaqi_from_readings(pm25, pm10, no2, o3, so2=None) -> tuple[int, str, str]:
    """Return (tier_index 0-5, label, hex_color) as max over all pollutants."""
    # For each pollutant with a value, find which tier it falls in
    # Overall EAQI = max tier index across all pollutants
```

**Frontend color update:** AQILayer.tsx heatmap gradient should use the 6 EEA colors. Individual sensor circles should be colored by their `aqi_color` property (already injected by layers.py).

### Anti-Patterns to Avoid

- **Don't try to use PEGELONLINE for Kocher/Jagst/Lein:** These are state rivers, not in PEGELONLINE. Runtime queries return empty arrays.
- **Don't load WFS features as live GeoJSON from frontend:** LUBW WFS has EPSG:25832 by default and no CORS headers — proxy through backend or transform server-side.
- **Don't hold SQLAlchemy sessions at class level:** BaseConnector pattern creates fresh session per `persist()` call — required for APScheduler job isolation (existing Pitfall 8 in codebase).
- **Don't call `persist()` in `normalize()`:** Self._feature_id must be set in `run()` via `upsert_feature()` before `normalize()` is called (UBAConnector pattern).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| WMS tile serving | Custom tile proxy | MapLibre raster source with WMS URL template | MapLibre has built-in WMS support via `{bbox-epsg-3857}` |
| AQI color calculation | Custom color algorithm | EEA EAQI thresholds (constants in geojson.py) | Official EU standard; WHO-aligned thresholds |
| Water station upsert | Custom SQL | BaseConnector.upsert_feature() | Already handles ON CONFLICT for (town_id, domain, source_id) |
| Water timeseries | New table | Existing `water_readings` hypertable (migration 001) | Already created with 5-year retention |
| WFS parsing | Custom XML parser | httpx fetch with `outputFormat=application/json` | WFS 2.0 supports GeoJSON output |

---

## Confirmed API Endpoints

### PEGELONLINE REST API (HIGH confidence — live verified)

| Endpoint | Purpose |
|----------|---------|
| `https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations.json?waters=NECKAR&includeTimeseries=true&includeCurrentMeasurement=true` | All Neckar stations with current water level |
| `https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations/{uuid}/W/measurements.json?start=P90D` | 90-day history for a station |
| `https://www.pegelonline.wsv.de/webservices/gis/aktuell/wfs?service=wfs&version=1.1.0&request=GetFeature&typeName=gk:waterlevels&outputFormat=application/json` | All federal gauge stations as GeoJSON (for initial feature seeding) |

Auth: None. License: DL-DE-Zero-2.0.

### LUBW WMS — Flood Zones (MEDIUM confidence — GetCapabilities verified)

| Service ID | URL | Layers | Content |
|------------|-----|--------|---------|
| `UIS_0100000003900001` | `https://rips-gdi.lubw.baden-wuerttemberg.de/arcgis/services/wms/UIS_0100000003900001/MapServer/WMSServer` | `0` = HQ100, `1` = ÜSG | Public WMS, no auth |

**Note on HQ10/HQextrem:** LUBW documentation states these are "WMS Dienste im UIS-Landesintranet" (state intranet only). Only HQ100 + statutory ÜSG designations are publicly available. WATR-03 scope must acknowledge this limitation.

### EBA Railway Noise WMS (HIGH confidence — GetCapabilities verified)

| Service | URL | Key Layers |
|---------|-----|-----------|
| Isophonen | `https://geoinformation.eisenbahn-bundesamt.de/wms/isophonen` | `isophonen_ek_lden` (Lden nationwide), `isophonen_ek_lnight` (Lnight nationwide) |

Auth: None. INSPIRE-compliant.

### LUBW WFS — Environmental Layers (MEDIUM confidence — GetCapabilities verified)

| Feature Type | URL | Output |
|-------------|-----|--------|
| Naturschutzgebiet | `https://rips-gdi.lubw.baden-wuerttemberg.de/arcgis/services/wfs/Naturschutzgebiet/MapServer/WFSServer` | GeoJSON supported |
| Wasserschutzgebiet | `https://rips-gdi.lubw.baden-wuerttemberg.de/arcgis/services/wfs/Wasserschutzgebiet/MapServer/WFSServer` | GeoJSON supported |

Auth: None. Coordinate system: EPSG:25832 (request EPSG:4326 via `srsName`). Bbox filtering supported.

### HVZ BW — State Water Levels (LOW confidence — no public API confirmed)

URL: `https://hvz.lubw.baden-wuerttemberg.de/` — web portal only. No documented REST API or JSON endpoint. Kocher river data is here but not machine-readable via a stable endpoint.

**Options for WATR-02:**
1. HTML scraping of `https://www.hvz.baden-wuerttemberg.de/overview.html` (fragile, not recommended for production)
2. PEGELONLINE WFS has no Kocher stations — confirmed by live query
3. Scope WATR-02 as "show available PEGELONLINE stations near Aalen" and note Kocher is state-managed

---

## EU Air Quality Index — Official Breakpoints (HIGH confidence — EEA verified)

```
Tier 0 Good          : PM2.5 ≤5,  PM10 ≤10, NO2 ≤10, O3 ≤50  — color #50F0E6 (teal)
Tier 1 Fair          : PM2.5 ≤15, PM10 ≤20, NO2 ≤20, O3 ≤100 — color #50CCAA (green)
Tier 2 Moderate      : PM2.5 ≤25, PM10 ≤50, NO2 ≤50, O3 ≤130 — color #F0E641 (yellow)
Tier 3 Poor          : PM2.5 ≤50, PM10 ≤100,NO2 ≤100,O3 ≤240 — color #FF5050 (red)
Tier 4 Very Poor     : PM2.5 ≤75, PM10 ≤150,NO2 ≤200,O3 ≤380 — color #960032 (dark red)
Tier 5 Extremely Poor: PM2.5 >75, PM10 >150,NO2 >200,O3 >380 — color #7D2181 (purple)
```

Overall EAQI = max tier index across all measured pollutants (EU methodology: worst pollutant wins).

The existing `AQI_TIERS` in `schemas/geojson.py` is a simplified single-dimensional scale (0-20-40-60-80). This must be replaced with the per-pollutant EAQI calculation. The `aqi_tier()` function needs to accept individual pollutant values, not a single composite score.

---

## Common Pitfalls

### Pitfall 1: PEGELONLINE Returns Empty for State Rivers
**What goes wrong:** Query PEGELONLINE for Kocher stations — empty array returned, connector silently produces no observations.
**Why it happens:** PEGELONLINE covers federal waterways (WSV) only. Kocher/Jagst/Rems are state rivers (Baden-Württemberg).
**How to avoid:** Seed connector config with specific Neckar station UUIDs. Use `?waters=NECKAR` to enumerate available stations at connector startup.
**Warning signs:** `stations.json?radius=50` around Aalen returns zero results — this is expected, not a bug.

### Pitfall 2: WMS BBOX Projection Mismatch
**What goes wrong:** MapLibre sends tiles in EPSG:3857 (Web Mercator), but WMS request uses wrong CRS parameter.
**Why it happens:** WMS 1.3.0 uses `CRS=`, WMS 1.1.x uses `SRS=`. LUBW services are EPSG:25832 native.
**How to avoid:** Use `CRS=EPSG:3857` in WMS 1.3.0 URL template. MapLibre's `{bbox-epsg-3857}` placeholder is in EPSG:3857 coordinates. Test with `GetMap` request before building layer component.
**Warning signs:** Tiles load but geography is completely wrong (Europe in wrong position).

### Pitfall 3: LUBW WFS Returns EPSG:25832 by Default
**What goes wrong:** WFS GetFeature returns features in UTM Zone 32N (meters), not WGS84 (degrees). upsert_feature() expects WKT in SRID 4326.
**Why it happens:** LUBW WFS native CRS is EPSG:25832. Default output does not reproject.
**How to avoid:** Add `srsName=urn:ogc:def:crs:EPSG::4326` to WFS GetFeature request. Or use PostGIS `ST_Transform` in upsert SQL if reprojection is needed server-side.
**Warning signs:** Features stored with coordinates in the millions (meters, not degrees).

### Pitfall 4: persist() Has No "water" Branch
**What goes wrong:** `Observation(domain="water", ...)` is passed to `persist()`, but `base.py` only handles `air_quality`, `weather`, `transit`. Water observations are silently dropped.
**Why it happens:** `persist()` uses if/elif — unmatched domains are no-ops.
**How to avoid:** Add `elif obs.domain == "water":` branch to `persist()` in `base.py` before writing PegelonlineConnector.
**Warning signs:** Connector runs without error but `water_readings` table stays empty.

### Pitfall 5: Historical AQI Query Range for UBA
**What goes wrong:** UBAConnector's `fetch()` only requests today's data (`date_from=today&date_to=today`). 90-day backfill requires a separate one-time or range-aware fetch.
**Why it happens:** Current UBAConnector design is incremental, not backfill-aware.
**How to avoid:** WAIR-06 can be satisfied by the existing hypertable accumulating data over time. For the 90-day view to work from day one, add a backfill method to UBAConnector that fetches `date_from=today-90d&date_to=today` on first run (no existing data in table).
**Warning signs:** Historical chart shows only recent days even though 90 days requested.

### Pitfall 6: AQI Color Scale Not Updated in Both Layers.py and AQILayer.tsx
**What goes wrong:** Backend `aqi_tier()` updated to EAQI colors, but AQILayer.tsx heatmap gradient still uses old 5-color hardcoded array. Colors are inconsistent between hover popup and heatmap.
**Why it happens:** AQI color appears in two places: backend (`schemas/geojson.py` → `aqi_color` property in features) and frontend (`AQILayer.tsx` heatmap paint expression).
**How to avoid:** Update both simultaneously. Consider passing `aqi_color` from GeoJSON properties into the circle layer paint to unify color source.

### Pitfall 7: WMS Opacity and Visibility Toggle
**What goes wrong:** WMS raster layer toggled off in sidebar but tiles still visible, or opacity control missing.
**Why it happens:** MapLibre raster layers use `layout.visibility` like vector layers, but opacity is `paint.raster-opacity` not a layout property.
**How to avoid:** Use `layout={{ visibility: visible ? "visible" : "none" }}` and set `paint={{ "raster-opacity": 0.65 }}` as default. Follow AQILayer.tsx visibility pattern exactly.

---

## Existing Codebase — What Already Works

| Component | Location | Role in Phase 6 |
|-----------|----------|-----------------|
| `water_readings` hypertable | migration 001 | Already created — no new migration needed for water time-series |
| `upsert_feature()` | base.py | Used by PEGELONLINE connector to register station points |
| `AQI_TIERS` / `aqi_tier()` | schemas/geojson.py | Must be replaced with EAQI per-pollutant breakpoints |
| `CONNECTOR_ATTRIBUTION` dict | schemas/geojson.py | Add `PegelonlineConnector` and `LUBWConnector` entries |
| `VALID_DOMAINS` | schemas/geojson.py | Already includes `"water"` |
| `layers.py` generic branch | routers/layers.py | Water domain falls into generic branch (features + no reading join). A lateral join to `water_readings` must be added for water domain. |
| `useLayerData` hook | hooks/useLayerData.ts | Used as-is for water domain frontend |
| `Sidebar.tsx` layerVisibility | components/sidebar/Sidebar.tsx | Must extend interface to include water, flood, noise, environment booleans |
| `MapView.tsx` | components/map/MapView.tsx | Must add new layer components + extend layerVisibility prop |

**layers.py water domain gap:** The generic SQL branch returns only feature geometry + properties, but for water domain we also want current level. The `air_quality` branch uses a `LATERAL JOIN` to get latest reading. Water domain needs the same pattern added.

---

## Environment Availability Audit

All dependencies are already present in the project (httpx, pydantic, FastAPI). No new runtime tools required for backend connectors. Frontend WMS layers use MapLibre raster source — built-in capability.

External services are public REST/WMS/WFS endpoints — no local installation needed.

| Dependency | Required By | Available | Notes |
|------------|------------|-----------|-------|
| httpx | PEGELONLINE connector | ✓ (in pyproject.toml) | Already used by all connectors |
| PEGELONLINE REST API | WATR-01 | ✓ (verified live) | Free, no auth |
| LUBW WMS rips-gdi | WATR-03 | ✓ (GetCapabilities verified) | Public WMS |
| EBA WMS isophonen | WATR-04 | ✓ (GetCapabilities verified) | Public WMS |
| LUBW WFS rips-gdi | WATR-05 | ✓ (GetCapabilities verified) | Public WFS |
| HVZ BW machine API | WATR-02 | ✗ (no public API found) | Web portal only — scraping or descope |

**Missing dependencies with fallback:**
- HVZ BW (WATR-02): No public API. Fallback = use PEGELONLINE Neckar stations for WATR-01 and note WATR-02 requires either scraping or deferral. Recommend: implement PegelonlineConnector using Neckar stations and label WATR-02 as partially addressed (proximity water data available, Kocher-specific deferred).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x + pytest-asyncio 1.3.x |
| Config file | `backend/pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `cd backend && python -m pytest tests/test_connector.py tests/test_api_layers.py -x -q` |
| Full suite command | `cd backend && python -m pytest -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WAIR-05 | eaqi_from_readings returns correct tier + color for known inputs | unit | `pytest tests/test_aqi.py -x` | ❌ Wave 0 |
| WAIR-05 | layers.py air_quality injects eaqi_color per sensor | unit | `pytest tests/test_api_layers.py::test_layers_air_quality_properties -x` | ✅ (extend) |
| WAIR-06 | UBA backfill fetches date range on empty table | unit (mock) | `pytest tests/connectors/test_uba_backfill.py -x` | ❌ Wave 0 |
| WATR-01 | PegelonlineConnector.normalize() produces water domain Observations | unit | `pytest tests/connectors/test_pegelonline.py -x` | ❌ Wave 0 |
| WATR-01 | water layer returns GeoJSON with level_cm property | unit | `pytest tests/test_api_layers.py::test_layers_water -x` | ❌ Wave 0 |
| WATR-03 | WMS flood layer renders visible in MapLibre | visual/manual | Manual browser check | manual |
| WATR-04 | WMS noise layer renders visible in MapLibre | visual/manual | Manual browser check | manual |
| WATR-05 | LUBWWfsConnector stores Naturschutzgebiet polygons in features | unit (mock) | `pytest tests/connectors/test_lubw_wfs.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_connector.py tests/test_api_layers.py -x -q`
- **Per wave merge:** `cd backend && python -m pytest -x -q`
- **Phase gate:** Full backend suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_aqi.py` — EAQI calculation unit tests covering all 6 tiers + max-over-pollutants logic
- [ ] `backend/tests/connectors/test_pegelonline.py` — PegelonlineConnector.normalize() unit test with fixture data
- [ ] `backend/tests/connectors/test_uba_backfill.py` — UBA backfill date range logic (if backfill implemented)
- [ ] `backend/tests/connectors/test_lubw_wfs.py` — LUBWWfsConnector unit test with mocked WFS response
- [ ] `backend/tests/test_api_layers.py` — extend with `test_layers_water` test case

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Hardcoded AQI scale (5 tiers, arbitrary thresholds) | EEA EAQI per-pollutant 6-tier official standard | Colors match European AQI maps; WHO-aligned |
| Custom river data scraping | PEGELONLINE REST API (official WSV service) | Free, stable, DL-DE-Zero-2.0 license |
| Building custom tile server for static overlays | WMS raster source in MapLibre directly | Zero backend infrastructure for static government data |

---

## Open Questions

1. **WATR-02 — Kocher/HVZ BW machine-readable access**
   - What we know: HVZ BW provides Kocher gauge data via a web portal (hvz.lubw.baden-wuerttemberg.de). No REST API documented.
   - What's unclear: Whether LUBW provides any undocumented JSON API for gauge data, or whether the data can be extracted from the page's JavaScript data structures.
   - Recommendation: Plan should implement WATR-01 using PEGELONLINE Neckar stations, and scope WATR-02 as "best-effort": attempt HVZ BW page JSON extraction at implementation time; if not feasible without scraping, document as deferred and provide Neckar data as proxy.

2. **WATR-03 — HQ10/HQextrem flood layers access**
   - What we know: LUBW documentation explicitly states HWGK HQ10/HQ50/HQextrem WMS is in the state intranet (UIS-Landesintranet). Public WMS `UIS_0100000003900001` has HQ100 + ÜSG layers only.
   - What's unclear: Whether an unauthenticated public WMS for HWGK exists that we haven't found, or whether the public UDO web app proxies it.
   - Recommendation: Plan for ÜSG (statutory flood zones, publicly available WMS) as the deliverable for WATR-03. Label as "HQ100 flood zone overlay" and document that HQ10/HQextrem are intranet-restricted.

3. **UBA 90-day backfill strategy (WAIR-06)**
   - What we know: UBA API supports `date_from`/`date_to` for arbitrary date ranges. Current connector fetches only today.
   - What's unclear: Whether backfill should be a one-time startup behavior, a separate admin endpoint, or just "wait 90 days."
   - Recommendation: Add backfill logic to UBAConnector.run() — on first run (empty table for station), fetch last 90 days. Subsequent runs are incremental (today only). Mirror for SensorCommunityConnector.

4. **LUBW road noise WMS — exact service ID**
   - What we know: LUBW provides noise maps (Lärmkartierung 2022 road noise). WMS URL structure follows `rips-gdi.lubw.baden-wuerttemberg.de/arcgis/services/wms/UIS_XXXXXXXXXX/MapServer/WMSServer`. The road noise service ID was not confirmed.
   - What's unclear: The specific UIS service ID for Straßenverkehrslärm (road noise) WMS.
   - Recommendation: Plan task to probe `rips-metadaten.lubw.de` for the road noise WMS service ID, or use EBA railway noise (fully confirmed) as the WATR-04 deliverable and document road noise as pending.

---

## Sources

### Primary (HIGH confidence)
- PEGELONLINE REST API docs — https://www.pegelonline.wsv.de/webservice/dokuRestapi — verified endpoints, response format
- PEGELONLINE WFS GetCapabilities — https://www.pegelonline.wsv.de/webservices/gis/aktuell/wfs — confirmed feature type `gk:waterlevels`, JSON output
- EEA European Air Quality Index — https://airindex.eea.europa.eu/AQI/index.html — official EAQI 6-tier per-pollutant breakpoints
- EBA WMS isophonen GetCapabilities — https://geoinformation.eisenbahn-bundesamt.de/wms/isophonen — confirmed layer names
- Existing project codebase — base.py, uba.py, weather.py, schemas/geojson.py, layers.py

### Secondary (MEDIUM confidence)
- LUBW WMS UIS_0100000003900001 GetCapabilities — `rips-gdi.lubw.baden-wuerttemberg.de` — HQ100 + ÜSG confirmed
- LUBW WFS Naturschutzgebiet/Wasserschutzgebiet GetCapabilities — confirmed GeoJSON output format
- LUBW metadata portal — https://rips-metadaten.lubw.de/ — WFS descriptions and access terms

### Tertiary (LOW confidence)
- HVZ BW machine API — no public API confirmed; web portal only (hvz.lubw.baden-wuerttemberg.de)
- LUBW road noise WMS service ID — not confirmed, probe required at implementation time

---

## Metadata

**Confidence breakdown:**
- PEGELONLINE REST API: HIGH — live API verified, docs confirmed
- PEGELONLINE Kocher limitation: HIGH — verified empty result from live API query
- LUBW WMS flood layers: MEDIUM — GetCapabilities verified but HQ10/HQextrem intranet restriction is based on metadata docs
- EBA noise WMS: HIGH — GetCapabilities verified, layer names confirmed
- LUBW WFS layers: MEDIUM — GetCapabilities verified, GeoJSON output confirmed
- EAQI breakpoints: HIGH — official EEA source
- HVZ BW API: LOW — no API found, web portal only
- LUBW road noise WMS ID: LOW — not confirmed

**Research date:** 2026-04-06
**Valid until:** 2026-07-06 (90 days; APIs are stable government services)
