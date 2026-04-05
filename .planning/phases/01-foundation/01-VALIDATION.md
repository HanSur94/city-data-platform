---
phase: 1
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `cd backend && uv run pytest tests/ -x -q` |
| **Full suite command** | `cd backend && uv run pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/ -x -q`
- **After every plan wave:** Run `cd backend && uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | PLAT-02 | integration | `docker-compose up -d && docker-compose ps` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | PLAT-07, PLAT-08 | integration | `uv run pytest tests/test_migrations.py` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 1 | PLAT-01 | unit | `uv run pytest tests/test_config.py` | ❌ W0 | ⬜ pending |
| 01-04-01 | 04 | 1 | PLAT-06 | unit | `uv run pytest tests/test_connector.py` | ❌ W0 | ⬜ pending |
| 01-05-01 | 05 | 1 | GEO-06 | integration | `uv run pytest tests/test_boundaries.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/conftest.py` — shared fixtures (DB connection, town config)
- [ ] `backend/pyproject.toml` — pytest + pytest-asyncio as dev dependencies
- [ ] `docker-compose.yml` — test database service

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| docker-compose up starts all services | PLAT-02 | Requires Docker daemon | Run `docker-compose up -d` and verify all containers are healthy |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
