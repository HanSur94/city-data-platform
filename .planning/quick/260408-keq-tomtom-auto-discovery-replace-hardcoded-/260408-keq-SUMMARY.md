---
phase: quick
plan: 260408-keq
subsystem: backend/connectors
tags: [traffic, tomtom, discovery, caching, refactor]
dependency_graph:
  requires: []
  provides: [auto-discovered-tomtom-segments, segment-cache]
  affects: [backend/app/connectors/tomtom.py]
tech_stack:
  added: []
  patterns: [grid-scan-discovery, json-file-cache, frc-filtering, coordinate-dedup]
key_files:
  created: []
  modified:
    - backend/app/connectors/tomtom.py
    - backend/tests/connectors/test_tomtom.py
decisions:
  - "road_key uses 5-decimal-place rounding of first+last coordinate for dedup (deterministic across API calls)"
  - "ALLOWED_FRC = FRC0-FRC3; FRC4+ excluded as local/residential roads add noise"
  - "Cache TTL 7 days: segments don't change frequently; avoids re-discovery on every poll"
  - "asyncio.sleep(0.05) between discovery probes to be polite to TomTom API rate limits"
metrics:
  duration: "~10 minutes"
  completed: "2026-04-08T12:47:20Z"
  tasks_completed: 1
  files_changed: 2
---

# Quick 260408-keq: TomTom Auto-Discovery Replace Hardcoded Segments Summary

**One-liner:** Grid-scan discovery replacing 35 hardcoded AALEN_ROAD_SEGMENTS with dynamic FRC0-FRC3 segment detection from town.bbox + 7-day JSON cache.

## What Was Built

Replaced the hardcoded `AALEN_ROAD_SEGMENTS` list in `TomTomConnector` with automatic road segment discovery. The connector now:

1. Generates a ~800m grid of probe points from `town.bbox` using `_generate_grid_points()`
2. Queries TomTom Flow API at each probe, filters to FRC0-FRC3 (motorways through secondary roads)
3. Deduplicates segments by first+last coordinate pair via `_make_road_key()`
4. Caches discovered segments to `/tmp/tomtom_segments_{town_id}.json` with 7-day TTL
5. Subsequent polls load from cache; re-discovery happens only when cache expires

The connector is now generic — works for any configured town, not just Aalen.

## Commits

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Grid-scan discovery + cache + FRC filter + updated tests | e59376e |

## Tests

21 tests pass (13 existing + 8 new):
- `test_generate_grid_points_covers_bbox` — grid covers full bbox, all points in bounds
- `test_make_road_key_deterministic` — same coords produce same key
- `test_make_road_key_different_segments` — different coords produce different keys
- `test_discover_filters_frc4_plus` — FRC4 excluded, FRC2 kept
- `test_discover_deduplicates_same_segment` — two probes on same road → 1 segment
- `test_cache_roundtrip` — save + load preserves all segment fields
- `test_load_cache_returns_none_when_missing` — missing file → None
- `test_cache_expired_returns_none` — 8-day-old cache → None

## Deviations from Plan

None — plan executed exactly as written. (Minor fix: test used non-existent `_save_cache_to_path` patch; corrected to `patch.object(connector, "_save_cache")` during RED phase.)

## Known Stubs

None — auto-discovery is fully wired. Cache and filtering logic is complete and tested.

## Self-Check: PASSED

- `backend/app/connectors/tomtom.py` — FOUND
- `backend/tests/connectors/test_tomtom.py` — FOUND
- Commit e59376e — FOUND
- `AALEN_ROAD_SEGMENTS` count in tomtom.py: 0 (removed)
- All 21 tests pass
