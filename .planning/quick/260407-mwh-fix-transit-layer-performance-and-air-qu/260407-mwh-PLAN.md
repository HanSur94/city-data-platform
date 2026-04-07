---
phase: quick-260407-mwh
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/connectors/gtfs_rt.py
  - backend/app/routers/layers.py
  - frontend/lib/api.ts
  - frontend/hooks/useLayerData.ts
  - frontend/components/map/BusPositionLayer.tsx
  - frontend/components/map/BusRouteLayer.tsx
  - frontend/app/page.tsx
autonomous: true
requirements: [PERF-TRANSIT, BUG-AIRQUALITY, BUG-FEATURETYPE]
must_haves:
  truths:
    - "Transit layer returns only bus_position features (~240) instead of all 161K features"
    - "Air quality layer returns 200 OK (not 500) when at=None"
    - "Traffic and demographics layers also work with at=None"
    - "GTFS-RT features have feature_type property for server-side filtering"
  artifacts:
    - path: "backend/app/routers/layers.py"
      provides: "feature_type filter on transit SQL + fixed asyncpg NULL param handling"
    - path: "backend/app/connectors/gtfs_rt.py"
      provides: "feature_type property on vehicle and trip_update features"
    - path: "frontend/lib/api.ts"
      provides: "fetchLayer with optional feature_type parameter"
  key_links:
    - from: "frontend/components/map/BusPositionLayer.tsx"
      to: "/api/layers/transit?feature_type=bus_position"
      via: "fetchLayer call with feature_type param"
      pattern: "fetchLayer.*transit.*bus_position"
    - from: "backend/app/routers/layers.py"
      to: "features table"
      via: "SQL WHERE with feature_type filter"
      pattern: "feature_type"
---

<objective>
Fix three related bugs: (1) transit layer returns 161K features (25MB/17s) instead of filtering server-side, (2) air quality SQL fails with asyncpg AmbiguousParameterError when at=None, (3) GTFS-RT connector creates features without feature_type property.

Purpose: Reduce transit API response from 25MB to ~500KB, fix air quality 500 errors, prevent stale feature accumulation.
Output: Patched backend SQL queries, GTFS-RT connector, and frontend fetch calls.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@backend/app/routers/layers.py
@backend/app/connectors/gtfs_rt.py
@frontend/lib/api.ts
@frontend/hooks/useLayerData.ts
@frontend/components/map/BusPositionLayer.tsx
@frontend/components/map/BusRouteLayer.tsx
@frontend/components/map/TransitLayer.tsx
@frontend/app/page.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix backend — GTFS-RT feature_type + transit SQL filter + asyncpg NULL param</name>
  <files>backend/app/connectors/gtfs_rt.py, backend/app/routers/layers.py</files>
  <action>
**gtfs_rt.py (lines 160-180):**
- Add `"feature_type": "bus_position"` to the vehicle feature properties dict (line ~164, alongside trip_id and route_id)
- Add `"feature_type": "trip_update"` to the trip_update feature properties dict (line ~178, alongside trip_id)

**layers.py — transit query (lines 55-72):**
- Add feature_type filtering to the transit SQL. When the `feature_type` query param is provided, add `AND f.properties->>'feature_type' = :feature_type` to the WHERE clause. When not provided, return all transit features (backward compatible).
- Pass `feature_type` into the params dict when not None.
- Pattern: similar to how air_quality already handles feature_type with `ft_filter` string injection (lines 83-86), but use a parameterized approach:
  ```python
  ft_filter = ""
  params = {"town_id": current_town.id}
  if feature_type:
      ft_filter = "AND f.properties->>'feature_type' = :feature_type"
      params["feature_type"] = feature_type
  ```
  Then inject `{ft_filter}` into the SQL string (change `text("""...""")` to `text(f"""...""")`).

**layers.py — asyncpg NULL param fix (lines 104, 140, 195):**
The pattern `AND (:at IS NULL OR time <= :at)` causes asyncpg AmbiguousParameterError when at=None because asyncpg cannot infer the type of a NULL parameter.

Fix all three LATERAL subqueries (air_quality line 104, traffic line 140, demographics line 195) by replacing:
```sql
AND (:at IS NULL OR time <= :at)
```
with:
```sql
AND (CAST(:at AS timestamptz) IS NULL OR time <= CAST(:at AS timestamptz))
```

This tells asyncpg the parameter type explicitly, resolving the ambiguity while preserving the same logic (when at is None, the CAST result is NULL, IS NULL is true, so all rows match).
  </action>
  <verify>
    <automated>cd /Users/hannessuhr/Projects/city-data-platform && python -c "
import ast, sys
# Verify gtfs_rt.py has feature_type in both branches
with open('backend/app/connectors/gtfs_rt.py') as f:
    src = f.read()
assert src.count('feature_type') >= 2, 'Missing feature_type in gtfs_rt.py'
assert 'bus_position' in src, 'Missing bus_position feature_type'
assert 'trip_update' in src, 'Missing trip_update feature_type'
# Verify layers.py has CAST fix
with open('backend/app/routers/layers.py') as f:
    lsrc = f.read()
assert 'CAST(:at AS timestamptz)' in lsrc, 'Missing CAST fix in layers.py'
assert lsrc.count('CAST(:at AS timestamptz)') >= 3, 'CAST fix not applied to all 3 queries'
assert 'feature_type' in lsrc.split('transit')[1].split('elif')[0], 'Missing feature_type filter in transit query'
print('All backend checks passed')
"</automated>
  </verify>
  <done>
