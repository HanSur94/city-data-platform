# Phase 1: Foundation - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

A running local environment with correct schema, town config, and connector abstraction that all future work builds on. Docker Compose starts PostgreSQL + TimescaleDB + PostGIS + FastAPI. Alembic migration creates domain hypertables, features spatial table, towns/sources config tables. Town config via YAML files (aalen.yaml, example.yaml). BaseConnector abstract class defined. BKG VG250 administrative boundaries loaded.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure infrastructure phase. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key constraints from PROJECT.md:
- Hybrid architecture: own FastAPI backend + TimescaleDB/PostGIS + NGSI-LD compatible API
- Town-config-driven from the start (PLAT-01)
- Docker Compose self-hosted deployment (PLAT-02)
- Plugin-based connector architecture with BaseConnector pattern (PLAT-06)
- TimescaleDB for time-series (PLAT-07), PostGIS for spatial (PLAT-08)
- Frontend runs on port 4000 (not 3000 — Grafana occupies 3000 on target system)
- Smart Data Models schemas for NGSI-LD compatibility (PLAT-03 — Phase 3)

</decisions>

<code_context>
## Existing Code Insights

Greenfield project — no existing code. Empty git repository with .planning/ directory only.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase. Refer to ROADMAP phase description and success criteria.

</specifics>

<deferred>
## Deferred Ideas

None — infrastructure phase.

</deferred>
