# Phase 2: First Connectors - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

Transit and air quality data flow continuously from upstream sources through validated Pydantic models into TimescaleDB hypertables with staleness tracking. This phase implements 4 connectors:
1. GTFSConnector — downloads NVBW GTFS feed, parses stops/routes, writes to features table; GTFS-RT positions/delays to transit hypertable
2. UBA air quality connector — fetches PM10, PM2.5, NO2, O3 from Umweltbundesamt API (station in Aalen)
3. Sensor.community connector — fetches citizen-science air quality data from nearby sensors
4. DWD/Bright Sky weather connector — fetches current conditions and MOSMIX forecasts

All connectors follow the BaseConnector pattern from Phase 1. Each records last_successful_fetch and handles HTTP 200 with empty payload as failure.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — infrastructure/data ingestion phase. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

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

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- backend/app/connectors/base.py — BaseConnector ABC with fetch(), transform(), load() contract
- backend/app/connectors/stub.py — StubConnector reference implementation
- backend/app/config.py — Town model, ConnectorConfig, load_town()
- backend/app/db.py — async_engine, AsyncSessionLocal, DATABASE_URL

### Established Patterns
- TDD: write failing tests first, then implement
- Alembic for schema (001_initial_schema.py already created all hypertables)
- Pydantic models for all external data validation
- uv for package management

### Integration Points
- Connectors register via towns/aalen.yaml connector configs
- Data writes to existing hypertables (air_quality_readings, transit_positions)
- features table for spatial data (stops, route shapes)

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure/data ingestion phase. Refer to ROADMAP phase description and success criteria.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
