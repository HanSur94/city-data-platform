# Pitfalls Research

**Domain:** Open city data aggregation platform (multi-source, self-hosted, German municipal)
**Researched:** 2026-04-05
**Confidence:** MEDIUM — combination of verified patterns from similar open-source city projects, German ecosystem documentation, and time-series/geospatial engineering post-mortems

---

## Critical Pitfalls

### Pitfall 1: Aalen-Specific Hardcoding That Masquerades as Generic

**What goes wrong:**
The reference city (Aalen) gets special-cased at every layer — connector logic, coordinate bounds, datasource URLs, German-language labels — because it's the first working instance and the path of least resistance. Six months later, adding a second town (say, Ulm) requires touching 40 files instead of one config.

**Why it happens:**
The "generic architecture" goal lives only in documentation. Under deadline pressure, developers hard-code the known-working API endpoint instead of wiring it through a connector configuration system. Each shortcut compounds.

**How to avoid:**
Treat Aalen as `CITY_ID=aalen` from day one. Every data source, every API URL, every bounding box, every tile extent must come from a town configuration object, not from constants or environment variables with `AALEN_` prefixes. Build the second town (even a stub) in parallel with Aalen to prove genericism early.

**Warning signs:**
- Any file containing "Aalen", "Ostalbkreis", or Baden-Württemberg-specific geographic constants
- Environment variable names that reference a city name
- SQL queries with literal bounding-box coordinates that match Aalen's bounds
- A connector that fetches from a URL without reading the base URL from config

**Phase to address:**
Foundation / data ingestion phase — enforce the town-config abstraction before the first connector is written, not after.

---

### Pitfall 2: Upstream APIs Have No SLA and Will Silently Stop Working

**What goes wrong:**
German municipal open data APIs (CKAN portals, Mobilithek feeds, local GTFS exports) go offline without notice, change URL schemes, or return empty payloads while still returning HTTP 200. The platform continues showing the last cached data. Users assume the data is current. Trust erodes the moment someone notices a discrepancy.

**Why it happens:**
Developers build the happy path — data flows, maps update — but don't design for the failure modes of public-sector APIs with no contractual uptime obligation.

**How to avoid:**
- Every connector must record a `last_successful_fetch` timestamp alongside data
- Every dashboard panel must display data age ("as of 14 min ago")
- Implement staleness thresholds per data type: traffic at >15 min stale = yellow badge; air quality at >1 hour = red badge; GTFS schedule at >7 days = error state
- Treat "HTTP 200 with empty payload" as a failure, not success
- Build a connector health dashboard (internal) from day one

**Warning signs:**
- Dashboard shows data but no timestamp
- Connectors have no `last_fetched`/`last_succeeded` concept
- No alerting when a source goes silent
- Tests only cover the happy path (API responds with valid data)

**Phase to address:**
Data ingestion phase — health metadata must be a first-class schema concept before any connector goes to production.

---

### Pitfall 3: Schema Drift From Upstream API Changes Silently Breaks Pipelines

**What goes wrong:**
A municipal API changes a field name (e.g., `flow_count` becomes `vehicle_count`), adds a required parameter, or changes date format. The connector either throws a parsing error (best case) or silently writes nulls to the database (worst case). Both break the dashboard, but the silent case is discovered weeks later.

**Why it happens:**
Public APIs from German municipalities often lack versioning, deprecation notices, or changelogs. GTFS quality issues in Germany are so common that the community maintains a dedicated GitHub issue tracker for them. Developers assume upstream stability they don't have.

**How to avoid:**
- Define explicit Pydantic/TypeScript schema models for every ingested payload — never pass raw JSON to storage
- Fail loudly at the connector boundary when schema validation fails
- Log schema validation failures to a separate monitoring table
- Write schema contracts as tests that run against live endpoints in CI (or nightly)
- Pin GTFS feed versions with checksums; alert on feed changes before automatic processing

**Warning signs:**
- Connectors that do `data['field']` without schema validation
- Database columns that are nullable but shouldn't be
- No connector-level error rate metric
- GTFS feeds fetched without validation against official GTFS Canonical Validator

**Phase to address:**
Data ingestion phase — schema validation must be built into connector architecture, not added later.

---

### Pitfall 4: Map Performance Collapses With Real Data Volumes

**What goes wrong:**
The map works beautifully with 50 test markers. With real city data — 800 bus stops, 2,000 traffic measurement points, air quality sensors with 5-minute resolution over 2 years — the browser freezes on load, tile rendering stalls, and the UI becomes unusable on mid-range hardware.

**Why it happens:**
Developers test with synthetic data that is 10-100x smaller than production data. The mistake is treating map rendering as a frontend detail rather than an architecture concern. Dumping a PostGIS query result directly into a Leaflet/MapLibre layer without aggregation or tile-based delivery is the common failure mode.

