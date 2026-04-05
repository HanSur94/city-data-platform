---
phase: 2
slug: first-connectors
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio |
| **Config file** | backend/pyproject.toml |
| **Quick run command** | `cd backend && uv run pytest tests/connectors/ -x -q` |
| **Full suite command** | `cd backend && uv run pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds (includes live API calls) |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/connectors/ -x -q`
- **After every plan wave:** Run `cd backend && uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 0 | PLAT-07 | integration | `uv run pytest tests/test_migrations.py -v` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | TRAF-01 | integration | `uv run pytest tests/connectors/test_gtfs.py -v` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | TRAF-02 | integration | `uv run pytest tests/connectors/test_gtfs_rt.py -v` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 1 | WAIR-03, WAIR-04 | integration | `uv run pytest tests/connectors/test_air_quality.py -v` | ❌ W0 | ⬜ pending |
| 02-04-01 | 04 | 1 | WAIR-01, WAIR-02 | integration | `uv run pytest tests/connectors/test_weather.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/connectors/__init__.py` — connector test package
- [ ] `backend/tests/connectors/conftest.py` — shared connector test fixtures
- [ ] Migration 002 — weather_readings hypertable (missing from Phase 1 schema)
- [ ] New packages: gtfs-kit, gtfs-realtime-bindings, apscheduler

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Scheduler runs connectors on cron | All | Requires long-running process + time passage | Start FastAPI, wait 5+ min, check DB for new rows |
| GTFS-RT live positions | TRAF-02 | Real-time feed may not have Aalen vehicles at test time | Check transit_positions table after scheduler run |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
