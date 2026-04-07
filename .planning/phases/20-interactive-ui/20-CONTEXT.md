# Phase 20: Interactive UI Overhaul - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Six UI improvements: draggable data explorer modals from KPI tiles, collapsible sidebars, map legend overlay, map rotation, weather skybox, fix bus interpolation display.

</domain>

<decisions>
## Implementation Decisions

### Draggable Data Explorer Modals (REQ-UI-01)
- Click KPI tile on right sidebar -> opens floating modal window
- Modal is draggable (react-rnd or custom drag), resizable
- Shows domain-specific content: latest values, time-series Recharts chart, data table
- Multiple modals can be open simultaneously
- Modal has close button, title bar with domain name

### Collapsible Sidebars (REQ-UI-02)
- Left sidebar (layers): toggle button at top-right edge, collapses to thin strip with expand arrow
- Right sidebar (dashboard): toggle button at top-left edge, same behavior
- Smooth CSS transition (width 0 with overflow hidden or transform translateX)
- Map fills full width when both collapsed

### Map Legend Overlay (REQ-UI-03)
- Button on map (bottom-left or bottom-right) with legend icon
- Click expands legend panel as overlay on top of map
- Shows active layer legends (AQI colors, traffic colors, etc.)
- Collapses back to button on click

### Map Rotation (REQ-UI-04)
- Enable MapLibre dragRotate (right-click drag to rotate)
- Add NavigationControl with compass/bearing indicator
- Allow pitch control (tilt) via ctrl+drag or touch
- Reset bearing button

### Weather Skybox (REQ-UI-05)
- MapLibre sky layer with gradient based on weather data
- Fetch current weather from KPI endpoint
- Clear sky: blue gradient, Overcast: gray, Rain: dark gray, Night: dark blue
- Update when weather data refreshes

### Fix Bus Interpolation (REQ-UI-06)
- BusInterpolationConnector exists but needs GTFS static data loaded first
- Ensure GTFSConnector loads shapes + stops + stop_times for OstalbMobil
- BusPositionLayer already exists — verify it renders when data flows
- May need to fix the GTFS download URL (NVBW URL returned 404 earlier)
- Fallback: use schedule-only interpolation if no GTFS-RT delays available

### Claude's Discretion
- Drag library choice (react-rnd vs custom CSS drag)
- Exact legend placement and styling
- Sky gradient color values for each weather condition
- GTFS feed URL fallback if NVBW is down

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- KpiTile.tsx with onSelect callback
- DashboardPanel.tsx renders all KPI tiles
- TimeSeriesChart component
- BusPositionLayer.tsx and BusRouteLayer.tsx exist
- BusInterpolationConnector exists with shape_walk algorithm
- MapView.tsx with NavigationControl (may need enabling rotation)
- WeatherConnector provides current conditions via KPI

### Integration Points
- Create DataExplorerModal component
- Modify page.tsx layout for collapsible sidebars
- Add LegendOverlay to MapView
- Enable dragRotate on Map component
- Add sky layer to map style
- Debug/fix GTFS data loading pipeline

</code_context>

<specifics>
No additional specifics.
</specifics>

<deferred>
## Deferred Ideas
- Dock modals to sides of screen
- Modal state persistence across page reloads
- Animated weather particles (rain, snow)
</deferred>
