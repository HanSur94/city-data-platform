---
phase: quick-261116-cx5
plan: 01
subsystem: backend-connectors
tags: [overpass, sensor-community, lubw-wfs, lhp, bast, ocpdb, parking, police, layer-registry]
status: complete
requires: []
provides:
  - shared Overpass helper (User-Agent, mirror fall-through, config overpass_urls)
  - repaired connectors for Sensor.Community, LUBW WFS, LHP, BASt, EV charging, parking, police cleanup
  - layer registry links that match what each layer shows
affects: [backend/app/connectors, backend/app/routers/metadata.py, towns/aalen.yaml]
tech-stack:
  added: []
  patterns:
    - "one helper per external API family (overpass_client) instead of per-connector inline httpx"
    - "fetch failures propagate to scheduler._run_connector; staleness advances only after a fetch that returned"
key-files:
  created:
    - backend/app/connectors/overpass_client.py
    - backend/tests/connectors/test_overpass_client.py
    - backend/tests/connectors/test_police.py
  modified:
    - backend/app/connectors/overpass_community.py
    - backend/app/connectors/overpass_roadworks.py
    - backend/app/connectors/osm_buildings.py
    - backend/app/connectors/cycling.py
    - backend/app/connectors/sensor_community.py
    - backend/app/connectors/lubw_wfs.py
    - backend/app/connectors/lhp.py
    - backend/app/connectors/ev_charging.py
    - backend/app/schemas/geojson.py
    - backend/app/connectors/bast.py
    - backend/app/connectors/parking.py
    - backend/app/models/parking.py
    - backend/app/connectors/police.py
    - backend/app/routers/metadata.py
    - towns/aalen.yaml
    - backend/tests/connectors/test_sensor_community.py
    - backend/tests/connectors/test_lubw_wfs.py
    - backend/tests/connectors/test_lhp.py
    - backend/tests/connectors/test_ev_charging.py
    - backend/tests/connectors/test_bast.py
    - backend/tests/connectors/test_parking.py
    - backend/tests/test_api_metadata.py
decisions:
  - "BASt is features-only: annual DTV stored as feature properties, no traffic_readings rows, daily poll"
  - "energy layer links MastrConnector only (SMARD feature is not drawn); reads never_fetched until MaStR is fixed"
  - "Parking garages without a verified position stay at the town centre and carry location_approximate; no coordinates invented"
  - "Overpass default mirror list kept at three entries, unverified (no mirror answered with JSON during the single probe)"
metrics:
  completed: 2026-11-16
  tasks: 3
  commits: 3
  plan_head_before: 4d36bd155e030b9fc687ba550483e4d4a8b2fbf6
  plan_head_after: 15e613b1da821400eb607570a474bf10df0cdebc
actuals:
  tokens: 33000
  tasks: 3
  commits: 3
---

# Quick 261116-cx5: Fix broken data sources Summary

Nine connectors now request and parse the formats their public sources serve today, with offline tests cut from real responses; one shared Overpass helper identifies itself and falls through a mirror list.

## Commits

| Task | Commit | Content |
|------|--------|---------|
| 1 (tracer) | c60d675 | `overpass_client.overpass_query` + wiring of community, roadworks, buildings, cycling; tracer test through `OverpassCommunityConnector.run()` |
| 2 | 379c6d6 | Sensor.Community path URL, LUBW WFS GeoJSON + unique ids, Kocher gauge BW_00142, EV charging on MobiData OCPDB without false success |
| 3 | 15e613b | BASt annual CSV with year fallback, parking table parser, police cleanup SQL, MobiData disabled, registry links |

## Verification (executed)

- Full backend suite (`-m "not slow"`): before 350 passed / 10 failed / 1 skipped / 4 deselected / 6 errors; after **414 passed** / 10 failed / 0 skipped / 6 deselected / 6 errors. The sorted FAILED/ERROR id lists are **identical** (diff empty). 64 new offline tests; the skip disappeared and deselected rose by 2 because the two live Sensor.Community tests are now `@pytest.mark.slow`.
- Scope: `git diff 4d36bd1` is empty for `frontend/`, `backend/pyproject.toml`, `backend/uv.lock`, `mastr.py`, `mobidata_bw.py`, `test_mobidata_bw.py`. No dependency changes.
- Grep gates all pass: helper used by 4/4 Overpass connectors, no single-endpoint constant left, qualified LUBW type names present, old gauge number / old EV host / old parking class / old interval cast / old BASt path segment gone, `make_interval` and `renderTcDataExportCSV` present.
- `towns/aalen.yaml` checked with `yaml.safe_load`: LhpConnector `BW_00142` / 48.8804 / 10.0972, BastConnector 86400 s, MobiDataBWConnector `enabled: false`, MastrConnector still enabled. Registry check printed "config ok".
- Police SQL live check (read-only, rolled back): `SELECT count(*) ... NOW() - make_interval(days => :days)` with `days=7` ran on the real asyncpg driver and returned 0 rows. No PostgresSyntaxError.
- Git: exactly three new commits on `fix/broken-data-sources`, nothing pushed; unrelated untracked `.planning/` and `docs/` files untouched.

