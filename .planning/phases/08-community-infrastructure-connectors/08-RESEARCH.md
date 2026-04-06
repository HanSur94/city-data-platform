# Phase 8: Community & Infrastructure Connectors - Research

**Researched:** 2026-04-06
**Domain:** OSM Overpass API (POIs), Bundesnetzagentur Ladesäulenregister (EV charging CSV), Energieatlas BW / LUBW solar WMS, GOA Ostalbkreis waste calendar
**Confidence:** MEDIUM-HIGH (data sources verified; solar WMS endpoint not resolved to exact URL)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Data Sources & Scope**
- Waste collection: Overpass API (OSM) for Wertstoffhof locations + iCal feed from Aalen GWA for pickup schedules if available
- Schools/healthcare/parks: Overpass API with amenity tags — schools (amenity=school/kindergarten), healthcare (amenity=pharmacy/hospital/doctors), parks (leisure=park/playground/sports_centre)
- Construction sites/roadworks: Autobahn API (already Phase 7) for Autobahn + OSM construction notes for local roadworks — no Aalen-specific construction API available
- EV charging: Bundesnetzagentur Ladesäulenregister CSV (open data, updated monthly) — official German EV charging registry

**Map Layer Organization & Presentation**
- Two new sidebar groups: "Gemeinwesen" (Community: waste, schools, healthcare, parks) and "Infrastruktur" (Infrastructure: roadworks, EV charging, solar)
- Icon strategy: colored circles with category-specific colors — Schools=blue, Healthcare=red, Parks=green, Waste=brown, EV=purple. Consistent with existing layer pattern
- Solar potential: WMS overlay from Energieatlas BW if available; if no WMS endpoint found, defer to Phase 9
- MaStR solar distinction: Phase 7 EnergyLayer already renders with yellow/amber icons — solar potential raster overlays underneath

**Popup Content & Dashboard**
- Community POI popups: name, address, category, opening hours (where available), distance from map center. German labels
- EV charging popup: operator, address, plug types (CCS/Type2/CHAdeMO), max power kW, number of points, status if available
- No new KPI tiles — these are spatial/POI layers, not time-series. Add a "Community" count summary in existing dashboard area
- Waste collection popup: next pickup date per waste type (Restmüll, Biomüll, Papier, Gelber Sack) if iCal feed available, otherwise Wertstoffhof hours

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
| COMM-01 | Waste collection schedules and recycling locations/Wertstoffhöfe on map | Overpass API amenity=recycling + OSM waste_disposal tags; GOA Ostalbkreis has no public iCal API — feature-only connector |
| COMM-02 | Schools and childcare (Kita/Schule) — locations, types on map | Overpass API amenity=school,kindergarten confirmed working in Aalen bbox (313 total POIs across all categories) |
| COMM-03 | Healthcare facilities — doctors, pharmacies, hospitals, emergency services on map | Overpass API amenity=pharmacy,hospital,doctors,clinic,dentist confirmed working |
| COMM-04 | Public spaces — parks, playgrounds, sports facilities on map | Overpass API leisure=park,playground,sports_centre confirmed working |
| INFR-01 | Active construction sites and roadworks with detour info | OSM highway=construction Overpass query for local roads; Autobahn API already handles Autobahn (Phase 7) |
| INFR-02 | EV charging stations on map (Bundesnetzagentur Ladesäulenregister) | CSV confirmed at data.bundesnetzagentur.de, columns verified: Breitengrad/Längengrad/Betreiber/Steckertypen1-4/Anschlussleistung/Anzahl Ladepunkte |
| INFR-03 | Roof solar potential map (where available from BW/municipal data) | LUBW WMS exists (metadata confirmed) but exact GetCapabilities URL not resolved — conditional implementation with graceful fallback |
| INFR-04 | Existing solar installations on buildings (from MaStR registry) | MaStR EnergyLayer already renders solar_rooftop/solar_ground in Phase 7 — INFR-04 is display-only, achieved by EnergyLayer filter/style extension |
</phase_requirements>

---

## Summary

Phase 8 adds seven new data connectors and two new frontend layer groups to the city data platform. All community POI data (schools, healthcare, parks, waste locations, roadworks) comes from OpenStreetMap via the Overpass API — a well-established pattern with no auth and a free public endpoint. EV charging data comes from the Bundesnetzagentur Ladesäulenregister, a monthly-updated CSV (~43 MB) with confirmed column structure. Solar potential (INFR-03) requires a LUBW WMS raster overlay whose GetCapabilities URL is referenced in metadata catalogs but not resolvable to a working URL through public web research — implementation should attempt the known RIPS-GDI pattern and defer gracefully if unavailable.

The most significant architectural decision is that all new POI layers use the **features-only connector pattern** (like MastrConnector/LubwWfsConnector): `run()` calls `upsert_feature()`, `normalize()` returns `[]`, and no hypertable writes occur. The frontend follows the EnergyLayer template: `useLayerData(domain, town)` → GeoJSON Source → circle Layer with `match` expression for color-coding → domain popup component. Two new domain keys (`community` and `infrastructure`) must be registered in `VALID_DOMAINS` and `CONNECTOR_ATTRIBUTION`, and new query branches added to `layers.py`.

