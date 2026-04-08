---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: — AalenPulse Feature Parity
status: verifying
stopped_at: "Completed quick task 260408-dbq: Ensure all real bus stops (Haltestellen) appear on map"
last_updated: "2026-04-08T07:47:11.341Z"
last_activity: "2026-04-07 - Completed quick task 260407-mwh: Fix transit layer performance and air quality SQL bug"
progress:
  total_phases: 19
  completed_phases: 10
  total_plans: 23
  completed_plans: 23
  percent: 14
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-06)

**Core value:** Citizens and city officials can see all publicly available city data in one place, on a map, updated live — no technical expertise required.
**Current focus:** v2.0 — Implementing AalenPulse requirements gaps

## Current Position

Phase: 20
Plan: Not started
Status: Phase complete — ready for verification
Last activity: 2026-04-08 - Completed quick task 260408-fm8: Make buses rectangular shaped on map, bus stops get colored dots

Progress: [██░░░░░░░░] 14%

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

## Accumulated Context

### Decisions

- v1.0 completed with 10 phases, 46 plans
- v2.0 scope: 8 phases (11-18) covering AalenPulse requirements gaps
- Phase numbering continues from v1.0 (11+) for consistency
- Adaptive polling via skip logic: scheduler at 600s, connector skips off-peak if <1800s elapsed
- congestion_ratio in feature properties, speed_avg_kmh in traffic_readings for schema compat
- [Phase 11]: Separate source ID traffic-flow to avoid conflict with existing traffic source for BASt circles
- [Phase 12]: Used asyncio.to_thread for lhpapi since it is synchronous/blocking
- [Phase 12]: Separate kocher-features source to avoid interfering with existing water-features source
- [Phase 13]: Feature-properties-only pattern for parking: infrastructure domain features with no hypertable writes
- [Phase 13]: Used CircleParking icon from lucide-react for parking KPI tile
- [Phase 14]: Lazy import of gtfs_kit inside methods to keep test collection fast
- [Phase 14]: Pure function extraction (shape_walk, interpolate_position) for direct unit testing of algorithms
- [Phase 14]: Used inline fetchLayer with 30s setInterval instead of useLayerData (60s) for bus position refresh
- [Phase 14]: Separate GeoJSON source IDs (bus-positions, bus-routes) to avoid transit source interference
- [Phase 15]: Pure function extraction for IDW and grid generation enables unit testing without database
- [Phase 15]: feature_type filter on layers endpoint separates grid cells from sensor points without new endpoint
- [Phase 15]: MapLibre heatmap layer type for grid overlay with dynamic paint expression rebuild on pollutant change
- [Phase 15]: Separate air-quality-grid source ID to avoid conflict with existing air-quality sensor source
- [Phase 16]: Computation connector pattern for SolarProductionConnector (override run() like AirQualityGridConnector)
- [Phase 16]: Disabled LadesaeulenConnector, replaced by EvChargingConnector with live OCPDB status
- [Phase 16]: Added source query param to infrastructure layers endpoint for OCPDB vs BNetzA separation
- [Phase 16]: Separate GeoJSON sources (solar-glow, ev-charging-live) to avoid conflicts with existing sources
- [Phase 16]: EvChargingPopup backward-compatible: source=ocpdb shows live status, else legacy BNetzA fields
- [Phase 17-static-layers]: Dual WmsOverlayLayer instances for LDEN/LNight to avoid tile reload on metric toggle
- [Phase 17-static-layers]: Zensus 2022 WMS for demographics grid instead of backend point data
- [Phase 17-static-layers]: CyclingLayer uses inline fetch with source=cycling query param for API sub-filtering
- [Phase 18]: Static LAYER_METADATA_REGISTRY with DB merge for last_updated only
- [Phase 18]: useLayerMetadata hook polls /api/metadata/layers every 60s with stale detection at 2x interval
- [Phase 19]: Semantic ID computed automatically in upsert_feature (backward compatible)
- [Phase 19]: feature_observations VIEW unions all 7 hypertables for cross-domain queries
- [Phase 19]: Feature data endpoint accepts both UUID and semantic_id via string heuristic
- [Phase 19]: UnifiedBuildingPopup renders domain sections conditionally based on observations data presence
- [Phase 19]: useFeatureData uses useState+useEffect cancel pattern matching existing hooks
- [Phase 19]: CrossDomainSection as reusable collapsible component for cross-domain popup data
- [Phase 19]: MapView onMapReady callback pattern for exposing flyTo to parent without forwardRef
- [Phase 19]: 800ms delay for popup after flyTo animation on search result selection
- [Phase quick-260407-gih]: Separate SQL queries per section with try/except for independent resilience in monitor endpoint
- [Phase quick-260407-gih]: Inline connector table in admin page instead of modifying existing ConnectorHealthTable for backward compatibility
- [Phase 20-interactive-ui]: Toggle buttons positioned at panel edges with translate-x-full for always-visible access
- [Phase 20-interactive-ui]: LegendOverlay independent from sidebar legends - both coexist
- [Phase 20-interactive-ui]: Native pointer events + CSS resize for DataExplorerModal drag/resize (no react-rnd dependency)
- [Phase 20-interactive-ui]: KPI tile click opens floating DataExplorerModal, replaces inline DomainDetailPanel toggle
- [Phase 20]: MapLibre setFog() for weather sky gradient instead of sky layer (no terrain required)
- [Phase 20]: Default NVBW bwgesamt URL when gtfs_url not configured instead of skipping

