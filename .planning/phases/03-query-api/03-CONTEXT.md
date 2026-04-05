# Phase 3: Query API - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

FastAPI exposes clean, town-scoped GeoJSON, time-series, and KPI endpoints that the frontend can consume without ever touching the database directly. Requirements: PLAT-03 (NGSI-LD compatible API), PLAT-04 (data source attribution), PLAT-05 (connector health monitoring/staleness).

Endpoints needed:
- GET /api/layers/{domain}?town={town} → GeoJSON FeatureCollection
- GET /api/timeseries/{domain}?town={town}&start=...&end=... → time-ordered readings
- GET /api/kpi?town={town} → current KPIs across domains
- Every response includes attribution and last_updated fields
- Unknown town → 404 with clear error

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — infrastructure/API phase. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key constraints:
- NGSI-LD compatible API layer (PLAT-03) — responses should follow Smart Data Models schemas where applicable
- Data source attribution in every response (PLAT-04) — Datenlizenz Deutschland compliance
- Connector health/staleness exposed (PLAT-05) — last_successful_fetch, validation_error_count from sources table
- FastAPI already running on port 8000 with /health endpoint
- TimescaleDB hypertables: air_quality_readings, transit_positions, water_readings, energy_readings, weather_readings
- PostGIS features table with spatial data
- Town-scoped queries via town_id parameter

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- backend/app/main.py — FastAPI app with lifespan, /health endpoint
- backend/app/db.py — async_engine, AsyncSessionLocal
- backend/app/config.py — Town model, load_town()
- backend/alembic/versions/ — schema definitions for all tables

### Established Patterns
- Async SQLAlchemy with AsyncSessionLocal
- Pydantic models for all data validation
- Town-scoped via TOWN env var

### Integration Points
- New routers mount on the existing FastAPI app
- Queries hit TimescaleDB hypertables and features table
- Attribution comes from sources table metadata

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure/API phase.

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>
