---
phase: quick-260408-fm8
plan: 01
subsystem: frontend/map/transit
tags: [bus, maplibre, symbol-layer, SDF-image, visual]
tech-stack:
  added: []
  patterns:
    - MapLibre SDF image registration via map.addImage with ImageData from canvas
    - icon-rotate data-driven expression for bearing-aligned symbols
    - icon-halo-color for delay indication on symbol layers
key-files:
  modified:
    - frontend/components/map/BusPositionLayer.tsx
    - frontend/components/map/BusStopLayer.tsx
decisions:
  - Used ImageData (ctx.getImageData) instead of HTMLCanvasElement for map.addImage — canvas element is not a valid MapLibre image type
  - Added map.hasImage guard to prevent duplicate image registration on re-renders
  - SDF (signed distance field) mode enables data-driven icon-color tinting from a single white source image
metrics:
  duration: 8 minutes
  completed: 2026-04-08
  tasks_completed: 2
  files_modified: 2
---

# Quick Task 260408-fm8: Make buses rectangular-shaped on map

**One-liner:** Rectangle bus icons with bearing-based rotation via MapLibre SDF symbol layer; bus stop dots now correctly colored by transport mode string matching.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Replace bus position circles with rotated rectangle symbols | 7de4006 | BusPositionLayer.tsx |
| 2 | Fix bus stop dot colors to use mode-based string matching | bccab62 | BusStopLayer.tsx |

## What Was Built

**Task 1 — BusPositionLayer.tsx:**
- Registered a 24x12 rounded-rectangle SDF image (`bus-rect`) using `map.addImage()` with `ImageData` from an HTML canvas context
- SDF mode (`sdf: true`) allows the white source image to be tinted per-feature via `icon-color`
- Replaced `circleLayer` (CircleLayerSpecification) with `symbolLayer` (SymbolLayerSpecification)
- `icon-rotate: ['get', 'bearing']` aligns rectangles with bus direction of travel
- `icon-rotation-alignment: 'map'` keeps rotation relative to map orientation
- Delay indication moved from `circle-stroke-color` to `icon-halo-color` (green/yellow/orange/red)
- Removed unused `CircleLayerSpecification` import

**Task 2 — BusStopLayer.tsx:**
- Changed `circle-color` match expression from hex values (`#1565c0`, `#c62828`, `#2e7d32`) to string names (`bus`, `train`, `tram`)
- Actual `route_type_color` property carries string names, not hex — previous code always fell through to grey fallback
- Increased `circle-radius` from 5 to 6 for better visibility
- Bus stops now correctly show blue (bus), red (train), green (tram)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] HTMLCanvasElement not accepted by map.addImage**
- **Found during:** Task 1 TypeScript compilation
- **Issue:** `map.addImage('bus-rect', canvas, ...)` fails TypeScript — `HTMLCanvasElement` is not in the accepted union type for MapLibre's `addImage`
- **Fix:** Used `ctx.getImageData(0, 0, size.w, size.h)` to produce an `ImageData` object, which is in the accepted type union
- **Files modified:** BusPositionLayer.tsx
- **Commit:** 7de4006

## Self-Check: PASSED

- `frontend/components/map/BusPositionLayer.tsx` — exists, modified
- `frontend/components/map/BusStopLayer.tsx` — exists, modified
- Commit 7de4006 — present in git log
- Commit bccab62 — present in git log
- `npx tsc --noEmit` — no errors
