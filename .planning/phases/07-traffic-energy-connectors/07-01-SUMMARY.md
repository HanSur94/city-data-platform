---
phase: 07-traffic-energy-connectors
plan: "01"
subsystem: backend/connectors
tags:
  - traffic
  - energy
  - alembic
  - timescaledb
  - kpi-schemas
  - test-stubs
dependency_graph:
  requires:
    - "06-weather-environment/06-04-SUMMARY.md"
  provides:
    - "traffic_readings hypertable (migration 003)"
    - "BaseConnector.persist() traffic branch"
    - "TrafficKPI + EnergyKPI Pydantic/TS models"
    - "Wave 0 test stubs for BASt, Autobahn, MobiData BW, SMARD, MaStR connectors"
  affects:
    - "backend/app/connectors/base.py"
    - "backend/app/schemas/responses.py"
    - "frontend/types/kpi.ts"
tech_stack:
  added:
    - "migration 003 (traffic_readings hypertable with 2yr retention)"
  patterns:
    - "TimescaleDB by_range('time') hypertable creation"
    - "ON CONFLICT DO NOTHING for traffic INSERT (idempotent)"
    - "Optional KPI fields (default None) for backward compat"
key_files:
  created:
    - backend/alembic/versions/003_traffic_readings.py
    - backend/tests/connectors/test_bast.py
    - backend/tests/connectors/test_autobahn.py
    - backend/tests/connectors/test_mobidata_bw.py
    - backend/tests/connectors/test_smard.py
    - backend/tests/connectors/test_mastr.py
  modified:
    - backend/app/connectors/base.py
    - backend/app/schemas/geojson.py
    - backend/app/schemas/responses.py
    - frontend/types/kpi.ts
decisions:
  - "traffic_readings uses ON CONFLICT DO NOTHING (idempotent ingest — re-running connectors safe)"
  - "TrafficKPI/EnergyKPI are optional (None) in KPIResponse so existing callers are backward-compatible"
  - "VALID_DOMAINS now has 6 domains: air_quality, transit, weather, water, energy, traffic"
metrics:
  duration_minutes: 8
  completed_date: "2026-04-06"
  tasks_completed: 2
  tasks_total: 2
  files_created: 7
  files_modified: 4
---

# Phase 7 Plan 01: Traffic & Energy Foundation Summary

**One-liner:** Alembic migration 003 creates traffic_readings hypertable with 2-year retention; BaseConnector.persist() gains traffic branch; TrafficKPI/EnergyKPI types added to backend (Pydantic) and frontend (TypeScript); 12 Wave-0 test stubs across 5 connector files in RED/skip state.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Alembic migration 003 + persist() traffic branch + domain registration | 7e68747 | 003_traffic_readings.py, base.py, geojson.py |
| 2 | Backend + frontend KPI schemas + Wave 0 test stubs | 78ef953 | responses.py, kpi.ts, 5 test files |

## What Was Built

### Task 1: Infrastructure Layer

**`backend/alembic/versions/003_traffic_readings.py`** — New hypertable migration following the 002 pattern:
- Columns: `time`, `feature_id` (FK to features), `vehicle_count_total` (Kfz/h), `vehicle_count_hgv` (SV/h), `speed_avg_kmh`, `congestion_level`
- Uses `by_range('time')` (TimescaleDB v2.x API, not positional string)
- 2-year retention policy

**`backend/app/connectors/base.py`** — `persist()` extended with `elif obs.domain == "traffic"` branch:
- Inserts into `traffic_readings` with ON CONFLICT DO NOTHING
- Observation domain docstring updated to include "traffic"

**`backend/app/schemas/geojson.py`** — Domain and attribution updates:
- VALID_DOMAINS: 5 → 6 domains (added "traffic")
- CONNECTOR_ATTRIBUTION: 7 → 12 entries (added BastConnector, AutobahnConnector, MobiDataBWConnector, SmardConnector, MastrConnector)

### Task 2: Type System + Test Stubs

**`backend/app/schemas/responses.py`** — New KPI models:
- `TrafficKPI`: active_roadworks (int), flow_status (str|None), last_updated
- `EnergyKPI`: renewable_percent, generation_mix (dict[str, float]), wholesale_price_eur_mwh, last_updated
- `KPIResponse` extended with optional `traffic: TrafficKPI | None = None` and `energy: EnergyKPI | None = None`

**`frontend/types/kpi.ts`** — Mirrored TypeScript interfaces:
- `TrafficKPI` and `EnergyKPI` interfaces added
- `KPIResponse` extended with `traffic: TrafficKPI | null` and `energy: EnergyKPI | null`

**Wave 0 Test Stubs** (12 stubs across 5 files, all in RED/skip state):
- `test_bast.py`: 3 stubs (CSV parse, congestion level, source_id format)
- `test_autobahn.py`: 2 stubs (roadworks parse, 50km distance filter)
- `test_mobidata_bw.py`: 2 stubs (CSV parse, shared BASt output format)
- `test_smard.py`: 3 stubs (two-step fetch, null filtering, renewable % calc)
- `test_mastr.py`: 2 stubs (Landkreis filter, Lage field mapping)

## Verification Results

```
migration parses OK
domains+attribution OK
TrafficKPI OK / EnergyKPI OK / KPIResponse optional fields OK
12 stubs: ssssssssssss (12 skipped in 0.26s)
VALID_DOMAINS check passed
TrafficKPI/EnergyKPI import passed
```

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

**Note on plan verification command:** The plan's `<automated>` verify for Task 2 used `KPIResponse(town='test', air_quality=None, ...)` which fails because existing KPI fields are non-optional. The code itself is correct; the verification command in the plan had incorrect test data. Replaced with a proper instantiation using valid KPI objects.

## Known Stubs

The 12 test stubs are intentional Wave-0 RED stubs. They contain `pytest.skip("RED: ... not implemented")` which is the TDD workflow design for Plans 02/03. These stubs are NOT functionality stubs — they're test scaffolding to enable TDD in subsequent plans.

## Self-Check

Files created/exist:
- `backend/alembic/versions/003_traffic_readings.py` ✓
- `backend/tests/connectors/test_bast.py` ✓
- `backend/tests/connectors/test_autobahn.py` ✓
- `backend/tests/connectors/test_mobidata_bw.py` ✓
- `backend/tests/connectors/test_smard.py` ✓
- `backend/tests/connectors/test_mastr.py` ✓

Commits:
- 7e68747 (Task 1) ✓
- 78ef953 (Task 2) ✓