- gtfs_rt.py vehicle features include `feature_type: "bus_position"` property
- gtfs_rt.py trip_update features include `feature_type: "trip_update"` property
- Transit SQL supports optional `feature_type` query param filtering via properties JSONB
- Air quality, traffic, and demographics LATERAL subqueries use `CAST(:at AS timestamptz)` instead of bare `:at`
  </done>
</task>

<task type="auto">
  <name>Task 2: Fix frontend — pass feature_type param for transit fetches + DB cleanup SQL</name>
  <files>frontend/lib/api.ts, frontend/components/map/BusPositionLayer.tsx, frontend/components/map/BusRouteLayer.tsx, frontend/app/page.tsx</files>
  <action>
**api.ts — extend fetchLayer signature (line 8):**
Add optional `featureType` parameter to `fetchLayer`:
```typescript
export async function fetchLayer(
  domain: string,
  town = 'aalen',
  at?: Date | null,
  featureType?: string,
): Promise<LayerResponse> {
  const params = new URLSearchParams({ town })
  if (at) params.set('at', at.toISOString())
  if (featureType) params.set('feature_type', featureType)
  ...
}
```

**BusPositionLayer.tsx (line 180):**
Change `fetchLayer('transit', town)` to `fetchLayer('transit', town, null, 'bus_position')`.
This ensures only bus_position features are returned (~240 instead of 161K).

**BusRouteLayer.tsx (line 41):**
This component uses `useLayerData('transit', town)` which calls `fetchLayer` without feature_type — it gets ALL transit features and then client-filters for `feature_type === 'shape'`. To fix:
- Replace `useLayerData('transit', town)` with a custom inline fetch approach (matching BusPositionLayer pattern), OR
- Simpler: add feature_type support to `useLayerData`. Add an optional 4th param `featureType?: string` to useLayerData, and pass it through to fetchLayer.
- Then change to `useLayerData('transit', town, undefined, 'shape')`.

**Update useLayerData** (frontend/hooks/useLayerData.ts):
Add `featureType` parameter:
```typescript
export function useLayerData(domain: string, town = 'aalen', timestamp?: Date | null, featureType?: string) {
```
Pass it to fetchLayer: `const json = await fetchLayer(domain, town, timestamp, featureType);`
Add `featureType` to the useEffect dependency array.

**page.tsx (line 176):**
The `transit` useLayerData call feeds TransitLayer (stops). Transit stops have `feature_type: 'stop'` presumably. Check what feature_type stops have. If stops don't have feature_type set yet, leave the page.tsx transit call WITHOUT feature_type filter (it will still work, just returning stops + any unfiltered features). The key win is BusPositionLayer and BusRouteLayer no longer pulling 161K features.

Actually, examining TransitLayer.tsx — it renders clustered stop circles. The `transit` data from page.tsx line 176 feeds this. Since stops may not have feature_type set, and the main performance problem is BusPositionLayer fetching everything, the page.tsx call can remain as-is for now. The stop count is manageable.

**DB cleanup — create a one-time SQL script:**
Create file `backend/scripts/cleanup_stale_transit.sql`:
```sql
-- One-time cleanup: delete transit features at POINT(0,0) without feature_type
-- These are stale trip_update placeholders from before the feature_type fix
DELETE FROM features
WHERE domain = 'transit'
  AND ST_Equals(geometry, ST_GeomFromText('POINT(0 0)', 4326))
  AND (properties->>'feature_type') IS NULL;
```
Print a note that this script should be run manually against the DB once.
  </action>
  <verify>
    <automated>cd /Users/hannessuhr/Projects/city-data-platform && grep -q "featureType" frontend/lib/api.ts && grep -q "feature_type" frontend/lib/api.ts && grep -q "bus_position" frontend/components/map/BusPositionLayer.tsx && grep -q "shape" frontend/components/map/BusRouteLayer.tsx && grep -q "featureType" frontend/hooks/useLayerData.ts && test -f backend/scripts/cleanup_stale_transit.sql && echo "All frontend checks passed"</automated>
  </verify>
  <done>
- fetchLayer accepts optional featureType parameter and passes it as feature_type query param
- useLayerData accepts optional featureType parameter and passes through to fetchLayer
- BusPositionLayer fetches with feature_type=bus_position (response drops from 25MB to ~500KB)
- BusRouteLayer fetches with feature_type=shape (only route shapes, not all transit)
- cleanup_stale_transit.sql script exists for one-time DB cleanup of 161K stale features
  </done>
</task>

</tasks>

<verification>
1. Backend: `cd backend && python -m pytest tests/ -x -q` (existing tests still pass)
2. Frontend: `cd frontend && npx next build` (no type errors)
3. Manual: Start backend, call `curl "http://localhost:8000/api/layers/transit?town=aalen&feature_type=bus_position"` — should return only bus_position features, response should be <1MB
4. Manual: Call `curl "http://localhost:8000/api/layers/air_quality?town=aalen"` — should return 200 (not 500)
5. Run cleanup SQL against database to remove stale POINT(0,0) features
</verification>

<success_criteria>
- Transit layer API response with feature_type=bus_position returns <1MB (was 25MB)
- Air quality layer returns 200 OK when no `at` parameter is provided
- Traffic and demographics layers also work without `at` parameter
- GTFS-RT connector writes feature_type property on all new features
- Frontend bus position refresh no longer downloads 161K features every 30s
</success_criteria>

<output>
After completion, create `.planning/quick/260407-mwh-fix-transit-layer-performance-and-air-qu/260407-mwh-SUMMARY.md`
</output>
