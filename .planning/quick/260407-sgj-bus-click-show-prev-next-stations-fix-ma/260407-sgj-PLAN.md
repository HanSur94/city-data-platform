---
phase: quick-260407-sgj
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/models/bus_interpolation.py
  - backend/app/connectors/bus_interpolation.py
  - frontend/components/map/BusPopup.tsx
  - frontend/components/map/MapView.tsx
autonomous: true
requirements: [BUS-PREV-NEXT, BUS-FOLLOW-PERF]
must_haves:
  truths:
    - "Clicking a bus shows both previous station and next station in popup"
    - "Following a bus (popup tracking) does NOT cause full map re-render"
    - "Bus popup still follows the moving bus dot smoothly"
  artifacts:
    - path: "backend/app/models/bus_interpolation.py"
      provides: "BusPosition model with prev_stop field"
      contains: "prev_stop"
    - path: "backend/app/connectors/bus_interpolation.py"
      provides: "Interpolation sets prev_stop based on current segment"
      contains: "prev_stop"
    - path: "frontend/components/map/BusPopup.tsx"
      provides: "Displays both previous and next station"
      contains: "prev_stop"
    - path: "frontend/components/map/MapView.tsx"
      provides: "Optimized bus tracking that avoids unnecessary re-renders"
  key_links:
    - from: "backend/app/connectors/bus_interpolation.py"
      to: "frontend/components/map/BusPopup.tsx"
      via: "prev_stop property in GeoJSON feature properties"
      pattern: "prev_stop"
---

<objective>
Two fixes for the bus position layer:
1. Show previous station AND next station when clicking on a bus dot (currently only next_stop is shown).
2. Fix performance: when following a bus, the popup tracking loop causes full map re-renders every animation frame. Only the popup position should update, not the entire map.

Purpose: Better bus information and smooth map interaction when following a bus.
Output: Updated backend model + interpolation, updated BusPopup, optimized MapView tracking.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/components/map/MapView.tsx
@frontend/components/map/BusPopup.tsx
@frontend/components/map/BusPositionLayer.tsx
@backend/app/models/bus_interpolation.py
@backend/app/connectors/bus_interpolation.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add prev_stop to backend model and interpolation</name>
  <files>backend/app/models/bus_interpolation.py, backend/app/connectors/bus_interpolation.py</files>
  <action>
1. In `backend/app/models/bus_interpolation.py`, add `prev_stop: str = ""` field to `BusPosition` model, right after `next_stop`. Update the docstring to document it ("Name of the last departed stop").

2. In `backend/app/connectors/bus_interpolation.py`, update the `interpolate_position()` function to populate `prev_stop` in every `BusPosition` return:
   - **Trip not departed** (line ~148-162): `prev_stop=""` (no previous stop yet), `next_stop=trip.stop_times[0][0]` (already correct).
   - **Dwelling at stop i** (line ~166-191): `prev_stop=trip.stop_times[i-1][0] if i > 0 else ""`, `next_stop=stop_name` (already correct — dwelling at this stop means it IS the next stop).
   - **Between stops i and i+1** (line ~194-228): `prev_stop=trip.stop_times[i][0]` (just departed from stop i), `next_stop=name_b` (already correct, approaching stop i+1). The variable `_name_a` on line 195 should be renamed to `name_a` and used as `prev_stop`.
   - **Fallback at end** (line ~231-245): `prev_stop=trip.stop_times[-2][0] if len(trip.stop_times) >= 2 else ""`, `next_stop=trip.stop_times[-1][0]` (already correct).

3. In the GeoJSON properties dict (line ~331-344), add `"prev_stop": pos.prev_stop` alongside existing `"next_stop"`.
  </action>
  <verify>
    <automated>cd /Users/hannessuhr/Projects/city-data-platform && python -m pytest backend/tests/connectors/test_bus_interpolation.py -x -q 2>&1 | tail -5</automated>
  </verify>
  <done>BusPosition model has prev_stop field, interpolation populates it correctly in all code paths, GeoJSON properties include prev_stop</done>
</task>

<task type="auto">
  <name>Task 2: Show prev/next stations in BusPopup and fix map re-render on follow</name>
  <files>frontend/components/map/BusPopup.tsx, frontend/components/map/MapView.tsx</files>
  <action>
**BusPopup.tsx** — Show both previous and next station:
1. Extract `prev_stop` from `props.prev_stop as string | undefined` (same pattern as existing `nextStop`).
2. Replace the single "Naechster Halt" paragraph with two lines:
   - If `prevStop` exists: `<p className="text-[13px]">Letzter Halt: {prevStop}</p>`
   - If `nextStop` exists: `<p className="text-[13px]">Naechster Halt: {nextStop}</p>`
   Keep the same styling. Show both when available. If prev_stop is empty (bus hasn't departed), only show next.

**MapView.tsx** — Fix the bus popup tracking `useEffect` (lines ~227-250) that causes full map re-renders:

The problem: `setPopupInfo()` is called on EVERY `requestAnimationFrame` (~60fps), creating a new object each time. This triggers React to re-render the entire `<Map>` component tree including all layers, sources, and child components.

Fix approach — only call `setPopupInfo` when coordinates actually changed:

```tsx
const track = () => {
  const map = mapRef.current?.getMap();
  if (!map) { raf = requestAnimationFrame(track); return; }
  const features = map.querySourceFeatures('bus-positions', {
    filter: ['==', ['get', 'trip_id'], tripId],
  });
  if (features.length > 0 && features[0].geometry.type === 'Point') {
    const [lng, lat] = features[0].geometry.coordinates;
    setPopupInfo((prev) => {
      if (!prev || prev.domain !== 'busPosition') return prev;
      // Skip update if position unchanged (within ~1m precision)
      if (
        Math.abs(prev.longitude - lng) < 0.00001 &&
        Math.abs(prev.latitude - lat) < 0.00001
      ) {
        return prev; // Same reference = no re-render
      }
      return { ...prev, longitude: lng, latitude: lat, feature: features[0] as GeoJSON.Feature };
    });
  }
  raf = requestAnimationFrame(track);
};
```

The key change: returning the SAME `prev` reference when coordinates haven't moved enough skips the React re-render. The threshold of 0.00001 degrees (~1m) avoids floating point jitter while still being smooth enough for bus movement at 30s poll intervals.
  </action>
  <verify>
    <automated>cd /Users/hannessuhr/Projects/city-data-platform/frontend && npx next build 2>&1 | tail -3</automated>
  </verify>
  <done>BusPopup shows "Letzter Halt" and "Naechster Halt", map does not re-render on every animation frame when following a bus</done>
</task>

</tasks>

<verification>
1. Backend tests pass: `python -m pytest backend/tests/connectors/test_bus_interpolation.py -x`
2. Frontend builds without errors: `cd frontend && npx next build`
3. Manual: Click a bus dot — popup shows both "Letzter Halt" and "Naechster Halt"
4. Manual: Click a bus and follow it — map buildings/layers should NOT flash/refresh; only the popup moves
</verification>

<success_criteria>
- Bus popup displays previous station (Letzter Halt) and next station (Naechster Halt)
- Following a bus does not cause visible map flickering or layer re-rendering
- All existing bus position functionality (animation, line colors, delay indicators) unchanged
</success_criteria>

<output>
After completion, create `.planning/quick/260407-sgj-bus-click-show-prev-next-stations-fix-ma/260407-sgj-SUMMARY.md`
</output>
