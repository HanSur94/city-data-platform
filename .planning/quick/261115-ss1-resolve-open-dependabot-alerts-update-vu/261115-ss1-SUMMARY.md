---
phase: quick-261115-ss1
plan: 01
subsystem: dependencies
tags: [dependabot, security, uv, npm, next, maplibre-gl, shadcn]
requires: []
provides:
  - "All 193 Dependabot alerts resolved except 2 with no upstream patch (braces, deepmerge)"
affects: [backend/uv.lock, frontend/package.json, frontend/package-lock.json, frontend/components/map/MapView.tsx]
tech-stack:
  added: []
  patterns:
    - "maplibre-gl v6 namespace import + setWorkerUrl(new URL(literal, import.meta.url)) under Next/Turbopack"
key-files:
  created: []
  modified:
    - backend/uv.lock
    - frontend/package.json
    - frontend/package-lock.json
    - frontend/components/map/MapView.tsx
key-decisions:
  - "fastapi kept at 0.135.3 (starlette>=0.46.0 has no upper bound; tests pass on starlette 1.10.0)"
  - "eslint-config-next kept at 16.2.2 (not 16.4.6): 16.4.6 requires eslint-plugin-react-hooks ^7.1.0, which adds 3 new set-state-in-effect lint errors in unchanged files"
  - "eslint-plugin-react-hooks held at 7.0.1 in the lock by not letting npm re-resolve it"
status: complete
commits: 3
plan_head_before: 211e069403bdaf436ee6266b5c476e181e463487
plan_head_after: a1af8f766b7ac90f10c9ad5525419f37f5f9a0d8
actuals:
  tokens: 60000
  tasks: 3
  commits: 3
metrics:
  completed: 2026-11-15
---

# Phase quick-261115-ss1 Plan 01: Resolve open Dependabot alerts Summary

Resolved 191 of the 193 open Dependabot alerts with three revertable commits (backend lock, next/shadcn/transitives, maplibre-gl 5 to 6). The remaining 2 (braces, deepmerge) have no patched version upstream.

## Commits

| Task | Commit | Content |
| ---- | ------ | ------- |
| 1 | 282889d | backend/uv.lock targeted re-lock (22 alerts) |
| 2 | bee03ff | next 16.4.6, shadcn ^4.23.0, in-range transitive refresh |
| 3 | a1af8f7 | maplibre-gl ^6.18.0, react-map-gl ^8.1.3, MapView.tsx v6 changes |

Nothing pushed. Branch is `fix/dependabot-alerts`.

## Versions

### Backend (uv.lock)

| Package | Old | New |
| ------- | --- | --- |
| anyio | 4.13.0 | 4.14.2 |
| certifi | 2026.2.25 | 2026.10.23 |
| cryptography | 46.0.6 | 50.0.2 |
| idna | 3.11 | 3.20 |
| lxml | 6.0.2 | 6.1.3 |
| mako | 1.3.10 | 1.4.3 |
| pytest | 9.0.2 | 9.2.0 |
| starlette | 1.0.0 | 1.10.0 |
| urllib3 | 2.6.3 | 2.8.0 |
| zeep | 4.3.2 | 4.3.3 |
| pytz | 2026.1.post1 | removed (only zeep 4.3.2 required it) |

The uv.lock commit also carries the previously uncommitted local modification: beautifulsoup4 4.14.3, lhpapi 1.0.10 and soupsieve 2.8.3, which the lock was missing relative to pyproject.toml. A name/version diff against HEAD showed no movement beyond the 10 packages, pytz and these three.

fastapi decision: kept at 0.135.3 (no bump, no fallback needed).

### Frontend

Direct: next 16.2.2 -> 16.4.6 (exact), shadcn ^4.1.2 -> ^4.23.0, maplibre-gl ^5.22.0 -> ^6.18.0 (locked 6.18.0), react-map-gl ^8.1.0 -> ^8.1.3 (locked 8.1.3, @vis.gl/react-maplibre 8.1.3). eslint-config-next unchanged at 16.2.2 (see below). No other package.json lines changed.

