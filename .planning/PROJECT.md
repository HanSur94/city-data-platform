# City Data Platform

## What This Is

An open-source data platform that aggregates and visualizes all freely available public data for small German towns — traffic, water, electricity, wastewater, air quality, and public transport — into a unified map + dashboard interface. Think open-source Palantir for municipalities. Generic enough to work for any town, starting with Aalen as the reference city.

## Core Value

Citizens and city officials can see all publicly available city data in one place, on a map, updated live — no technical expertise required.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Interactive map showing the city with data layers (traffic, utilities, environment, transport)
- [ ] Dashboard with KPIs, charts, and summary tiles alongside the map
- [ ] Traffic data ingestion and visualization (road flow, congestion)
- [ ] Water supply data ingestion and visualization
- [ ] Electricity grid data ingestion and visualization
- [ ] Wastewater (Abwasser) data ingestion and visualization
- [ ] Air quality data ingestion and visualization
- [ ] Public transport data ingestion and visualization (bus, train / Öffis)
- [ ] Generic architecture — configurable per town, not hardcoded to Aalen
- [ ] Polished enough for a city official to use without technical knowledge
- [ ] Historical data and trends (not just live snapshots)

### Out of Scope

- Mobile native app — web-first, responsive design instead
- User accounts / authentication — public data, public access
- Data collection / IoT sensors — consume existing open data APIs only
- Predictive analytics / AI — show what IS, not what MIGHT BE (for v1)
- Multi-language support — German first, internationalize later

## Context

- Builds on experience from a traffic tracker project (similar concept, narrower scope)
- **Aalen is a federally funded Smart City model project** (#AAHDHGemeinsamDigital, 2nd cohort) with €17.5M shared funding (with Heidenheim), running through December 2027
- Aalen already operates a live dashboard at aalen-dashboard.de with LoRaWAN IoT sensors (traffic counting, river level, soil moisture, parking, air quality)
- Partners: SmartMakers GmbH, Conclurer GmbH, Fraunhofer IAO (KTS advisor), Hochschule Aalen (Prof. Dr. Anna Nagl)
- Aalen's Smart City roadmap explicitly calls for a nationwide LoRaWAN network, an open-source municipal data platform, a digital twin, and an Open Data portal
- 50+ free data sources available: DWD/Bright Sky (weather), UBA (air quality station IN Aalen), SMARD (energy), NVBW (3,688 transit routes), BASt (traffic counts), MobiData BW, Wegweiser Kommune (700+ indicators, CC0), LGL (3D building models), PEGELONLINE (water levels), and many more
- FIWARE is the EU/German standard for smart city data (18+ German cities), with NGSI-LD as the API standard
- Key German standards: DIN SPEC 91357, NGSI-LD, DCAT-AP.de, Smart Data Models
- Neighboring OK Labs: Stuttgart (created Sensor.Community/Luftdaten.info), Ulm (Verschwörhaus)
- daten.bw (BW open data portal, CKAN-based) launched July 2023
- Target audience ranges from curious citizens to city officials — UI must work for both
- Open source from day one

## Constraints

- **Data sources**: Only freely available / open data — no paid APIs or restricted feeds
- **Deployment**: Must run on modest hardware (self-hostable, not cloud-dependent)
- **Scope**: Generic architecture from the start — no Aalen-specific hardcoding
- **Standards**: NGSI-LD compatible API layer, Smart Data Models schemas, DCAT-AP.de metadata
- **Licensing**: Datenlizenz Deutschland (DL-DE-BY-2.0) attribution required for most German open data

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Map + Dashboard split view | Both spatial and analytical perspectives needed for city data | — Pending |
| Generic multi-town architecture | User wants any German town to work, not just Aalen | — Pending |
| Open data only | Keeps it open-source friendly, no licensing issues | — Pending |
| Web-first, no native app | Broadest reach, simplest deployment | — Pending |
| Hybrid architecture | Own lightweight backend (FastAPI + TimescaleDB) with NGSI-LD compatible API — simpler than full FIWARE, but interoperable with EU standard ecosystem | — Pending |
| Smart Data Models schemas | Data follows standardized NGSI-LD models so FIWARE systems can connect | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-05 after initialization*
