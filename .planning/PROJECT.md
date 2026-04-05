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
- German open data ecosystem: many cities publish data via CKAN portals, Open Data platforms, or standardized APIs
- Aalen (pop. ~67k, Baden-Württemberg) serves as the reference/test city
- Target audience ranges from curious citizens to city officials — UI must work for both
- Open source from day one

## Constraints

- **Data sources**: Only freely available / open data — no paid APIs or restricted feeds
- **Deployment**: Must run on modest hardware (self-hostable, not cloud-dependent)
- **Scope**: Generic architecture from the start — no Aalen-specific hardcoding
- **Stack**: Best-fit for the domain (research will determine)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Map + Dashboard split view | Both spatial and analytical perspectives needed for city data | — Pending |
| Generic multi-town architecture | User wants any German town to work, not just Aalen | — Pending |
| Open data only | Keeps it open-source friendly, no licensing issues | — Pending |
| Web-first, no native app | Broadest reach, simplest deployment | — Pending |

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
