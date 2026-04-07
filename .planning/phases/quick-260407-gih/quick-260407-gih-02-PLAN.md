---
phase: quick-260407-gih
plan: 02
type: execute
wave: 2
depends_on: ["quick-260407-gih-01"]
files_modified:
  - frontend/types/admin.ts
  - frontend/lib/api.ts
  - frontend/hooks/useAdminHealth.ts
  - frontend/app/admin/page.tsx
  - frontend/components/admin/SystemHealthCard.tsx
  - frontend/components/admin/HypertableStatsTable.tsx
  - frontend/components/admin/FeatureRegistrySummary.tsx
autonomous: true
requirements: [MON-02]

must_haves:
  truths:
    - "Admin page at /admin shows system health card with DB status, versions, uptime, total size"
    - "Admin page shows hypertable stats table with name, rows, size, chunks, compression, date range, retention"
    - "Admin page shows connector health table with status badges (existing component reused)"
    - "Admin page shows feature registry summary with per-domain counts and semantic_id coverage"
    - "Page auto-refreshes every 30 seconds"
  artifacts:
    - path: "frontend/types/admin.ts"
      provides: "TypeScript types for AdminMonitorResponse"
      contains: "AdminMonitorResponse"
    - path: "frontend/components/admin/SystemHealthCard.tsx"
      provides: "System health card component"
      contains: "SystemHealthCard"
    - path: "frontend/components/admin/HypertableStatsTable.tsx"
      provides: "Hypertable stats table component"
      contains: "HypertableStatsTable"
    - path: "frontend/components/admin/FeatureRegistrySummary.tsx"
      provides: "Feature registry summary component"
      contains: "FeatureRegistrySummary"
    - path: "frontend/app/admin/page.tsx"
      provides: "Enhanced admin page composing all sections"
      contains: "AdminMonitorResponse"
  key_links:
    - from: "frontend/app/admin/page.tsx"
      to: "/api/admin/monitor"
      via: "fetchAdminMonitor in lib/api.ts"
      pattern: "fetchAdminMonitor"
    - from: "frontend/hooks/useAdminHealth.ts"
      to: "frontend/lib/api.ts"
      via: "fetchAdminMonitor call"
      pattern: "fetchAdminMonitor"
---

<objective>
Enhance the /admin page with a comprehensive monitoring dashboard showing system health, hypertable stats, connector health, and feature registry -- all from the new /api/admin/monitor endpoint.

Purpose: Give operators a single-page view of the entire platform's health and data status.
Output: Full admin dashboard with 4 data sections, auto-refreshing every 30s.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/app/admin/page.tsx
@frontend/types/admin.ts
@frontend/hooks/useAdminHealth.ts
@frontend/lib/api.ts
@frontend/components/admin/ConnectorHealthTable.tsx
@frontend/components/admin/StalenessBar.tsx
@frontend/components/ui/card.tsx

IMPORTANT: This project uses Next.js 16.2.2. Read node_modules/next/dist/docs/ before writing code if unsure about APIs. Use 'use client' directive for client components.

<interfaces>
From frontend/types/admin.ts (current):
```typescript
export interface AdminHealthItem { ... } // existing connector health type
export interface AdminHealthSummary { ... }
export interface AdminHealthResponse { ... }
```

From frontend/lib/api.ts:
```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
export async function fetchAdminHealth(town: string): Promise<AdminHealthResponse>
```

From frontend/hooks/useAdminHealth.ts:
```typescript
export function useAdminHealth(town = 'aalen') // returns { data, loading, error }
// Already has 30s auto-refresh via setInterval
```

From frontend/components/ui/card.tsx:
- Card, CardContent, CardDescription, CardHeader, CardTitle (shadcn/ui)

Available shadcn/ui components: badge, button, card, chart, label, separator, tooltip
NOTE: No table.tsx component exists -- use plain HTML tables (matching existing ConnectorHealthTable pattern)
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add TypeScript types and API fetch function for monitor endpoint</name>
  <files>frontend/types/admin.ts, frontend/lib/api.ts, frontend/hooks/useAdminHealth.ts</files>
  <read_first>
    - frontend/types/admin.ts
    - frontend/lib/api.ts
    - frontend/hooks/useAdminHealth.ts
  </read_first>
  <action>
**frontend/types/admin.ts** -- append new types (keep existing AdminHealthItem, AdminHealthSummary, AdminHealthResponse):