### Pending Todos

None yet.

### Blockers/Concerns

- ~~TomTom API key needed for Phase 11 (traffic flow)~~ — resolved: .env + config.py env var resolution (260408-hyd)
- LHP gauge ident for Huttlingen needs lookup at implementation
- sw-aalen.de parking page structure may change — scraper fragility

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260407-mwh | Fix transit layer performance and air quality SQL bug | 2026-04-07 | 5c9cc3d | [260407-mwh-fix-transit-layer-performance-and-air-qu](./quick/260407-mwh-fix-transit-layer-performance-and-air-qu/) |
| 260407-pft | Bus position layer visual overhaul: per-line colors, train/bus distinction, sidebar line filter | 2026-04-07 | d120c78 | [260407-pft-bus-position-layer-visual-overhaul-per-l](./quick/260407-pft-bus-position-layer-visual-overhaul-per-l/) |
| 260407-sgj | Bus popup shows prev/next stations; fix map re-render when following bus | 2026-04-07 | d4d2c9a | [260407-sgj-bus-click-show-prev-next-stations-fix-ma](./quick/260407-sgj-bus-click-show-prev-next-stations-fix-ma/) |
| 260408-dbq | Ensure all real bus stops (Haltestellen) appear on map with route info | 2026-04-08 | 8514732 | [260408-dbq-ensure-all-real-bus-stops-haltestellen-f](./quick/260408-dbq-ensure-all-real-bus-stops-haltestellen-f/) |
| 260408-fm8 | Make buses rectangular-shaped on map: rotated rectangle symbol, stop color fix | 2026-04-08 | bccab62 | [260408-fm8-make-buses-rectangular-shaped-on-map-bus](./quick/260408-fm8-make-buses-rectangular-shaped-on-map-bus/) |
| 260408-hyd | Set up TomTom env var resolution: ${VAR} substitution in YAML config, .env.example, Docker wiring | 2026-04-08 | 805c59c | [260408-hyd-set-up-tomtom-traffic-busyness-integrati](./quick/260408-hyd-set-up-tomtom-traffic-busyness-integrati/) |
| 260408-jiz | Batch upsert features to unblock asyncio event loop: batch_upsert_features on BaseConnector, migrate GTFS/BusInterpolation/GTFSRealtime | 2026-04-08 | 86d4ebd | [260408-jiz-batch-upsert-features-to-unblock-asyncio](./quick/260408-jiz-batch-upsert-features-to-unblock-asyncio/) |

## Session Continuity

Last session: 2026-04-08T11:00:08Z
Stopped at: Completed quick task 260408-jiz: Batch upsert features to unblock asyncio
Resume file: None
