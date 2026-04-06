---
phase: 08-community-infrastructure-connectors
plan: "02"
subsystem: backend-connectors
tags: [ev-charging, bnetza, solar, lubw, infrastructure, csv-parsing, yaml-config]
dependency_graph:
  requires: [backend/app/connectors/base.py, backend/app/connectors/mastr.py]
  provides: [LadesaeulenConnector, SolarPotentialConnector]
  affects: [towns/aalen.yaml, backend/app/connectors/__init__.py]
tech_stack:
  added: [csv.DictReader (stdlib), xml.etree.ElementTree (stdlib)]
  patterns: [24h-file-cache, features-only-connector, graceful-deferral-probe]
key_files:
  created:
    - backend/app/connectors/ladesaeulen.py
    - backend/app/connectors/solar_potential.py
    - backend/tests/connectors/test_ladesaeulen.py
  modified:
    - backend/app/connectors/__init__.py
    - towns/aalen.yaml
decisions:
  - "_parse_german_float uses val.replace(',', '.') then float() — returns None on empty/invalid, not 0.0"
  - "LadesaeulenConnector source_id uses PLZ+Strasse+Hausnummer for deduplication; falls back to row index"
  - "SolarPotentialConnector is probe-only — no features upserted; wms_url stored as class attribute for frontend"
  - "aalen.yaml SolarPotentialConnector enabled: false — only enable after WMS URL confirmed at runtime"
  - "INFR-04 covered by Phase 7 MaStrConnector solar_rooftop classification — no new connector needed"
  - "__init__.py kept minimal — only exports Phase 8 connectors to avoid import chain failures from optional deps"
metrics:
  duration_seconds: 222
  completed_date: "2026-04-06"
  tasks_completed: 2
  files_created: 3
  files_modified: 2
---

# Phase 8 Plan 02: EV Charging + Solar Potential Connectors Summary

**One-liner:** BNetzA EV charging CSV connector with German comma-decimal parsing and Ostalbkreis filtering, plus LUBW solar WMS probe connector with graceful deferral.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for LadesaeulenConnector | 7e01648 | backend/tests/connectors/test_ladesaeulen.py |
| 1 (GREEN) | LadesaeulenConnector implementation | 23c7985 | backend/app/connectors/ladesaeulen.py, __init__.py |
| 2 | SolarPotentialConnector + aalen.yaml wiring | d74040a | backend/app/connectors/solar_potential.py, __init__.py, towns/aalen.yaml |

## What Was Built

### LadesaeulenConnector (INFR-02)

- Downloads BNetzA Ladesäulenregister CSV (25MB+) with 24h local cache
- `_parse_german_float(val)` converts comma-decimal to Python float, returns None for empty/invalid
- Filters rows by `Kreis/kreisfreie Stadt` == `kreis_filter` config (default: Ostalbkreis)
- Skips rows with missing/unparseable coordinates (Breitengrad/Laengengrad)
- Aggregates plug types from Steckertypen1-4 (excludes empty strings)
- Computes `max_power_kw` from P1-P4 power values
- Upserts features: `domain="infrastructure"`, `category="ev_charging"`
- Properties: operator, address, plug_types, max_power_kw, num_charging_points, charging_type

### SolarPotentialConnector (INFR-03)

- Probes LUBW RIPS-GDI WMS GetCapabilities endpoint
- If 200 + valid WMS XML with layers: logs layer names, stores WMS base URL in `self.wms_url`
- If non-200 or no layers: logs "Solar potential WMS not available — INFR-03 deferred"
- No features upserted — intentional probe for frontend WmsOverlayLayer conditional rendering
- `normalize()` returns [] (probe-only connector)
- `enabled: false` in aalen.yaml until WMS endpoint is confirmed

### aalen.yaml Phase 8 Entries

All 4 Phase 8 connectors registered:
- `OverpassCommunityConnector` (enabled: true, 86400s)
- `OverpassRoadworksConnector` (enabled: true, 3600s)
- `LadesaeulenConnector` (enabled: true, kreis_filter: Ostalbkreis)
- `SolarPotentialConnector` (enabled: false, wms_url placeholder)

### INFR-04 Coverage

INFR-04 (solar installation classification) is covered by the existing Phase 7 `MastrConnector` `solar_rooftop` classification from MaStR data. No additional connector required.

## Test Results

13 tests pass in `backend/tests/connectors/test_ladesaeulen.py`:
- `test_parse_german_float_*` — 5 tests for comma-decimal parsing edge cases
- `test_normalize_returns_empty` — features-only connector
- `test_kreis_filtering` — validates fixture row counts
- `test_run_upserts_ostalbkreis_only` — 3 of 6 rows upserted (1 filtered, 2 missing coords)
- `test_run_properties_structure` — domain, geometry, all property keys
- `test_run_plug_type_aggregation` — Typ2 and CCS present, empty strings excluded
- `test_run_max_power_calculation` — 150.0 kW from EnBW row
- `test_run_skips_missing_coordinates` — exactly 3 upserts
- `test_connector_default_kreis_filter` — defaults to Ostalbkreis

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] __init__.py kept minimal to avoid import chain failures**

- **Found during:** Task 1 GREEN phase
- **Issue:** Writing all connector imports to `__init__.py` caused `ModuleNotFoundError: No module named 'gtfs_kit'` because the gtfs connector imports gtfs_kit at module level, which is an optional heavy dependency not always available in the test environment
- **Fix:** `__init__.py` only exports LadesaeulenConnector and SolarPotentialConnector (the two Phase 8 connectors from this plan) — the file was originally empty, so this adds the minimum necessary
- **Files modified:** backend/app/connectors/__init__.py
- **Commit:** 23c7985 (updated in d74040a)

## Known Stubs

- `SolarPotentialConnector` stores `self.wms_url = ""` until WMS probe succeeds at runtime. This is intentional — the connector is `enabled: false` in aalen.yaml and INFR-03 is explicitly deferred until LUBW endpoint is confirmed.

## Self-Check: PASSED
