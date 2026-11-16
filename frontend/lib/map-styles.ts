import { layers, namedFlavor } from '@protomaps/basemaps';
import type { ExpressionSpecification, HillshadeLayerSpecification, LayerSpecification, LightSpecification, SkySpecification, SourceSpecification, StyleSpecification } from 'maplibre-gl';

export const BASE_LAYERS = ['dark', 'light', 'orthophoto', 'satellite'] as const;
export type BaseLayer = (typeof BASE_LAYERS)[number];
export const DEFAULT_BASE_LAYER: BaseLayer = 'dark';

/**
 * Map the `base` URL param to a BaseLayer. Whitelists the known values, maps the
 * legacy value 'osm' (old raster OpenStreetMap base) to 'light', and falls back
 * to the default for anything else.
 */
export function parseBaseLayer(raw: string | null | undefined): BaseLayer {
  if (raw === 'osm') return 'light';
  const match = BASE_LAYERS.find((b) => b === raw);
  return match ?? DEFAULT_BASE_LAYER;
}

export const PROTOMAPS_SOURCE_ID = 'protomaps';
export const TERRAIN_SOURCE_ID = 'terrain-dem';
export const HILLSHADE_SOURCE_ID = 'hillshade-dem';
export const HILLSHADE_LAYER_ID = 'hillshade-relief';
export const TERRAIN_EXAGGERATION = 1.3;

// Follow-up: self-host glyphs, sprites and DEM tiles (currently fetched from public CDNs).
const GLYPHS_URL = 'https://protomaps.github.io/basemaps-assets/fonts/{fontstack}/{range}.pbf';
const SPRITE_BASE_URL = 'https://protomaps.github.io/basemaps-assets/sprites/v4/';
const DEM_TILES_URL = 'https://elevation-tiles-prod.s3.amazonaws.com/terrarium/{z}/{x}/{y}.png';

const PROTOMAPS_ATTRIBUTION =
  '<a href="https://protomaps.com">Protomaps</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';
const DEM_ATTRIBUTION =
  'Terrain: <a href="https://github.com/tilezen/joerd/blob/master/docs/attribution.md">Mapzen / AWS Terrain Tiles</a>';

// EEA EAQI 6-tier heatmap color ramp (density 0→1 mapped to tier colors)
export const AQI_COLOR_RAMP = [
  { threshold: 0,   color: 'rgba(80,240,230,0)' },
  { threshold: 0.2, color: '#50F0E6' },
  { threshold: 0.4, color: '#50CCAA' },
  { threshold: 0.6, color: '#F0E641' },
  { threshold: 0.8, color: '#FF5050' },
  { threshold: 0.9, color: '#960032' },
  { threshold: 1.0, color: '#7D2181' },
] as const;

// EEA EAQI tier colors matching EAQI_TIER_COLORS in backend/app/schemas/geojson.py
export const AQI_TIER_COLORS: Record<string, string> = {
  good:            '#50F0E6',
  fair:            '#50CCAA',
  moderate:        '#F0E641',
  poor:            '#FF5050',
  very_poor:       '#960032',
  extremely_poor:  '#7D2181',
  unknown:         '#9e9e9e',
};

// EAQI tier order, best to worst (matches the six colours of AQI_TIER_COLORS).
export const EAQI_TIER_ORDER = [
  'good',
  'fair',
  'moderate',
  'poor',
  'very_poor',
  'extremely_poor',
] as const;

// Upper bounds (ug/m3) of good, fair, moderate, poor, very_poor per pollutant. Mirrors
// EAQI_BREAKPOINTS in backend/app/schemas/geojson.py (EEA EAQI, airindex.eea.europa.eu) so
// 3D cells and sensor badges agree. The backend bands are inclusive upper bounds while a
// MapLibre `step` switches at the bound itself; the difference only shows at exact equality.
export const EAQI_BREAKPOINTS: Record<'pm25' | 'pm10' | 'no2' | 'o3', readonly number[]> = {
  pm25: [5, 15, 25, 50, 75],
  pm10: [10, 20, 50, 100, 150],
  no2:  [10, 20, 50, 100, 200],
  o3:   [50, 100, 130, 240, 380],
};