The GOA Ostalbkreis waste management service (for pickup schedules) does not expose a public iCal or API — a third-party CalDAV service that previously bridged this existed but is no longer reachable. The connector scope for COMM-01 is therefore Wertstoffhof locations via Overpass (amenity=recycling), stored as features without pickup schedule data.

**Primary recommendation:** Use the LubwWfsConnector/MastrConnector features-only pattern for all new connectors; follow EnergyLayer/EnergyPopup as the frontend template.

---

## Standard Stack

### Core (inherited from project — no new additions)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.28.x | Async HTTP — Overpass API, BNetzA CSV download | Already in pyproject.toml |
| Pydantic | 2.x | Response validation for Overpass JSON | Already in pyproject.toml |
| shapely | 2.x | Centroid calculation for polygon OSM features | Already in pyproject.toml |
| react-map-gl/maplibre | 8.x | MapLibre React bindings | Already in frontend |
| BaseConnector | — | Features-only connector base class | Established pattern |

### New Python Dependency
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| icalendar | 6.x | Parse iCal feeds | Only needed if an iCal feed URL is found for GOA; currently not required |

Note: `icalendar` is already available in the project Python environment (v6.3.1) but is NOT in `pyproject.toml`. Do not add it unless the GOA iCal feed is confirmed reachable — per current research, it is not.

### Installation
No new backend packages required for the confirmed scope.

---

## Data Source Reference

### Overpass API

- **Endpoint:** `https://overpass-api.de/api/interpreter` (free, no auth, public)
- **Method:** HTTP POST with `data=<query>` body (or GET with `?data=`)
- **Format:** `[out:json][timeout:25]` — returns JSON with `elements[]` array
- **Rate limit:** ~10,000 requests/day per IP; use bbox filtering to minimize data
- **Aalen bbox:** `48.76,9.97,48.90,10.22` (lat_min,lon_min,lat_max,lon_max)
- **License:** ODbL (OpenStreetMap) — attribution required

**Query pattern for Aalen POIs (verified — returned 313 elements for schools+healthcare combined):**
```
[out:json][timeout:25];
(
  node["amenity"~"school|kindergarten|pharmacy|hospital|doctors|clinic"](48.76,9.97,48.90,10.22);
  way["amenity"~"school|kindergarten|pharmacy|hospital|doctors|clinic"](48.76,9.97,48.90,10.22);
);
out center;
```

Key: `out center` returns the centroid of way/relation geometries — avoids needing shapely for polygons.

**Tags per domain:**

| Domain | Overpass Tags |
|--------|--------------|
| Schools (COMM-02) | `amenity=school`, `amenity=kindergarten` |
| Healthcare (COMM-03) | `amenity=pharmacy`, `amenity=hospital`, `amenity=doctors`, `amenity=clinic`, `amenity=dentist` |
| Parks (COMM-04) | `leisure=park`, `leisure=playground`, `leisure=sports_centre`, `leisure=pitch` |
| Wertstoffhöfe (COMM-01) | `amenity=recycling`, `amenity=waste_disposal` (filter for manned collection points) |
| Roadworks (INFR-01) | `highway=construction` |

**Properties available per feature:**
- `tags.name` — facility name
- `tags["addr:street"]`, `tags["addr:housenumber"]`, `tags["addr:city"]`, `tags["addr:postcode"]`
- `tags.opening_hours` — present for pharmacies/doctors, sparse for schools
- `tags.amenity` or `tags.leisure` — category discriminator
- `lat`/`lon` for nodes; `center.lat`/`center.lon` for ways

### Bundesnetzagentur Ladesäulenregister (INFR-02)

- **Download URL pattern:** `https://data.bundesnetzagentur.de/Bundesnetzagentur/DE/Fachthemen/ElektrizitaetundGas/E-Mobilitaet/Ladesaeulenregister_BNetzA_{YYYY-MM-DD}.csv`
- **Latest verified URL:** `https://data.bundesnetzagentur.de/Bundesnetzagentur/DE/Fachthemen/ElektrizitaetundGas/E-Mobilitaet/Ladesaeulenregister_BNetzA_2026-03-25.csv`
- **File size:** ~43 MB
- **Update frequency:** Monthly
- **License:** CC BY 4.0 (Bundesnetzagentur open data) — confirmed from BNetzA E-Mobility page
- **Encoding:** UTF-8
- **Separator:** Semicolon (`;`)
- **Decimal separator:** Comma (`,`) — e.g., `11,5` for 11.5 kW

