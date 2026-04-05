---
phase: 04-map-frontend
plan: 02
subsystem: frontend
tags: [map, maplibre, pmtiles, sidebar, ui, react, nextjs]
dependency_graph:
  requires: [04-01]
  provides: [map-shell, sidebar-ui, layer-toggles, aqi-legend, transit-legend]
  affects: [04-03]
tech_stack:
  added: [shadcn/label]
  patterns: [dynamic-import-ssr-false, pmtiles-protocol-useEffect, layerVisibility-props]
key_files:
  created:
    - frontend/components/map/MapView.tsx
    - frontend/components/sidebar/Sidebar.tsx
    - frontend/components/sidebar/LayerToggle.tsx
    - frontend/components/sidebar/AQILegend.tsx
    - frontend/components/sidebar/TransitLegend.tsx
    - frontend/components/ui/label.tsx
  modified:
    - frontend/app/page.tsx
    - frontend/.gitignore
decisions:
  - "PMTiles binary excluded from git via public/tiles/*.pmtiles glob in .gitignore"
  - "page.tsx is 'use client' to hold layerVisibility useState — passed as props to Sidebar and MapView"
  - "Label shadcn component added (not in Plan 01 install) to support LayerToggle accessibility"
  - "PMTiles file not downloaded — Protomaps daily build URL returned 404 (network issue); noted as known gap"
metrics:
  duration_minutes: 3
  completed_date: "2026-04-05"
  tasks_completed: 2
  files_created: 6
  files_modified: 2
---

# Phase 04 Plan 02: Map Shell and Sidebar Summary

**One-liner:** MapLibre map centered on Aalen with PMTiles SSR-safe setup, plus sidebar with German-labeled layer toggles (ÖPNV, Luftqualität), AQI color strip legend, and transit route swatches.

---

## What Was Built

### Task 1: MapView with PMTiles base map (SSR-safe)

- `frontend/components/map/MapView.tsx` — client component wrapping react-map-gl/maplibre `Map`, with PMTiles protocol registered in a `useEffect` using `useRef` to prevent double-registration. Centered on Aalen `[10.0918, 48.8374]` at zoom 13, min 8, max 18.
- `frontend/app/page.tsx` — replaced default scaffold with a `'use client'` page holding `layerVisibility` state (`transit`, `airQuality` booleans). MapView loaded via `next/dynamic` with `ssr: false` to prevent `window-is-not-defined` SSR errors.
- `frontend/.gitignore` — added `public/tiles/*.pmtiles` to exclude binary map data from git.

### Task 2: Sidebar with layer toggles and legends

- `frontend/components/sidebar/LayerToggle.tsx` — single toggle row using shadcn `Switch` + `Label`, minimum 44px touch target, optional red freshness-error dot.
- `frontend/components/sidebar/AQILegend.tsx` — horizontal color strip using `AQI_TIER_COLORS` from `lib/map-styles.ts` (5 tiers: Gut, Moderat, Schlecht, Sehr schlecht, Gefährlich).
- `frontend/components/sidebar/TransitLegend.tsx` — route type swatches using `TRANSIT_COLORS` from `lib/map-styles.ts` (Bus, Bahn, Straßenbahn).
- `frontend/components/sidebar/Sidebar.tsx` — main sidebar with "Stadtdaten Aalen" heading, "Ebenen" section with two toggles, "Legende" section with AQI + transit legends. Desktop (≥1024px): fixed 280px aside. Tablet/mobile: overlay drawer triggered by floating `Layers` button.
- `frontend/components/ui/label.tsx` — shadcn label component added (was missing from Plan 01 install).

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added shadcn label component**
- **Found during:** Task 2
- **Issue:** `LayerToggle.tsx` requires `@/components/ui/label` for accessibility-compliant toggle rows, but it was not installed in Plan 01
- **Fix:** Ran `npx shadcn add label --yes` to install the component
- **Files modified:** `frontend/components/ui/label.tsx`
- **Commit:** 35091cd

---

## Known Gaps

### PMTiles binary file not downloaded

- **File:** `frontend/public/tiles/aalen.pmtiles`
- **Reason:** Protomaps daily build URL (`https://build.protomaps.com/YYYY-MM-DD.pmtiles`) returned HTTP 404 during execution — the daily build for 2026-04-05 was not yet available or the URL format changed.
- **Impact:** Map will render but show empty tiles when running `npm run dev` without this file. The map component and style system are correctly wired.
- **Resolution:** Run the extract command once the file is available:
  ```bash
  npx pmtiles extract https://build.protomaps.com/{date}.pmtiles \
    frontend/public/tiles/aalen.pmtiles --bbox=9.8,48.7,10.3,49.0
  ```
  Or download from: https://protomaps.com/downloads/osm

---

## Known Stubs

None — all components are wired to real state and real constants. Layer visibility state is stored in `page.tsx` but actual layer rendering (adding/removing MapLibre layers) is Plan 03's responsibility per the plan's explicit scope boundary.

---

## Self-Check: PASSED

All 7 key files verified present. Both task commits verified (dc428e5, 35091cd). Build exits 0 with 0 TypeScript errors.