/** Colour of a feature by the EAQI tier of its `pollutant` property (grey when not a number). */
export function eaqiColorExpression(pollutant: keyof typeof EAQI_BREAKPOINTS): ExpressionSpecification {
  const bounds = EAQI_BREAKPOINTS[pollutant];
  const steps: (number | string)[] = [];
  bounds.forEach((bound, i) => {
    steps.push(bound, AQI_TIER_COLORS[EAQI_TIER_ORDER[i + 1]]);
  });
  return [
    'case',
    ['==', ['typeof', ['get', pollutant]], 'number'],
    ['step', ['get', pollutant], AQI_TIER_COLORS[EAQI_TIER_ORDER[0]], ...steps],
    AQI_TIER_COLORS.unknown,
  ] as ExpressionSpecification;
}

// Transit route type colors (per CONTEXT.md: bus=blue, train=red, tram=green)
export const TRANSIT_COLORS: Record<string, string> = {
  bus:   '#1565c0',
  train: '#c62828',
  tram:  '#2e7d32',
};

/** Subtle hillshade tuned per base style. */
export const HILLSHADE_PAINT: Record<BaseLayer, NonNullable<HillshadeLayerSpecification['paint']>> = {
  dark: {
    'hillshade-shadow-color': '#05070b',
    'hillshade-highlight-color': '#3d4a5e',
    'hillshade-accent-color': '#141922',
    'hillshade-exaggeration': 0.35,
  },
  light: {
    'hillshade-shadow-color': '#6b604f',
    'hillshade-highlight-color': '#ffffff',
    'hillshade-accent-color': '#8c826f',
    'hillshade-exaggeration': 0.3,
  },
  orthophoto: {
    'hillshade-shadow-color': '#000000',
    'hillshade-highlight-color': '#ffffff',
    'hillshade-accent-color': '#000000',
    'hillshade-exaggeration': 0.25,
  },
  satellite: {
    'hillshade-shadow-color': '#000000',
    'hillshade-highlight-color': '#ffffff',
    'hillshade-accent-color': '#000000',
    'hillshade-exaggeration': 0.25,
  },
};

/** 3D building colour ramp (height in metres -> colour) and opacity per base style. */
export const BUILDING_PALETTES: Record<BaseLayer, { stops: Array<[number, string]>; opacity: number }> = {
  dark: { stops: [[0, '#3a4763'], [20, '#55688f'], [60, '#8ea8d6']], opacity: 1 },
  light: { stops: [[0, '#ece7dd'], [20, '#cfc8b8'], [60, '#a89f8d']], opacity: 1 },
  orthophoto: { stops: [[0, '#e6e6e6'], [20, '#d2d2d2'], [60, '#bdbdbd']], opacity: 0.9 },
  satellite: { stops: [[0, '#e6e6e6'], [20, '#d2d2d2'], [60, '#bdbdbd']], opacity: 0.9 },
};

// Clear-day fallback until MapAtmosphere applies the live, sun/weather-driven values.
type Flavor = ReturnType<typeof namedFlavor>;

const TWIN_BG = '#0a0e15';

/**
 * Basemap flavor per vector style. "dark" is a blue-tinted digital-twin variant of
 * the Protomaps dark flavor: the stock one is near-black grey on grey, so roads,
 * water and parks are hard to tell apart under 3D buildings and data layers.
 */