**Verified column names:**
| Column | Content |
|--------|---------|
| `Betreiber` | Operator name |
| `Straße` | Street address |
| `Hausnummer` | House number |
| `Adresszusatz` | Address supplement |
| `Postleitzahl` | Postal code |
| `Ort` | City |
| `Bundesland` | Federal state |
| `Kreis/kreisfreie Stadt` | District |
| `Breitengrad` | Latitude (EPSG:4326, comma decimal) |
| `Längengrad` | Longitude (EPSG:4326, comma decimal) |
| `Inbetriebnahmedatum` | Commissioning date |
| `Anschlussleistung` | Connection power (kW, comma decimal) |
| `Art der Ladeeinrichtung` | Type (Normalladen/Schnellladen) |
| `Anzahl Ladepunkte` | Number of charging points |
| `Steckertypen1` | Plug type 1 (e.g., "Typ2", "CCS", "CHAdeMO") |
| `P1 [kW]` | Power for plug 1 |
| `Steckertypen2` | Plug type 2 |
| `P2 [kW]` | Power for plug 2 |
| `Steckertypen3` | Plug type 3 |
| `P3 [kW]` | Power for plug 3 |
| `Steckertypen4` | Plug type 4 |
| `P4 [kW]` | Power for plug 4 |

**Filtering for Aalen (Ostalbkreis):** Filter `Kreis/kreisfreie Stadt == "Ostalbkreis"` after loading the full CSV. This avoids the need to download a filtered version.

**Coordinate parsing:** `float(row["Breitengrad"].replace(",", "."))` — the comma decimal must be normalized before float conversion.

**Download strategy:** Like MastrConnector, cache the CSV locally with a 24-hour mtime check. The file is 43 MB; re-downloading on every poll_interval would be wasteful. Cache in `/tmp/ladesaeulenregister.csv` or a configurable path.

### GOA Ostalbkreis Waste Calendar (COMM-01)

- **Provider:** GOA (Gesellschaft im Ostalbkreis zur Abfallbewirtschaftung mbH)
- **Website:** https://www.goa-online.de/leistungen/abfuhrkalender/
- **iCal API:** None confirmed. The GOA offers an online calendar tool requiring street-level input — no programmatic endpoint documented. A third-party CalDAV bridge (dav.datenschleuder.com) previously existed but is now unreachable (ECONNREFUSED).
- **Consequence:** COMM-01 scope is Wertstoffhof locations via Overpass only. Pickup schedule data cannot be retrieved automatically. Popup shows Wertstoffhof hours from OSM `opening_hours` tag where available; no pickup calendar dates.

### LUBW Solar Potential WMS (INFR-03)

- **Metadata record:** Two records exist in LUBW RIPS metadata system:
  - `https://rips-metadaten.lubw.de/trefferanzeige?docuuid=43579f76-a2fb-4b5c-9db4-e9e11bcfb3df` — "WMS Photovoltaik Dachfläche (Potenzial)"
  - `https://rips-metadaten.lubw.de/trefferanzeige?docuuid=6d21c3ec-e6ec-4762-a11c-b64ca2b03938` — "Dach-Photovoltaik (Potenzial)"
- **GetCapabilities URL:** Not confirmed. The metadata page returns "Keine Detailinformationen verfügbar". The RIPS-GDI pattern used for other LUBW WMS is `https://rips-gdi.lubw.baden-wuerttemberg.de/arcgis/services/{service}/MapServer/WMSServer?REQUEST=GetCapabilities&SERVICE=WMS`, but the service name for solar potential was not found in public search results.
- **Data access:** The Energieatlas BW portal at `https://www.energieatlas-bw.de/sonne/dachflachen/solarpotenzial-auf-dachflachen` renders this data interactively, suggesting an underlying tile service, but the URL is not public documentation.
- **License:** "Bedingungen der Nutzungsvereinbarung für Daten des UIS" — the UIS usage terms require attribution to LUBW.
- **Implementation strategy:** Attempt `https://rips-gdi.lubw.baden-wuerttemberg.de/arcgis/services/wms/UIS_0100000003700001/MapServer/WMSServer` as a candidate (similar pattern to existing `UIS_0100000003900001` used for flood hazard in WmsOverlayLayer). If no valid solar layer found, the WmsOverlayLayer for solar is skipped and INFR-03 is conditionally deferred.

### MaStR INFR-04 (existing Phase 7 EnergyLayer)

INFR-04 ("Existing solar installations on buildings") is already addressed by the Phase 7 EnergyLayer (MaStR data). The `solar_rooftop` classification via `_classify_installation()` in `mastr.py` already produces the correct feature type. INFR-04 requires only that the EnergyLayer visually distinguishes `solar_rooftop` features — which the existing `match` expression in EnergyLayer already does with amber/yellow circles. No new connector needed. The sidebar may need a brief callout in the Energie group noting this.

---

## Architecture Patterns

### Connector Pattern: Features-Only (use for all Phase 8 connectors)

All Phase 8 connectors follow the LubwWfsConnector / MastrConnector pattern:
- Override `run()` — do NOT use the default fetch→normalize→persist pipeline
- `normalize()` returns `[]` (satisfies ABC)
- `run()` calls `upsert_feature()` for each POI, then `_update_staleness()`
- No hypertable writes (features table only)

