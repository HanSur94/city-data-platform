# API Coverage — quick 261116-cx5 (repair of existing public-data connectors)

> Full coverage by default. Opt-outs are explicit, reasoned decisions. This task re-points existing integrations at the endpoints the sources serve today; capability names are prefixed with the service.

| capability | decision | reason |
|---|---|---|
| overpass.interpreter-query | INTEGRATE | |
| overpass.public-mirrors | INTEGRATE | |
| overpass.status-endpoint | OPT-OUT | not needed — fall-through on 406/429/5xx/timeout handles overload without an extra pre-check request |
| sensor-community.filter-area | INTEGRATE | |
| sensor-community.filter-box-type-country | OPT-OUT | not needed — the radius around the town centre is the existing design and returns the town's sensors |
| lubw-wfs.getfeature-naturschutzgebiet | INTEGRATE | |
| lubw-wfs.getfeature-wasserschutzgebiet | INTEGRATE | |
| lubw-wfs.getcapabilities | OPT-OUT | not needed — qualified type names are fixed in code and were verified against GetCapabilities at planning time |
| lubw-wfs.other-services | OPT-OUT | explicitly out of scope — repair task restores the two existing layers only |
| hvz-lhp.gauge-reading | INTEGRATE | |
| hvz-lhp.further-kocher-gauges | OPT-OUT | not needed yet — the layer shows the Kocher at Huettlingen; Unterkochen (00049) and Stefansweiler Muehle (00143) are possible follow-ups |
| bast.annual-results-csv-latest-year | INTEGRATE | |
| bast.annual-results-csv-all-years | OPT-OUT | not needed — the map shows the newest published year only |
| bast.hourly-series | OPT-OUT | not needed yet — the moved source publishes annual results; an hourly series would need a separate source decision |
| ocpdb.locations-radius | INTEGRATE | |
| ocpdb.pagination | INTEGRATE | |
| ocpdb.evse-status | INTEGRATE | |
| ocpdb.locations-bbox-filter | OPT-OUT | not needed — radius query plus the existing client-side town-bbox filter already selects the town |
| ocpdb.location-detail | OPT-OUT | not needed — list items already carry EVSEs and connectors |
| ocpdb.tariffs-opening-times-facilities | OPT-OUT | not needed yet — the popup has no fields for them and frontend changes are out of scope |
| stadtwerke-aalen.occupancy-table | INTEGRATE | |
| stadtwerke-aalen.garage-capacity-page | OPT-OUT | not needed yet — not a probed endpoint in this task; capacities come from OSM where available, rest listed as open |
| mobidata-bw.traffic-count-csv | OPT-OUT | source returns 404 and no machine-readable replacement exists; connector disabled with reason |
| mastr.bulk-download | OPT-OUT | explicitly out of scope — multi-gigabyte download needs a user decision |
