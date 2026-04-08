---
phase: quick-260408-kqo
plan: 01
subsystem: frontend/map
tags: [chart, traffic, timeseries, popup, recharts]
dependency_graph:
  requires: [useTimeseries hook, /api/timeseries/traffic endpoint]
  provides: [TrafficFlowPopupChart component, 24h chart in TrafficFlowPopup]
  affects: [MapView.tsx, TrafficFlowPopup.tsx]
tech_stack:
  added: []
  patterns: [SensorPopupChart pattern, dual-yAxis Recharts LineChart, client-side congestion ratio computation]
key_files:
  created:
    - frontend/components/map/TrafficFlowPopupChart.tsx
  modified:
    - frontend/components/map/TrafficFlowPopup.tsx
    - frontend/components/map/MapView.tsx
decisions:
  - Congestion ratio computed client-side from speed_avg_kmh / freeflow_kmh (clamped [0,1]) to avoid backend changes
  - Congestion line conditionally rendered only when freeflowKmh is available and >0
  - Dual YAxis: left for speed (km/h), right for congestion ratio ([0,1])
metrics:
  duration: ~10 minutes
  completed: "2026-04-08"
  tasks: 1
  files: 3
---

# Quick Task 260408-kqo: TomTom traffic time-series chart (congestion) - Summary

**One-liner:** 24h dual-line speed+congestion chart in TrafficFlowPopup using useTimeseries('traffic') with client-side congestion ratio from freeflow speed.

## What Was Built

Added `TrafficFlowPopupChart.tsx` following the exact `SensorPopupChart.tsx` pattern. When a user clicks a TomTom traffic flow segment, the popup now shows a 24h chart below the static values with:
- Blue line: speed in km/h (left Y axis)
- Orange line: congestion ratio 0-1 (right Y axis, only when freeflowKmh is available)

Congestion ratio is computed on the frontend: `1 - speed / freeflowKmh`, clamped to [0, 1]. If no freeflow speed is available, only the speed line renders.

Loading state: shimmer skeleton at 100px height. Empty or error: silently returns null.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create TrafficFlowPopupChart and wire into popup | 83c0865 | TrafficFlowPopupChart.tsx (created), TrafficFlowPopup.tsx, MapView.tsx |

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- frontend/components/map/TrafficFlowPopupChart.tsx: exists (103 lines, > 50 min)
- frontend/components/map/TrafficFlowPopup.tsx: imports and renders TrafficFlowPopupChart
- frontend/components/map/MapView.tsx: passes featureId and town to TrafficFlowPopup
- Commit 83c0865 exists