```python
# Source: established pattern from backend/app/connectors/lubw_wfs.py

class OverpassCommunityConnector(BaseConnector):
    async def fetch(self) -> dict:
        bbox = self.town.bbox
        # Overpass bbox: lat_min,lon_min,lat_max,lon_max
        bbox_str = f"{bbox.lat_min},{bbox.lon_min},{bbox.lat_max},{bbox.lon_max}"
        query = f"""
        [out:json][timeout:25];
        (
          node["amenity"~"school|kindergarten"](bbox:{bbox_str});
          way["amenity"~"school|kindergarten"](bbox:{bbox_str});
        );
        out center;
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": query},
            )
            resp.raise_for_status()
            return resp.json()

    def normalize(self, raw: Any) -> list[Observation]:
        return []

    async def run(self) -> None:
        raw = await self.fetch()
        for element in raw.get("elements", []):
            tags = element.get("tags", {})
            # Use center for ways, direct for nodes
            lat = element.get("lat") or (element.get("center") or {}).get("lat")
            lon = element.get("lon") or (element.get("center") or {}).get("lon")
            if lat is None or lon is None:
                continue
            source_id = f"osm:{element['type']}:{element['id']}"
            await self.upsert_feature(
                source_id=source_id,
                domain="community",
                geometry_wkt=f"POINT({lon} {lat})",
                properties={
                    "name": tags.get("name", ""),
                    "amenity": tags.get("amenity", ""),
                    "address": f"{tags.get('addr:street', '')} {tags.get('addr:housenumber', '')}".strip(),
                    "opening_hours": tags.get("opening_hours", ""),
                    "category": "school",
                },
            )
        await self._update_staleness()
```

### New Domain Keys Required

Two new domain strings must be added to the backend:

1. `"community"` — covers schools, healthcare, parks, waste locations (COMM-01 through COMM-04)
2. `"infrastructure"` — covers EV charging, roadworks, solar (INFR-01, INFR-02, INFR-03)

**Files to update:**
- `backend/app/schemas/geojson.py` — add `"community"` and `"infrastructure"` to `VALID_DOMAINS` frozenset; add new entries to `CONNECTOR_ATTRIBUTION`
- `backend/app/routers/layers.py` — add `elif domain in ("community", "infrastructure"):` query branch (plain features, no reading join — same as generic `else` branch but explicit for clarity)

### Frontend Layer Pattern

Follow EnergyLayer.tsx exactly — the pattern is mature:

```typescript
// Pattern: useLayerData → GeoJSON Source → filtered circle layers with match expression
// Source: frontend/components/map/EnergyLayer.tsx

export default function CommunityLayer({ town, visible, category }: CommunityLayerProps) {
  const { data } = useLayerData('community', town);
  if (!visible || !data) return null;
  // Filter GeoJSON client-side by category property
  const filtered = {
    ...data,
    features: data.features.filter(f => f.properties?.category === category),
  };
  return (
    <Source id={`community-${category}`} type="geojson" data={filtered} cluster={true} clusterMaxZoom={12}>
      <Layer id={`community-${category}-clusters`} type="circle" source={`community-${category}`}
        filter={['has', 'point_count']}
        paint={{ 'circle-color': CATEGORY_COLORS[category], 'circle-radius': 14 }} />
      <Layer id={`community-${category}-points`} type="circle" source={`community-${category}`}
        filter={['!', ['has', 'point_count']]}
        paint={{ 'circle-color': CATEGORY_COLORS[category], 'circle-radius': 7,
                 'circle-stroke-width': 1, 'circle-stroke-color': '#ffffff' }} />
    </Source>
  );
}
```

**Color mapping (from CONTEXT.md decisions):**
```typescript
const CATEGORY_COLORS: Record<string, string> = {
  school: '#3b82f6',      // blue
  healthcare: '#ef4444',  // red
  park: '#22c55e',        // green
  waste: '#92400e',       // brown
  ev_charging: '#a855f7', // purple
};
```

### Sidebar Extension Pattern

The existing Sidebar.tsx follows a repeating group pattern. Add two new Separator + group blocks after the existing "Energie" group:

```typescript
// After existing Energie group separator:
<Separator className="mt-6" />
<div className="pt-2">
  <p className="px-4 text-[12px] font-normal text-muted-foreground uppercase tracking-wide mb-2 mt-6">Gemeinwesen</p>
  <LayerToggle id="schools-toggle" label="Schulen & Kitas" checked={...} onCheckedChange={() => onToggleLayer('schools')} />
  <LayerToggle id="healthcare-toggle" label="Gesundheit" checked={...} onCheckedChange={() => onToggleLayer('healthcare')} />
  <LayerToggle id="parks-toggle" label="Parks & Spielplätze" checked={...} onCheckedChange={() => onToggleLayer('parks')} />
  <LayerToggle id="waste-toggle" label="Wertstoffhöfe & Recycling" checked={...} onCheckedChange={() => onToggleLayer('waste')} />
</div>
<Separator className="mt-6" />
<div className="pt-2">
  <p className="px-4 text-[12px] font-normal text-muted-foreground uppercase tracking-wide mb-2 mt-6">Infrastruktur</p>
  <LayerToggle id="roadworks-toggle" label="Baustellen (OSM)" checked={...} onCheckedChange={() => onToggleLayer('roadworks')} />
  <LayerToggle id="ev-toggle" label="E-Ladesäulen (BNetzA)" checked={...} onCheckedChange={() => onToggleLayer('evCharging')} />
  {/* Solar WMS conditional on data availability */}
  <LayerToggle id="solar-toggle" label="Solarpotenzial Dächer" checked={...} onCheckedChange={() => onToggleLayer('solarPotential')} />
</div>
```

