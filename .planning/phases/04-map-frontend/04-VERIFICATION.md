---
phase: 04-map-frontend
verified: 2026-04-05T23:30:00Z
status: gaps_found
score: 5/7 success criteria verified
gaps:
  - truth: "App loads at port 4000 showing Aalen centered on a MapLibre GL JS map with OpenStreetMap/basemap.de tiles"
    status: partial
    reason: "PMTiles binary file frontend/public/tiles/aalen.pmtiles is missing. The map component is correctly wired to load 'pmtiles:///tiles/aalen.pmtiles', but the file does not exist on disk. The map will load with an empty/blank base layer. This was acknowledged in 04-02-SUMMARY as a known gap (Protomaps daily build URL returned 404 during execution)."
    artifacts:
      - path: "frontend/public/tiles/aalen.pmtiles"
        issue: "File does not exist — directory frontend/public/tiles/ does not exist at all"
    missing:
      - "Download the PMTiles file: npx pmtiles extract https://build.protomaps.com/{date}.pmtiles frontend/public/tiles/aalen.pmtiles --bbox=9.8,48.7,10.3,49.0"
      - "Alternatively download from https://protomaps.com/downloads/osm and extract the Aalen bounding box"
  - truth: "docker-compose frontend service reaches backend API correctly"
    status: failed
    reason: "docker-compose.yml sets NEXT_PUBLIC_API_URL=http://localhost:8000 for the frontend service. Inside a Docker container, 'localhost' refers to the container itself, not the host or the backend service. The correct value for container-to-container communication is http://backend:8000 (using the Docker Compose service name). This means the transit and air_quality layer fetches will silently fail when running via docker-compose."
    artifacts:
      - path: "docker-compose.yml"
        issue: "NEXT_PUBLIC_API_URL set to http://localhost:8000 instead of http://backend:8000 for frontend service"
    missing:
      - "Change NEXT_PUBLIC_API_URL in docker-compose.yml frontend service from http://localhost:8000 to http://backend:8000"
human_verification:
  - test: "Visual map rendering with PMTiles base layer"
    expected: "After providing aalen.pmtiles, map shows Aalen OSM street tiles in light theme with German street names at zoom 13"
    why_human: "Cannot verify visual tile rendering without running the app and without the PMTiles file present"
  - test: "Transit clustering behavior across zoom levels"
    expected: "At zoom 13 stops appear as cluster circles with count numbers; zoom in to 14+ causes clusters to dissolve to individual colored dots (blue=bus, red=train, green=tram)"
    why_human: "Zoom-based visual behavior requires browser interaction to verify"
  - test: "AQI heatmap rendering"
    expected: "AQI sensor locations render as a smooth heatmap overlay with colors transitioning green to red based on AQI values"
    why_human: "Heatmap visual rendering requires real API data and browser to verify"
  - test: "Feature popup click interaction"
    expected: "Clicking a transit stop dot shows popup with stop name, route type, freshness indicator; clicking AQI area shows PM2.5, PM10, NO2, AQI badge, freshness"
    why_human: "Click interaction on map features requires running app with backend data"
  - test: "Layer toggle removes/adds layers without page reload"
    expected: "Toggling OPNV switch OFF immediately removes transit dots/clusters; toggling ON restores them; same for Luftqualitat heatmap"
    why_human: "Requires running app to verify immediate visibility change without reload"
  - test: "Tablet responsive layout"
    expected: "At 768px width sidebar is hidden and floating Layers button appears at bottom-left; clicking button opens overlay drawer"
    why_human: "Responsive behavior requires browser at specific viewport width"
---

# Phase 4: Map Frontend Verification Report

