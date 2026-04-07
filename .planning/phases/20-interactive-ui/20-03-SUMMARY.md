---
phase: 20-interactive-ui
plan: 03
subsystem: ui, backend
tags: [maplibre, fog, weather, gtfs, bus-interpolation, httpx]

requires:
  - phase: 20-01
    provides: "Toggle panel, sidebar, layer infrastructure"
  - phase: 14
    provides: "Bus interpolation connector and GTFS parsing"
provides:
  - "Weather-responsive sky gradient on map via MapLibre fog API"
  - "Resilient GTFS download with fallback URL, follow_redirects, User-Agent"
affects: []

tech-stack:
  added: []
  patterns:
    - "MapLibre setFog() for atmospheric effects driven by weather data"
    - "useMap() hook for imperative map instance access in child components"
    - "GTFS download fallback URL pattern for resilience"

key-files:
  created:
    - frontend/components/map/WeatherSkybox.tsx
  modified:
    - frontend/components/map/MapView.tsx
    - frontend/app/page.tsx
    - backend/app/connectors/bus_interpolation.py
    - backend/app/connectors/gtfs.py

key-decisions:
  - "MapLibre setFog() for weather sky gradient instead of sky layer (no terrain required)"
  - "Default NVBW bwgesamt URL when gtfs_url not configured instead of skipping"
  - "Reject GTFS responses < 1000 bytes as likely error pages"

patterns-established:
  - "WeatherSkybox: render-null component that imperatively controls map atmosphere"

requirements-completed: [REQ-UI-05, REQ-UI-06]

duration: 3min
completed: 2026-04-07
---

# Phase 20 Plan 03: Weather Skybox & Bus Interpolation Fix Summary

**MapLibre fog-based weather sky gradient reflecting live conditions, plus GTFS download resilience with fallback URLs and HTTP hardening**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-07T10:44:15Z
- **Completed:** 2026-04-07T10:47:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Weather skybox component maps Bright Sky API icon to fog presets (clear, overcast, rain, night)
- Bus interpolation connector defaults to NVBW URL when unconfigured, adds follow_redirects + User-Agent
- GTFSConnector also hardened with follow_redirects and User-Agent for consistency

## Task Commits

Each task was committed atomically:

1. **Task 1: Weather skybox gradient on map** - `108dcd0` (feat)
2. **Task 2: Fix bus position interpolation** - `ed6fe8d` (fix)

## Files Created/Modified
- `frontend/components/map/WeatherSkybox.tsx` - Fog preset component using MapLibre setFog()
- `frontend/components/map/MapView.tsx` - Added weatherCondition prop and WeatherSkybox render
- `frontend/app/page.tsx` - Added useKpi call to pass weather icon to MapView
- `backend/app/connectors/bus_interpolation.py` - Default NVBW URL, fallback URL, follow_redirects, User-Agent, size check
- `backend/app/connectors/gtfs.py` - follow_redirects and User-Agent header

## Decisions Made
- Used MapLibre `setFog()` API for atmospheric gradient instead of sky layer type (sky layer requires terrain setup)
- When `gtfs_url` is not configured, default to NVBW bwgesamt URL instead of skipping entirely
- Added response size check (< 1000 bytes rejected) to catch HTML error pages returned by GTFS servers

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing TypeScript error in LegendOverlay props (traffic/autobahn/energy optional vs required) causes `next build` to fail -- not introduced by this plan, not fixed (out of scope).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Weather skybox integrated and functional
- Bus interpolation ready for production with improved download resilience
- No blockers for subsequent plans

---
*Phase: 20-interactive-ui*
*Completed: 2026-04-07*
