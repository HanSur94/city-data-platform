# Phase 4: Map Frontend - Research

**Researched:** 2026-04-05
**Domain:** Next.js 16 + react-map-gl 8 + MapLibre GL JS 5 + PMTiles + shadcn/ui
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Left sidebar panel for layer toggles — collapsible on mobile, standard map UI pattern
- Legend displayed inside the sidebar, below toggles — always visible when sidebar open
- Base map: OpenStreetMap via Protomaps PMTiles — self-hostable, no API key needed
- Light theme — better readability for officials, standard for map apps
- Air quality: **Heatmap overlay** — interpolated color field across the city (like weather radar), health-tier colors (green/yellow/orange/red/purple)
- Transit stops: Small dots with clustering — cluster at zoom <14, individual stops at street level
- Route polylines: Colored lines by route type — bus=blue, train=red, tram=green
- Popup content: Compact card — value + unit + freshness timestamp, 200px max width
- Next.js with App Router + TypeScript — `create-next-app` standard setup
- react-map-gl + MapLibre GL JS for map integration
- State management: React useState + URL params — simple enough for map state
- Styling: Tailwind CSS + shadcn/ui as per stack research
- Port 4000 (not 3000 — Grafana conflict on target system)

### Claude's Discretion
- Component file structure within the Next.js app
- Exact PMTiles base map URL/file
- Clustering algorithm parameters
- Heatmap interpolation radius and intensity settings
- Responsive breakpoints for tablet layout

### Deferred Ideas (OUT OF SCOPE)
- 3D building extrusion (Phase 9)
- Time slider for historical data (Phase 5)
- Shareable permalink URLs (Phase 5)
- deck.gl overlays for high-density data (future optimization)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MAP-01 | Interactive map centered on configured town with pan/zoom | MapLibre GL JS 5 via react-map-gl 8 `initialViewState` prop; Aalen coords `[10.0918, 48.8374]` |
| MAP-02 | Toggleable data layers per domain (transport, air) | React useState controls MapLibre layer visibility; `setLayoutProperty('layer-id', 'visibility', 'none\|visible')` pattern |
| MAP-03 | Vector tile rendering for performant display (not raw GeoJSON) | PMTiles provides OSM vector tiles for base map; GeoJSON layers from API are acceptable at city scale (few hundred features) |
| MAP-04 | Layer legend with color coding and icons per data type | AQI tier colors from API `aqi_color` field; transit route type colors from `properties.route_type` |
| MAP-05 | Zoom-appropriate detail levels (cluster at city scale, detail at street scale) | MapLibre GeoJSON source `cluster: true` with `clusterMaxZoom: 13`; dissolves at zoom ≥ 14 |
| MAP-07 | Click/hover on map features shows detail popup with current readings | react-map-gl `<Popup>` component + `interactiveLayerIds` + `onClick` on `<Map>` |
| MAP-08 | Base map with OpenStreetMap / basemap.de tiles | Protomaps PMTiles with `pmtiles://` protocol and `@protomaps/basemaps` style layers |
</phase_requirements>

---

## Summary

Phase 4 builds the entire frontend from scratch: a greenfield Next.js 16 App Router project in `/frontend`. The stack is locked by prior decisions — react-map-gl 8 + MapLibre GL JS 5 for the map, Protomaps PMTiles for the OSM base map, Tailwind CSS 4 + shadcn/ui for UI components. The FastAPI backend at port 8000 already serves the GeoJSON layer endpoints consumed in this phase. The docker-compose.yml needs a `frontend` service added.

The two primary map features — transit clustering and AQI heatmap — each require distinct MapLibre layer types. Clustering uses a GeoJSON source with `cluster: true` and three linked layers (cluster circles, count labels, individual dots). The heatmap uses MapLibre's built-in `heatmap` layer type driven by the AQI numeric value in feature properties, not individual point markers. Both are rendered via react-map-gl's `<Source>` and `<Layer>` components.

The biggest technical risk is the Turbopack/MapLibre web worker conflict in Next.js 16 dev mode — this is a known open issue that requires disabling Turbopack during development. Production builds are unaffected. The map component must be wrapped with `dynamic(..., { ssr: false })` to avoid SSR hydration errors since MapLibre requires browser globals.

