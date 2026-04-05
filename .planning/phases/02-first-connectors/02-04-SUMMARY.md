---
phase: 02-first-connectors
plan: "04"
subsystem: backend/connectors
tags: [gtfs, transit, connector, tdd, bbox-filter, postgis]
dependency_graph:
  requires: [02-01]
  provides: [GTFSConnector, transit stop features, route shape features]
  affects: [features table, transit_positions (NOT written)]
tech_stack:
  added: [gtfs-kit 12.0.3]
  patterns: [TDD RED-GREEN, temp-file-for-gtfs-kit, bbox-filter-after-parse, upsert_feature]
key_files:
  created:
    - backend/app/connectors/gtfs.py
    - backend/tests/connectors/test_gtfs.py
  modified:
    - backend/pyproject.toml
decisions:
  - "gtfs-kit 12.x requires Path/str not BytesIO — use tempfile.NamedTemporaryFile"
  - "GTFS connector does NOT call persist() — stops/shapes are static features not time-series positions"
  - "Shapes included if ANY point within bbox (not all); stops filtered on lat+lon range"
metrics:
  duration_seconds: 135
  completed_date: "2026-04-05T18:57:56Z"
  tasks_completed: 1
  files_created: 2
  files_modified: 1
---

# Phase 02 Plan 04: GTFSConnector (GTFS Stops + Shapes) Summary

GTFSConnector downloads NVBW bwgesamt GTFS zip via httpx, bbox-filters stops and route shapes to Aalen bounds, and upserts them as Point/LineString features in the features table using gtfs-kit 12 with a temp-file workaround.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | GTFSConnector test file | a4a74a2 | backend/tests/connectors/test_gtfs.py, backend/pyproject.toml |
| 1 (GREEN) | GTFSConnector implementation | 883bbdc | backend/app/connectors/gtfs.py |

## Verification

```
cd backend && uv run pytest tests/connectors/test_gtfs.py -v -m "not slow"
# 4 passed in 0.71s — no network required
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] gtfs-kit 12.x does not accept BytesIO**
- **Found during:** TDD GREEN phase
- **Issue:** Plan specified `gtfs_kit.read_feed(io.BytesIO(raw), dist_units="km")` but gtfs-kit 12.0.3 signature is `read_feed(path_or_url: Path | str, dist_units: str)` — passing BytesIO raises `TypeError: expected str, bytes or os.PathLike object, not BytesIO`
- **Fix:** Write raw bytes to a `tempfile.NamedTemporaryFile(suffix=".zip")`, pass the Path to gtfs_kit, then unlink the temp file in a finally block
- **Files modified:** backend/app/connectors/gtfs.py
- **Commit:** 883bbdc

**2. [Rule 1 - Bug] feed.stops is None when GTFS contains no stops**
- **Found during:** TDD GREEN — `test_shape_outside_bbox_excluded` creates a fixture with shapes but no stops
- **Issue:** `feed.stops` returns `None` (not empty DataFrame) when no stops are in the GTFS feed; accessing `.stop_lat` on None raises AttributeError
- **Fix:** Added `if feed.stops is None or feed.stops.empty:` guard before filtering
- **Files modified:** backend/app/connectors/gtfs.py
- **Commit:** 883bbdc

## Known Stubs

None — GTFSConnector.run() is not wired to the APScheduler yet (that is Phase 02-01's scheduler). The connector logic itself is complete and unit tested.

## Key Decisions

- **gtfs-kit temp file pattern:** Since gtfs-kit 12.x accepts only `Path | str`, all GTFS bytes must be written to a temp file first. The temp file is always deleted in a `finally` block to avoid leaking disk space even if parsing fails.
- **No persist() call:** Transit stops and route shapes are static geospatial features — they belong in the `features` table, not `transit_positions`. `run()` calls `upsert_feature()` for each observation and then `_update_staleness()`.
- **Shape bbox logic:** A shape is included if ANY of its points lies within the Aalen bbox. This captures routes that pass through Aalen even if they start or end elsewhere.

## Self-Check: PASSED

- backend/app/connectors/gtfs.py: FOUND
- backend/tests/connectors/test_gtfs.py: FOUND
- RED commit a4a74a2: FOUND
- GREEN commit 883bbdc: FOUND