function flavorFor(flavor: 'dark' | 'light'): Flavor {
  const base = namedFlavor(flavor);
  if (flavor === 'light') return base;
  return {
    ...base,
    background: TWIN_BG,
    earth: '#111722',
    park_a: '#14261f',
    park_b: '#163326',
    wood_a: '#12261d',
    wood_b: '#132c20',
    scrub_a: '#152420',
    scrub_b: '#152820',
    pedestrian: '#1a2130',
    industrial: '#151b27',
    school: '#1a202d',
    hospital: '#1b202c',
    water: '#0f3558',
    buildings: '#1e2738',
    pier: '#2a3445',
    other: '#2a3446',
    minor_service: '#2c3649',
    minor_a: '#3a4762',
    minor_b: '#323d54',
    link: '#4a5a7c',
    major: '#52648a',
    highway: '#7088b8',
    railway: '#454e63',
    minor_service_casing: TWIN_BG,
    minor_casing: TWIN_BG,
    link_casing: TWIN_BG,
    major_casing_late: TWIN_BG,
    major_casing_early: TWIN_BG,
    highway_casing_late: TWIN_BG,
    highway_casing_early: TWIN_BG,
    bridges_other: '#2a3446',
    bridges_minor: '#3a4762',
    bridges_link: '#4a5a7c',
    bridges_major: '#52648a',
    bridges_highway: '#7088b8',
    bridges_other_casing: TWIN_BG,
    bridges_minor_casing: TWIN_BG,
    bridges_link_casing: TWIN_BG,
    bridges_major_casing: TWIN_BG,
    bridges_highway_casing: TWIN_BG,
    tunnel_other: '#222b3a',
    tunnel_minor: '#222b3a',
    tunnel_link: '#222b3a',
    tunnel_major: '#222b3a',
    tunnel_highway: '#222b3a',
    tunnel_other_casing: TWIN_BG,
    tunnel_minor_casing: TWIN_BG,
    tunnel_link_casing: TWIN_BG,
    tunnel_major_casing: TWIN_BG,
    tunnel_highway_casing: TWIN_BG,
    boundaries: '#5b6b8a',
    city_label: '#d5def0',
    city_label_halo: TWIN_BG,
    subplace_label: '#94a1bb',
    subplace_label_halo: TWIN_BG,
    roads_label_major: '#aab6cf',
    roads_label_major_halo: TWIN_BG,
    roads_label_minor: '#8591aa',
    roads_label_minor_halo: TWIN_BG,
    address_label: '#66728a',
    address_label_halo: TWIN_BG,
    landcover: base.landcover && {
      ...base.landcover,
      grassland: 'rgba(22, 44, 33, 1)',
      farmland: 'rgba(21, 32, 28, 1)',
      forest: 'rgba(16, 42, 30, 1)',
      scrub: 'rgba(20, 38, 30, 1)',
      urban_area: 'rgba(19, 24, 34, 1)',
      barren: 'rgba(26, 28, 32, 1)',
    },
  };
}

/**
 * Basemap layers without the generic POI icons (shops, restaurants, ...). The
 * platform's own data layers are the points of interest; the stock icons only
 * clutter the 3D scene.
 */
function basemapLayers(flavor: 'dark' | 'light'): LayerSpecification[] {
  return layers(PROTOMAPS_SOURCE_ID, flavorFor(flavor), { lang: 'de' }).filter(
    (l) => l.id !== 'pois',
  );
}

function defaultSky(): SkySpecification {
  return {
    'sky-color': '#5a8fd8',
    'horizon-color': '#cfe3f5',
    'fog-color': '#dfe9f3',
    'sky-horizon-blend': 0.5,
    'horizon-fog-blend': 0.6,
    'fog-ground-blend': 0.5,
  };
}

function defaultLight(): LightSpecification {
  return {
    anchor: 'map',
    position: [1.5, 210, 40],
    color: '#ffffff',
    intensity: 0.5,
  };
}

// Fresh source objects per style: no shared mutable object between styles.
function sharedSources(pmtilesUrl: string): Record<string, SourceSpecification> {
  return {
    [PROTOMAPS_SOURCE_ID]: {
      type: 'vector',
      url: pmtilesUrl,
      attribution: PROTOMAPS_ATTRIBUTION,
    },
    // Separate raster-dem sources for terrain and hillshade (MapLibre recommendation).
    [TERRAIN_SOURCE_ID]: {
      type: 'raster-dem',
      tiles: [DEM_TILES_URL],
      encoding: 'terrarium',
      tileSize: 256,
      maxzoom: 15,
      attribution: DEM_ATTRIBUTION,
    },
    [HILLSHADE_SOURCE_ID]: {
      type: 'raster-dem',
      tiles: [DEM_TILES_URL],
      encoding: 'terrarium',
      tileSize: 256,
      maxzoom: 15,
      attribution: DEM_ATTRIBUTION,
    },
  };
}