**Primary recommendation:** Build the MapView component as a pure client component with SSR disabled via `next/dynamic`, register the PMTiles protocol once in a `useEffect`, and use react-map-gl `<Source>` + `<Layer>` components throughout — never drop to the raw MapLibre JS API unless necessary.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 16.2.2 | Full-stack React framework | App Router, TypeScript, Turbopack (with caveats — see pitfalls) |
| React | 19.x | UI layer | Required by Next.js 16 |
| TypeScript | 5.x | Type safety | Stack decision; prevents coordinate/property type bugs |
| react-map-gl | 8.1.0 | React wrapper for MapLibre | vis.gl official wrapper; `<Source>`, `<Layer>`, `<Popup>` as React components |
| maplibre-gl | 5.22.0 | WebGL map engine | Open-source, self-hostable, WebGL rendering |
| pmtiles | 4.4.0 | PMTiles HTTP range protocol | Registers `pmtiles://` URL protocol with MapLibre |
| @protomaps/basemaps | latest | Protomaps style layer generator | Generates MapLibre style JSON for PMTiles OSM base map |
| tailwindcss | 4.2.2 | Utility CSS | Stack decision; v4 uses CSS variable system, no config file |
| shadcn/ui | latest | Copy-paste UI components | Stack decision; Radix UI + Tailwind, fully owned code |
| lucide-react | 1.7.0 | Icons | shadcn/ui default icon library |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @protomaps/basemaps | latest | Generate MapLibre style layers for PMTiles | Required for light-themed vector base map from PMTiles |
| date-fns | latest | Relative time formatting | "2 min ago" freshness strings; built-in `formatDistanceToNow` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PMTiles self-hosted | MapTiler Cloud tiles | MapTiler requires API key; PMTiles is free, self-hosted |
| @protomaps/basemaps | mapbox-gl styles | Mapbox styles are proprietary; Protomaps is open-source |
| date-fns | dayjs / Intl.RelativeTimeFormat | date-fns has `formatDistanceToNow` built-in; no locale config needed |
| Tailwind v4 CSS variables | Tailwind v3 config | shadcn/ui requires Tailwind 4+; v3 is not compatible |

**Installation:**

```bash
# In /frontend directory after create-next-app
pnpm add maplibre-gl react-map-gl pmtiles @protomaps/basemaps date-fns
pnpm add -D @types/maplibre-gl

# shadcn components
npx shadcn@latest add switch badge separator button card tooltip
```

**Version verification:** Versions above confirmed against npm registry on 2026-04-05.

---

## Architecture Patterns

### Recommended Project Structure

```
frontend/
├── app/
│   ├── layout.tsx          # Root layout, Inter font, Tailwind globals
│   ├── page.tsx            # Home page: Server Component shell, dynamic-imports MapView
│   └── globals.css         # Tailwind v4 @import, MapLibre CSS import
├── components/
│   ├── map/
│   │   ├── MapView.tsx         # 'use client'; react-map-gl Map wrapper, PMTiles setup
│   │   ├── TransitLayer.tsx    # Source + 3 Layers (clusters, count, individual dots)
│   │   ├── AQILayer.tsx        # Source + heatmap Layer + point Layer (for popup hit area)
│   │   ├── FeaturePopup.tsx    # <Popup> component, renders popup card content
│   │   └── FreshnessIndicator.tsx  # Colored dot + relative time
│   └── sidebar/
│       ├── Sidebar.tsx         # Layout + collapse state + tablet drawer
│       ├── LayerToggle.tsx     # shadcn Switch + layer label
│       ├── AQILegend.tsx       # AQI color scale strip
│       └── TransitLegend.tsx   # Route type color swatches
├── hooks/
│   ├── useLayerData.ts     # Fetch + 60s polling for /api/layers/{domain}
│   └── useRelativeTime.ts  # formatDistanceToNow wrapper, updates on interval
├── lib/
│   ├── api.ts              # fetch wrappers for backend endpoints
│   └── map-styles.ts       # Protomaps style builder, AQI color ramp constants
└── types/
    └── geojson.ts          # GeoJSON FeatureCollection types matching API response
```

### Pattern 1: SSR-Safe Map Initialization

MapLibre GL JS requires `window` and WebGL, which do not exist during Next.js server rendering. All map code must be client-only.

**What:** Wrap the entire map component in `next/dynamic` with `ssr: false` from a Server Component.
**When to use:** Any component that imports `maplibre-gl` or `react-map-gl/maplibre`.

