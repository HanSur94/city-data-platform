# Phase 16: Live Solar Production & EV Charging Status - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Add computed live solar production per building (MaStR capacity x irradiance) and real-time EV charger availability from MobiData BW OCPDB API.

</domain>

<decisions>
## Implementation Decisions

### Solar Production
- Computation: installed_kW (from MaStR features) x current_irradiance_factor (from Bright Sky weather)
- Run every 15 minutes
- Store in energy_readings per building feature
- 3D view: buildings with solar glow proportional to output
- Click popup: "Potential: X kW | Installed: Y kW | Current: Z kW"

### EV Charging
- MobiData BW OCPDB API for real-time charger status
- AVAILABLE / OCCUPIED / INOPERATIVE / OUT_OF_ORDER / UNKNOWN
- Map pins: green=available, red=occupied, gray=offline
- Icon size proportional to power (11kW AC small, 150kW DC large)
- Replace existing static BNetzA Ladesaeulen data with live OCPDB data

### Claude's Discretion
- OCPDB API endpoint details and auth requirements
- Solar irradiance factor calculation from weather data
- Building glow implementation approach

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- MastrConnector already loads solar installations with capacity
- WeatherConnector provides irradiance data via Bright Sky
- LadesaeulenConnector has static charger locations (to be replaced/enhanced)
- EnergyLayer.tsx shows MaStR installations
- energy_readings hypertable

### Integration Points
- Add SolarProductionConnector to backend/app/connectors/
- Add EvChargingConnector (or enhance LadesaeulenConnector) 
- Extend EnergyLayer or create SolarGlowLayer
- Create EvChargingLayer with live status pins

</code_context>

<specifics>
No additional specifics beyond AalenPulse requirements.
</specifics>

<deferred>
## Deferred Ideas
- Per-building energy profile popup combining heat demand + solar + Fernwaerme
- Solar production forecast based on weather forecast
</deferred>