```typescript
export interface HypertableStats {
  table_name: string
  row_count: number
  disk_size_bytes: number
  chunk_count: number
  compression_ratio: number | null
  oldest_timestamp: string | null
  newest_timestamp: string | null
  retention_policy: string | null
}

export interface ConnectorHealthInfo {
  connector_class: string
  domain: string
  status: 'green' | 'yellow' | 'red' | 'never_fetched'
  last_successful_fetch: string | null
  poll_interval_seconds: number | null
  validation_error_count: number
}

export interface FeatureDomainCount {
  domain: string
  total_features: number
  with_semantic_id: number
  with_address: number
}

export interface SystemInfo {
  db_ok: boolean
  timescaledb_version: string | null
  postgis_version: string | null
  total_db_size: string
  total_db_size_bytes: number
  server_uptime_seconds: number
}

export interface AdminMonitorResponse {
  town: string
  checked_at: string
  system_info: SystemInfo
  hypertable_stats: HypertableStats[]
  connector_health: ConnectorHealthInfo[]
  feature_registry: FeatureDomainCount[]
}
```

**frontend/lib/api.ts** -- add fetchAdminMonitor function:
```typescript
export async function fetchAdminMonitor(town: string): Promise<AdminMonitorResponse> {
  const res = await fetch(`${API_BASE}/api/admin/monitor?town=${encodeURIComponent(town)}`)
  if (!res.ok) throw new Error(`Admin monitor fetch failed: ${res.status}`)
  return res.json() as Promise<AdminMonitorResponse>
}
```
Import AdminMonitorResponse from '@/types/admin'.

**frontend/hooks/useAdminHealth.ts** -- rename to useAdminMonitor or add a second hook. Best approach: add a new `useAdminMonitor` hook in the same file following the exact same useState+useEffect+setInterval pattern as useAdminHealth but calling fetchAdminMonitor. Keep useAdminHealth for backward compatibility.

```typescript
export function useAdminMonitor(town = 'aalen') {
  const [data, setData] = useState<AdminMonitorResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const json = await fetchAdminMonitor(town)
        if (!cancelled) { setData(json); setLoading(false); setError(false) }
      } catch {
        if (!cancelled) { setLoading(false); setError(true) }
      }
    }
    load()
    const id = setInterval(load, 30_000)
    return () => { cancelled = true; clearInterval(id) }
  }, [town])

  return { data, loading, error }
}
```
  </action>
  <verify>
    <automated>cd /Users/hannessuhr/Projects/city-data-platform/frontend && npx tsc --noEmit --pretty 2>&1 | head -30</automated>
  </verify>
  <acceptance_criteria>
    - grep -q "AdminMonitorResponse" frontend/types/admin.ts
    - grep -q "HypertableStats" frontend/types/admin.ts
    - grep -q "SystemInfo" frontend/types/admin.ts
    - grep -q "fetchAdminMonitor" frontend/lib/api.ts
    - grep -q "useAdminMonitor" frontend/hooks/useAdminHealth.ts
  </acceptance_criteria>
  <done>Types, API function, and hook all compile without TypeScript errors</done>
</task>

<task type="auto">
  <name>Task 2: Create admin dashboard components and update page</name>
  <files>frontend/components/admin/SystemHealthCard.tsx, frontend/components/admin/HypertableStatsTable.tsx, frontend/components/admin/FeatureRegistrySummary.tsx, frontend/app/admin/page.tsx</files>
  <read_first>
    - frontend/app/admin/page.tsx
    - frontend/components/admin/ConnectorHealthTable.tsx
    - frontend/components/ui/card.tsx
    - frontend/components/admin/StalenessBar.tsx
    - frontend/types/admin.ts
  </read_first>
  <action>
**1. frontend/components/admin/SystemHealthCard.tsx** ('use client'):
- Import Card, CardContent, CardHeader, CardTitle from '@/components/ui/card'
- Import SystemInfo from '@/types/admin'
- Props: { systemInfo: SystemInfo, checkedAt: string }
- Display in a Card:
  - CardTitle: "Systemgesundheit"
  - Grid layout (2 cols on sm, 4 cols on md) with:
    - DB Status: green dot + "Verbunden" if db_ok, red dot + "Fehler" if not
    - TimescaleDB: version string or "—"
    - PostGIS: version string or "—"
    - Datenbankgroesse: total_db_size (human readable from backend)
    - Server-Uptime: format server_uptime_seconds as "Xd Yh Zm" 
    - Letzter Check: format checkedAt as German locale datetime