```typescript
// app/page.tsx (Server Component — no 'use client')
import dynamic from 'next/dynamic';

const MapView = dynamic(() => import('@/components/map/MapView'), {
  ssr: false,
  loading: () => <div className="flex-1 bg-muted animate-pulse" />,
});

export default function Home() {
  return (
    <main className="flex h-screen">
      <Sidebar />
      <MapView className="flex-1" />
    </main>
  );
}
```

### Pattern 2: PMTiles Protocol Registration

The `pmtiles://` URL protocol must be registered with MapLibre before any map renders.

**What:** Call `maplibregl.addProtocol` once per app lifecycle.
**When to use:** Inside the `MapView` component's `useEffect` with empty deps.

```typescript
// Source: https://docs.protomaps.com/pmtiles/maplibre
import { Protocol } from 'pmtiles';
import maplibregl from 'maplibre-gl';
import { useEffect } from 'react';

// Inside MapView component:
useEffect(() => {
  const protocol = new Protocol();
  maplibregl.addProtocol('pmtiles', protocol.tile);
  return () => {
    maplibregl.removeProtocol('pmtiles');
  };
}, []);
```

### Pattern 3: Protomaps Light Base Map Style

```typescript
// Source: https://docs.protomaps.com/basemaps/maplibre
import { layers, namedFlavor } from '@protomaps/basemaps';

const PMTILES_URL = 'pmtiles:///tiles/aalen.pmtiles'; // or hosted URL

const mapStyle = {
  version: 8,
  glyphs: 'https://protomaps.github.io/basemaps-assets/fonts/{fontstack}/{range}.pbf',
  sprite: 'https://protomaps.github.io/basemaps-assets/sprites/v4/light',
  sources: {
    protomaps: {
      type: 'vector',
      url: PMTILES_URL,
      attribution: '© OpenStreetMap contributors',
    },
  },
  layers: layers('protomaps', namedFlavor('light'), { lang: 'de' }),
};
```

**PMTiles file:** Use `pmtiles extract` to extract the Aalen bounding box from the daily build at `https://build.protomaps.com/{date}.pmtiles` with `--bbox=9.8,48.7,10.3,49.0`. Place file in `frontend/public/tiles/aalen.pmtiles` and reference via `/tiles/aalen.pmtiles`.

### Pattern 4: GeoJSON Source with Clustering (Transit)

```typescript
// Source: MapLibre GL JS docs — cluster example
import { Source, Layer } from 'react-map-gl/maplibre';
import type { CircleLayer, SymbolLayer } from 'react-map-gl/maplibre';

// Three layers required for clustering:
const clusterLayer: CircleLayer = {
  id: 'transit-clusters',
  type: 'circle',
  source: 'transit',
  filter: ['has', 'point_count'],
  paint: {
    'circle-color': '#f4f5f7',
    'circle-radius': 12,
    'circle-stroke-width': 1,
    'circle-stroke-color': '#9ca3af',
  },
};

const clusterCountLayer: SymbolLayer = {
  id: 'transit-cluster-count',
  type: 'symbol',
  source: 'transit',
  filter: ['has', 'point_count'],
  layout: {
    'text-field': '{point_count_abbreviated}',
    'text-font': ['Noto Sans Regular'],
    'text-size': 12,
  },
};

const unclusteredStopLayer: CircleLayer = {
  id: 'transit-stops',
  type: 'circle',
  source: 'transit',
  filter: ['!', ['has', 'point_count']],
  paint: {
    'circle-radius': 4,
    'circle-stroke-width': 1,
    'circle-stroke-color': '#ffffff',
    // color driven by route_type in properties:
    'circle-color': [
      'match', ['get', 'route_type_color'],
      'bus', '#1565c0',
      'train', '#c62828',
      'tram', '#2e7d32',
      '#9ca3af', // default
    ],
  },
};

// Usage:
<Source
  id="transit"
  type="geojson"
  data={transitGeoJSON}
  cluster={true}
  clusterMaxZoom={13}
  clusterRadius={40}
>
  <Layer {...clusterLayer} />
  <Layer {...clusterCountLayer} />
  <Layer {...unclusteredStopLayer} />
</Source>
```

### Pattern 5: AQI Heatmap Layer

The heatmap is driven by the numeric `aqi` property in air quality feature properties. A separate invisible circle layer provides click targets since heatmap layers are not clickable.

