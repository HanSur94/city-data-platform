---
phase: quick-260407-gih
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/routers/admin.py
  - backend/app/schemas/responses.py
autonomous: true
requirements: [MON-01]

must_haves:
  truths:
    - "GET /api/admin/monitor?town=aalen returns JSON with hypertable_stats, connector_health, feature_registry, system_info sections"
    - "Each hypertable entry includes row_count, disk_size_bytes, chunk_count, compression_ratio, oldest_ts, newest_ts, retention_policy"
    - "system_info includes db_ok, timescaledb_version, postgis_version, total_db_size, server_uptime_seconds"
  artifacts:
    - path: "backend/app/routers/admin.py"
      provides: "GET /api/admin/monitor endpoint"
      contains: "admin/monitor"
    - path: "backend/app/schemas/responses.py"
      provides: "Pydantic response models for monitor endpoint"
      contains: "AdminMonitorResponse"
  key_links:
    - from: "backend/app/routers/admin.py"
      to: "TimescaleDB system views"
      via: "SQL queries to timescaledb_information.hypertables, chunks, compression_settings"
      pattern: "timescaledb_information"
---

<objective>
Create the comprehensive backend monitoring endpoint GET /api/admin/monitor that aggregates hypertable stats, connector health, feature registry counts, and system info into a single response.

Purpose: Provide all data the admin dashboard needs in one API call.
Output: Working endpoint returning structured JSON with all four data sections.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@backend/app/routers/admin.py
@backend/app/schemas/responses.py
@backend/app/main.py
@backend/app/db.py
@backend/app/dependencies.py

<interfaces>
From backend/app/routers/admin.py:
- router = APIRouter(tags=["admin"])
- Existing endpoint: GET /admin/health (connector staleness)
- Uses: get_db, get_current_town, Town, text()

From backend/app/main.py:
- app.include_router(admin.router, prefix="/api")
- Router already registered, no changes needed to main.py

The 7 hypertables are:
- air_quality_readings
- weather_readings
- transit_positions
- water_readings
- energy_readings
- traffic_readings
- demographics_readings
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add Pydantic response models for monitor endpoint</name>
  <files>backend/app/schemas/responses.py</files>
  <read_first>
    - backend/app/schemas/responses.py
  </read_first>
  <action>
Append the following Pydantic models to backend/app/schemas/responses.py:

1. **HypertableStats** (BaseModel):
   - table_name: str
   - row_count: int
   - disk_size_bytes: int
   - chunk_count: int
   - compression_ratio: float | None (None if compression not enabled)
   - oldest_timestamp: datetime | None
   - newest_timestamp: datetime | None
   - retention_policy: str | None (e.g. "30 days" or None)

2. **ConnectorHealthInfo** (BaseModel):
   - connector_class: str
   - domain: str
   - status: str (green/yellow/red/never_fetched)
   - last_successful_fetch: datetime | None
   - poll_interval_seconds: int | None
   - validation_error_count: int

3. **FeatureDomainCount** (BaseModel):
   - domain: str
   - total_features: int
   - with_semantic_id: int
   - with_address: int

4. **SystemInfo** (BaseModel):
   - db_ok: bool
   - timescaledb_version: str | None
   - postgis_version: str | None
   - total_db_size: str (human-readable like "1.2 GB")
   - total_db_size_bytes: int
   - server_uptime_seconds: float

5. **AdminMonitorResponse** (BaseModel):
   - town: str
   - checked_at: datetime
   - system_info: SystemInfo
   - hypertable_stats: list[HypertableStats]
   - connector_health: list[ConnectorHealthInfo]
   - feature_registry: list[FeatureDomainCount]
  </action>
  <verify>
    <automated>cd /Users/hannessuhr/Projects/city-data-platform/backend && python -c "from app.schemas.responses import AdminMonitorResponse, HypertableStats, SystemInfo, ConnectorHealthInfo, FeatureDomainCount; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - grep -q "class AdminMonitorResponse" backend/app/schemas/responses.py
    - grep -q "class HypertableStats" backend/app/schemas/responses.py
    - grep -q "class SystemInfo" backend/app/schemas/responses.py
    - grep -q "class ConnectorHealthInfo" backend/app/schemas/responses.py
    - grep -q "class FeatureDomainCount" backend/app/schemas/responses.py
  </acceptance_criteria>
  <done>All 5 Pydantic models importable without error</done>
</task>

<task type="auto">
  <name>Task 2: Add GET /api/admin/monitor endpoint</name>
  <files>backend/app/routers/admin.py</files>
  <read_first>
    - backend/app/routers/admin.py
    - backend/app/schemas/responses.py
    - backend/app/db.py
    - backend/app/dependencies.py
  </read_first>
  <action>
Add a new endpoint to backend/app/routers/admin.py: `GET /admin/monitor`

The endpoint queries 4 data sections using raw SQL via `text()` (matching existing patterns):