**How to avoid:**
- Use vector tiles (PMTiles or server-side via Martin/pg_tileserv) for all spatial data, not GeoJSON served raw
- Implement zoom-level-aware data density: cluster points at low zoom, show detail at high zoom
- Cap real-time overlay markers at a configurable maximum with a zoom-to-see-more message
- Use deck.gl or MapLibre GL JS with WebGL rendering for any layer exceeding ~5,000 points
- Test with full production data volumes before any UI milestone is marked done

**Warning signs:**
- Map data loaded as a single GeoJSON fetch in the frontend
- No clustering or aggregation at low zoom levels
- Frontend JS bundle includes full dataset as inline JSON
- Load time > 3 seconds on the map view

**Phase to address:**
Map visualization phase — tile strategy must be decided before any layer implementation, not retrofitted.

---

### Pitfall 5: Time-Series Database Chosen for Convenience, Not for the Query Patterns

**What goes wrong:**
The project starts with PostgreSQL/TimescaleDB because it's familiar, or with InfluxDB v1 because there are old tutorials for it. As historical data accumulates (air quality every 5 min, traffic every 1 min, over months), trend queries slow from seconds to minutes. Dashboard loads degrade. Users give up on historical views.

**Why it happens:**
Early data volumes are small enough that any database feels fast. The decision to switch databases mid-project (from TimescaleDB to QuestDB, for example) is a major migration with significant risk, so teams live with the degradation instead.

**How to avoid:**
- Evaluate databases against the actual query patterns before choosing: time-range aggregations, last-N queries, multi-metric joins, downsampling
- TimescaleDB is the right choice if the team is PostgreSQL-native and data volumes are modest (under ~100M rows per table); the PostgreSQL ecosystem compatibility is worth the ingestion trade-off
- QuestDB is the right choice if ingestion throughput is critical and SQL-only queries suffice
- InfluxDB 3.0 Core has hard limits (72-hour retention, 5 database cap) that make it unsuitable for a self-hosted multi-year historical platform without paid tier
- Benchmark with 12 months of realistic synthetic data before committing

**Warning signs:**
- No benchmarking with realistic data volumes before DB decision
- Choosing a database because a tutorial uses it, not because query patterns match
- Using InfluxDB 3.0 Core for a self-hosted deployment without checking retention limits

**Phase to address:**
Foundation phase — database selection must be benchmarked before schema design, not after.

---

### Pitfall 6: No Data Attribution Display Causes License Compliance Failures

**What goes wrong:**
German open data is published under licenses like Datenlizenz Deutschland – Namensnennung (equivalent to CC-BY) or CC-BY 4.0, all of which require attribution in every use. A platform that aggregates 8 data sources and shows none of their attributions is non-compliant with every single one of those licenses.

**Why it happens:**
Developers treat attribution as a legal formality rather than a technical requirement. It's deferred to "later" and forgotten.

**How to avoid:**
- Store license metadata alongside every data source in the connector config
- Render a data sources/attribution panel in the UI that is always accessible
- When a data layer is active on the map, display its attribution in the map corner (same pattern as OpenStreetMap attribution)
- Audit each source's license during connector development, not at release

**Warning signs:**
- No `license` or `attribution` field in the data source configuration schema
- Map view has no attribution overlay
- Connector documentation lacks license information

**Phase to address:**
Foundation/connector phase — attribution metadata must be part of the data source schema from the start.

---

### Pitfall 7: Self-Hosting "Modest Hardware" Requirement Conflicts With Data Accumulation

**What goes wrong:**
The platform is designed for self-hosting on a small server. After 12 months of operation, storing traffic data at 1-minute resolution, air quality at 5-minute resolution, and GTFS-RT at 30-second resolution across 6 data domains for one city, the database has grown to 50-200 GB. The server runs out of disk. Queries slow down. Operators don't know how to manage retention.

**Why it happens:**
Storage implications of time-series data are non-obvious. 1 row per minute = 526,000 rows per year per metric. With dozens of sensors per domain and 6 domains, this compounds quickly.

**How to avoid:**
- Define explicit retention policies per data type from day one (e.g., raw traffic: 90 days; hourly aggregates: 5 years; daily aggregates: indefinite)
- Implement automatic downsampling pipelines: raw → hourly → daily
- Document estimated storage requirements in deployment guides
- Use TimescaleDB's native compression or QuestDB's columnar compression — both achieve 10-20x compression on typical sensor data
- Expose a storage health metric in the admin/ops view

**Warning signs:**
- No retention policy defined for any data type
- Raw data stored indefinitely with no aggregation
- Deployment docs don't mention storage planning
- No disk usage monitoring