```typescript
// Source: MapLibre GL JS heatmap example
import type { HeatmapLayer, CircleLayer } from 'react-map-gl/maplibre';

const aqiHeatmapLayer: HeatmapLayer = {
  id: 'aqi-heatmap',
  type: 'heatmap',
  source: 'air-quality',
  paint: {
    'heatmap-weight': [
      'interpolate', ['linear'],
      ['get', 'aqi'],
      0, 0,
      80, 1,
    ],
    'heatmap-intensity': 0.8,
    'heatmap-radius': [
      'interpolate', ['linear'], ['zoom'],
      10, 20,
      14, 40,
    ],
    'heatmap-color': [
      'interpolate', ['linear'], ['heatmap-density'],
      0,    'rgba(0,200,83,0)',
      0.25, '#00c853',
      0.5,  '#ffeb3b',
      0.75, '#ff9800',
      1.0,  '#b71c1c',
    ],
    'heatmap-opacity': 0.8,
  },
};

// Click-target layer (transparent circles, same source):
const aqiPointLayer: CircleLayer = {
  id: 'aqi-points',
  type: 'circle',
  source: 'air-quality',
  paint: {
    'circle-radius': 6,
    'circle-color': 'transparent',
  },
};
```

### Pattern 6: Click Popup with interactiveLayerIds

```typescript
// Source: react-map-gl docs + community patterns
import Map, { Popup } from 'react-map-gl/maplibre';

const [popupInfo, setPopupInfo] = useState<{
  longitude: number;
  latitude: number;
  feature: GeoJSON.Feature;
} | null>(null);

<Map
  interactiveLayerIds={['transit-stops', 'aqi-points']}
  onClick={(e) => {
    const feature = e.features?.[0];
    if (!feature || !e.lngLat) return;
    setPopupInfo({
      longitude: e.lngLat.lng,
      latitude: e.lngLat.lat,
      feature,
    });
  }}
>
  {popupInfo && (
    <Popup
      longitude={popupInfo.longitude}
      latitude={popupInfo.latitude}
      onClose={() => setPopupInfo(null)}
      closeOnClick={false}
      maxWidth="200px"
      anchor="bottom"
    >
      <FeaturePopup feature={popupInfo.feature} />
    </Popup>
  )}
</Map>
```

### Pattern 7: 60-Second Polling Hook

```typescript
// hooks/useLayerData.ts
import { useState, useEffect, useRef } from 'react';

export function useLayerData(domain: string, town: string = 'aalen') {
  const [data, setData] = useState<GeoJSON.FeatureCollection | null>(null);
  const [lastFetched, setLastFetched] = useState<Date | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(
          `http://localhost:8000/api/layers/${domain}?town=${town}`
        );
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        setData(json);
        setLastFetched(new Date());
        setError(false);
      } catch {
        setError(true);
      }
    };

    fetchData();
    const id = setInterval(fetchData, 60_000);
    return () => clearInterval(id);
  }, [domain, town]);

  return { data, lastFetched, error };
}
```

### Pattern 8: Docker Compose Frontend Service

```yaml
# Addition to docker-compose.yml
frontend:
  build: ./frontend
  environment:
    NEXT_PUBLIC_API_URL: http://localhost:8000
    PORT: 4000
  ports:
    - "4000:4000"
  depends_on:
    - backend
  restart: unless-stopped