**1. system_info** — single query block:
```sql
-- DB connection: if we get here, db_ok = True
-- TimescaleDB version:
SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'
-- PostGIS version:
SELECT extversion FROM pg_extension WHERE extname = 'postgis'
-- Total DB size:
SELECT pg_database_size(current_database()) as size_bytes
-- Server uptime:
SELECT extract(epoch from (now() - pg_postmaster_start_time())) as uptime_seconds
```

**2. hypertable_stats** — for each of the 7 known hypertables, query:
```sql
-- Use a single CTE approach for efficiency:
WITH ht AS (
  SELECT hypertable_name, 
         num_chunks,
         pg_size_pretty(hypertable_size(format('%I', hypertable_name))) as size_pretty,
         hypertable_size(format('%I', hypertable_name)) as size_bytes
  FROM timescaledb_information.hypertables
  WHERE hypertable_schema = 'public'
),
counts AS (
  SELECT 'air_quality_readings' as tbl, count(*) as cnt, min(time) as oldest, max(time) as newest FROM air_quality_readings
  UNION ALL
  SELECT 'weather_readings', count(*), min(time), max(time) FROM weather_readings
  UNION ALL
  SELECT 'transit_positions', count(*), min(time), max(time) FROM transit_positions
  UNION ALL
  SELECT 'water_readings', count(*), min(time), max(time) FROM water_readings
  UNION ALL
  SELECT 'energy_readings', count(*), min(time), max(time) FROM energy_readings
  UNION ALL
  SELECT 'traffic_readings', count(*), min(time), max(time) FROM traffic_readings
  UNION ALL
  SELECT 'demographics_readings', count(*), min(time), max(time) FROM demographics_readings
),
comp AS (
  SELECT hypertable_name,
         CASE WHEN after_compression_total_bytes > 0 
              THEN before_compression_total_bytes::float / after_compression_total_bytes
              ELSE NULL END as ratio
  FROM timescaledb_information.compression_settings cs
  JOIN hypertable_compression_stats(cs.hypertable_name::regclass) hcs ON true
  WHERE cs.hypertable_schema = 'public'
),
ret AS (
  SELECT hypertable_name::text, 
         config::json->>'drop_after' as drop_after
  FROM timescaledb_information.jobs
  WHERE proc_name = 'policy_retention'
    AND hypertable_schema = 'public'
)
```

NOTE: The compression stats query may fail on tables without compression. Wrap compression and retention lookups in try/except or use LEFT JOINs. If compression stats are unavailable for a table, set compression_ratio to None.

A simpler approach: query each section separately with try/except for robustness:
- Query timescaledb_information.hypertables for chunk count and size
- Query each table for count/min/max time  
- Query hypertable_compression_stats() per table (catch errors for uncompressed tables)
- Query timescaledb_information.jobs for retention policies

**3. connector_health** — reuse the existing classify_staleness logic from the same file. Query sources table (same as existing /admin/health) but build ConnectorHealthInfo objects.

**4. feature_registry** — query features table:
```sql
SELECT 
  domain,
  count(*) as total_features,
  count(semantic_id) as with_semantic_id,
  count(address) as with_address
FROM features
WHERE town_id = :town_id
GROUP BY domain
ORDER BY domain
```

Use `import time; _start_time = time.time()` at module level to track server uptime (time since module import, which happens at startup).

Wrap each section in try/except so partial failures don't kill the whole endpoint. If a section fails, return empty list/default values.

Return AdminMonitorResponse with all sections.
  </action>
  <verify>
    <automated>cd /Users/hannessuhr/Projects/city-data-platform/backend && python -c "from app.routers.admin import router; routes = [r.path for r in router.routes]; assert '/admin/monitor' in routes, f'Routes: {routes}'; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - grep -q "admin/monitor" backend/app/routers/admin.py
    - grep -q "AdminMonitorResponse" backend/app/routers/admin.py
    - grep -q "hypertable_stats" backend/app/routers/admin.py
    - grep -q "system_info" backend/app/routers/admin.py
    - grep -q "feature_registry" backend/app/routers/admin.py
    - grep -q "connector_health" backend/app/routers/admin.py
  </acceptance_criteria>
  <done>GET /api/admin/monitor?town=aalen returns JSON with all 4 sections; partial failures return defaults not 500</done>
</task>

</tasks>

<verification>
- Endpoint registered at /api/admin/monitor (router already included in main.py)
- Response includes system_info, hypertable_stats, connector_health, feature_registry keys
- Each hypertable entry has row_count, disk_size_bytes, chunk_count, compression_ratio, oldest/newest timestamp, retention_policy
- Partial DB failures produce degraded response, not 500
</verification>

<success_criteria>
- python -c "from app.routers.admin import router" succeeds
- /admin/monitor route exists in router
- All Pydantic models importable
</success_criteria>

<output>
After completion, create `.planning/phases/quick-260407-gih/quick-260407-gih-01-SUMMARY.md`
</output>
