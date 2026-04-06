---
phase: 7
slug: traffic-energy-connectors
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-06
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio 9.x |
| **Config file** | `backend/pyproject.toml` |
| **Quick run command** | `cd backend && pytest tests/connectors/ -x -q` |
| **Full suite command** | `cd backend && pytest -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && pytest tests/connectors/ -x -q`
- **After every plan wave:** Run `cd backend && pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 0 | TRAF-03 | unit | `pytest tests/connectors/test_bast.py -x` | ❌ W0 | ⬜ pending |
| 07-01-02 | 01 | 0 | TRAF-04 | unit | `pytest tests/connectors/test_autobahn.py -x` | ❌ W0 | ⬜ pending |
| 07-01-03 | 01 | 0 | TRAF-05 | unit | `pytest tests/connectors/test_mobidata_bw.py -x` | ❌ W0 | ⬜ pending |
| 07-01-04 | 01 | 0 | ENRG-01 | unit | `pytest tests/connectors/test_smard.py -x` | ❌ W0 | ⬜ pending |
| 07-01-05 | 01 | 0 | ENRG-02 | unit | `pytest tests/connectors/test_mastr.py -x` | ❌ W0 | ⬜ pending |
| 07-02-01 | 02 | 1 | TRAF-03 | unit | `pytest tests/connectors/test_bast.py -x` | ❌ W0 | ⬜ pending |
| 07-03-01 | 03 | 1 | TRAF-04 | unit | `pytest tests/connectors/test_autobahn.py -x` | ❌ W0 | ⬜ pending |
| 07-04-01 | 04 | 1 | TRAF-05 | unit | `pytest tests/connectors/test_mobidata_bw.py -x` | ❌ W0 | ⬜ pending |
| 07-05-01 | 05 | 1 | ENRG-01/03 | unit | `pytest tests/connectors/test_smard.py -x` | ❌ W0 | ⬜ pending |
| 07-06-01 | 06 | 1 | ENRG-02 | unit | `pytest tests/connectors/test_mastr.py -x` | ❌ W0 | ⬜ pending |
| 07-07-01 | 07 | 2 | ENRG-03 | unit | `pytest tests/test_api_kpi.py -x` | ✅ extend | ⬜ pending |
| 07-07-02 | 07 | 2 | ENRG-04 | unit | `pytest tests/test_api_timeseries.py -x` | ✅ extend | ⬜ pending |
| 07-07-03 | 07 | 2 | TRAF-03/04 | unit | `pytest tests/test_api_layers.py -x` | ✅ extend | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/connectors/test_bast.py` — stubs for TRAF-03: CSV parse, normalize, congestion level
- [ ] `tests/connectors/test_autobahn.py` — stubs for TRAF-04: mock API, feature upsert
- [ ] `tests/connectors/test_mobidata_bw.py` — stubs for TRAF-05: BW CSV normalize
- [ ] `tests/connectors/test_smard.py` — stubs for ENRG-01/03: two-step fetch, null filtering, renewable %
- [ ] `tests/connectors/test_mastr.py` — stubs for ENRG-02: Landkreis filter, Lage field mapping
- [ ] `backend/alembic/versions/003_traffic_readings.py` — migration for traffic_readings hypertable

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Map renders traffic flow circles with green/yellow/red colors | TRAF-03 | Visual rendering in browser | Open app, enable Traffic layer, verify colored circles at station locations |
| Autobahn warning/closure icons appear on map | TRAF-04 | Visual rendering in browser | Open app, enable Autobahn layer, verify ⚠/✗ icons on A7/A6 |
| MaStR installations clustered on map with color-coded types | ENRG-02 | Visual rendering + clustering in browser | Open app, enable Energy/Renewables layer, verify solar=yellow, wind=blue, battery=green clusters |
| Energy KPI tile shows stacked bar + renewable % | ENRG-01 | Visual layout in browser | Open dashboard, verify energy KPI tile format |
| Energy detail panel shows generation mix stacked area chart + price line | ENRG-03/04 | Chart rendering in browser | Click energy KPI tile, verify charts in detail panel |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