```

```dockerfile
# frontend/Dockerfile
FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ENV PORT=4000
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
ENV PORT=4000
EXPOSE 4000
CMD ["node", "server.js"]
```

Note: Next.js `output: 'standalone'` must be set in `next.config.ts` for this Dockerfile.

### Anti-Patterns to Avoid

- **Importing maplibre-gl in a Server Component:** `ReferenceError: window is not defined`. All map imports must be in `'use client'` components or dynamic-imported with `ssr: false`.
- **Using Turbopack in dev with MapLibre:** Known bug (GitHub issue #86495) — MapLibre's inline worker dies on Turbopack's HMR ping. Set `"dev": "next dev"` (no `--turbopack` flag) in `package.json`.
- **Heatmap layers as click targets:** MapLibre heatmap layers do not fire click events. Use a separate transparent circle layer on the same source for interaction.
- **Registering PMTiles protocol after Map renders:** Protocol must be registered before MapLibre requests any tile. Register in `useEffect` with empty deps, before Map component mounts.
- **Hardcoding API URL:** Use `NEXT_PUBLIC_API_URL` env var; in Docker the backend service name resolves differently than `localhost`.
- **Using `useState` for layer visibility instead of MapLibre `setLayoutProperty`:** Re-rendering the entire Source causes a flash. Prefer toggling MapLibre's own layer visibility property.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Relative time ("2 min ago") | Custom time formatter | `date-fns formatDistanceToNow` | Handles edge cases, locale, pluralization |
| Map popup positioning | Manual coordinate calculation | react-map-gl `<Popup>` component | Handles anchor flipping at edges, z-index, offset |
| GeoJSON clustering | Manual cluster algorithm | MapLibre GeoJSON source `cluster: true` | Built-in, GPU-accelerated, handles zoom transitions |
| Heatmap color interpolation | Custom WebGL shader | MapLibre `heatmap` layer type | Expression-driven, paint property controlled |
| Layer toggle UI | Custom toggle | shadcn `<Switch>` | Accessible, keyboard nav, touch target correct |
| PMTiles tile fetching | Custom HTTP range client | `pmtiles` npm package + `addProtocol` | Handles byte-range requests, caching, format parsing |

**Key insight:** MapLibre handles all rendering complexity — clustering, heatmap, vector tiles. React's job is state management and UI only; avoid mixing MapLibre JS API calls with React state management.

---

## Runtime State Inventory

Step 2.5: SKIPPED — Phase 4 is greenfield (new `/frontend` directory). No rename/refactor/migration involved.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Next.js build + dev | ✓ | 22.22.1 | — |
| npm | Package installation | ✓ | 10.9.4 | — |
| pnpm | CLAUDE.md recommends pnpm | ✗ | — | Use npm (available) |
| Docker | Frontend service in compose | ✓ | 29.3.1 | Run `npm run dev` directly |
| Docker Compose | `docker-compose up` | ✓ | v5.1.1 | — |
| Backend (port 8000) | API data fetch | Not checked at research time | — | Mock data during dev |

**Missing dependencies with no fallback:**
- None that block execution.

**Missing dependencies with fallback:**
- pnpm not installed — use `npm` instead (available). CLAUDE.md recommends pnpm; install with `npm install -g pnpm` or use `corepack enable`.

---

## Common Pitfalls

### Pitfall 1: Turbopack + MapLibre Worker Conflict

**What goes wrong:** `next dev` in Next.js 15/16 enables Turbopack by default. MapLibre sends a "ping" HMR message to its inline web worker; Turbopack tears the worker down. Clustering and tile layers never render in dev mode.

**Why it happens:** Turbopack's module worker isolation rejects unrecognized messages. This is a known open issue (vercel/next.js #86495, reported November 2025, unresolved as of April 2026).

**How to avoid:** Set the dev script in `package.json` to `"next dev"` without `--turbopack`. Production builds with `next build` are not affected.

**Warning signs:** Clusters don't appear; tile layer is blank; browser console shows worker termination messages.

### Pitfall 2: SSR Window Reference Errors

**What goes wrong:** `ReferenceError: window is not defined` at build time because MapLibre and react-map-gl access browser globals at module load time.

**Why it happens:** Next.js App Router renders all components on the server by default; MapLibre assumes a browser environment.

**How to avoid:** Always wrap `MapView` with `dynamic(() => import(...), { ssr: false })` in the parent Server Component. Never import `maplibre-gl` in any file that doesn't have `'use client'` at the top.

**Warning signs:** Build error mentioning `window`, `document`, or `navigator`; errors during `next build`.

### Pitfall 3: PMTiles Protocol Not Registered Before Map Mounts

**What goes wrong:** Map renders blank; console shows `Unknown protocol: pmtiles://`.

**Why it happens:** MapLibre tries to fetch tiles when the `mapStyle` prop is applied, before the `useEffect` cleanup has run.

**How to avoid:** Register the PMTiles protocol in a `useEffect(() => { ... }, [])` at the top of the `MapView` component, before the `<Map>` JSX. Alternatively, register at module level (outside the component) — valid because there is only one Map instance.

**Warning signs:** Console `Unknown protocol` errors; blank map tile area.

### Pitfall 4: Heatmap Layer Not Clickable

**What goes wrong:** Clicking the heatmap area produces no feature events; popup never opens for air quality sensors.

**Why it happens:** MapLibre heatmap layers are raster-rendered and do not participate in feature picking (`queryRenderedFeatures`).

**How to avoid:** Always add a companion transparent circle layer (`type: 'circle'`, `circle-color: 'transparent'`) on the same GeoJSON source. Include this layer's ID in `interactiveLayerIds`. The heatmap provides visual; the circle layer provides interaction.