// Hidden by default; visibility is toggled at runtime (GeospatialOverlayLayer).
function hillshadeLayer(base: BaseLayer): HillshadeLayerSpecification {
  return {
    id: HILLSHADE_LAYER_ID,
    type: 'hillshade',
    source: HILLSHADE_SOURCE_ID,
    layout: { visibility: 'none' },
    paint: HILLSHADE_PAINT[base],
  };
}

function buildVectorStyle(flavor: 'dark' | 'light', pmtilesUrl: string): StyleSpecification {
  const base = basemapLayers(flavor);
  const firstRoad = base.findIndex((l) => l.id.startsWith('roads'));
  const insertAt = firstRoad === -1 ? base.length : firstRoad;
  const withHillshade: LayerSpecification[] = [
    ...base.slice(0, insertAt),
    hillshadeLayer(flavor),
    ...base.slice(insertAt),
  ];
  return {
    version: 8,
    glyphs: GLYPHS_URL,
    sprite: `${SPRITE_BASE_URL}${flavor}`,
    sources: sharedSources(pmtilesUrl),
    sky: defaultSky(),
    light: defaultLight(),
    layers: withHillshade,
  };
}

function buildRasterStyle(
  base: 'orthophoto' | 'satellite',
  pmtilesUrl: string,
  rasterSource: SourceSpecification,
): StyleSpecification {
  // Dark-flavor labels (light text, dark halo) read best on aerial imagery.
  const labels = basemapLayers('dark').filter((l) => l.type === 'symbol');
  return {
    version: 8,
    glyphs: GLYPHS_URL,
    sprite: `${SPRITE_BASE_URL}dark`,
    sources: { [base]: rasterSource, ...sharedSources(pmtilesUrl) },
    sky: defaultSky(),
    light: defaultLight(),
    layers: [
      { id: `${base}-tiles`, type: 'raster', source: base },
      hillshadeLayer(base),
      ...labels,
    ],
  };
}

function buildOrthophotoStyle(pmtilesUrl: string): StyleSpecification {
  return buildRasterStyle('orthophoto', pmtilesUrl, {
    type: 'raster',
    tiles: [
      'https://owsproxy.lgl-bw.de/owsproxy/ows/WMS_LGL-BW_ATKIS_DOP?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=DOP&STYLES=&FORMAT=image/jpeg&TRANSPARENT=false&CRS=EPSG:3857&BBOX={bbox-epsg-3857}&WIDTH=256&HEIGHT=256',
    ],
    tileSize: 256,
    attribution: 'LGL Baden-Wuerttemberg, dl-de/by-2-0',
  });
}

function buildSatelliteStyle(pmtilesUrl: string): StyleSpecification {
  return buildRasterStyle('satellite', pmtilesUrl, {
    type: 'raster',
    tiles: [
      'https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2021_3857/default/GoogleMapsCompatible/{z}/{y}/{x}.jpg',
    ],
    tileSize: 256,
    attribution: 'Sentinel-2 cloudless by EOX, contains Copernicus Sentinel data',
  });
}

export function getMapStyle(baseLayer: BaseLayer, pmtilesUrl: string): StyleSpecification {
  switch (baseLayer) {
    case 'light':
      return buildVectorStyle('light', pmtilesUrl);
    case 'orthophoto':
      return buildOrthophotoStyle(pmtilesUrl);
    case 'satellite':
      return buildSatelliteStyle(pmtilesUrl);
    case 'dark':
    default:
      return buildVectorStyle('dark', pmtilesUrl);
  }
}

/** Id of the first symbol (label) layer; used as beforeId so 3D buildings sit beneath labels. */
export function firstSymbolLayerId(style: StyleSpecification): string | undefined {
  return style.layers.find((l) => l.type === 'symbol')?.id;
}