Transitive (npm update, no overrides): @babel/core 7.29.0 -> 7.29.13; @humanfs/node 0.16.7 -> 0.16.8; baseline-browser-mapping 2.10.15 -> 2.11.37; brace-expansion 1.1.13 -> 1.1.22 and 5.0.5 -> 5.0.13; browserslist 4.28.2 -> 4.29.5; fflate 0.8.2 -> 0.8.3; ip-address 10.1.0 -> 10.7.6; js-yaml 4.1.1 -> 4.3.2; nanoid 3.3.11 -> 3.3.20; postcss 8.4.31/8.5.8 -> 8.5.23; postcss-selector-parser 7.1.1 -> 7.2.1; protocol-buffers-schema 3.6.0 -> 3.6.1; sharp 0.34.5 -> 0.35.5; source-map-js 1.2.1 -> 1.2.2; zod 3.25.76/4.3.6 -> 4.6.7. Gone from the tree after shadcn 4.23: hono, @hono/node-server, @modelcontextprotocol/sdk, body-parser, express (via sdk), proxy-addr, qs, fast-uri.

eslint-config-next outcome: the plan's fallback applied. With next and eslint-config-next both at 16.4.6, lint errors rose 11 -> 14 (three new `react-hooks/set-state-in-effect` errors in BusPositionLayer.tsx:492, FeatureSearch.tsx:76, useLayerMetadata.ts:53, all unchanged files). The cause is eslint-config-next 16.4.6 requiring eslint-plugin-react-hooks ^7.1.0 (7.1.1). A first attempt that only reinstalled eslint-config-next@16.2.2 still left 7.1.1 in the lock (14 errors), so the lock was rebuilt from HEAD with eslint-config-next left at 16.2.2 and eslint-plugin-react-hooks staying at 7.0.1. Result: 11 errors, same as baseline. There is now a version mismatch (next 16.4.6, eslint-config-next 16.2.2); eslint-config-next has no alert of its own. Follow-up: when the 3 new findings are fixed in source, move eslint-config-next to 16.4.x.

## Gate output

Backend (`pytest -q -m "not slow"`):
- Baseline: `4 failed, 306 passed, 1 skipped, 4 deselected, 20 errors in 33.29s`
- After: `4 failed, 306 passed, 1 skipped, 4 deselected, 1 warning, 20 errors in 12.33s`
- `comm -13` of baseline vs after failing ids: empty. All failures are environmental and pre-existing: tests/test_boundaries.py (6 errors), tests/test_connector.py (6), tests/test_migrations.py (8) need PostgreSQL; tests/test_config.py (2) and tests/test_multi_town.py (1) fail on environment/config; tests/connectors/test_ladesaeulen.py (1 failed).
- `uv lock --check` passes.

Frontend (baseline -> final, after maplibre commit):
- build: 0 -> 0
- tsc: 0 errors -> 0 errors
- lint: rc 1, 11 errors -> rc 1, 11 errors (the 11 lint errors, 13 warnings are pre-existing, mostly react-hooks/set-state-in-effect)
- `npm ci` succeeded on the Task 2 lock; `npm ci --dry-run` passes on the final lock.

## maplibre outcome

Upgraded to maplibre-gl 6.18.0 and react-map-gl 8.1.3. Only frontend/components/map/MapView.tsx changed in source: default import became `import * as maplibregl from 'maplibre-gl'`, plus a module-scope `maplibregl.setWorkerUrl(new URL('maplibre-gl/dist/maplibre-gl-worker.mjs', import.meta.url).toString())` with a comment. No type fixes were needed (tsc clean). The production build emitted the worker as `frontend/.next/static/media/maplibre-gl-worker.1ownoxc0w6_hx.mjs` (plus a dev variant `maplibre-gl-worker-dev.0809uj1_burjj.mjs`).

Orchestrator browser check (2026-11-15, `next dev` on Next 16.4.6, no backend running): the base map rendered from `public/tiles/aalen.pmtiles`, the maplibre worker file loaded, and panning worked. Not checked, because no backend was running: bus positions, the AQI layer and feature popups. Console errors seen were failed API calls to the backend and 400/500 responses from the public LUBW and LGL WMS servers, which return the same codes to a direct request.

Remaining human check with a running backend (not done, non-blocking): run `npm --prefix frontend run dev`, open the map in a WebGL2 browser, and confirm base tiles render, bus positions and the AQI layer draw, feature clicks open popups, and the console shows no maplibre worker or GPUInitializationError errors. Only a build and type check were run; the map was not exercised in a browser.

