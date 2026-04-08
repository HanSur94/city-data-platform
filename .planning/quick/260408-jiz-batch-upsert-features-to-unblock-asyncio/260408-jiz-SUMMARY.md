---
phase: quick-260408-jiz
plan: "01"
subsystem: backend/connectors
tags: [performance, async, database, connectors, gtfs, bus]
dependency_graph:
  requires: []
  provides: [batch_upsert_features on BaseConnector]
  affects: [GTFSConnector, BusInterpolationConnector, GTFSRealtimeConnector, asyncio event loop availability]
tech_stack:
  added: []
  patterns: [batch upsert with per-chunk commit and asyncio.sleep(0) yield]
key_files:
  created: []
  modified:
    - backend/app/connectors/base.py
    - backend/app/connectors/gtfs.py
    - backend/app/connectors/bus_interpolation.py
    - backend/app/connectors/gtfs_rt.py
decisions:
  - Iterate individual statements within each chunk (not executemany) to collect RETURNING UUIDs per row
  - Single AsyncSessionLocal for entire batch to avoid connection pool exhaustion
  - asyncio.sleep(0) after each chunk commit to yield to TomTom and other polling connectors
  - Keep original upsert_feature() intact for low-volume connectors (1-5 features)
metrics:
  duration: "~8 minutes"
  completed: "2026-04-08"
  tasks_completed: 2
  files_modified: 4
---

# Phase quick-260408-jiz Plan 01: Batch Upsert Features Summary

**One-liner:** Added `batch_upsert_features()` to BaseConnector with per-chunk commit and asyncio.sleep(0) yield, migrating GTFS (~2000 features), BusInterpolation, and GTFSRealtime connectors from ~85k individual DB sessions per cycle to ~170 batched commits.

## What Was Built

### Task 1: batch_upsert_features on BaseConnector (ae0332f)

Added `async def batch_upsert_features(features, batch_size=500) -> dict[str, str]` to `BaseConnector` in `backend/app/connectors/base.py` immediately after the existing `upsert_feature()` method.

Key implementation details:
- Opens ONE `AsyncSessionLocal` for the entire batch (vs. one per feature previously)
- Loops features in chunks of `batch_size` (default 500)
- Executes the same INSERT ... ON CONFLICT ... RETURNING SQL as `upsert_feature()`
- After each chunk: `await session.commit()` then `await asyncio.sleep(0)` — the sleep(0) yields the event loop so TomTom and other connectors can run between batches
- Collects `source_id -> str(UUID)` mapping and returns it
- Original `upsert_feature()` left completely untouched

### Task 2: Migrate three connectors (86d4ebd)

**gtfs.py** (`run()` lines 247-263):
- Replaced `for item in normalized: await self.upsert_feature(...)` loop
- Now builds `features = [(source_id, "transit", wkt, properties), ...]` list and calls `await self.batch_upsert_features(features)` once
- GTFS typically upserts ~2000 stop/shape features — this reduces from 2000 sessions to 4 chunk commits

**bus_interpolation.py** (loop around line 394):
- Restructured to collect `features_to_upsert` and `pending_obs` during the position loop
- After loop: `feature_ids_map = await self.batch_upsert_features(features_to_upsert)`
- Then builds observations using `feature_ids_map[src_id]` for each pending observation
- Preserves identical Observation construction, just deferred until after batch upsert

**gtfs_rt.py** (`run()` lines 154-188):
- Replaced two individual `await self.upsert_feature(...)` calls with list accumulation
- Tracks `entity_source_ids: dict[str, str]` (entity.id -> source_id) during entity loop
- After loop: batch upserts, rebuilds `feature_ids: dict[str, str]` from `feature_ids_map` using the entity_source_ids mapping
- Passes `feature_ids` to `self.normalize()` as before — no downstream change

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: backend/app/connectors/base.py
- FOUND: backend/app/connectors/gtfs.py
- FOUND: backend/app/connectors/bus_interpolation.py
- FOUND: backend/app/connectors/gtfs_rt.py
- FOUND: commit ae0332f (Task 1)
- FOUND: commit 86d4ebd (Task 2)