**Phase Goal:** Citizens can open the app, see Aalen on a map, toggle transit and air quality layers, and know how fresh the data is
**Verified:** 2026-04-05T23:30:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | App loads at port 4000 showing Aalen centered on a MapLibre GL JS map with OSM tiles | PARTIAL | MapView.tsx: coordinates [10.0918, 48.8374], zoom 13, PMTiles URL wired — but aalen.pmtiles file is missing from disk |
| 2 | Transit layer renders stops and route polylines with clustering at city scale | VERIFIED (code) | TransitLayer.tsx: clusterMaxZoom=13, 3 layers (clusters, count labels, stop dots), route_type_color match expression |
| 3 | Air quality layer renders sensor locations color-coded by AQI health tier with visible legend | VERIFIED (code) | AQILayer.tsx: heatmap-weight driven by 'aqi' property, color ramp matches AQI_TIER_COLORS; AQILegend.tsx renders 5-tier strip |
| 4 | Each layer has a toggle switch; turning off removes it from the map without page reload | VERIFIED (code) | Layout visibility via 'visible'/'none' prop spread on each Layer component; Sidebar.tsx has two Switch toggles wired to layerVisibility state in page.tsx |
| 5 | Clicking or hovering a map feature opens a detail popup with readings and freshness timestamp | VERIFIED (code) | MapView.tsx: interactiveLayerIds=['transit-stops','aqi-points'], onClick handler sets popupInfo, Popup + FeaturePopup rendered; FreshnessIndicator embedded |
| 6 | Layout is responsive and usable on a 768px-wide tablet screen | VERIFIED (code) | Sidebar.tsx: lg:hidden floating button, overlay drawer with drawerOpen state; desktop aside uses hidden lg:flex |
| 7 | Docker-compose frontend reaches backend API | FAILED | docker-compose.yml NEXT_PUBLIC_API_URL=http://localhost:8000 — will not resolve to backend container from within frontend container |

**Score:** 5/7 success criteria verified (plus 2 human-needed)

