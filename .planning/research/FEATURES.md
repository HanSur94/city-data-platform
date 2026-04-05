# Feature Research

**Domain:** Open city data aggregation and visualization platform (small German municipalities)
**Researched:** 2026-04-05
**Confidence:** MEDIUM — based on analysis of comparable platforms (Sentilo, CKAN, FIWARE, OpenDataSoft, Grafana smart city deployments) and German open data ecosystem research. Feature expectations from citizens/officials are inferred from comparable deployments; no direct user research yet.

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Interactive map with city overview | Every city data product centers on a map; users orient spatially first | MEDIUM | Leaflet or MapLibre GL on OSM tiles; Aalen bounding box as default view |
| Toggleable data layers | Users need to show/hide traffic, air quality, transport etc. independently | LOW | Layer control panel; persistent state in URL or localStorage |
| KPI summary panel / dashboard tiles | City officials and citizens expect a "headline numbers" view without reading a map | LOW | Counts, averages, status lights; rendered alongside or below the map |
| Time range selector / historical view | Raw snapshots are useless for decision-making; "how was it last week?" is the first question | MEDIUM | Date range picker feeding a time-filtered query; requires time-series data storage |
| Charts / trend visualizations | Data trends (e.g. air quality over a month) are how non-technical users consume data | MEDIUM | Line charts, bar charts per data domain; Recharts or Chart.js |
| Per-layer data freshness indicator | Users need to know when data was last updated to judge reliability | LOW | Timestamp badge per layer; stale data warning after configurable threshold |
| Mobile-responsive layout | Citizens access on phones; officials may use tablets in the field | MEDIUM | CSS grid / flexbox breakpoints; map usable on small screens |
| Public transport: lines and stops on map | GTFS data is widely available for Germany via DELFI/gtfs.de; absence would feel like a missing feature | MEDIUM | GTFS static feed ingestion; render stop markers and route polylines |
| Air quality index display | AQI is understood by the public and expected from any environmental layer | LOW | Color-coded AQI badge; standard EU/WHO thresholds |
| Traffic flow / congestion indicators | Most citizens' primary data curiosity; strongly expected from a city data platform | MEDIUM | Color-coded road segments or heatmap overlay |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Generic multi-town configuration | Any German town can self-host with a config file — not locked to Aalen | HIGH | Town config schema (bounding box, data source URLs, enabled layers); documented onboarding |
| All six data domains unified in one view | Competitors/portals cover one domain at a time; unified view is rare for small municipalities | HIGH | Requires six separate ingestors behind a shared data model and layer system |
| Permalink / shareable view URLs | Officials can share "traffic at 8am Monday" view with colleagues; unusual in municipal tools | LOW | Encode active layers, time range, map viewport in URL query params |
| Data export (CSV / GeoJSON) | Citizens and journalists can take data elsewhere; CKAN portals do this, but not visualization tools | LOW | Per-layer download button hitting an API endpoint |
| Embed snippet for council pages | City websites can embed a live map tile or chart without deploying the full platform | MEDIUM | Iframe-safe embed mode; scoped CSS; configurable default view |
| Multi-town comparison view | Allow side-by-side comparison of e.g. air quality between Aalen and neighboring towns | HIGH | Requires normalized data model across towns; defer to v2 |
| Data source health dashboard (operator view) | Operators need to know when an upstream data source goes silent | MEDIUM | Internal-facing status page; per-source uptime, last-seen timestamp, error log |
| Town-specific theming (logo, colors) | Low-friction adoption: town colors in header makes officials feel it's "their" product | LOW | CSS variables / theme config in the town config file |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| User accounts and authentication | "Personalized saved views", "admin panel access" | Adds auth infrastructure, GDPR surface, session management, password reset flows — none of this is needed for public open data | Use URL-encoded state for saved views; use server-side config files for admin settings |
| Real-time push / websockets for all layers | "Live" data feels more impressive | Most upstream sources (CKAN, Umweltbundesamt, GTFS-RT) have polling intervals of 1–15 minutes; WebSocket complexity buys nothing; polling on 30s/60s intervals is invisible to users | HTTP polling with configurable refresh interval per layer |
| Predictive analytics / AI forecasting | "Predict tomorrow's air quality" sounds like a win | Requires ML pipeline, training data, model maintenance; misleads non-technical users if wrong; out of scope for v1 | Show clear historical trends; let users draw their own conclusions |
| IoT sensor ingestion / custom data upload | "We have our own sensors" | Crosses into data collection infrastructure; requires authentication, schema validation, storage quotas; fundamentally different product | Stick to consuming published open data APIs; document how to add a new data source connector |
| Native mobile app (iOS/Android) | Wider reach | Doubles development effort; web-first responsive design covers 95% of use cases for this type of platform | Responsive web; PWA manifest for installability without a native app |
| Multi-language / i18n from day one | "International users" | German municipalities publish data in German; internationalizing strings early creates maintenance overhead before the schema is stable | German first; add i18n scaffold at v1.x after core is stable |
| Comment / feedback system on data points | "Community engagement" | Moderation burden; GDPR concerns; scope creep away from data visualization | Link to city's existing feedback channel (email, 311 system) |
| 3D building / terrain visualization | Impressive demos | Heavy rendering cost; requires proprietary building footprint data; distracts from data content | 2D map tiles with choropleth / heatmap overlays are sufficient and performant |