**Warning signs:** `e.features` is empty or undefined when clicking in the heatmap area.

### Pitfall 5: CORS in Dev Mode

**What goes wrong:** Fetch to `http://localhost:8000/api/layers/...` blocked by CORS policy.

**Why it happens:** Next.js dev server on port 4000 and FastAPI on port 8000 are different origins.

**How to avoid:** Add a Next.js `rewrites` config in `next.config.ts`:

```typescript
rewrites: async () => [
  { source: '/api/:path*', destination: 'http://localhost:8000/api/:path*' },
],
```

This proxies `/api/*` through Next.js in dev, eliminating CORS. In Docker, the services talk directly via Docker network — no CORS issue.

**Warning signs:** Browser console `Access-Control-Allow-Origin` CORS error on fetch.

### Pitfall 6: MapLibre CSS Not Imported

**What goes wrong:** Map controls (zoom buttons, compass), popups, and markers appear unstyled or invisible.

**Why it happens:** MapLibre's default CSS is not bundled automatically; it must be explicitly imported.

**How to avoid:** Add `import 'maplibre-gl/dist/maplibre-gl.css'` in `MapView.tsx` (the `'use client'` component that imports `react-map-gl/maplibre`). Next.js will handle CSS extraction at build time.

**Warning signs:** Zoom control buttons missing; popup appears at wrong position; map attribution overlaps content.

### Pitfall 7: Tailwind 4 + shadcn Init Differences

**What goes wrong:** Running `npx shadcn@latest init` on a Tailwind v4 project requires different configuration than v3 tutorials describe.

**Why it happens:** Tailwind v4 dropped `tailwind.config.js` in favor of CSS `@theme` directives. shadcn v4-compatible CLI handles this but generates a different `components.json`.

**How to avoid:** Leave the `tailwind.config` field empty in `components.json` for Tailwind v4. The shadcn CLI (latest) auto-detects Tailwind v4 when run on a project created with `create-next-app` and Tailwind v4. Do not follow v3 setup guides.

**Warning signs:** shadcn components lack correct CSS variable bindings; buttons appear unstyled.

---

## Code Examples

### Complete MapView shell

```typescript
// components/map/MapView.tsx
'use client';

import { useEffect, useState, useCallback } from 'react';
import Map, { Source, Layer, Popup, NavigationControl } from 'react-map-gl/maplibre';
import { Protocol } from 'pmtiles';
import { layers as protomapsLayers, namedFlavor } from '@protomaps/basemaps';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { buildMapStyle } from '@/lib/map-styles';
import { useLayerData } from '@/hooks/useLayerData';

const AALEN_CENTER = { longitude: 10.0918, latitude: 48.8374 };

export default function MapView({ transitVisible, aqiVisible }: {
  transitVisible: boolean;
  aqiVisible: boolean;
}) {
  const [popupInfo, setPopupInfo] = useState<{
    longitude: number;
    latitude: number;
    feature: GeoJSON.Feature;
  } | null>(null);

  const { data: transitData } = useLayerData('transit');
  const { data: aqiData } = useLayerData('air_quality');

  useEffect(() => {
    const protocol = new Protocol();
    maplibregl.addProtocol('pmtiles', protocol.tile);
    return () => { maplibregl.removeProtocol('pmtiles'); };
  }, []);

  const onClick = useCallback((e: maplibregl.MapMouseEvent) => {
    const feature = e.features?.[0];
    if (!feature) { setPopupInfo(null); return; }
    setPopupInfo({
      longitude: e.lngLat.lng,
      latitude: e.lngLat.lat,
      feature,
    });
  }, []);

  return (
    <Map
      initialViewState={{ ...AALEN_CENTER, zoom: 13 }}
      style={{ width: '100%', height: '100%' }}
      mapStyle={buildMapStyle()}
      minZoom={8}
      maxZoom={18}
      interactiveLayerIds={['transit-stops', 'aqi-points']}
      onClick={onClick}
    >
      <NavigationControl position="bottom-right" />
      {/* TransitLayer and AQILayer as sub-components */}
      {popupInfo && (
        <Popup
          longitude={popupInfo.longitude}
          latitude={popupInfo.latitude}
          onClose={() => setPopupInfo(null)}
          closeOnClick={false}
          maxWidth="200px"
        >
          {/* FeaturePopup renders here */}
        </Popup>
      )}
    </Map>
  );
}
```