## Checker result

`check_alerts.py --allow braces,deepmerge` over all 193 alerts exits 0: `total=193 resolved=191 unresolved=0 no_patch=2`. Sanity run at the start (unchanged tree) gave `total=193 resolved=0 unresolved=191 no_patch=2`. Backend-only: `total=22 resolved=22 unresolved=0 no_patch=0`.

Remaining alerts:
- braces 3.0.3 (high): advisory GHSA-vfj7-8cjw-p6xm is withdrawn and has no patched version; it comes via micromatch, whose latest release (4.0.8) requires ^3.0.3.
- deepmerge 4.3.1 (low): GHSA-gcqx-w48m-w2h4, no patched version exists; it comes via shadcn.

## npm audit cross-check

`metadata.vulnerabilities`: low 2, moderate 11, high 0, critical 0, total 13 (saved to the scratchpad as npm-audit-final.json). None of these are among the 193 alerts, and none were force-fixed. npm's offered "fixes" would downgrade eslint-config-next to 15.5.29 and shadcn to 1.0.0, so they were not applied.
- minimatch 7.0.0 - 11.0.0 (moderate, DoS via globparts), via @typescript-eslint/typescript-estree <= 8.72.2 and @ts-morph/common; no in-range fix.
- @typescript-eslint/eslint-plugin, parser, type-utils, typescript-estree, utils, and typescript-eslint (all moderate, <= 8.72.2): flagged only "via" minimatch; eslint-config-next also flagged via typescript-eslint.
- @ts-morph/common and ts-morph (moderate): via minimatch (shadcn dependency chain).
- deepmerge (low) with @shadcn/registry (low) and shadcn (moderate): "via" deepmerge, no patch exists.

## Docker check

No change needed. frontend/Dockerfile uses node:22-alpine (satisfies next and sharp 0.35 `node >=20.9.0`); the lock contains `@next/swc-linux-x64-musl` 16.4.6 (equal to next) and `@img/sharp-linuxmusl-x64` 0.35.5. backend uses python:3.12-slim with `uv sync --no-dev --frozen`; the new lock carries `cryptography-50.0.2-cp311-abi3-manylinux...x86_64` and `lxml-6.1.3-cp312-cp312-manylinux...x86_64` wheels. Dockerfiles, docker-compose.yml and pyproject.toml are unchanged (verified with git diff against the start commit).

## Deviations from Plan

**1. [Rule 3 - Blocking] eslint-config-next left at 16.2.2 (plan fallback) and react-hooks plugin kept at 7.0.1.**
- Found during: Task 2 compare (lint 11 -> 14 errors)
- Fix: see Versions section. The first fallback attempt was insufficient; the lock was rebuilt from HEAD so npm did not re-resolve eslint-plugin-react-hooks.
- Files modified: frontend/package.json (net no change to this line), frontend/package-lock.json
- Commit: bee03ff

Otherwise the plan was executed as written. The Next 16 upgrade guide (`frontend/node_modules/next/dist/docs/01-app/02-guides/upgrading/version-16.md`) was read before any frontend change; the project was already on 16.2, and no Next.js code was changed.

## Known Stubs

None.

## Threat Flags

None.

## Follow-ups (not done)

- shadcn is only used for `@import "shadcn/tailwind.css"`; vendoring that stylesheet would remove deepmerge and the shadcn-tree advisories.
- Watch typescript-eslint for a minimatch >= 11.0.1 release.
- Fix the 3 new `set-state-in-effect` findings (BusPositionLayer.tsx:492, FeatureSearch.tsx:76, useLayerMetadata.ts:53) and then move eslint-config-next to 16.4.x with next.
- Browser smoke test of the map under maplibre-gl 6.

## Self-Check: PASSED

- Commits 282889d, bee03ff, a1af8f7 exist on the branch; each carries the Co-Authored-By trailer.
- Changed files vs start commit: backend/uv.lock, frontend/package.json, frontend/package-lock.json, frontend/components/map/MapView.tsx only.
- Working tree has no staged or modified tracked files; untracked files are the pre-existing ones.