## Feature Dependencies

```
[Map view]
    └──requires──> [Tile server / OSM base layer]
    └──requires──> [Town configuration (bounding box, center)]

[Data layers on map]
    └──requires──> [Map view]
    └──requires──> [Data ingestors (one per domain)]
    └──requires──> [Normalized internal data model]

[Time range selector]
    └──requires──> [Time-series data storage]
                       └──requires──> [Data ingestors with timestamp preservation]

[Historical charts]
    └──requires──> [Time-series data storage]
    └──enhances──> [Time range selector]

[KPI dashboard tiles]
    └──requires──> [At least one data ingestor running]
    └──enhances──> [Charts / trend visualizations]

[Permalink / shareable URLs]
    └──enhances──> [Map view]
    └──enhances──> [Time range selector]

[Data export]
    └──requires──> [Normalized internal data model]
    └──requires──> [API layer exposing query endpoints]

[Multi-town configuration]
    └──requires──> [Town config schema]
    └──requires──> [All ingestors parameterized (no hardcoded Aalen URLs)]

[Embed snippet]
    └──requires──> [Map view]
    └──requires──> [Permalink / shareable URLs]

[Data source health dashboard]
    └──requires──> [All data ingestors running]
    └──enhances──> [Per-layer data freshness indicator]

[Public transport layer]
    └──requires──> [GTFS static feed ingestor]
    └──enhances──> [GTFS-RT ingestor (for live departures)]

[Multi-town comparison view] ──conflicts──> [Single-town scope assumption in map view]
```

### Dependency Notes

- **Data layers require normalized internal data model:** Each of the six domains (traffic, water, electricity, wastewater, air quality, transport) has a different upstream format. A shared internal model is the foundation everything else builds on — this must be designed early.
- **Historical charts require time-series storage:** If the first ingestors only store latest state (no history), retrofitting time-series storage is a rewrite. Design for it from the first ingestor.
- **Multi-town configuration requires parameterized ingestors:** Hardcoding any Aalen-specific URL or identifier in an ingestor blocks multi-town adoption. Config-driven design must be enforced from the first ingestor written.
- **Embed snippet conflicts with full auth:** If auth is added later, embeds break. Keeping the platform fully public is a prerequisite for embeds to work.

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to validate the concept.

- [ ] Interactive map with layer toggle — proves the core interaction model
- [ ] At least two data domains live (recommended: public transport + air quality — both have reliable German open data sources) — proves multi-domain aggregation
- [ ] KPI summary tiles for active layers — proves the dashboard dimension
- [ ] Time range selector with one week of historical data — proves it's more than a live snapshot
- [ ] Town configuration file for Aalen — proves the generic architecture intention
- [ ] Data freshness indicators — needed for user trust with live data
- [ ] Mobile-responsive layout — non-negotiable for public launch

### Add After Validation (v1.x)

Features to add once core is working.

