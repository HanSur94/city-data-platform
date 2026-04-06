---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: Completed 05-dashboard/05-07-PLAN.md
last_updated: "2026-04-06T00:03:17.729Z"
last_activity: 2026-04-06 -- Phase 06 execution started
progress:
  total_phases: 10
  completed_phases: 4
  total_plans: 28
  completed_plans: 22
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-05)

**Core value:** Citizens and city officials can see all publicly available city data in one place, on a map, updated live — no technical expertise required.
**Current focus:** Phase 06 — weather-environment

## Current Position

Phase: 06 (weather-environment) — EXECUTING
Plan: 1 of 5
Status: Executing Phase 06
Last activity: 2026-04-06 -- Phase 06 execution started

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: none yet
- Trend: -

*Updated after each plan completion*
| Phase 01-foundation P03 | 151 | 2 tasks | 9 files |
| Phase 01-foundation P04 | 3 | 2 tasks | 4 files |
| Phase 02-first-connectors P04 | 135 | 1 tasks | 3 files |
| Phase 02-first-connectors P05 | 3 | 2 tasks | 4 files |
| Phase 03-query-api P03 | 20 | 2 tasks | 6 files |
| Phase 04-map-frontend P02 | 3 | 2 tasks | 8 files |
| Phase 04-map-frontend P03 | 525526 | 2 tasks | 6 files |
| Phase 05-dashboard P05 | 2 | 2 tasks | 3 files |
| Phase 05-dashboard P06 | 3 | 2 tasks | 2 files |
| Phase 05-dashboard P07 | 2 | 1 tasks | 1 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Init: Hybrid architecture chosen — FastAPI + TimescaleDB + PostGIS + NGSI-LD compat layer (not full FIWARE Orion)
- Init: Frontend on port 4000 (Grafana occupies 3000 on target system)
- Init: Town config YAML from line one — Aalen is `CITY_ID=aalen`, never hardcoded
- Init: Build order: schema first, then one vertical slice (transit + air quality), then expand
- [Phase 01-foundation]: Town id validated as alphanumeric slug via Pydantic field_validator in config.py
- [Phase 01-foundation]: BaseConnector.persist() is no-op in Phase 1 — SQLAlchemy session injection deferred to Phase 2
- [Phase 01-foundation]: Observation is a dataclass (not Pydantic model) — no DB schema coupling in Phase 1
- [Phase 01-foundation]: Use json.dumps() for JSONB properties in load_vg250.py — psycopg2 COPY requires valid JSON strings not Python dict repr
- [Phase 01-foundation]: FastAPI lifespan loads town from TOWN env var, fails fast on missing/invalid config — get_current_town() dependency pattern established
- [Phase 02-first-connectors]: gtfs-kit 12.x requires Path/str not BytesIO — use tempfile.NamedTemporaryFile for in-memory GTFS zip parsing
- [Phase 02-first-connectors]: GTFSConnector does NOT call persist() — transit stops/shapes are static features in features table, not time-series positions
- [Phase 02-first-connectors]: GTFSRealtimeConnector overrides run() to upsert features before normalize() — transit_positions.feature_id must be UUID, not trip_id string
- [Phase 02-first-connectors]: gtfs_rt_url empty string = graceful skip with log warning (NVBW GTFS-RT URL unconfirmed)
- [Phase 03-query-api]: asyncio_default_test_loop_scope=session required for async tests sharing APScheduler singleton
- [Phase 03-query-api]: KPI DB queries wrapped in try/except for graceful degradation in test environments without TimescaleDB
- [Phase 04-map-frontend]: page.tsx is use-client to hold layerVisibility state; MapView loaded with next/dynamic ssr:false to prevent window-is-not-defined SSR errors
- [Phase 04-map-frontend]: Use CircleLayerSpecification (not CircleLayer) — actual exported type from react-map-gl/maplibre
- [Phase 04-map-frontend]: base-ui TooltipTrigger uses render prop not asChild — different API from Radix UI
- [Phase 05-dashboard]: Base UI PopoverTrigger uses render prop not asChild — DateRangePicker trigger uses native button with manual styling
- [Phase 05-dashboard]: onValueChange for Base UI Slider receives (value: number | number[], eventDetails) — normalised to number via Array.isArray guard
- [Phase 05-dashboard]: MapView wrapped in relative div to allow absolute badge overlay without breaking Map fill
- [Phase 05-dashboard]: historicalTimestamp is optional prop on MapView — existing callers need no change until Plan 07
- [Phase 05-dashboard]: page.tsx: useUrlState is single source of truth — no local useState for layerVisibility, domain, dateRange, or timestamp
- [Phase 05-dashboard]: Suspense + HomeInner pattern for pages using useSearchParams-based hooks — enforced in page.tsx Plan 07

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 2: LUBW air quality station IDs for Aalen must be confirmed before connector scope is finalized
- Phase 2: MobiData BW GTFS-RT feed quality needs validation step (GTFS Canonical Validator) before transit connector is marked complete
- Phase 7: MDM/Mobilithek traffic feed access may require registration — verify before committing; BASt count data is fallback
- Phase 7: Stadtwerke APIs for water/electricity/wastewater are highly fragmented — may require per-Aalen discovery spike

## Session Continuity

Last session: 2026-04-05T23:36:46.779Z
Stopped at: Completed 05-dashboard/05-07-PLAN.md
Resume file: None
