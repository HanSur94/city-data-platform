// import { layers, namedFlavor } from '@protomaps/basemaps'; // Re-enable when using PMTiles vector tiles
import type { StyleSpecification } from 'maplibre-gl';

export type BaseLayer = 'osm' | 'orthophoto' | 'satellite';

// Alias for convenience
type MapStyleSpecification = StyleSpecification;

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

// Transit route type colors (per CONTEXT.md: bus=blue, train=red, tram=green)
export const TRANSIT_COLORS: Record<string, string> = {
  bus:   '#1565c0',
  train: '#c62828',
  tram:  '#2e7d32',
};

export function buildMapStyle(_pmtilesUrl: string): StyleSpecification {
  // Use OSM raster tiles as default base layer.
  // For vector tiles, download PMTiles and switch to the protomaps variant below.
  return {
    version: 8,
    glyphs: 'https://protomaps.github.io/basemaps-assets/fonts/{fontstack}/{range}.pbf',
    sprite: 'https://protomaps.github.io/basemaps-assets/sprites/v4/light',
    sources: {
      osm: {
        type: 'raster',
        tiles: [
          'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
        ],
        tileSize: 256,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      },
    },
    layers: [{ id: 'osm-tiles', type: 'raster', source: 'osm' }],
  };
}

export function buildOrthophotoStyle(): MapStyleSpecification {
  return {
    version: 8,
    glyphs: 'https://protomaps.github.io/basemaps-assets/fonts/{fontstack}/{range}.pbf',
    sprite: 'https://protomaps.github.io/basemaps-assets/sprites/v4/light',
    sources: {
      orthophoto: {
        type: 'raster',
        tiles: [
          'https://owsproxy.lgl-bw.de/owsproxy/ows/WMS_LGL-BW_ATKIS_DOP?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=DOP&STYLES=&FORMAT=image/jpeg&TRANSPARENT=false&CRS=EPSG:3857&BBOX={bbox-epsg-3857}&WIDTH=256&HEIGHT=256',
        ],
        tileSize: 256,
        attribution: 'LGL Baden-Wuerttemberg, dl-de/by-2-0',
      },
    },
    layers: [{ id: 'orthophoto-tiles', type: 'raster', source: 'orthophoto' }],
  };
}

export function buildSatelliteStyle(): MapStyleSpecification {
  return {
    version: 8,
    glyphs: 'https://protomaps.github.io/basemaps-assets/fonts/{fontstack}/{range}.pbf',
    sprite: 'https://protomaps.github.io/basemaps-assets/sprites/v4/light',
    sources: {
      satellite: {
        type: 'raster',
        tiles: [
          'https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2021_3857/default/GoogleMapsCompatible/{z}/{y}/{x}.jpg',
        ],
        tileSize: 256,
        attribution: 'Sentinel-2 cloudless by EOX, contains Copernicus Sentinel data',
      },
    },
    layers: [{ id: 'satellite-tiles', type: 'raster', source: 'satellite' }],
  };
}

export function getMapStyle(baseLayer: BaseLayer, pmtilesUrl: string): MapStyleSpecification {
  if (baseLayer === 'orthophoto') return buildOrthophotoStyle();
  if (baseLayer === 'satellite') return buildSatelliteStyle();
  return buildMapStyle(pmtilesUrl) as MapStyleSpecification;
}