- [ ] Remaining four data domains (traffic, water, electricity, wastewater) — add domain by domain once the ingestor pattern is proven
- [ ] Permalink / shareable URLs — add when users start asking "how do I share this?"
- [ ] Data export (CSV / GeoJSON) — add when journalists or researchers show interest
- [ ] Data source health dashboard — add when running in production and operators need visibility
- [ ] Town-specific theming — add when a second town onboards

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] Multi-town comparison view — requires normalizing data across towns; needs real adoption first
- [ ] Embed snippet — deferred until stable embed contract can be maintained
- [ ] GTFS-RT live departures — adds real-time complexity; static timetable is sufficient for v1
- [ ] i18n / multi-language — defer until there's a concrete non-German user

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Interactive map with layer toggle | HIGH | MEDIUM | P1 |
| Public transport layer (GTFS) | HIGH | MEDIUM | P1 |
| Air quality layer | HIGH | LOW | P1 |
| KPI summary tiles | HIGH | LOW | P1 |
| Time range selector + historical data | HIGH | MEDIUM | P1 |
| Data freshness indicator | HIGH | LOW | P1 |
| Mobile-responsive layout | HIGH | MEDIUM | P1 |
| Traffic flow layer | HIGH | MEDIUM | P1 |
| Water / electricity / wastewater layers | MEDIUM | MEDIUM | P2 |
| Permalink / shareable URLs | MEDIUM | LOW | P2 |
| Data export (CSV / GeoJSON) | MEDIUM | LOW | P2 |
| Data source health dashboard | MEDIUM | MEDIUM | P2 |
| Town-specific theming | LOW | LOW | P2 |
| Multi-town comparison view | MEDIUM | HIGH | P3 |
| Embed snippet | LOW | MEDIUM | P3 |
| GTFS-RT live departures | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | CKAN / GovData portals | Sentilo (Barcelona) | Grafana + smart city plugins | Our Approach |
|---------|------------------------|---------------------|------------------------------|--------------|
| Map view | Rarely; mostly table/catalog UI | Yes, sensor viewer on map | Via plugins (Orchestra Cities, etc.) | First-class map + dashboard split view |
| Multi-domain aggregation | No — one dataset at a time | Yes — sensor types vary | Via multiple data sources | Six domains unified behind shared model |
| Citizen-friendly UI | No — developer/analyst-focused | Moderate | No — analyst-focused | Non-technical UI for both citizens and officials |
| Historical data | Yes — static file downloads | Yes — via Grafana integration | Yes — core Grafana strength | Interactive time range selector in the UI |
| Generic/multi-town | No — per-city deployments | Moderate — multi-tenant | No — manual per deployment | Config-file-driven, documented onboarding |
| Self-hostable | Yes | Yes | Yes | Yes — must run on modest hardware |
| German open data focus | Yes (GovData, DCAT-AP.de) | No — IoT/sensor focus | No | Yes — CKAN, DELFI, Umweltbundesamt sources |
| Open source | Yes | Yes | Yes | Yes — from day one |

## Sources

- [Grafana: Monitoring smart cities with Grafana, Timescale, and Sentilo](https://grafana.com/blog/2023/05/26/monitoring-smart-cities-with-grafana-timescale-and-sentilo/) — MEDIUM confidence
- [GTFS for Germany (gtfs.de)](https://gtfs.de/en/) — HIGH confidence (official source)
- [DELFI initiative — German national GTFS](https://gtfs.de/en/realtime/) — HIGH confidence
- [GovData — German Open Data Portal (GitHub)](https://github.com/GovDataOfficial/GovDataPortal) — HIGH confidence
- [Sentilo open source smart city platform](https://www.sentilo.io/) — MEDIUM confidence
- [FIWARE Smart Cities platform overview](https://www.fiware.org/about-us/smart-cities/) — MEDIUM confidence
- [Leveraging CKAN for publishing open data in Germany](https://ckan.org/blog/leveraging-ckan-publishing-open-data-germany) — HIGH confidence
- [OpenDataSoft ODS Widgets](https://github.com/opendatasoft/ods-widgets) — MEDIUM confidence
- [CKAN embed widget](https://github.com/opendata-swiss/ckan-embed) — MEDIUM confidence
- [Open Data promotes citizen engagement (The Hill)](https://thehill.com/opinion/technology/439467-open-data-promotes-citizen-engagement-at-the-local-level/) — LOW confidence (opinion piece)
- [Smart City Dashboard EDAG reference](https://smartcity.edag.com/en/referenzen/smart-city-dashboard/) — LOW confidence (marketing material)

---
*Feature research for: Open city data platform for small German municipalities*
*Researched: 2026-04-05*
