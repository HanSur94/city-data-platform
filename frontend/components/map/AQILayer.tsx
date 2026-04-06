'use client';
import { Source, Layer } from 'react-map-gl/maplibre';
import type { HeatmapLayerSpecification, CircleLayerSpecification } from 'react-map-gl/maplibre';
import type { LayerResponse } from '@/types/geojson';

interface AQILayerProps {
  data: LayerResponse | null;
  visible: boolean;
}

const visibility = (v: boolean): 'visible' | 'none' => v ? 'visible' : 'none';

const aqiHeatmapLayer: HeatmapLayerSpecification = {
  id: 'aqi-heatmap',
  type: 'heatmap',
  source: 'air-quality',
  layout: { visibility: 'visible' },
  paint: {
    'heatmap-weight': ['interpolate', ['linear'], ['get', 'aqi_tier_index'], 0, 0, 5, 1],
    'heatmap-intensity': 0.8,
    'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 10, 20, 14, 40],
    'heatmap-color': [
      'interpolate', ['linear'], ['heatmap-density'],
      0,   'rgba(80,240,230,0)',
      0.2, '#50F0E6',
      0.4, '#50CCAA',
      0.6, '#F0E641',
      0.8, '#FF5050',
      0.9, '#960032',
      1.0, '#7D2181',
    ],
    'heatmap-opacity': 0.8,
  },
};

// Pulsing glow ring behind sensor dots — larger, translucent for pulse effect (REQ-AIR-04)
const aqiPulseRingLayer: CircleLayerSpecification = {
  id: 'aqi-pulse-ring',
  type: 'circle',
  source: 'air-quality',
  layout: { visibility: 'visible' },
  paint: {
    'circle-radius': ['interpolate', ['linear'], ['zoom'], 10, 12, 14, 20],
    'circle-color': ['get', 'aqi_color'],
    'circle-opacity': 0.3,
    'circle-blur': 0.6,
  },
};

// Colored EEA EAQI circles — color driven by aqi_color property from backend
const aqiColorLayer: CircleLayerSpecification = {
  id: 'aqi-circles',
  type: 'circle',
  source: 'air-quality',
  layout: { visibility: 'visible' },
  paint: {
    'circle-radius': 8,
    'circle-color': ['get', 'aqi_color'],
    'circle-opacity': 0.85,
    'circle-stroke-width': 2,
    'circle-stroke-color': '#ffffff',
    'circle-blur': 0.4,
  },
};

// Transparent click-target circles — REQUIRED because heatmap layers don't fire click events
const aqiPointLayer: CircleLayerSpecification = {
  id: 'aqi-points',
  type: 'circle',
  source: 'air-quality',
  layout: { visibility: 'visible' },
  paint: {
    'circle-radius': 12,
    'circle-color': 'rgba(0,0,0,0)',
  },
};

export default function AQILayer({ data, visible }: AQILayerProps) {
  if (!data) return null;
  const vis = visibility(visible);
  return (
    <Source id="air-quality" type="geojson" data={data}>
      <Layer {...aqiHeatmapLayer} layout={{ ...aqiHeatmapLayer.layout, visibility: vis }} />
      <Layer {...aqiPulseRingLayer} layout={{ ...aqiPulseRingLayer.layout, visibility: vis }} />
      <Layer {...aqiColorLayer} layout={{ ...aqiColorLayer.layout, visibility: vis }} />
      <Layer {...aqiPointLayer} layout={{ ...aqiPointLayer.layout, visibility: vis }} />
    </Source>
  );
}
