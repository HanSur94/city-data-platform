---
phase: 01-foundation
plan: 03
subsystem: backend/config + backend/connectors
tags: [pydantic, yaml, config-loader, connector-pattern, tdd, abstract-class]
dependency_graph:
  requires:
    - 01-01 (Docker Compose + FastAPI scaffold with uv environment)
  provides:
    - Town YAML config system with Pydantic validation
    - BaseConnector abstract class + Observation dataclass
    - StubConnector no-op implementation
    - 14 passing tests (config + connector)
  affects:
    - 01-04 (VG250 boundary import — uses Town/load_town for bbox)
    - Phase 2 connectors (inherit from BaseConnector)
tech_stack:
  added:
    - PyYAML 6.x (yaml.safe_load for town YAML parsing)
    - Pydantic BaseModel with field_validator (Town, TownBbox, ConnectorConfig)
  patterns:
    - TDD red-green cycle for both tasks
    - YAML -> dict -> Pydantic model_validate() for town loading
    - ABC + abstractmethod for connector contract enforcement
    - Dataclass for Observation (lightweight, no DB dependency)
key_files:
  created:
    - towns/aalen.yaml (Aalen reference town config with bbox and StubConnector)
    - towns/example.yaml (template for new town onboarding)
    - backend/app/config.py (Town, TownBbox, ConnectorConfig models + load_town())
    - backend/app/connectors/__init__.py (package init)
    - backend/app/connectors/base.py (BaseConnector ABC + Observation dataclass)
    - backend/app/connectors/stub.py (StubConnector no-op implementation)
    - backend/tests/test_config.py (7 tests for YAML loading and validation)
    - backend/tests/test_connector.py (7 tests for connector contract)
  modified:
    - backend/pyproject.toml (added [tool.pytest.ini_options] asyncio_mode=auto)
decisions:
  - "Town id validated as alphanumeric slug (hyphens/underscores allowed) via field_validator"
  - "persist() is no-op in Phase 1 — SQLAlchemy session injection deferred to Phase 2"
  - "asyncio_mode=auto set in pyproject.toml to simplify async test authoring"
  - "Observation is a dataclass, not a Pydantic model — no DB schema coupling in Phase 1"
metrics:
  duration_seconds: 151
  completed_date: "2026-04-05"
  tasks_completed: 2
  files_created: 8
  files_modified: 1
  tests_added: 14
  tests_passing: 14
---

# Phase 01 Plan 03: Town Config System + BaseConnector Summary

**One-liner:** Pydantic YAML town config loader (load_town) + BaseConnector ABC with StubConnector, verified by 14 TDD tests.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Town YAML files + Pydantic config loader | f02baf7 | towns/aalen.yaml, towns/example.yaml, backend/app/config.py, backend/tests/test_config.py |
| 2 | BaseConnector abstract class + StubConnector | ad4740f | backend/app/connectors/{__init__,base,stub}.py, backend/tests/test_connector.py, backend/pyproject.toml |

## What Was Built

### Town Config System

`load_town('aalen')` reads `towns/aalen.yaml`, validates via Pydantic, and returns a `Town` object with full bbox and connector list. Key validation:

- `id` must be an alphanumeric slug (hyphens/underscores allowed) — enforced by `@field_validator`
- Missing required fields (`id`, `display_name`, `bbox`) raise `ValidationError`
- Missing `connectors` key defaults to `[]` — no YAML change required for simple towns
- Non-existent town YAML raises `FileNotFoundError` with helpful message listing available towns

### BaseConnector Pattern

`BaseConnector(ABC)` enforces the connector contract via Python's `abc.abstractmethod`. Concrete connectors must implement:
- `async def fetch(self) -> Any` — retrieve raw data from external source
- `def normalize(self, raw: Any) -> list[Observation]` — transform to Observation objects

`persist()` is provided by the base class as a no-op in Phase 1. Phase 2 will inject a SQLAlchemy session here.

`StubConnector` implements the full contract with no network calls — used for testing and as the placeholder in `towns/aalen.yaml`.

### Observation Dataclass

`Observation(feature_id, domain, values, timestamp, source_id)` is the normalized data unit ready for persistence. Using a `dataclass` keeps it lightweight and independent of the database schema.

## Verification Results

```
14 passed in 0.07s
- test_config.py: 7/7 passed
- test_connector.py: 7/7 passed
```

Final integration check confirmed:
```
aalen: aalen lon_min=9.97 lat_min=48.76 lon_max=10.22 lat_max=48.9
example: example lon_min=0.0 lat_min=0.0 lon_max=1.0 lat_max=1.0
```

## Deviations from Plan

None — plan executed exactly as written. The existing `asyncio: mode=Mode.STRICT` in the worktree environment already supported `@pytest.mark.asyncio` markers; setting `asyncio_mode = "auto"` in pyproject.toml as specified by the plan caused tests to remain green (14/14).

## Known Stubs

- `backend/app/connectors/base.py`: `persist()` is a no-op (`pass`). This is intentional — Phase 2 will wire the SQLAlchemy session. The stub does not prevent plan goal (connector contract testing without a database).

## Self-Check: PASSED

Files verified:
- towns/aalen.yaml: FOUND
- towns/example.yaml: FOUND
- backend/app/config.py: FOUND
- backend/app/connectors/base.py: FOUND
- backend/app/connectors/stub.py: FOUND
- backend/tests/test_config.py: FOUND
- backend/tests/test_connector.py: FOUND

Commits verified:
- f02baf7: FOUND (Task 1)
- ad4740f: FOUND (Task 2)