## Overpass mirror probe (single request per mirror, as the plan allows)

| Mirror | Result |
|--------|--------|
| https://overpass-api.de/api/interpreter | HTTP 502, "at capacity ... request queue is full" (text, not JSON) |
| https://overpass.private.coffee/api/interpreter | no answer within 40 s (curl code 000) |
| https://overpass.kumi.systems/api/interpreter | no answer within 40 s (curl code 000) |

Overpass mirror verification: none answered with JSON at execution time. `DEFAULT_OVERPASS_URLS` keeps all three in the order above, **unverified** (PENDING orchestrator). The probe doubled as the garage-position lookup; since no JSON came back, no OSM coordinates or capacities were available for parking.

## Staleness audit

Connectors touched here that caught a fetch failure and still advanced `sources.last_successful_fetch`: **EvChargingConnector only**. Fixed (try/except around fetch removed, failure propagates; tested). Not affected: OverpassCommunity, Cycling, SensorCommunity, LubwWfs, Lhp, Bast, Police (no catch around fetch), OverpassRoadworks (staleness on an empty result happens after a successful fetch), OsmBuildings and Parking (catch then return without staleness), MobiDataBW (disabled).

## Parking: positions and capacity

- Garages with a position from the static table: P2 Reichsstädter Markt (48.8358 / 10.0920), P5 Spitalstraße (48.8350 / 10.0960). Both existed before; unchanged.
- **location_approximate** (placed at the town centre 48.8360 / 10.0935, warning logged): P1 Rathaus, P3 Spritzenhausplatz, P6 Bahnhof, P1 Kubus. No coordinate was invented. These four overlap on the map until verified positions are added.
- No capacity is known for any garage (the page no longer publishes one and the OSM lookup returned nothing). `total_spots` and `occupancy_pct` are therefore empty for all six; the static table supports an optional `capacity` per entry (tested with a patched table).

## Decisions

- **BASt features-only.** The file is annual averages (DTV, vehicles per day). `vehicle_count_total` = round(DTV / 24) is stored as a feature property together with station, road, lanes, SV share, data year and remark; `traffic_readings` is not written (no unique key, 2-year retention, hourly re-runs would only duplicate rows). Poll interval is now 86400 s. Station 8468 Westumgehung Aalen has no DTV in 2024 ("Datenprobleme in 2024"): it is stored without counts, so the map shows it without a level.
- **Energy layer** links `MastrConnector` only: the frontend EnergyLayer shows no SMARD feature (the one SMARD point lies at the centre of Germany). It will read `never_fetched` until MaStR works.
- **roadNoise** has no connector (external WMS). **lubwEnv** now lists `LubwWfsConnector`. `mobiData` entry removed; MobiDataBWConnector disabled with the reason in `towns/aalen.yaml`.
- LUBW zones keep the `naturschutz:` / `wasserschutz:` source-id prefix the map filter needs; id is `GmlID` (else `OBJECTID`); features without any id are skipped with a warning instead of sharing a fallback id.

## Deviations from Plan

**1. [Rule 3 - Blocking] Legacy `_parse_bast_csv` and its fixed filter box kept in bast.py**
- **Found during:** Task 3 verification (collection error in `tests/connectors/test_mobidata_bw.py`).
- **Issue:** the plan said to delete the module-level fixed bbox constants. `mobidata_bw.py` (out of scope, must stay unchanged) imports `_parse_bast_csv`, which uses them; deleting both broke the import of `MobiDataBWConnector` and therefore the connector registry.
- **Fix:** kept `_parse_bast_csv` as a clearly labelled legacy helper with private `_LEGACY_BBOX_*` constants (behaviour identical to before). `BastConnector` itself no longer uses them: it derives the filter box from the town bbox plus `buffer_deg`.
- **Files modified:** backend/app/connectors/bast.py
- **Commit:** 15e613b

**2. [Rule 1 - Test correction] Buildings connector test asserts the tight centre box**
- `OsmBuildingsConnector` has always queried a tight box around the town centre (unchanged behaviour), so the shared "query contains the town bbox" assertion checks the derived box for that one connector. Test only, no code change.
- **Commit:** c60d675

No auth gates. No package installs.

## PENDING - orchestrator (needs the rebuilt backend image; not claimed here)

