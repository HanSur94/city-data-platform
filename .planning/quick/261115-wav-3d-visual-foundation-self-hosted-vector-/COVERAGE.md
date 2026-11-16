# API Coverage — AWS Terrain Tiles (Mapzen) + Protomaps basemaps-assets

> Full coverage by default. Opt-outs are explicit, reasoned decisions.
> Detector note: the scan fired on the phrase "no Next.js-specific API ... wiring" (false positive). The task does consume two external static tile/asset hosts, so the matrix below records their capability surface. LGL WMS and EOX WMTS usage is unchanged by this task.

| capability | decision | reason |
|---|---|---|
| terrain-tiles terrarium PNG XYZ ({z}/{x}/{y}.png, z0-15) | INTEGRATE | |
| terrain-tiles normal PNG (surface normals) | OPT-OUT | not needed — MapLibre raster-dem decodes elevation encodings only (terrarium/mapbox/custom) |
| terrain-tiles geotiff | OPT-OUT | not needed — not decodable by MapLibre in the browser; no server-side elevation processing in this slice |
| terrain-tiles skadi (HGT) | OPT-OUT | not needed — same reason as geotiff |
| basemaps-assets fonts ({fontstack}/{range}.pbf) | INTEGRATE | |
| basemaps-assets sprites v4 dark | INTEGRATE | |
| basemaps-assets sprites v4 light | INTEGRATE | |
| basemaps-assets sprites v4 white/grayscale/black | OPT-OUT | not needed yet — only the dark and light flavors are offered as base maps |
| self-hosting of fonts/sprites/DEM | OPT-OUT | explicitly out of scope for this slice — recorded as a follow-up comment in frontend/lib/map-styles.ts |
