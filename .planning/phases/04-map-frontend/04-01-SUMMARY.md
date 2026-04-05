---
phase: 04-map-frontend
plan: "01"
subsystem: frontend
tags: [next.js, typescript, maplibre, react-map-gl, protomaps, shadcn, docker]
dependency_graph:
  requires: [03-query-api]
  provides: [frontend-scaffold, type-definitions, polling-hooks, docker-frontend-service]
  affects: [04-02-map-components, 04-03-sidebar-ui]
tech_stack:
  added:
    - Next.js 16.2.2 (App Router, standalone output)
    - React 19.x
    - maplibre-gl 5.22.0
    - react-map-gl 8.1.0
    - pmtiles 4.4.0
    - "@protomaps/basemaps"
    - date-fns
    - shadcn/ui (switch, badge, separator, button, card, tooltip)
    - Tailwind CSS 4.x
  patterns:
    - Next.js App Router with TypeScript
    - Standalone output for Docker
    - Turbopack disabled (MapLibre web worker compat)
    - NEXT_PUBLIC_API_URL env var for API base
    - 60-second polling hook pattern
key_files:
  created:
    - frontend/package.json
    - frontend/next.config.ts
    - frontend/tsconfig.json
    - frontend/app/globals.css
    - frontend/app/layout.tsx
    - frontend/.env.local
    - frontend/types/geojson.ts
    - frontend/lib/api.ts
    - frontend/lib/map-styles.ts
    - frontend/hooks/useLayerData.ts
    - frontend/hooks/useRelativeTime.ts
    - frontend/Dockerfile
    - frontend/components/ui/ (switch, badge, separator, button, card, tooltip)
  modified:
    - docker-compose.yml
decisions:
  - "Turbopack disabled in dev script — MapLibre GL JS inline web worker conflicts with Turbopack"
  - "Next.js standalone output enabled — required for minimal Docker image with node server.js"
  - "Inter font replaces Geist — UI-SPEC mandates Inter as the typography font"
  - "lang=de set on html element — German-only app per UI-SPEC copywriting contract"
  - "frontend/lib/ force-added to git — global .gitignore excludes **/lib/ pattern"
metrics:
  duration_minutes: 4
  completed_date: "2026-04-05"
  tasks_completed: 3
  tasks_total: 3
  files_created: 13
  files_modified: 1
---

# Phase 04 Plan 01: Next.js Frontend Scaffold Summary

Next.js 16 frontend bootstrapped with MapLibre, PMTiles, shadcn/ui, TypeScript types mirroring backend LayerResponse, 60-second polling hook, and Docker integration on port 4000.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Scaffold Next.js 16 project | 7cddff7, e0ad2c5 | package.json, next.config.ts, globals.css, layout.tsx, components/ |
| 2 | Type definitions, lib utilities, hooks | 3bbce27 | types/geojson.ts, lib/api.ts, lib/map-styles.ts, hooks/*.ts |
| 3 | Dockerfile and docker-compose service | 4fe9b3b | frontend/Dockerfile, docker-compose.yml |

## Decisions Made

1. **Turbopack disabled** — `"dev": "next dev"` (no `--turbopack`). MapLibre GL JS uses an inline web worker that conflicts with Turbopack's module resolution in dev mode. Production builds are unaffected.

2. **Standalone output** — `output: 'standalone'` in next.config.ts. Required for the multi-stage Dockerfile to copy only `/.next/standalone` into the runner image, keeping the image minimal.

3. **Inter font instead of Geist** — UI-SPEC Design System table mandates Inter via `next/font/google`. The scaffold default (Geist) was replaced.

4. **lang="de" on html** — UI-SPEC copywriting contract: all text is German-only. No i18n layer needed in Phase 4.

5. **Port 4000** — Locked decision from STATE.md: Grafana occupies port 3000 on the target deployment system.

6. **force-add frontend/lib/** — Global user gitignore (`~/.gitignore`) has `**/lib/` pattern. Force-added to ensure lib/api.ts and lib/map-styles.ts are tracked.

## Verification Results

```
1. npm run build — EXIT 0, no TypeScript errors
2. grep maplibre-gl frontend/package.json — "maplibre-gl": "^5.22.0" FOUND
3. grep "4000" docker-compose.yml — "4000:4000" FOUND
4. grep "NEXT_PUBLIC_API_URL" frontend/lib/api.ts — env var pattern FOUND
5. grep "standalone" frontend/next.config.ts — output: 'standalone' FOUND
6. grep '"dev"' frontend/package.json — "next dev" (no --turbopack) FOUND
```

## Must-Have Artifacts

| Artifact | Status |
|----------|--------|
| frontend/package.json with maplibre-gl | DONE |
| frontend/types/geojson.ts exports LayerResponse, AQIFeatureProperties, TransitFeatureProperties | DONE |
| frontend/lib/map-styles.ts exports buildMapStyle, AQI_COLOR_RAMP, TRANSIT_COLORS | DONE |
| frontend/hooks/useLayerData.ts exports useLayerData (60s polling) | DONE |
| frontend/Dockerfile multi-stage Node 22 Alpine | DONE |
| docker-compose.yml frontend service on port 4000 | DONE |

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Noted Observations

**Global gitignore conflict (tracked, not a bug):** The developer's global `~/.gitignore` excludes `**/lib/` directories. The plan required `frontend/lib/api.ts` and `frontend/lib/map-styles.ts` to be committed. These were force-added with `git add -f`. This is a one-time setup concern and does not affect CI/CD or other contributors.

## Known Stubs

None. This plan creates infrastructure only (no UI components with data sources). Hooks (`useLayerData`, `useRelativeTime`) are complete implementations, not stubs — they will receive real data once Plans 02 and 03 wire map components.

## Self-Check: PASSED