### API Response Shape (from layers.py + geojson.py)

```typescript
// types/geojson.ts — matches LayerResponse schema exactly
interface Attribution {
  source_name: string;
  license: string;
  license_url: string;
  url?: string;
}

interface LayerResponse {
  '@context': string;     // NGSI-LD context URL
  type: 'FeatureCollection';
  features: GeoJSON.Feature[];
  attribution: Attribution[];
  last_updated: string | null;  // ISO datetime string
  town: string;
  domain: string;
}

// Air quality feature properties (injected by layers.py):
interface AQIFeatureProperties {
  aqi_tier: 'good' | 'moderate' | 'poor' | 'bad' | 'very_bad' | 'unknown';
  aqi_color: string;  // hex color from aqi_tier()
  aqi: number | null;
  pm25: number | null;
  pm10: number | null;
  no2: number | null;
  o3: number | null;
}
```

### Relative Time Formatting

```typescript
// hooks/useRelativeTime.ts
import { formatDistanceToNow } from 'date-fns';
import { de } from 'date-fns/locale';

export function useRelativeTime(timestamp: string | null): string {
  if (!timestamp) return 'Kein Zeitstempel';
  const date = new Date(timestamp);
  return formatDistanceToNow(date, { addSuffix: true, locale: de });
}
// Returns: "vor 2 Minuten", "vor 28 Minuten", "vor etwa 1 Stunde"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Mapbox GL JS | MapLibre GL JS | Dec 2020 (Mapbox license change) | Must use MapLibre; no API key needed |
| react-map-gl with mapLib prop | `import Map from 'react-map-gl/maplibre'` | v7/v8 | Direct subpath import; cleaner than passing mapLib |
| `tailwind.config.js` | CSS `@theme` directives | Tailwind v4 | No config file; all customization in CSS |
| shadcn `@shadcn/ui` package | Copy-paste via `npx shadcn@latest add` | 2023+ | Components are owned code in repo, not a dependency |
| `next dev --turbopack` | `next dev` (webpack) | v15/v16 (workaround) | MapLibre workers fail with Turbopack in dev mode |
| create-react-app | Next.js App Router | 2022 (CRA deprecated) | Next.js is the current standard |

**Deprecated/outdated:**
- `mapLibregl.addLayer` / `addSource` in `useEffect`: Use react-map-gl `<Source>` + `<Layer>` declarative components instead.
- `react-map-gl < v7` patterns with `mapLib` prop: Replaced by subpath imports.
- `tailwind.config.js` customizations: Not compatible with Tailwind v4 CSS variable system.

---

## Open Questions

1. **PMTiles file hosting: local vs CDN**
   - What we know: `frontend/public/tiles/aalen.pmtiles` works for dev and Docker. Production could use the Protomaps CDN (no hotlinking guarantee) or a self-hosted S3-compatible bucket.
   - What's unclear: File size for Aalen bounding box extract (estimate: 50–200 MB depending on zoom levels).
   - Recommendation: Extract and commit the PMTiles file to the repo during Wave 1 setup. Use `/tiles/aalen.pmtiles` path. Revisit hosting for production in a later phase.

2. **API URL in Docker vs dev**
   - What we know: In dev, the frontend on 4000 fetches from `http://localhost:8000`. In Docker, `localhost` from inside the container won't reach the backend service.
   - What's unclear: Whether to use Next.js rewrites, an nginx proxy, or Docker service name directly.
   - Recommendation: Use Next.js rewrites (`/api/* -> http://backend:8000/api/*`) in `next.config.ts`. This works in both dev (proxy to localhost:8000) and Docker (proxy to backend service name).

3. **Transit route polylines from API**
   - What we know: The transit layer returns GeoJSON features from the `features` table. Some features are Points (stops), some are LineStrings (route shapes).
   - What's unclear: Whether the API already returns shapes/polylines or only stops.
   - Recommendation: Inspect the actual API response during Wave 1. If polylines are present, add a line layer. If not, the transit display is stops-only for Phase 4.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Playwright (browser E2E) — frontend does not exist yet; no vitest config |
| Config file | `frontend/playwright.config.ts` — Wave 0 gap |
| Quick run command | `npx playwright test --project=chromium` |
| Full suite command | `npx playwright test` |

