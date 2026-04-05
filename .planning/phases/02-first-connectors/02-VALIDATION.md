---
phase: 2
slug: first-connectors
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
revised: 2026-04-05
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio |
| **Config file** | backend/pyproject.toml |
| **Quick run command** | `cd backend && uv run pytest tests/connectors/ -x -q -m "not slow"` |
| **Full suite command** | `cd backend && uv run pytest tests/ -v -m "not slow"` |
| **Slow tests** | `cd backend && uv run pytest tests/connectors/test_gtfs.py -v -m slow --timeout=180` |
| **Estimated runtime (fast)** | ~30 seconds (live UBA, SensorCommunity, Weather, GTFS-RT fixture) |
| **Estimated runtime (slow)** | ~3-4 minutes (includes live NVBW GTFS download) |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/connectors/ -x -q -m "not slow"`
- **After every plan wave:** Run `cd backend && uv run pytest tests/ -v -m "not slow"`
- **Before `/gsd:verify-work`:** Full suite (including `not slow`) must be green; slow tests optional
- **Max feedback latency:** 30 seconds (fast tests only; slow tests excluded from latency requirement)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Test File | Status |
|---------|------|------|-------------|-----------|-------------------|-----------|--------|
| 02-01-T1 | 01 | 1 | — | integration | `uv run alembic upgrade head && uv run python -c "import gtfs_kit; import apscheduler"` | N/A | ⬜ pending |
| 02-01-T2 | 01 | 1 | — | import check | `uv run python -c "from app.connectors.base import BaseConnector; from app.scheduler import setup_scheduler"` | N/A | ⬜ pending |
| 02-02-T1 | 02 | 2 | WAIR-03, WAIR-04 | integration (live API) | `uv run pytest tests/connectors/test_uba.py tests/connectors/test_sensor_community.py -v` | test_uba.py, test_sensor_community.py | ⬜ pending |
| 02-03-T1 | 03 | 2 | WAIR-01, WAIR-02 | integration (live API) | `uv run pytest tests/connectors/test_weather.py -v` | test_weather.py | ⬜ pending |
| 02-04-T1 | 04 | 2 | TRAF-01 | unit (fast fixture) | `uv run pytest tests/connectors/test_gtfs.py -v -m "not slow"` | test_gtfs.py | ⬜ pending |
| 02-05-T1 | 05 | 3 | TRAF-02 | unit (fixture protobuf) | `uv run pytest tests/connectors/test_gtfs_rt.py -v` | test_gtfs_rt.py | ⬜ pending |
| 02-05-T2 | 05 | 3 | TRAF-02 | import + config check | `uv run python -c "from app.scheduler import scheduler; from app.main import app"` | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements (Plan 02-01)

- [ ] `backend/tests/connectors/__init__.py` — connector test package
- [ ] `backend/tests/connectors/conftest.py` — shared connector test fixtures (aalen_town, stub_connector_config)
- [ ] Migration 002 — weather_readings hypertable, features unique constraint, sources staleness columns
- [ ] New packages: gtfs-kit, gtfs-realtime-bindings, apscheduler
- [ ] `BaseConnector.persist()` upgraded from no-op to real DB writes
- [ ] `BaseConnector.run()` upgraded to call `_update_staleness()` after persist
- [ ] `BaseConnector._update_staleness()` writes to `sources.last_successful_fetch`
- [ ] `BaseConnector.upsert_feature()` added

---

## Staleness Tracking Coverage

Sources staleness columns (added in migration 002) are written by `BaseConnector._update_staleness()`.
Every connector that overrides `run()` MUST call `await self._update_staleness()` at end of run.

| Connector | Overrides run()? | Calls _update_staleness()? |
|-----------|-----------------|---------------------------|
| UBAConnector | Yes | Yes (plan 02-02 requirement) |
| SensorCommunityConnector | Yes | Yes (plan 02-02 requirement) |
| WeatherConnector | Yes | Yes (plan 02-03 requirement) |
| GTFSConnector | Yes | Yes (plan 02-04 requirement) |
| GTFSRealtimeConnector | Yes | Yes (plan 02-05 requirement) |

---

## Test Tier Strategy

| Tier | Mark | Files | Runtime | When to Run |
|------|------|-------|---------|-------------|
| Fast | (default, no mark) | test_gtfs.py (fixture), test_gtfs_rt.py | < 30s | Every task commit |
| Live API | (default, no mark) | test_uba.py, test_sensor_community.py, test_weather.py | ~20s | Every task commit |
| Slow | `@pytest.mark.slow` | test_gtfs.py (live download) | ~3 min | Explicitly with `-m slow` |

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Scheduler runs connectors on cron | All | Requires long-running process + time passage | Start FastAPI, wait 5+ min, check DB for new rows |
| GTFS-RT live positions | TRAF-02 | Real-time feed URL unconfirmed; may not have Aalen vehicles at test time | After URL confirmed: check transit_positions table after scheduler run |
| sources.last_successful_fetch updated | PLAT-07 | Requires live connector run against real DB | After scheduler run: `SELECT connector_class, last_successful_fetch FROM sources WHERE town_id='aalen'` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Fast feedback latency < 30s (slow tests excluded)
- [ ] GTFS live download test marked @pytest.mark.slow
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
