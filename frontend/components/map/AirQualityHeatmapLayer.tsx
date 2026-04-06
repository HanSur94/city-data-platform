'use client';
import { useMemo } from 'react';
import { Source, Layer } from 'react-map-gl/maplibre';
import type { HeatmapLayerSpecification } from 'react-map-gl/maplibre';
import type { LayerResponse } from '@/types/geojson';

export type Pollutant = 'pm25' | 'pm10' | 'no2' | 'o3';

interface AirQualityHeatmapLayerProps {
  data: LayerResponse | null;
  visible: boolean;
  activePollutant: Pollutant;
}

const visibility = (v: boolean): 'visible' | 'none' => v ? 'visible' : 'none';

/**
 * WHO-based thresholds for normalizing pollutant values to 0-1 weight.
 * Values at or above `veryUnhealthy` map to weight 1.0.
 */
const POLLUTANT_THRESHOLDS: Record<Pollutant, { good: number; moderate: number; unhealthy: number; veryUnhealthy: number }> = {
  pm25: { good: 15, moderate: 30, unhealthy: 55, veryUnhealthy: 75 },
  pm10: { good: 45, moderate: 90, unhealthy: 180, veryUnhealthy: 250 },
  no2:  { good: 40, moderate: 100, unhealthy: 200, veryUnhealthy: 300 },
  o3:   { good: 60, moderate: 120, unhealthy: 180, veryUnhealthy: 240 },
};

/**
 * Build a MapLibre heatmap layer spec for the active pollutant.
 * The heatmap-weight expression maps the pollutant value through the
 * WHO threshold breakpoints to produce a 0-1 normalized weight.
 */
function buildHeatmapLayer(pollutant: Pollutant): HeatmapLayerSpecification {
  const t = POLLUTANT_THRESHOLDS[pollutant];
  return {
    id: 'air-grid-heatmap',
    type: 'heatmap',
    source: 'air-quality-grid',
    layout: { visibility: 'visible' },
    paint: {
      'heatmap-weight': [
        'interpolate', ['linear'],
        ['coalesce', ['get', pollutant], 0],
        0,                0,
        t.good,           0.25,
        t.moderate,       0.5,
        t.unhealthy,      0.75,
        t.veryUnhealthy,  1.0,
      ],
      'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 8, 0.6, 14, 1.2],
      'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 8, 25, 12, 50, 16, 80],
      'heatmap-color': [
        'interpolate', ['linear'], ['heatmap-density'],
        0,    'rgba(0,228,0,0)',
        0.2,  '#00e400',   // green
        0.4,  '#ffff00',   // yellow
        0.6,  '#ff7e00',   // orange
        0.8,  '#ff0000',   // red
        1.0,  '#8f3f97',   // purple
      ],
      'heatmap-opacity': 0.5,
    },
  };
}

export default function AirQualityHeatmapLayer({ data, visible, activePollutant }: AirQualityHeatmapLayerProps) {
  const layerSpec = useMemo(() => buildHeatmapLayer(activePollutant), [activePollutant]);

  if (!data) return null;

  return (
    <Source id="air-quality-grid" type="geojson" data={data}>
      <Layer {...layerSpec} layout={{ ...layerSpec.layout, visibility: visibility(visible) }} />
    </Source>
  );
}