### MapView Extension

MapView.tsx must be extended with new optional props (following existing `trafficVisible`/`energyVisible` optional props pattern). New layer components conditionally rendered:

```typescript
// MapView interactiveLayerIds extension:
interactiveLayerIds={[
  // existing...
  'community-schools-points', 'community-healthcare-points',
  'community-parks-points', 'community-waste-points',
  'infrastructure-ev-points',
  'infrastructure-roadworks-points',
]}
```

Domain detection in onClick handler extends the existing pattern with prefix matching.

### Popup Components

One popup component per domain group:
- `CommunityPopup.tsx` — for schools, healthcare, parks, waste (reads `category` property to show appropriate labels)
- `EvChargingPopup.tsx` — for EV charging stations (plug types, power, operator)
- `RoadworksPopup.tsx` — for OSM construction (description from `name` tag, highway type being constructed)

CommunityPopup pattern (same structure as EnergyPopup.tsx):
```typescript
export default function CommunityPopup({ feature }: { feature: Feature }) {
  const props = feature.properties ?? {};
  return (
    <div className="text-sm space-y-1 max-w-[200px]">
      <p className="text-[16px] font-semibold">{props.name || 'Einrichtung'}</p>
      <p className="text-[13px]">{props.address}</p>
      {props.opening_hours && <p className="text-[12px] text-muted-foreground">Öffnungszeiten: {props.opening_hours}</p>}
      <p className="text-[11px] text-muted-foreground capitalize">{CATEGORY_LABELS[props.category] ?? props.category}</p>
    </div>
  );
}
```

### aalen.yaml — New Connector Entries

Eight new connector entries, following the established pattern:

```yaml
- connector_class: OverpassCommunityConnector
  poll_interval_seconds: 86400
  enabled: true
  config:
    amenity_filter: "school|kindergarten"
    category: "school"
    domain: "community"
    attribution: "OpenStreetMap contributors, ODbL"

- connector_class: OverpassHealthcareConnector
  poll_interval_seconds: 86400
  enabled: true
  config:
    category: "healthcare"
    attribution: "OpenStreetMap contributors, ODbL"

- connector_class: OverpassParksConnector
  poll_interval_seconds: 86400
  enabled: true
  config:
    category: "park"
    attribution: "OpenStreetMap contributors, ODbL"

- connector_class: OverpassWasteConnector
  poll_interval_seconds: 86400
  enabled: true
  config:
    category: "waste"
    attribution: "OpenStreetMap contributors, ODbL"

- connector_class: OverpassRoadworksConnector
  poll_interval_seconds: 3600
  enabled: true
  config:
    category: "roadwork"
    attribution: "OpenStreetMap contributors, ODbL"

- connector_class: LadesaeulenConnector
  poll_interval_seconds: 86400
  enabled: true
  config:
    kreis_filter: "Ostalbkreis"
    attribution: "Bundesnetzagentur, CC BY 4.0"

- connector_class: SolarPotentialConnector
  poll_interval_seconds: 86400
  enabled: false   # enabled only if WMS endpoint is confirmed
  config:
    wms_url: ""    # placeholder — set when LUBW endpoint is confirmed
    attribution: "Landesanstalt fuer Umwelt Baden-Wuerttemberg (LUBW)"
```

**Design choice on connector granularity:** One connector per Overpass category (not one mega-connector) — this keeps each connector's poll failure isolated and makes staleness tracking per-category meaningful. All write to domain `"community"` with a `category` property discriminator.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Overpass query construction | Custom DSL builder | Inline QL strings with f-string bbox interpolation | Overpass QL is simple; Python libraries add deps without value |
| CSV coordinate parsing | Float-parse with locale | `str.replace(",", ".")` then `float()` | BNetzA CSVs use German comma-decimal; one-liner fix |
| WMS tile URL construction | Custom tile URL builder | WmsOverlayLayer.tsx (already exists) | Phase 6 already solved this with raster-opacity toggle pattern |
| Distance from map center | PostGIS ST_Distance | JavaScript calculation in popup (client-side) | Distance is a UI feature, not a query filter; simpler client-side |
| Cluster rendering | Custom aggregation | MapLibre Source cluster:true | MapLibre handles clustering natively in the Source spec |

---

## Common Pitfalls

