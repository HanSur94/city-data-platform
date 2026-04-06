# Phase 15: Air Quality Heatmap — IDW Interpolation - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Create continuous air quality surface across Aalen using IDW spatial interpolation from UBA + sensor.community point data. Translucent heatmap overlay with pollutant toggle.

</domain>

<decisions>
## Implementation Decisions

### IDW Algorithm
- Inverse Distance Weighting on 50m x 50m grid covering Aalen bbox
- estimated = sum(value * 1/dist^2) / sum(1/dist^2)
- Recalculate every 5 minutes from latest sensor readings
- Input: all available readings from UBA + sensor.community in Aalen bbox

### Connector Design
- Computation connector: AirQualityGridConnector
- Reads from air_quality_readings (latest per sensor)
- Produces grid cell features with interpolated values
- Domain: "air_quality" with feature_type="air_grid"
- Values: {pm25, pm10, no2, o3} per grid cell

### Frontend Display
- 2D: translucent color overlay (green -> yellow -> orange -> red -> purple)
- Pollutant toggle: PM2.5 / PM10 / NO2 / O3
- Sensor points as pulsing dots with live readings
- Click sensor -> time-series popup chart

### Claude's Discretion
- Grid cell count optimization (full 50m grid vs adaptive resolution)
- Rendering approach (canvas overlay, deck.gl heatmap, or GeoJSON fill)
- Time-series chart implementation in popup

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- UBAConnector and SensorCommunityConnector already store readings
- air_quality_readings hypertable with pm25, pm10, no2, o3
- AQILayer.tsx shows sensor points
- TimeSeriesChart component exists

### Integration Points
- Add AirQualityGridConnector to backend/app/connectors/
- Create AirQualityHeatmapLayer frontend component
- Add pollutant toggle to sidebar or layer controls

</code_context>

<specifics>
No specific requirements beyond AalenPulse spec.
</specifics>

<deferred>
## Deferred Ideas
- 3D fog layer for air quality
- Terrain correction for valley pollution trapping
- Traffic proximity correction for NO2
</deferred>
