---
phase: 07-traffic-energy-connectors
plan: "02"
subsystem: backend/connectors
tags:
  - traffic
  - bast
  - autobahn
  - mobidata-bw
  - csv-parsing
  - haversine
  - tdd
dependency_graph:
  requires:
    - "07-traffic-energy-connectors/07-01-SUMMARY.md"
  provides:
    - "BastConnector: BASt annual traffic count CSV parser + congestion levels"
    - "AutobahnConnector: A7+A6 roadworks/closures with 50km haversine filter"
    - "MobiDataBWConnector: BW traffic count connector sharing BASt parse logic"
    - "_compute_congestion: free/moderate/congested classification"
    - "_haversine: great-circle distance calculation"
  affects:
    - "backend/app/connectors/bast.py"
    - "backend/app/connectors/autobahn.py"
    - "backend/app/connectors/mobidata_bw.py"
tech_stack:
  added: []
  patterns:
    - "windows-1252 CSV decoding via bytes.decode('windows-1252', errors='replace')"
    - "Shared parse logic: MobiDataBWConnector imports _parse_bast_csv/_compute_congestion from bast.py"
    - "Features-only connector pattern: normalize() returns [], all inserts via upsert_feature()"
    - "Haversine distance filtering in run() before upsert"
key_files:
  created:
    - backend/app/connectors/bast.py
    - backend/app/connectors/autobahn.py
    - backend/app/connectors/mobidata_bw.py
  modified:
    - backend/tests/connectors/test_bast.py
    - backend/tests/connectors/test_autobahn.py
    - backend/tests/connectors/test_mobidata_bw.py
decisions:
  - "MobiDataBWConnector imports _parse_bast_csv and _compute_congestion from bast.py — no code duplication"
  - "AutobahnConnector.normalize() returns [] — roadworks/closures are features-only (no time-series)"
  - "BASt bbox filter: lat 48.56-49.10, lon 9.77-10.42 (Aalen center +20km buffer)"
  - "Autobahn haversine filter: 50km radius from AALEN_CENTER (48.84, 10.09)"
  - "congestion_level thresholds: <50% capacity = free, 50-80% = moderate, >80% = congested"
  - "LANE_CAPACITY_VEH_H = 800 (standard German autobahn per-lane-per-hour estimate)"
metrics:
  duration_minutes: 4
  completed_date: "2026-04-06"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 3
---

# Phase 7 Plan 02: Traffic Connectors (BASt, Autobahn, MobiData BW) Summary

**One-liner:** BastConnector parses windows-1252 BASt CSV with congestion levels (free/moderate/congested); AutobahnConnector fetches A7+A6 roadworks/closures filtered to 50km via haversine; MobiDataBWConnector reuses BASt parse logic; 23 unit tests GREEN.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | BASt + MobiData BW traffic count connectors | 36abe6b | bast.py, mobidata_bw.py, test_bast.py, test_mobidata_bw.py |
| 2 | Autobahn API connector for roadworks and closures | 37b4534 | autobahn.py, test_autobahn.py |

## What Was Built

### Task 1: BASt + MobiData BW Connectors

**`backend/app/connectors/bast.py`** — BASt annual traffic count connector:
- `BAST_CSV_URL`: Points to 2023 annual hourly data CSV
- `_compute_congestion(count, lanes) -> str`: Returns "free" (<50% capacity), "moderate" (50-80%), "congested" (>80%) based on `count / (lanes * 800)`
- `_parse_bast_csv(raw: bytes) -> list[dict]`: Decodes windows-1252, parses semicolon CSV, filters to Aalen bbox+20km (lat 48.56-49.10, lon 9.77-10.42)
- `BastConnector.fetch()`: GET BASt CSV URL, return bytes
- `BastConnector.normalize()`: Parse CSV rows into Observations with domain="traffic", values keys: vehicle_count_total, vehicle_count_hgv, speed_avg_kmh, congestion_level
- `BastConnector.run()`: Upsert features → normalize → persist to traffic_readings → update staleness

**`backend/app/connectors/mobidata_bw.py`** — MobiData BW connector:
- `MobiDataBWConnector`: Inherits BaseConnector, imports `_parse_bast_csv` + `_compute_congestion` from bast.py
- Same run() pattern: upsert features → normalize → persist → update staleness
- source_id format: `mobidata_bw:{station_id}`

### Task 2: Autobahn Connector

**`backend/app/connectors/autobahn.py`** — Autobahn GmbH API connector:
- `AUTOBAHN_BASE`: `https://verkehr.autobahn.de/o/autobahn`
- `ROADS = ["A7", "A6"]`
- `AALEN_CENTER = (48.84, 10.09)`, `MAX_DISTANCE_KM = 50`
- `_haversine(lat1, lon1, lat2, lon2) -> float`: Haversine great-circle distance in km
- `AutobahnConnector.fetch()`: Fetches roadworks + closures for each road (4 HTTP calls: A7 roadworks, A7 closures, A6 roadworks, A6 closures), combines into JSON bytes
- `AutobahnConnector.normalize()`: Returns `[]` — features-only, no time-series
- `AutobahnConnector.run()`: Fetch → parse → filter by haversine distance → upsert_feature() → _update_staleness()
  - Properties: title, subtitle, description, is_blocked, type ("closure"/"roadwork"), extent, attribution, distance_km

## Verification Results

```
23 passed in 0.23s
All 3 connectors importable: BastConnector, AutobahnConnector, MobiDataBWConnector
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Float precision in geometry WKT coordinate assertion**
- **Found during:** Task 2 tests
- **Issue:** Test asserted `"10.20" in geometry` but `float("10.20")` becomes `10.2`, rendering as `"POINT(10.2 48.84)"`
- **Fix:** Changed assertion to `"10.2" in rw["geometry"]` (matches both 10.2 and 10.20)
- **Files modified:** backend/tests/connectors/test_autobahn.py
- **Commit:** 37b4534

## Known Stubs

None. All connector functionality is fully implemented and tested.

## Self-Check: PASSED

Files exist:
- `backend/app/connectors/bast.py` ✓
- `backend/app/connectors/autobahn.py` ✓
- `backend/app/connectors/mobidata_bw.py` ✓
- `backend/tests/connectors/test_bast.py` ✓
- `backend/tests/connectors/test_autobahn.py` ✓
- `backend/tests/connectors/test_mobidata_bw.py` ✓

Commits:
- 36abe6b (Task 1: BASt + MobiData BW) ✓
- 37b4534 (Task 2: Autobahn) ✓