**Note:** Unit tests with Vitest are an alternative for pure component logic. For map-heavy UI, Playwright smoke tests are more valuable because they verify the browser/WebGL rendering pipeline.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MAP-01 | Map loads centered on Aalen | smoke (Playwright) | `npx playwright test --grep "MAP-01"` | ❌ Wave 0 |
| MAP-02 | Layer toggle hides/shows layer | E2E (Playwright) | `npx playwright test --grep "MAP-02"` | ❌ Wave 0 |
| MAP-03 | PMTiles base map tiles render | smoke (Playwright) | `npx playwright test --grep "MAP-03"` | ❌ Wave 0 |
| MAP-04 | Legend renders with correct tier colors | E2E (Playwright) | `npx playwright test --grep "MAP-04"` | ❌ Wave 0 |
| MAP-05 | Clustering appears at zoom 12, dissolves at zoom 14 | E2E (Playwright) | `npx playwright test --grep "MAP-05"` | ❌ Wave 0 |
| MAP-07 | Click on stop opens popup with data | E2E (Playwright) | `npx playwright test --grep "MAP-07"` | ❌ Wave 0 |
| MAP-08 | Base map uses OSM tiles (PMTiles) | smoke (Playwright) | `npx playwright test --grep "MAP-08"` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `npx playwright test --grep "smoke" --project=chromium`
- **Per wave merge:** `npx playwright test --project=chromium`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `frontend/playwright.config.ts` — Playwright configuration, base URL `http://localhost:4000`
- [ ] `frontend/tests/map.spec.ts` — covers MAP-01 through MAP-08
- [ ] Framework install: `pnpm add -D @playwright/test && npx playwright install chromium`

---

## Project Constraints (from CLAUDE.md)

| Directive | Requirement |
|-----------|-------------|
| Port 4000 | Frontend must run on port 4000; Grafana occupies 3000 |
| Open data only | No paid API keys; PMTiles + OSM tiles are free |
| Self-hostable | Docker Compose deployment; no cloud-only services |
| No Mapbox GL JS | Use MapLibre GL JS (open-source fork) |
| No Google Maps | Use MapLibre + Protomaps |
| MapLibre GL JS 5.x + react-map-gl 8.x | Version compatibility locked |
| Next.js 16.x + React 19.x | Stack locked; do not mix React 18 |
| Tailwind CSS 4.x + shadcn/ui latest | shadcn requires Tailwind 4+ |
| pnpm preferred | Use pnpm; fallback to npm if pnpm unavailable |
| Biome for linting | Replace ESLint + Prettier with Biome |
| NGSI-LD attribution | Display `attribution` field from API in sidebar footer |
| Generic architecture | No Aalen-specific hardcoding; use `NEXT_PUBLIC_TOWN=aalen` env var |
| DL-DE-BY-2.0 attribution | Must display data source attribution from API response |

---

## Sources

### Primary (HIGH confidence)

- `npm view` — verified all library versions from npm registry on 2026-04-05
- https://docs.protomaps.com/pmtiles/maplibre — PMTiles protocol registration and addProtocol pattern
- https://docs.protomaps.com/basemaps/maplibre — Protomaps basemaps style builder, light flavor, lang param
- https://visgl.github.io/react-map-gl/docs/get-started — react-map-gl 8 MapLibre subpath import pattern
- `backend/app/routers/layers.py` — API response structure confirmed from source
- `backend/app/schemas/geojson.py` — AQI tier labels, colors, LayerResponse schema confirmed from source
- GitHub issue vercel/next.js #86495 — Turbopack + MapLibre worker conflict confirmed

### Secondary (MEDIUM confidence)

- https://maplibre.org/maplibre-gl-js/docs/examples/create-a-heatmap-layer/ — heatmap paint properties
- WebSearch: react-map-gl 8 interactiveLayerIds + onClick pattern — confirmed by multiple sources
- WebSearch: shadcn Tailwind v4 init behavior — confirmed by shadcn official docs and community sources

### Tertiary (LOW confidence)

- PMTiles file size estimate for Aalen region (50–200 MB) — extrapolated from similar city extracts, not verified

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified against npm registry on research date
- Architecture: HIGH — patterns verified against official docs (Protomaps, react-map-gl, MapLibre)
- Pitfalls: HIGH — Turbopack issue confirmed via open GitHub issue; SSR pattern confirmed by Next.js docs
- PMTiles file hosting: MEDIUM — extract command verified, file size unconfirmed

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (stable libraries; PMTiles daily builds URL may change)