1. `sources.last_successful_fetch` appears for SensorCommunity, OsmBuildings, OverpassCommunity, Cycling, OverpassRoadworks, Parking, Bast, Lhp, LubwWfs (Overpass ones only once a mirror answers); EvCharging advances only on real successes.
2. `features` rows appear: community (schools/healthcare/parks/waste), cycling ways, roadworks (may legitimately be zero), buildings, parking (6 garages), traffic `bast:*` (3 stations: 8405, 8468, 8827), water `lhp:BW_00142` plus water_readings, `naturschutz:*` (4) and `wasserschutz:*` (about 20), air_quality Sensor.Community sensors with readings, `ev-charging-*` (about 83 inside the bbox).
3. `GET /api/metadata/layers?town=aalen`: ok for kocher, traffic, parking, roadworks, cycling, schools, healthcare, parks, waste, lubwEnv, evCharging; airQuality ok with Sensor.Community contributing; roadNoise static; energy never_fetched; no `mobiData` key.
4. **Overpass mirror list:** no mirror could be confirmed; re-probe once from the orchestrator environment and trim `DEFAULT_OVERPASS_URLS` (or set `overpass_urls` in `towns/aalen.yaml`).
5. Police cleanup: the SQL was verified read-only against asyncpg (item done); a check of the backend log after the next cleanup run is still advisable.

## Open items (out of scope, untouched)

- MastrConnector bulk-download parameter (needs a user decision).
- WegweiserKommune / StatistikBW partial parse failures; GTFS-RT feed id mismatch.
- Frontend: `lubwEnv` has no `metadataKey` yet, so its status is reported by the API but not shown in the sidebar; Schutzgebiete are only drawn while the water layer is on; EnergyLayer draws HeatDemand features; ParkingLayer colours by `occupancy_pct`, which is empty for all garages until capacities are known.
- Parking: verified coordinates (and capacities) for P1 Rathaus, P3 Spritzenhausplatz, P6 Bahnhof, P1 Kubus.
- Broken-windows ledger (`.planning/WINDOWS.md`) was not appended (CLI not available in this shell); the open parking positions above are the entries to record.

## Known Stubs

None. `location_approximate` garages are an intentional, flagged fallback (listed above), not a stub that blocks the plan goal.

## Threat Flags

None. No new endpoints or trust boundaries beyond the plan's threat register.

## Self-Check: PASSED

- Created files exist: overpass_client.py, test_overpass_client.py, test_police.py.
- Commits c60d675, 379c6d6, 15e613b are ancestors of HEAD (`git rev-list --count 4d36bd1..HEAD` = 3).
- Failed/error id lists before and after are identical.

## Orchestrator live verification (2026-11-16)

Backend image rebuilt twice (after the three task commits, and after the orchestrator's commit 79c8766).

Result: 26 of 29 `sources` rows have a `last_successful_fetch` (16 before this task).

| Connector | Result on the live stack |
|---|---|
| EvChargingConnector | fetched, 83 `ev_charging` features |
| LubwWfsConnector | fetched, 24 protected-area polygons (20 Wasserschutz, 4 Naturschutz) |
| OverpassRoadworksConnector | fetched, 15 roadworks |
| ParkingConnector | fetched, 6 garages (4 at the approximate town-centre position, none with capacity) |
| BastConnector | fetched, 3 stations |
| LhpConnector | fetched (gauge 00142) |
| SensorCommunityConnector | fetched, 92 entries from the API; 26 sensor features stored |
| CyclingInfraConnector | fetched after retry rounds, 1,405 features |
| OsmBuildingsConnector | fetched after retry rounds, 7,323 features |
| OverpassCommunityConnector | NOT fetched: overpass-api.de answered HTTP 502 in every round, including one extra manual run; the two fallback mirrors never sent data |
| MastrConnector | not fetched, out of scope (parameter fix would start a multi-GB download) |
| MobiDataBWConnector | disabled in towns/aalen.yaml; its old `sources` row remains and still reads never-fetched |

Added by the orchestrator (commit 79c8766) after the first rebuild showed HTTP 429/504 for three of four simultaneous Overpass requests: one Overpass request at a time per process, up to 3 rounds over the mirror list 60 s apart (a rejected 4xx query is not retried), and a 60 s limit for fallback mirrors. Five new tests; backend suite 419 passed, 10 failed, 6 errors (same failing ids).

Open after this task:
- Community places (schools, healthcare, parks, recycling) stay empty until the public Overpass server answers. The connector polls daily, so a failed run is not retried until the next day or the next restart. A shorter retry for connectors that have never succeeded would close this.
- `register_sources` never marks rows of disabled connectors as disabled, so MobiDataBW still appears in the admin health list.
- Parking: four garages without a verified position, no capacities, so no occupancy colouring.
- The two fallback Overpass mirrors did not answer from this network in any probe (planner, executor, orchestrator).