### Pitfall 1: Overpass Returns Ways — center.lat is in a Nested Object
**What goes wrong:** For `way` elements, coordinates are at `element.center.lat` / `element.center.lon`, not at `element.lat` / `element.lon`. Nodes have flat `element.lat` / `element.lon`. Missing this causes `None` coordinates and WKT construction failure.
**How to avoid:** Always use `element.get("lat") or (element.get("center") or {}).get("lat")` — the two-path extraction pattern.
**Warning signs:** Features absent from map despite 200 OK response.

### Pitfall 2: BNetzA CSV Decimal Comma Breaks float()
**What goes wrong:** `float("11,5")` raises ValueError. All power/coordinate columns in the BNetzA Ladesäulenregister use German comma decimals.
**How to avoid:** Normalize before float conversion: `float(val.replace(",", ".").strip())`.
**Warning signs:** Connector crashes on first CSV parse.

### Pitfall 3: Overpass Rate Limiting Under Heavy Load
**What goes wrong:** The public Overpass API (overpass-api.de) rate-limits aggressive clients. Multiple connectors polling at 86400s all firing on startup simultaneously triggers rate limits.
**How to avoid:** Stagger connector startup using `initial_delay_seconds` if APScheduler supports it. Alternatively, jitter poll intervals slightly per connector. Each Overpass query is one HTTP POST — five connectors × one request = fine at startup; only problematic if poll_interval is shortened.
**Warning signs:** HTTP 429 or `runtime error: timeout exceeded` in Overpass response.

### Pitfall 4: BNetzA CSV URL Changes Monthly
**What goes wrong:** The CSV URL includes the date (`Ladesaeulenregister_BNetzA_{YYYY-MM-DD}.csv`). Hardcoding the date means the connector fetches a stale file.
**How to avoid:** Resolve the current URL dynamically by scraping the download page, OR use the stable HTML page URL and extract the link. Alternative: MobiData BW also aggregates this dataset at `https://mobidata-bw.de/dataset/e-ladesaulen` — may have a stable permalink.
**Warning signs:** Connector returns 404 after monthly BNetzA update.

### Pitfall 5: domain key not in VALID_DOMAINS Causes 404
**What goes wrong:** `layers.py` validates domain against `VALID_DOMAINS`. If `"community"` or `"infrastructure"` are not added, all layer requests return 404. The frontend `useLayerData` hook catches this as an error.
**How to avoid:** Add new domain strings to `VALID_DOMAINS` frozenset in `geojson.py` as the first backend change.
**Warning signs:** `Error` state in `useLayerData`, no features visible, console shows 404 from `/api/layers/community`.

### Pitfall 6: MapView interactiveLayerIds Must Include New Layer IDs
**What goes wrong:** Clicking on community/infrastructure points produces no popup because the layer IDs are not in `interactiveLayerIds`. The onClick handler fires but `e.features?.[0]` is undefined.
**How to avoid:** Add all new circle point layer IDs to the `interactiveLayerIds` array in MapView.tsx when adding new layers.
**Warning signs:** Map renders features but clicking produces no popup.

### Pitfall 7: WMS Solar Layer Without Known Layer Name Silently Renders Blank Tiles
**What goes wrong:** WmsOverlayLayer fetches tiles with a layer name that doesn't exist — the WMS returns transparent PNG tiles with no error. The toggle appears to work but shows nothing.
**How to avoid:** Validate the WMS GetCapabilities response before wiring the component. Log the available layer names from GetCapabilities during connector startup.
**Warning signs:** WMS overlay toggled on but map shows no raster.

### Pitfall 8: Sidebar layerVisibility and onToggleLayer Type Must Be Extended
**What goes wrong:** The existing `SidebarProps` and `layerVisibility` type in `Sidebar.tsx` and `page.tsx` are typed as explicit union literals. Adding new layer keys without updating the type causes TypeScript errors (strict union check).
**How to avoid:** Update both the TypeScript type and the `useUrlState` initial state object in `page.tsx` for each new layer key.
**Warning signs:** TypeScript compiler errors `Argument of type '...' is not assignable to parameter of type ...`.

---

## Architecture Patterns

### Recommended Project Structure Changes
```
backend/app/connectors/
├── overpass_community.py    # COMM-02: schools, COMM-03: healthcare, COMM-04: parks, COMM-01: waste
├── overpass_roadworks.py    # INFR-01: OSM construction
├── ladesaeulen.py           # INFR-02: BNetzA EV charging
└── solar_potential.py       # INFR-03: LUBW WMS solar (conditional)

frontend/components/map/
├── CommunityLayer.tsx       # Schools, healthcare, parks, waste — category-filtered
├── InfrastructureLayer.tsx  # EV charging, roadworks — category-filtered
├── CommunityPopup.tsx       # Community POI popup
├── EvChargingPopup.tsx      # EV charging popup
└── RoadworksPopup.tsx       # Roadworks popup
```