**Phase to address:**
Foundation phase — retention and downsampling strategy must be defined with the data schema, not added later.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcode Aalen API URLs as constants | Fast first connector | Cannot add second city without refactor | Never |
| Store raw upstream JSON blobs in DB | No schema design needed | Queries become JSON-extraction nightmares; schema changes invisible | Never |
| Skip connector health/staleness tracking | Simpler initial code | Dashboard shows stale data with no indication; trust collapse | Never |
| Use PostgreSQL + raw queries for time-series | Familiar tooling | Unacceptable query times at scale; retroactive migration painful | Only as spike/prototype |
| Single monolithic ingestion process | Easy to start | Cannot update one connector without risking all; no per-source error isolation | MVP only, refactor in phase 2 |
| No data attribution in UI | Saves design work | License non-compliance on every page | Never |
| Fetch fresh data on every dashboard load | No caching complexity | External API hammering; rate limiting; slow UI | Never |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| GTFS (public transport) | Treating GTFS Static and GTFS-RT as the same format | Static is ZIP with CSV; RT is Protocol Buffers. Parse separately with different libraries |
| CKAN portals | Assuming all German CKAN instances use the same API version | Check `/api/3/action/package_list` versioning; some run CKAN 2.8, some 2.10 |
| Mobilithek (traffic) | Assuming free open access to all feeds | Some feeds require registration; Datex-II format requires specific XML parsing libraries |
| Municipal air quality APIs | Expecting consistent station IDs across cities | Station IDs are city-specific; must be mapped in connector config, not assumed |
| OpenStreetMap tiles | Using OSM tile CDN directly in production | OSM's tile CDN is for development only; self-host tiles via Protomaps/PMTiles for production use |
| Electricity/water utility APIs | Expecting REST JSON | Many German utility APIs serve WFS (Web Feature Service) or WMS; require OGC-compatible clients |
| GTFS-RT feeds | Using GTFS-RT from the transit authority directly | Many German feeds have known quality issues; validate against GTFS Canonical Validator before ingesting |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| GeoJSON dump to map frontend | Browser freeze, >10s load time on map | Vector tiles with zoom-level aggregation | ~500 simultaneous markers |
| No time-series compression | Disk fills within weeks for high-frequency data | Enable TimescaleDB compression or QuestDB columnar storage from day one | ~30 days at 1-min resolution, 10+ sensors |
| Dashboard queries raw table at full resolution | Chart loads slowly; DB CPU spikes | Materialized views or continuous aggregates for chart queries | >90 days of raw data |
| Polling all connectors in a single loop | One slow API blocks all ingestion | Isolated async connector workers per data source | Any source with >5s response time |
| Frontend fetches full historical dataset for sparklines | Slow initial page load | Pre-compute summary stats; lazy-load detail on user request | >1,000 data points per chart series |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| API keys for data sources committed to version control | Key leakage, unauthorized API usage | Store in environment variables or secrets manager; add to .gitignore from day one |
| No rate limiting on the platform's own API | Accidental or intentional DoS from heavy map clients | Add rate limiting at API gateway or reverse proxy level |
| Serving tile server without access controls in embedded iframe scenario | Tile scraping, unexpected bandwidth costs | Rate limit tile endpoint; consider Referer checking |
| Accepting user-supplied geographic filter bounds without validation | Server-side request amplification, excessive DB queries | Validate bounding box size; cap maximum query area |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No data freshness indicator | City official acts on 4-hour-old traffic data as if current | Show "last updated X min ago" on every data panel; use color coding for staleness |
| Map shows all layers simultaneously by default | Visual overload; map is unreadable | Default to one or two layers; let users enable others explicitly |
| "No data available" shown as blank panel | User assumes a bug, not a data gap | Show explicit "No data from source — last seen 3 days ago" with source attribution |
| Mobile layout not designed until late | City officials use tablets in meetings; layout broken | Design for 768px width from the start, not as an afterthought |
| Data units shown without context | "42 µg/m³" is meaningless to a citizen | Show EU/German air quality threshold annotations on charts |
| Generic error messages ("Error loading data") | User cannot distinguish API outage from code bug | Show connector-specific status: "Traffic API offline since 14:22 — last data from 14:18" |

---

## "Looks Done But Isn't" Checklist

