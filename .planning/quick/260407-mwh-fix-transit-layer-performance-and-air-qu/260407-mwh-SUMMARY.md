---
phase: quick-260407-mwh
plan: 01
subsystem: backend-api, frontend-components, gtfs-rt-connector
tags: [performance, bug-fix, transit, air-quality, asyncpg, gtfs-rt, feature-type]
dependency_graph:
  requires: []
  provides: [feature_type-server-filter, asyncpg-null-fix, gtfs-rt-feature-type]
  affects: [transit-layer, air-quality-layer, traffic-layer, demographics-layer, BusPositionLayer, BusRouteLayer]
tech_stack:
  added: []
  patterns:
    - "CAST(:at AS timestamptz) for asyncpg NULL parameter disambiguation"
    - "f-string SQL with {ft_filter} injection for optional WHERE clauses"
    - "featureType optional param threading: fetchLayer -> useLayerData -> component"
key_files:
  created:
    - backend/scripts/cleanup_stale_transit.sql
  modified:
    - backend/app/connectors/gtfs_rt.py
    - backend/app/routers/layers.py
    - frontend/lib/api.ts
    - frontend/hooks/useLayerData.ts
    - frontend/components/map/BusPositionLayer.tsx
    - frontend/components/map/BusRouteLayer.tsx
decisions:
  - "Transit SQL uses f-string injection (same pattern as air_quality) rather than separate endpoint for feature_type filter"
  - "BusRouteLayer uses useLayerData with featureType param rather than inline fetch to keep consistent hook usage"
  - "cleanup_stale_transit.sql is manual one-time script — not automated migration to avoid accidental data loss"
metrics:
  duration_seconds: 185
  completed_date: "2026-04-07"
  tasks_completed: 2
  files_modified: 6
  files_created: 1
---

# Quick Task 260407-mwh: Fix Transit Layer Performance and Air Quality NULL Bug

**One-liner:** Server-side feature_type filtering on transit endpoint (161K -> ~240 features) plus CAST(:at AS timestamptz) fix for asyncpg NULL ambiguity in air_quality, traffic, and demographics.

## Objective

Fix three related bugs:
1. Transit layer returned all 161K features (25MB/17s) — no server-side filter
2. Air quality, traffic, and demographics layers returned 500 errors when `at=None` (asyncpg AmbiguousParameterError)
3. GTFS-RT connector created vehicle/trip_update features without `feature_type` property — preventing future server-side filtering

## Tasks Completed

### Task 1: Backend fixes (commit `51de9a0`)

**gtfs_rt.py:**
- Added `"feature_type": "bus_position"` to vehicle feature properties in `run()` upsert call
- Added `"feature_type": "trip_update"` to trip_update feature properties in `run()` upsert call

**layers.py — transit query:**
- Added optional `feature_type` query param filter via f-string injection (`{ft_filter}`)
- When `feature_type` is provided: adds `AND f.properties->>'feature_type' = :feature_type` to WHERE clause
- When not provided: returns all transit features (backward compatible)

**layers.py — asyncpg NULL param fix:**
- Replaced `AND (:at IS NULL OR time <= :at)` with `AND (CAST(:at AS timestamptz) IS NULL OR time <= CAST(:at AS timestamptz))` in all 3 LATERAL subqueries (air_quality, traffic, demographics)
- asyncpg cannot infer type of a NULL parameter — explicit CAST resolves the ambiguity while preserving semantics

### Task 2: Frontend + DB cleanup (commit `491d666`)

**frontend/lib/api.ts:**
- Added optional `featureType?: string` parameter to `fetchLayer`
- Appends as `feature_type` query param when provided

**frontend/hooks/useLayerData.ts:**
- Added optional `featureType?: string` parameter
- Passes through to `fetchLayer` call
- Added `featureType` to `useEffect` dependency array

**frontend/components/map/BusPositionLayer.tsx:**
- Changed `fetchLayer('transit', town)` to `fetchLayer('transit', town, null, 'bus_position')`
- Response drops from ~25MB (161K features) to ~500KB (~240 features) every 30s refresh

**frontend/components/map/BusRouteLayer.tsx:**
- Changed `useLayerData('transit', town)` to `useLayerData('transit', town, undefined, 'shape')`
- Now fetches only route shape features instead of all transit features

**backend/scripts/cleanup_stale_transit.sql:**
- One-time cleanup script to delete stale `POINT(0 0)` trip_update placeholders lacking `feature_type`
- Must be run manually: `psql -U citydata -d citydata -f backend/scripts/cleanup_stale_transit.sql`

## Deviations from Plan

None — plan executed exactly as written.

The plan's verification assertion (`assert 'feature_type' in lsrc.split('transit')[1].split('elif')[0]`) had a false-negative due to the word "transit" appearing earlier in the file (in the `feature_type` Query description string). The actual code is correct — verified with a robust index-based check.

## Known Stubs

None — all data flows are wired. The cleanup SQL is intentionally manual (not a stub).

## Post-Deployment Steps

1. Rebuild Docker containers to pick up backend and frontend changes
2. Run `backend/scripts/cleanup_stale_transit.sql` once against the database to remove ~161K stale `POINT(0 0)` trip_update placeholder features

## Self-Check: PASSED

Files verified present:
- backend/app/connectors/gtfs_rt.py — modified
- backend/app/routers/layers.py — modified
- frontend/lib/api.ts — modified
- frontend/hooks/useLayerData.ts — modified
- frontend/components/map/BusPositionLayer.tsx — modified
- frontend/components/map/BusRouteLayer.tsx — modified
- backend/scripts/cleanup_stale_transit.sql — created

Commits verified:
- 51de9a0 — backend fixes
- 491d666 — frontend + cleanup script