**Alternative:** Consolidate all four Overpass community connectors into one `OverpassCommunityConnector` that fetches all tags in a single query and upserts with different category properties. This reduces API calls (1 instead of 4) and simplifies aalen.yaml. Trade-off: larger response payload, single failure point. Recommendation: use the consolidated single-query approach.

### Single-Query Consolidated Overpass Pattern (Recommended)

Instead of four separate connectors, one `OverpassCommunityConnector` handles all community POIs:

```python
# Single Overpass query fetching all community POIs at once
COMMUNITY_QUERY_TEMPLATE = """
[out:json][timeout:60];
(
  node["amenity"~"school|kindergarten|pharmacy|hospital|doctors|clinic|dentist|recycling|waste_disposal"]({bbox});
  way["amenity"~"school|kindergarten|pharmacy|hospital|doctors|clinic|dentist|recycling|waste_disposal"]({bbox});
  node["leisure"~"park|playground|sports_centre|pitch"]({bbox});
  way["leisure"~"park|playground|sports_centre|pitch"]({bbox});
);
out center;
"""
```

Category is then determined by `tags.get("amenity") or tags.get("leisure")` mapping:
- `school`/`kindergarten` → `"school"`
- `pharmacy`/`hospital`/`doctors`/`clinic`/`dentist` → `"healthcare"`
- `park`/`playground`/`sports_centre`/`pitch` → `"park"`
- `recycling`/`waste_disposal` → `"waste"`

And a separate `OverpassRoadworksConnector` writes to domain `"infrastructure"` with `category="roadwork"`.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate Overpass fetches per tag | Single union query with `~` regex | Ongoing best practice | Fewer API calls, single timeout |
| Raw GeoJSON layer in MapLibre | MapLibre cluster:true in Source | MapLibre 3+ | Cluster rendering is native, no client-side aggregation |
| WMS layer visibility toggle via layout | raster-opacity: 0 for hidden | Phase 6 established pattern | Prevents tile re-fetch on toggle |

---

## Open Questions

1. **LUBW Solar Potential WMS endpoint URL**
   - What we know: Metadata records exist in RIPS system for "WMS Photovoltaik Dachfläche (Potenzial)". The RIPS-GDI pattern for other LUBW services is `rips-gdi.lubw.baden-wuerttemberg.de/arcgis/services/wms/{service}/MapServer/WMSServer`.
   - What's unclear: The `{service}` name for the solar potential WMS. Candidates like `UIS_0100000003700001` are guesses.
   - Recommendation: Attempt `GetCapabilities` on likely RIPS-GDI paths at implementation time. If no valid layer found, INFR-03 solar WMS is deferred to Phase 9 per the CONTEXT.md decision. SolarPotentialConnector remains `enabled: false`.

2. **BNetzA CSV stable download URL**
   - What we know: URL includes a date component that changes monthly.
   - What's unclear: Whether BNetzA provides a stable redirect URL or whether the MobiData BW mirror has a stable permalink.
   - Recommendation: At implementation time, check if `https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/E-Mobilitaet/DownloadundKontakt.html` has a stable anchor link or redirect. As a fallback, scrape the page HTML to extract the current CSV link.

3. **OSM Roadwork Data Coverage in Aalen**
   - What we know: `highway=construction` is a valid OSM tag for active construction. OSM guidelines say only tag sites closed for 6+ months.
   - What's unclear: How many active `highway=construction` features currently exist in the Aalen bbox. The tag is sparse in Germany — mappers don't always add it for short-term works.
   - Recommendation: Implement the connector; display "Keine aktuellen Baustellen" in the UI if zero features returned. This is a best-effort data source — the decision is locked and the limitation was acknowledged in CONTEXT.md.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Overpass API (overpass-api.de) | COMM-01..04, INFR-01 | ✓ (public, no auth) | WFS 2.0 | overpass.kumi.systems mirror |
| BNetzA CSV download | INFR-02 | ✓ (confirmed URL) | 2026-03-25 edition | MobiData BW mirror |
| LUBW solar WMS | INFR-03 | Unknown | Unknown | Defer to Phase 9 |
| httpx (backend) | All connectors | ✓ | 0.28.x in pyproject.toml | — |
| shapely (backend) | WMS polygon centroids | ✓ | 2.x in pyproject.toml | — |
| icalendar (backend) | GOA waste iCal | — | Not in pyproject.toml (available in env) | N/A — GOA has no iCal |

**Missing dependencies with no fallback:** None — LUBW solar WMS has explicit defer fallback.

