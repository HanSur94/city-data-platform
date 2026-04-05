import { layers, namedFlavor } from '@protomaps/basemaps';

export const AQI_COLOR_RAMP = [
  { threshold: 0,    color: 'rgba(0,200,83,0)' },
  { threshold: 0.25, color: '#00c853' },
  { threshold: 0.5,  color: '#ffeb3b' },
  { threshold: 0.75, color: '#ff9800' },
  { threshold: 1.0,  color: '#b71c1c' },
] as const;

// AQI tier colors matching AQI_TIERS in backend/app/schemas/geojson.py
export const AQI_TIER_COLORS: Record<string, string> = {
  good:     '#00c853',
  moderate: '#ffeb3b',
  poor:     '#ff9800',
  bad:      '#f44336',
  very_bad: '#b71c1c',
  unknown:  '#9e9e9e',
};

// Transit route type colors (per CONTEXT.md: bus=blue, train=red, tram=green)
export const TRANSIT_COLORS: Record<string, string> = {
  bus:   '#1565c0',
  train: '#c62828',
  tram:  '#2e7d32',
};

export function buildMapStyle(pmtilesUrl: string) {
  return {
    version: 8 as const,
    glyphs: 'https://protomaps.github.io/basemaps-assets/fonts/{fontstack}/{range}.pbf',
    sprite: 'https://protomaps.github.io/basemaps-assets/sprites/v4/light',
    sources: {
      protomaps: {
        type: 'vector' as const,
        url: pmtilesUrl,
        attribution: '© OpenStreetMap contributors',
      },
    },
    layers: layers('protomaps', namedFlavor('light'), { lang: 'de' }),
  };
}