**2. frontend/components/admin/HypertableStatsTable.tsx** ('use client'):
- Import HypertableStats from '@/types/admin'
- Props: { stats: HypertableStats[] }
- HTML table matching ConnectorHealthTable styling (overflow-x-auto, rounded-lg border, sticky header)
- Columns: Tabelle, Zeilen, Groesse, Chunks, Kompression, Zeitraum, Retention
- Row rendering:
  - table_name: font-mono text-xs
  - row_count: formatted with toLocaleString('de-DE')
  - disk_size_bytes: format as KB/MB/GB helper function
  - chunk_count: plain number
  - compression_ratio: "X.Xx" or "—" if null
  - date range: format oldest_timestamp + " — " + newest_timestamp as dd.MM.yyyy or "—"
  - retention_policy: text or "—"
- Sort by disk_size_bytes descending (largest tables first)

**3. frontend/components/admin/FeatureRegistrySummary.tsx** ('use client'):
- Import Card, CardContent, CardHeader, CardTitle from '@/components/ui/card'
- Import FeatureDomainCount from '@/types/admin'
- Props: { registry: FeatureDomainCount[] }
- Card with title "Feature-Registry"
- Small table inside card: Domain, Gesamt, Mit Semantic-ID, Mit Adresse
- Each domain row shows counts, with semantic_id as "X / Y (Z%)" format
- Bottom summary row with totals bolded

**4. frontend/app/admin/page.tsx** -- full rewrite:
- Replace useAdminHealth with useAdminMonitor 
- Keep the existing skeleton and error states
- New layout structure (all in max-w-6xl container, up from max-w-5xl):
  - h1: "Systemstatus" (drop the "— Konnektoren" suffix since it's broader now)
  - Subtitle with town name and last check time
  - SystemHealthCard (system_info + checked_at)
  - Section heading "Hypertables" + HypertableStatsTable
  - Section heading "Konnektoren" + existing summary boxes (green/yellow/red/never) + ConnectorHealthTable (pass connector_health data mapped to AdminHealthItem format, OR update ConnectorHealthTable to accept ConnectorHealthInfo[])
  - Section heading "Feature-Registry" + FeatureRegistrySummary

For the connector section: The existing ConnectorHealthTable expects AdminHealthItem[] which has id, threshold_yellow, threshold_red etc. Two options:
  - Option A: Map ConnectorHealthInfo to AdminHealthItem shape (add dummy values for fields not in monitor response)
  - Option B (preferred): Create a simpler ConnectorMonitorTable component or update ConnectorHealthTable to accept a union type
  
  Best approach: Create a new minimal table in the page itself or pass the connector_health array directly and create a small inline table matching the existing style. The existing ConnectorHealthTable can remain for the old /admin/health endpoint if needed.

  Actually simplest: just render the connector_health data using a new simple table in the page (same HTML table pattern), showing: Konnektor, Domain, Status (reuse StalenessBar), Letzter Abruf, Intervall, Fehler. This avoids modifying the existing component.
  </action>
  <verify>
    <automated>cd /Users/hannessuhr/Projects/city-data-platform/frontend && npx tsc --noEmit --pretty 2>&1 | head -30</automated>
  </verify>
  <acceptance_criteria>
    - grep -q "SystemHealthCard" frontend/app/admin/page.tsx
    - grep -q "HypertableStatsTable" frontend/app/admin/page.tsx
    - grep -q "FeatureRegistrySummary" frontend/app/admin/page.tsx
    - grep -q "useAdminMonitor" frontend/app/admin/page.tsx
    - test -f frontend/components/admin/SystemHealthCard.tsx
    - test -f frontend/components/admin/HypertableStatsTable.tsx
    - test -f frontend/components/admin/FeatureRegistrySummary.tsx
  </acceptance_criteria>
  <done>Admin page renders all 4 sections (system health, hypertables, connectors, feature registry) with 30s auto-refresh; TypeScript compiles clean</done>
</task>

</tasks>

<verification>
- Visit http://localhost:4000/admin and confirm all 4 sections render
- System health card shows DB status, versions, uptime
- Hypertable table shows all 7 tables with stats
- Connector table shows status badges
- Feature registry shows per-domain counts
- Page auto-refreshes (check network tab for 30s interval)
</verification>

<success_criteria>
- All new components compile without TypeScript errors
- Admin page imports and renders all 4 dashboard sections
- useAdminMonitor hook fetches from /api/admin/monitor with 30s refresh
</success_criteria>

<output>
After completion, create `.planning/phases/quick-260407-gih/quick-260407-gih-02-SUMMARY.md`
</output>
