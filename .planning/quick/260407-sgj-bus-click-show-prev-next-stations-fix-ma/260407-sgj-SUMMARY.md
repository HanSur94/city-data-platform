---
phase: quick-260407-sgj
plan: "01"
subsystem: bus-position
tags: [bus, popup, performance, prev-stop, re-render]
dependency_graph:
  requires: []
  provides: [prev_stop-in-geojson, bus-popup-prev-next, bus-follow-no-rerender]
  affects: [BusPopup, MapView, BusInterpolationConnector, BusPosition]
tech_stack:
  added: []
  patterns: [same-reference-bail-out, functional-setstate-for-perf]
key_files:
  created: []
  modified:
    - backend/app/models/bus_interpolation.py
    - backend/app/connectors/bus_interpolation.py
    - frontend/components/map/BusPopup.tsx
    - frontend/components/map/MapView.tsx
decisions:
  - Threshold of 0.00001 degrees (~1m) chosen to filter floating-point jitter without delaying visible movement updates
  - prev_stop="" for not-departed and no-previous-stop cases (consistent empty-string sentinel)
  - Dwelling at stop i: prev_stop = stop_times[i-1] because bus arrived from that stop
metrics:
  duration: "~10 minutes"
  completed: "2026-04-07T18:33:40Z"
  tasks_completed: 2
  files_modified: 4
---

# Quick Task 260407-sgj: Bus Click Show Prev/Next Stations + Fix Map Re-render on Follow

**One-liner:** Added prev_stop field through backend model/interpolation/GeoJSON and displayed "Letzter Halt" in popup; fixed bus-follow re-render by returning same state reference when position is unchanged.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Add prev_stop to backend model and interpolation | 9987467 | backend/app/models/bus_interpolation.py, backend/app/connectors/bus_interpolation.py |
| 2 | Show prev/next stations in BusPopup + fix map re-render on follow | d4d2c9a | frontend/components/map/BusPopup.tsx, frontend/components/map/MapView.tsx |

## What Was Built

### Task 1 — Backend: prev_stop field

- Added `prev_stop: str = ""` field to `BusPosition` Pydantic model with docstring documentation.
- Updated `interpolate_position()` to populate `prev_stop` in all four code paths:
  - **Not departed:** `prev_stop=""` (no previous stop)
  - **Dwelling at stop i:** `prev_stop=stop_times[i-1][0] if i > 0 else ""`
  - **Between stops i and i+1:** `prev_stop=name_a` (just departed from stop i; renamed `_name_a` to `name_a`)
  - **Fallback at end:** `prev_stop=stop_times[-2][0] if len >= 2 else ""`
- Added `"prev_stop": pos.prev_stop` to the GeoJSON feature properties dict.

### Task 2 — Frontend: Popup display + re-render fix

**BusPopup.tsx:** Extracted `prev_stop` from feature properties; added conditional `<p>Letzter Halt: {prevStop}</p>` before the existing next-stop line. Both lines render when available; only next-stop shows if bus hasn't departed yet.

**MapView.tsx:** Replaced the inline `setPopupInfo` callback in the tracking `useEffect` with a functional update that returns `prev` unchanged (same object reference) when coordinates differ by less than 0.00001 degrees (~1m). React's bailout optimization detects the same reference and skips re-rendering the entire `<Map>` tree, eliminating the 60fps full-component re-render cycle when following a bus.

## Verification

- Backend: `python -m pytest backend/tests/connectors/test_bus_interpolation.py -x -q` → 13 passed
- Frontend: `npx next build` → succeeded, no errors

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- `backend/app/models/bus_interpolation.py` — modified, contains `prev_stop`
- `backend/app/connectors/bus_interpolation.py` — modified, contains `prev_stop`
- `frontend/components/map/BusPopup.tsx` — modified, contains `prev_stop`
- `frontend/components/map/MapView.tsx` — modified, contains optimized tracking
- Commits `9987467` and `d4d2c9a` exist in git log
