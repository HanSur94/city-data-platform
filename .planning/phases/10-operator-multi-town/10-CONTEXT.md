# Phase 10: Operator & Multi-Town - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

An operator can monitor connector health, a second town can be onboarded via a single YAML file, and demographic statistics complete the data offering. Requirements: PLAT-09, DEMO-01, DEMO-02, DEMO-03, DEMO-04.

Backend: admin health endpoint, demographics connectors (Wegweiser Kommune, Statistik BW GENESIS), Ulm stub town config. Frontend: admin health dashboard page, demographics detail panel + KPI tile, attribution footer bar.

</domain>

<decisions>
## Implementation Decisions

### Admin Health Dashboard & Multi-Town
- Admin dashboard: new /admin Next.js route with connector status table — green/yellow/red staleness badges, last-fetch timestamps, error rates. Separate from citizen-facing dashboard
- Multi-town validation: create towns/ulm.yaml stub with Ulm bbox + basic connectors, verify TOWN=ulm docker-compose up starts clean
- Attribution display: footer attribution bar listing active layer sources, updating dynamically as layers toggle. Datenlizenz Deutschland compliant

### Demographics Data Sources
- Primary: Wegweiser Kommune (700+ indicators, CC0) + Statistik BW GENESIS API for population basics
- Secondary: Zensus 2022 REST API + Bundesagentur employment data
- Presentation: new "Demografie" domain detail panel with KPI tiles (population, age structure, employment rate) + time-series charts. Follows DomainDetailPanel pattern
- KPI tile: population count + trend arrow + year. Click opens demographic detail panel

### Claude's Discretion
No items deferred — all grey areas resolved.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- backend/app/connectors/base.py — BaseConnector pattern
- backend/app/routers/kpi.py — KPI endpoint with domain-specific models
- frontend/components/dashboard/DomainDetailPanel.tsx — detail panel pattern
- frontend/components/dashboard/KpiTile.tsx — KPI tile pattern
- backend/app/connectors/scheduler.py — connector health tracking (last_successful_fetch)

### Integration Points
- New /admin route in Next.js
- New demographics connector in aalen.yaml
- DomainDetailPanel extended for demographics domain
- Attribution footer in layout.tsx

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond ROADMAP success criteria.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
