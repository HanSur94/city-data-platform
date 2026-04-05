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
    'heatmap-weight': ['interpolate', ['linear'], ['get', 'aqi'], 0, 0, 80, 1],
    'heatmap-intensity': 0.8,
    'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 10, 20, 14, 40],
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

// Transparent click-target circles — REQUIRED because heatmap layers don't fire click events (Pitfall 4)
const aqiPointLayer: CircleLayerSpecification = {
  id: 'aqi-points',
  type: 'circle',
  source: 'air-quality',
  layout: { visibility: 'visible' },
  paint: {
    'circle-radius': 8,
    'circle-color': 'rgba(0,0,0,0)',
  },
};

export default function AQILayer({ data, visible }: AQILayerProps) {
  if (!data) return null;
  const vis = visibility(visible);
  return (
    <Source id="air-quality" type="geojson" data={data}>
      <Layer {...aqiHeatmapLayer} layout={{ ...aqiHeatmapLayer.layout, visibility: vis }} />
      <Layer {...aqiPointLayer} layout={{ ...aqiPointLayer.layout, visibility: vis }} />
    </Source>
  );
}
