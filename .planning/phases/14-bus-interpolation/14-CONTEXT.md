# Phase 14: Bus Position Interpolation - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement interpolated bus positions from GTFS schedule + GTFS-RT delays. Show moving bus icons on routes colored by delay status. Interpolation engine runs every 30 seconds.

</domain>

<decisions>
## Implementation Decisions

### Interpolation Algorithm
- Every 30 seconds: fetch GTFS-RT, parse TripUpdates for OstalbMobil trips
- For each active trip: get ordered stop list + scheduled times + route shape from GTFS static
- Apply delay offset from GTFS-RT to stop times
- Find current segment (between which two stops the bus is now)
- Calculate progress fraction along segment
- Walk along shape geometry at progress fraction to get estimated lat/lon
- Expected accuracy: 100-300m

### Connector Design
- Computation connector (not a direct API connector)
- Reads from existing GTFS static data (features table) + GTFS-RT delay data
- Produces bus_position observations in transit_positions hypertable
- Domain: "transit"
- Values: {lat, lon, bearing, progress, trip_id, route_id, delay_seconds, line_name, destination, next_stop}

### Frontend Display
- Bus icons (small colored dots) moving along route geometry
- Color by delay: green <2min, yellow 2-5min, orange 5-10min, red >10min
- Click/hover popup: line number, destination, current delay, next stop
- Faint route lines when bus layer is active
- Smooth CSS/requestAnimationFrame animation between 30s updates

### Edge Cases
- Bus dwelling at stop: hold position at stop marker
- No delay data: fall back to pure schedule interpolation (assume on time)
- Trip not yet departed: show at origin stop with countdown
- Trip completed: remove icon
- Multiple buses on same route: each trip_id tracked independently

### Claude's Discretion
- Shape geometry walking algorithm (linear interpolation along LineString)
- How to match GTFS-RT trip_ids to static GTFS data
- Frontend animation approach for smooth movement

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- GTFSConnector already loads routes, stops, shapes from NVBW bwgesamt
- GTFSRealtimeConnector polls GTFS-RT feed for delays
- transit_positions hypertable: time, feature_id, trip_id, route_id, delay_seconds, geometry
- TransitLayer.tsx shows routes and stops

### Integration Points
- Add BusInterpolationConnector to backend/app/connectors/
- Read from features (shapes, stops) + GTFS-RT delay data
- Write interpolated positions to transit_positions
- Create BusPositionLayer frontend component
- Add BusPopup and sidebar toggle

</code_context>

<specifics>
## Specific Ideas

- OstalbMobil lines in Aalen: 71, 72, 73, 74, 81, 82, 83, 90+
- ~15-30 buses active simultaneously during operating hours
- GTFS-RT protobuf is small (~few KB), polling every 30s is within limits
- shapes.txt contains exact GPS polyline geometry of each route

</specifics>

<deferred>
## Deferred Ideas

- Cancelled trips from ServiceAlerts (dashed/dimmed route)
- Animated trail effect behind bus icon

</deferred>