**Missing dependencies with fallback:** LUBW solar WMS (fallback: defer INFR-03 to Phase 9).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `backend/pyproject.toml` (asyncio_mode=auto) |
| Quick run command | `cd backend && python -m pytest tests/connectors/ -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -x -q -m "not slow"` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COMM-01 | Overpass waste connector upserts Wertstoffhof features with category=waste | unit | `pytest tests/connectors/test_overpass_community.py::test_waste_category -x` | ❌ Wave 0 |
| COMM-02 | Overpass connector maps amenity=school to category=school | unit | `pytest tests/connectors/test_overpass_community.py::test_school_category -x` | ❌ Wave 0 |
| COMM-03 | Overpass connector maps amenity=pharmacy to category=healthcare | unit | `pytest tests/connectors/test_overpass_community.py::test_healthcare_category -x` | ❌ Wave 0 |
| COMM-04 | Overpass connector maps leisure=park to category=park | unit | `pytest tests/connectors/test_overpass_community.py::test_park_category -x` | ❌ Wave 0 |
| INFR-01 | Overpass roadworks connector writes domain=infrastructure, category=roadwork | unit | `pytest tests/connectors/test_overpass_roadworks.py -x` | ❌ Wave 0 |
| INFR-02 | LadesaeulenConnector parses CSV with comma decimals, filters Ostalbkreis | unit | `pytest tests/connectors/test_ladesaeulen.py -x` | ❌ Wave 0 |
| INFR-02 | EV popup renders Steckertypen1-4 and Anschlussleistung | unit | `pytest tests/connectors/test_ladesaeulen.py::test_popup_properties -x` | ❌ Wave 0 |
| INFR-03 | WMS overlay renders if URL available; skips gracefully if not | manual | Visual check in browser | N/A |
| INFR-04 | EnergyLayer solar_rooftop features visible (Phase 7 already done) | manual | Verify energy layer still renders | N/A |
| All | /api/layers/community and /api/layers/infrastructure return 200 | integration | `pytest tests/test_api_layers.py::test_community_layer_endpoint -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/connectors/ -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x -q -m "not slow"`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/connectors/test_overpass_community.py` — covers COMM-01..04, tests category mapping and center coordinate extraction for way elements
- [ ] `backend/tests/connectors/test_overpass_roadworks.py` — covers INFR-01, tests domain and category assignment
- [ ] `backend/tests/connectors/test_ladesaeulen.py` — covers INFR-02, tests CSV decimal comma normalization, Ostalbkreis filter, popup property names
- [ ] `backend/tests/test_api_layers.py` extension — add `test_community_layer_endpoint` and `test_infrastructure_layer_endpoint` after VALID_DOMAINS updated

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 8 |
|-----------|-------------------|
| Only freely available / open data | Overpass (ODbL), BNetzA CSV (CC BY 4.0), LUBW WMS (UIS terms), OSM (ODbL) all qualify |
| No Aalen-specific hardcoding | Bbox from `self.town.bbox`, Kreis filter from connector config yaml, not hardcoded |
| NGSI-LD compatible API layer | New domains `"community"` and `"infrastructure"` added to VALID_DOMAINS |
| Datenlizenz Deutschland attribution required | All new connectors must be added to `CONNECTOR_ATTRIBUTION` in `geojson.py` |
| Frontend on port 4000 | No change — existing setup |
| GSD workflow enforcement | All file changes through `/gsd:execute-phase` |
| Read `node_modules/next/dist/docs/` before writing Next.js code | Required for any new Next.js 16.x frontend components |

---

## Sources

### Primary (HIGH confidence)
- Overpass API — `https://overpass-api.de/api/interpreter` — live query tested, 313 elements returned for Aalen bbox
- OSM Wiki Overpass QL — `https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL` — query syntax
- BNetzA Ladesäulenregister columns — verified via MobiData BW dataset page and community documentation
- Existing codebase — `backend/app/connectors/lubw_wfs.py`, `mastr.py`, `base.py` — features-only pattern
- Existing codebase — `frontend/components/map/EnergyLayer.tsx`, `WmsOverlayLayer.tsx` — frontend patterns
- Existing codebase — `backend/app/routers/layers.py`, `backend/app/schemas/geojson.py` — domain registration pattern

### Secondary (MEDIUM confidence)
- BNetzA CSV URL — `https://data.bundesnetzagentur.de/.../Ladesaeulenregister_BNetzA_2026-03-25.csv` — confirmed via BNetzA download page (URL is date-stamped, may change)
- BNetzA CSV encoding/separator — semicolon, UTF-8, comma decimal — confirmed via MobiData BW and community documentation
- GOA no iCal — confirmed by failed connection to dav.datenschleuder.com and no API mention on goa-online.de
- LUBW solar WMS metadata record exists — confirmed by two RIPS metadata page references

### Tertiary (LOW confidence)
- LUBW Solar WMS GetCapabilities URL — not confirmed; RIPS-GDI pattern is plausible but the specific service name is unknown
- OSM roadwork data density in Aalen — not queried; assumed sparse based on OSM community guidelines

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all patterns established in Phases 6-7
- Architecture patterns: HIGH — features-only connector and EnergyLayer frontend template verified in codebase
- Data source specs (Overpass, BNetzA): HIGH — live API tested and columns documented
- Solar WMS: LOW — endpoint not confirmed
- GOA waste iCal: HIGH (confirmed unavailable)
- Pitfalls: HIGH — derived from actual codebase patterns and verified data formats

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (stable — Overpass and BNetzA are long-lived services; BNetzA URL date changes monthly but pattern is known)
