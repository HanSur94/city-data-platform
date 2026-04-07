---
phase: 19-feature-registry
plan: 02
subsystem: ui
tags: [react, maplibre, popup, building, feature-registry]

requires:
  - phase: 19-01
    provides: Feature registry API with /api/features/{id}/data endpoint
provides:
  - UnifiedBuildingPopup component showing all attached domain data
  - useFeatureData hook for fetching feature data from registry API
  - Interactive buildings-3d layer responding to click events
affects: [19-feature-registry]

tech-stack:
  added: []
  patterns: [unified-popup-with-multi-domain-sections, feature-data-hook-pattern]

key-files:
  created:
    - frontend/hooks/useFeatureData.ts
    - frontend/components/map/UnifiedBuildingPopup.tsx
  modified:
    - frontend/components/map/MapView.tsx

key-decisions:
  - "UnifiedBuildingPopup renders domain sections conditionally based on observations data presence"
  - "useFeatureData uses useState+useEffect pattern matching existing hooks (no SWR/React Query)"

patterns-established:
  - "Unified popup pattern: single component renders multiple domain sections from feature registry API"
  - "Feature data hook: useFeatureData(featureId) with cancel-on-change for stale request prevention"

requirements-completed: [REQ-REGISTRY-05, REQ-REGISTRY-06]

duration: 2min
completed: 2026-04-07
---

# Phase 19 Plan 02: Building Click & Unified Popup Summary

**Clickable buildings in 2D/3D with UnifiedBuildingPopup showing multi-domain data from feature registry API**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-07T08:16:44Z
- **Completed:** 2026-04-07T08:19:00Z
- **Tasks:** 3 (2 auto + 1 checkpoint auto-approved)
- **Files modified:** 3

## Accomplishments
- Created useFeatureData hook that fetches /api/features/{id}/data with loading/error/cancel states
- Built UnifiedBuildingPopup with conditional sections for Waerme, Solar, Fernwaerme, Demografie, and Energie
- Wired buildings-3d layer into MapView interactiveLayerIds and click handler
- German labels throughout; empty state shows "Keine Daten verfuegbar"

## Task Commits

Each task was committed atomically:

1. **Task 1: useFeatureData hook + UnifiedBuildingPopup component** - `a80d0a7` (feat)
2. **Task 2: Wire buildings into MapView click handling** - `f0b7aec` (feat)
3. **Task 3: Verify building click and popup** - auto-approved checkpoint (no code changes)

## Files Created/Modified
- `frontend/hooks/useFeatureData.ts` - Hook to fetch feature data from registry API with typed response
- `frontend/components/map/UnifiedBuildingPopup.tsx` - Unified building data card with multi-domain sections
- `frontend/components/map/MapView.tsx` - Added buildings-3d to interactiveLayerIds, building domain routing, UnifiedBuildingPopup rendering

## Decisions Made
- UnifiedBuildingPopup renders domain sections conditionally -- only shows sections where data exists in observations or properties
- useFeatureData uses useState+useEffect with cancelled flag pattern matching existing hooks (no SWR/React Query)
- Building features without feature_id (plain vector tile features) show "Keine Daten verfuegbar" without API call

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Building click interaction complete, ready for Plan 03 (search/filter features)
- Feature registry API from Plan 01 is wired to the frontend popup

---
*Phase: 19-feature-registry*
*Completed: 2026-04-07*