- [ ] **Map layer toggle:** Often missing fallback for when a data source has no data — verify all layers show a meaningful empty state, not a blank map
- [ ] **GTFS integration:** Often missing real-time trip updates (GTFS-RT); static schedule alone shows planned routes, not actual positions — verify RT feed is integrated
- [ ] **Data freshness display:** Often added as a label on the dashboard but missing from the map overlay — verify both views show data age
- [ ] **Multi-city genericism:** Often "generic" means one config file with Aalen values — verify a second city can be added by editing config only, with zero code changes
- [ ] **Attribution compliance:** Often displayed in a hidden footer — verify attribution is visible when each data layer is active, not buried in an "about" page
- [ ] **Storage retention:** Often configured but never tested — verify that old data is actually deleted or downsampled according to policy; check with a query against old timestamps
- [ ] **Connector isolation:** Often all connectors run in one process — verify one failing connector cannot block or crash others
- [ ] **Historical charts:** Often only "last 24 hours" is fast — verify 30-day and 90-day chart views are responsive on realistic data volumes

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Hardcoded Aalen throughout codebase | HIGH | Systematic refactor: extract town config object, test with stub second-city config, replace every hardcoded reference — budget a full sprint |
| Wrong time-series DB chosen | HIGH | Export data to Parquet; migrate schema; rewrite connector writes; re-import — expect 1-2 weeks downtime or parallel-run |
| Schema drift silent null-write | MEDIUM | Identify affected time range from logs; rerun connector with corrected schema against API historical endpoint if available; patch affected rows |
| No data attribution visible | LOW | Add attribution metadata to connector config; add UI component — 1-2 days work |
| Storage exhaustion | MEDIUM | Enable compression immediately; implement retention policy; archive old data to cheaper storage; document going forward |
| Map performance degraded | MEDIUM | Introduce vector tile layer for offending data source; implement clustering — 3-5 days per layer |
| Upstream API stops working | LOW | Implement staleness display (if missing); add source to health dashboard; notify operators — connector itself is recoverable when API returns |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Aalen hardcoding | Foundation (architecture) | Can add Stadt Ulm by editing one config file — zero code changes |
| Upstream API outages / silent failures | Data ingestion | Every connector writes `last_succeeded_at`; dashboard shows data age |
| Schema drift / silent null writes | Data ingestion | Pydantic/TypeScript schema model exists for every connector; CI tests schema against live endpoint |
| Map performance collapse | Map visualization | Load test with 12 months of realistic data before milestone sign-off |
| Wrong time-series database | Foundation (DB selection) | Benchmark 12-month synthetic dataset before committing to DB |
| License non-compliance | Foundation + each new connector | Attribution field required in connector config; UI renders attribution per active layer |
| Storage exhaustion on self-hosted | Foundation (schema + ops) | Retention policy documented; automated downsampling tested; disk usage metric exposed |
| Connector cross-contamination failure | Data ingestion | One connector can crash without affecting others; verified by killing one process under load |

---

## Sources

- [Common Mistakes When Building Smart City Solutions](https://bachasoftware.com/blog/insights-2/smart-city-solution-mistakes-and-how-to-avoid-them-789) — Smart city architecture anti-patterns (MEDIUM confidence)
- [GitHub: mfdz/GTFS-Issues — German GTFS Feed Quality Tracking](https://github.com/mfdz/GTFS-Issues) — Documented GTFS quality issues in German feeds (HIGH confidence)
- [GitHub: graphhopper/open-traffic-collection](https://github.com/graphhopper/open-traffic-collection) — German open traffic data sources and availability (HIGH confidence)
- [Mobilithek.info — German Mobility Data Platform](https://mobilithek.info/) — Official replacement for MDM/mCLOUD (HIGH confidence)
- [QuestDB: Comparing InfluxDB, TimescaleDB, QuestDB](https://questdb.com/blog/comparing-influxdb-timescaledb-questdb-time-series-databases/) — Time-series DB limitations for IoT/sensor data (MEDIUM confidence — vendor source)
- [Schema Evolution Without Breaking Consumers](https://datalakehousehub.com/blog/2026-02-de-best-practices-05-schema-evolution/) — Schema drift patterns and prevention (HIGH confidence)
- [Engineering Postmortem: Hidden Cost of Caching — Dashboard staleness](https://www.optijara.ai/en/blog/hidden-cost-of-caching-2-line-api-fix-hts-dashboard) — Staleness trust issues in dashboards (HIGH confidence)
- [GovData Licenses — Datenlizenz Deutschland](https://www.govdata.de/informationen/lizenzen) — German open data license requirements (HIGH confidence)
- [Heavy Map Visualizations Fundamentals](https://advena.hashnode.dev/heavy-map-visualizations-fundamentals-for-web-developers) — Map performance thresholds and solutions (MEDIUM confidence)
- [DCAT-AP 3.0 Specification](https://semiceu.github.io/DCAT-AP/releases/3.0.0/) — EU/German metadata standard (HIGH confidence)
- [Open Data Quality Is a Pipeline Problem](https://datalakehousehub.com/blog/2026-02-de-best-practices-03-data-quality-first/) — Data quality architecture patterns (HIGH confidence)

---
*Pitfalls research for: Open city data aggregation platform (German municipal, self-hosted)*
*Researched: 2026-04-05*
