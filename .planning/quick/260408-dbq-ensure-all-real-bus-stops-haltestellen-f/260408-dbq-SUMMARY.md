---
phase: quick
plan: 260408-dbq
subsystem: transit/gtfs
tags: [gtfs, bus-stops, scheduler, frontend, maplibre]
dependency_graph:
  requires: []
  provides: [gtfs-stop-features-with-routes, immediate-startup-run]
  affects: [TransitLayer, BusStopLayer, BusStopPopup, GTFSConnector, scheduler]
tech_stack:
  added: []
  patterns: [immediate-startup via next_run_time, GTFS join stop_times/trips/routes for route enrichment, MapLibre match expression for dynamic circle color]
key_files:
  created: []
  modified:
    - backend/app/scheduler.py
    - backend/app/connectors/gtfs.py
    - frontend/components/map/BusStopLayer.tsx
    - frontend/components/map/BusStopPopup.tsx
decisions:
  - next_run_time=datetime.now(utc) for poll_interval >= 3600s so stops populate on first startup
  - route enrichment is best-effort (wrapped in try/except) so GTFS feeds without full tables still work
  - dominant route type prefers train > tram > bus for color assignment
metrics:
  duration_minutes: 8
  completed_date: "2026-04-08"
  tasks_completed: 2
  files_modified: 4
---

# Quick Task 260408-dbq: Real Bus Stops (Haltestellen) on Map Summary

**One-liner:** GTFS stop features now populate on backend startup with route_names/route_type_color properties; BusStopLayer shows colored circles with name labels at zoom 14+; BusStopPopup renders serving line badges.

## What Was Built

### Task 1 — Scheduler immediate-run + stop route enrichment

**scheduler.py:** Added `next_run_time=datetime.now(timezone.utc)` for any connector with `poll_interval_seconds >= 3600`. This ensures GTFSConnector (7-day interval), HeatDemandConnector, OsmBuildingsConnector, and similar heavy connectors fire on container startup rather than waiting their full interval.

**gtfs.py:** After bbox-filtering stops, the connector now joins `stop_times` -> `trips` -> `routes` to build a `stop_id -> set[route_short_name]` mapping and a `stop_id -> set[route_type]` mapping. Each stop Observation receives:
- `route_names`: comma-separated sorted list of line short names serving that stop
- `route_type_color`: hex color based on dominant mode (train=#c62828, tram=#2e7d32, bus=#1565c0)

Route enrichment is wrapped in a best-effort try/except so feeds lacking complete tables still produce valid stop features.

### Task 2 — BusStopLayer and BusStopPopup visual enhancement

**BusStopLayer.tsx:** Circle paint now uses a MapLibre `match` expression on `route_type_color` to color-code stops by transport mode. Circle radius increased to 5px. Added a symbol layer for stop name labels at zoom >= 14 with text halo for readability. Both layers respect the `visible` prop.

**BusStopPopup.tsx:** Parses `route_names` comma-separated string and renders each line as a colored pill badge using `lineColor()` from BusPositionLayer for consistent per-line colors across the UI.

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- TypeScript compile: `npx tsc --noEmit` — no errors
- Python syntax check: `ast.parse` on both modified files — clean
- Import check (with mocked gtfs_kit): GTFSConnector and setup_scheduler import successfully; run_now logic confirmed present

## Auto-approved Checkpoint

checkpoint:human-verify auto-approved (auto_advance=true).

Verification steps for manual confirmation:
1. Restart backend container: `docker compose restart backend`
2. Wait ~60s for GTFS download and parse
3. `curl -s "http://localhost:8000/api/layers/transit?town=aalen&feature_type=stop" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Stops: {len(d[\"features\"])}')"` should return > 0
4. Open http://localhost:4000, enable transit layer — colored stop circles should appear
5. Zoom to 14+ — stop name labels appear
6. Click a stop — popup shows name + colored line badges

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 0adec02 | feat(quick-260408-dbq): immediate startup run for long-interval connectors + enrich stop features |
| 2 | 8514732 | feat(quick-260408-dbq): enhance BusStopLayer visuals + BusStopPopup with route badges |

## Self-Check: PASSED