Note: ROADMAP.md success criterion 2 mentions "vector tiles via Martin" but the implementation uses GeoJSON Source layers (not Martin tile server). This is an implementation deviation — transit/AQI data renders as client-side GeoJSON, not server-side vector tiles. The base map correctly uses PMTiles vector tiles. MAP-03 ("Vector tile rendering for performant display, not raw GeoJSON") is partially satisfied: the base map is vector tiles, but the data layers use raw GeoJSON from the API. For the current data volume (one town, limited sensors) this is functionally acceptable but diverges from the stated requirement.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/package.json` | All required dependencies | VERIFIED | maplibre-gl 5.22.0, react-map-gl 8.1.0, pmtiles 4.4.0, @protomaps/basemaps, date-fns all present |
| `frontend/next.config.ts` | output: standalone, no turbopack | VERIFIED | output: 'standalone' set; dev script is "next dev" (no --turbopack) |
| `frontend/app/globals.css` | maplibre-gl CSS import | VERIFIED | @import 'maplibre-gl/dist/maplibre-gl.css' at top of file |
| `frontend/types/geojson.ts` | LayerResponse, AQIFeatureProperties, TransitFeatureProperties | VERIFIED | All three interfaces exported with correct shape matching backend schema |
| `frontend/lib/map-styles.ts` | buildMapStyle, AQI_COLOR_RAMP, TRANSIT_COLORS | VERIFIED | All three exports present; AQI_TIER_COLORS also exported; namedFlavor('light') used |
| `frontend/hooks/useLayerData.ts` | 60-second polling hook | VERIFIED | useEffect with setInterval(load, 60_000), cancelled flag for cleanup, NEXT_PUBLIC_API_URL via fetchLayer |
| `frontend/hooks/useRelativeTime.ts` | 30s update interval for freshness | VERIFIED | setInterval(update, 30_000), formatDistanceToNow with de locale |
| `frontend/app/page.tsx` | 'use client', dynamic import ssr:false, useLayerData for both domains | VERIFIED | Both transit and air_quality useLayerData calls present; ssr:false on MapView dynamic import; all data props passed |
| `frontend/components/map/MapView.tsx` | PMTiles protocol, interactiveLayerIds, popup state | VERIFIED | addProtocol('pmtiles'), interactiveLayerIds=['transit-stops','aqi-points'], popupInfo useState, onClick handler |
| `frontend/components/map/TransitLayer.tsx` | 3 MapLibre layers, clustering, route-type colors | VERIFIED | clusterMaxZoom=13, cluster circles + count labels + stop dots; match expression for route_type_color |
| `frontend/components/map/AQILayer.tsx` | Heatmap + transparent click-target layer | VERIFIED | aqi-heatmap layer with heatmap-weight from 'aqi' property; aqi-points transparent circle layer for click targets |
| `frontend/components/map/FeaturePopup.tsx` | Domain-detected popup content, FreshnessIndicator | VERIFIED | isAQI detection via property presence; PM2.5/PM10/NO2/AQI badge for AQI; stop_name/route for transit; FreshnessIndicator embedded |
| `frontend/components/map/FreshnessIndicator.tsx` | Green/yellow/red dot, relative time, tooltip | VERIFIED | freshnessColor function with 5min/30min thresholds; useRelativeTime; base-ui Tooltip with render prop |
| `frontend/components/sidebar/Sidebar.tsx` | German labels, two toggles, legends, tablet drawer | VERIFIED | "Stadtdaten Aalen", "Ebenen", "OPNV (Bus & Bahn)", "Luftqualitat"; lg:hidden drawer logic |
| `frontend/components/sidebar/AQILegend.tsx` | 5-tier color strip from AQI_TIER_COLORS | VERIFIED | Colors imported from lib/map-styles.ts, not hardcoded; 5 tiers rendered |
| `frontend/components/sidebar/LayerToggle.tsx` | min-h-[44px] touch target, Switch + Label | VERIFIED | min-h-[44px] present; shadcn Switch and Label components used |
| `frontend/Dockerfile` | Multi-stage Node 22 Alpine, EXPOSE 4000 | VERIFIED | Two-stage build, EXPOSE 4000, CMD node server.js |
| `frontend/public/tiles/aalen.pmtiles` | PMTiles binary for Aalen | MISSING | Directory does not exist; map will show blank base layer at runtime |
| `docker-compose.yml` | Frontend service on port 4000 | PARTIAL | Service present on port 4000; NEXT_PUBLIC_API_URL incorrectly set to localhost:8000 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `frontend/app/page.tsx` | `frontend/components/map/MapView.tsx` | next/dynamic with ssr: false | WIRED | dynamic() with ssr: false confirmed at line 8-11 |
| `frontend/components/map/MapView.tsx` | pmtiles protocol | addProtocol('pmtiles') in useEffect | WIRED | maplibregl.addProtocol('pmtiles', protocol.tile) at line 48 |
| `frontend/components/sidebar/Sidebar.tsx` | `frontend/components/map/MapView.tsx` | layerVisibility state props | WIRED | layerVisibility flows from page.tsx useState to both Sidebar and MapView; toggles fire setLayerVisibility |
| `frontend/app/page.tsx` | `useLayerData` hook | useLayerData called for transit and air_quality | WIRED | const transit = useLayerData('transit'); const airQuality = useLayerData('air_quality') at lines 18-19 |
| `frontend/hooks/useLayerData.ts` | http://backend:8000/api/layers/{domain} | NEXT_PUBLIC_API_URL env var | PARTIAL | useLayerData calls fetchLayer which uses NEXT_PUBLIC_API_URL; but docker-compose sets this to localhost:8000 (wrong for container) |
| `frontend/components/map/MapView.tsx` | transit-stops + aqi-points layers | interactiveLayerIds prop | WIRED | interactiveLayerIds={['transit-stops', 'aqi-points']} at line 72 |
| `frontend/components/map/AQILayer.tsx` | aqi-heatmap layer | heatmap-weight driven by 'aqi' property | WIRED | 'heatmap-weight': ['interpolate', ['linear'], ['get', 'aqi'], 0, 0, 80, 1] at line 19 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `TransitLayer.tsx` | `data` prop (LayerResponse) | useLayerData('transit') in page.tsx → fetchLayer → GET /api/layers/transit | Yes — fetches from real API endpoint; 60s polling | FLOWING |
| `AQILayer.tsx` | `data` prop (LayerResponse) | useLayerData('air_quality') in page.tsx → fetchLayer → GET /api/layers/air_quality | Yes — fetches from real API endpoint; 60s polling | FLOWING |
| `FreshnessIndicator.tsx` | `lastFetched` prop (Date) | useLayerData returns lastFetched=new Date() on each successful fetch | Yes — set on every successful API response | FLOWING |
| `FeaturePopup.tsx` | `feature.properties` | MapLibre click event e.features[0] | Yes — directly from MapLibre layer click with real GeoJSON feature data | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| TypeScript types exported from geojson.ts | grep exports | LayerResponse, AQIFeatureProperties, TransitFeatureProperties all present | PASS |
| NEXT_PUBLIC_API_URL env var used (not hardcoded) | grep pattern in lib/api.ts | process.env.NEXT_PUBLIC_API_URL found | PASS |
| No turbopack in dev script | grep package.json dev script | "dev": "next dev" (no --turbopack) | PASS |
| Docker standalone output configured | grep next.config.ts | output: 'standalone' confirmed | PASS |
| PMTiles binary present | ls frontend/public/tiles/ | Directory does not exist | FAIL |
| docker-compose API URL correct for container | grep docker-compose.yml | localhost:8000 instead of backend:8000 | FAIL |

Step 7b: Full build check skipped — requires npm run build execution which is not run here. Build was confirmed clean in SUMMARY (0 TypeScript errors).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| MAP-01 | 04-01, 04-02 | Interactive map centered on configured town with pan/zoom | VERIFIED | MapView.tsx: longitude 10.0918, latitude 48.8374, zoom 13; Map component supports pan/zoom natively |
| MAP-02 | 04-02, 04-03 | Toggleable data layers per domain | VERIFIED | layerVisibility state in page.tsx; Sidebar switch toggles; layout visibility in TransitLayer and AQILayer |
| MAP-03 | 04-03 | Vector tile rendering for performant display (not raw GeoJSON) | PARTIAL | Base map uses PMTiles vector tiles correctly; but transit and AQI data layers use GeoJSON Source (not Martin/vector tiles). Per roadmap success criterion 2, Martin was intended for transit tiles. Data layers send raw GeoJSON from API. |
| MAP-04 | 04-02 | Layer legend with color coding per data type | VERIFIED | AQILegend.tsx: 5-tier color strip; TransitLegend.tsx: bus/train/tram swatches; colors imported from lib/map-styles.ts |
| MAP-05 | 04-03 | Zoom-appropriate detail levels (cluster at city scale, detail at street scale) | VERIFIED (code) | TransitLayer.tsx: clusterMaxZoom=13, filter ['has','point_count'] for clusters vs individual stops |
| MAP-07 | 04-03 | Click/hover on map features shows detail popup with current readings | VERIFIED (code) | MapView.tsx: interactiveLayerIds, onClick handler, Popup with FeaturePopup; FreshnessIndicator shows freshness |
| MAP-08 | 04-01, 04-02 | Base map with OpenStreetMap / basemap.de tiles | PARTIAL (runtime) | lib/map-styles.ts: buildMapStyle uses Protomaps/OSM tiles via namedFlavor('light'); but aalen.pmtiles file is missing so tiles won't render at runtime |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `docker-compose.yml` | 38 | NEXT_PUBLIC_API_URL=http://localhost:8000 | BLOCKER | API calls from frontend container will fail — localhost inside container is the container itself, not the backend service. Layer data will silently fail to load when running via docker-compose. |
| `frontend/public/tiles/` | N/A | Missing PMTiles binary | BLOCKER | Base map will render empty (no OSM tiles visible). This is a runtime data file, not a code issue, but prevents the primary visual requirement from being met. |

No TODO/FIXME/placeholder comments found in any source files. No empty return null stubs (TransitLayer/AQILayer return null only when data is null, which is correct guarding behavior). All color constants imported from lib/map-styles.ts, not hardcoded.

Note on MAP-03 / GeoJSON vs vector tiles: The plan and roadmap mention Martin tile server for transit data, but the implementation uses react-map-gl GeoJSON Source. This is a pragmatic deviation — GeoJSON sources work correctly in MapLibre for the current data volume. The code is not a stub; it is a deliberate implementation choice. However, it diverges from MAP-03's explicit "not raw GeoJSON" requirement and the roadmap success criterion mentioning Martin.

### Human Verification Required

### 1. Base Map Visual Rendering

**Test:** After providing aalen.pmtiles (see gap above), run `cd frontend && npm run dev`, open http://localhost:4000
**Expected:** Aalen appears on a light-theme OSM map with German street names; pan and zoom work smoothly
**Why human:** Visual tile rendering and interactivity cannot be verified without running the app

### 2. Transit Clustering at Zoom Levels

**Test:** With transit layer visible, check zoom 13 (initial) vs zoom 14+
**Expected:** Zoom 13: cluster circles with numbers; zoom 14+: individual colored dots (blue=bus, red=train, green=tram)
**Why human:** Zoom-based clustering behavior is visual and requires browser interaction

### 3. AQI Heatmap with Real Data

**Test:** With backend running and real AQI data in the database, check air quality layer
**Expected:** Smooth heatmap overlay with green-to-red color gradient based on actual AQI values from API
**Why human:** Heatmap rendering depends on actual API data and is visual

### 4. Feature Click Popups

**Test:** Click a visible transit stop dot and an AQI sensor area
**Expected:** Transit popup shows stop_name, route_type_color label, freshness dot + relative time; AQI popup shows PM2.5, PM10, NO2 values, colored AQI tier badge, freshness indicator
**Why human:** Requires running app with real backend data; popup content conditional on feature properties from API

### 5. Layer Toggle Immediacy

**Test:** Toggle OPNV switch OFF while looking at visible transit stops
**Expected:** Stops and clusters disappear immediately (no page flash, no reload animation)
**Why human:** "Immediate" toggle behavior is perceptible in browser only; code uses layout.visibility which avoids re-render flash but must be confirmed visually

### 6. FreshnessIndicator Color Progression

**Test:** Observe the freshness indicator dot color immediately after a successful fetch, then wait 5+ minutes
**Expected:** Green dot immediately after fetch; yellow after 5 minutes; red after 30 minutes
**Why human:** Time-dependent color state requires waiting or mocking time; visual output

### Gaps Summary

Two gaps block full goal achievement:

**Gap 1 — Missing PMTiles binary (runtime blocker):** The file `frontend/public/tiles/aalen.pmtiles` does not exist. The MapView is correctly wired to load it via `pmtiles:///tiles/aalen.pmtiles`, but without the file the base map will show blank tiles. The map component, PMTiles protocol registration, and Protomaps style builder are all correctly implemented. Resolution: download the Aalen bounding box extract from Protomaps daily builds.

**Gap 2 — Wrong API URL in docker-compose (deployment blocker):** `NEXT_PUBLIC_API_URL=http://localhost:8000` in the frontend service will resolve to the frontend container itself at runtime, not the backend service. API calls for layer data will fail silently (the error state in useLayerData will activate, showing red freshness dots, but no data). Resolution: change to `http://backend:8000` (Docker Compose service name). Note: local dev with `npm run dev` is unaffected since `frontend/.env.local` sets `NEXT_PUBLIC_API_URL=http://localhost:8000`, which is correct for non-containerized dev.

**MAP-03 partial — GeoJSON vs vector tiles:** The data layers (transit, AQI) use react-map-gl GeoJSON Source rather than Martin tile server as stated in the roadmap success criteria. The base map correctly uses PMTiles vector tiles. This is not a blocker for current functionality but is a deviation from the explicit requirement and the roadmap's stated approach.

Six human verification items remain that cannot be confirmed programmatically. These require running the app with the PMTiles file present and backend connected.

---

_Verified: 2026-04-05T23:30:00Z_
_Verifier: Claude (gsd-verifier)_
