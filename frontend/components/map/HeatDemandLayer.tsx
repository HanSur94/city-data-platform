'use client';
import { Source, Layer } from 'react-map-gl/maplibre';
import type { CircleLayerSpecification } from 'react-map-gl/maplibre';
import { useLayerData } from '@/hooks/useLayerData';
import type { LayerResponse } from '@/types/geojson';
import type { Feature } from 'geojson';

interface HeatDemandLayerProps {
  town: string;
  visible: boolean;
}

function filterHeatDemandFeatures(data: LayerResponse | null): LayerResponse | null {
  if (!data) return null;
  return {
    ...data,
    features: data.features.filter((f: Feature) =>
      f.properties?.feature_type === 'heat_demand'
    ),
  };
}

const HEAT_CLASS_COLORS: Record<string, string> = {
  blue: '#2166ac',
  light_blue: '#67a9cf',
  green: '#5aae61',
  yellow: '#fee08b',
  orange: '#f46d43',
  red: '#d73027',
};

const heatDemandCircleLayer: CircleLayerSpecification = {
  id: 'heat-demand-points',
  type: 'circle',
  source: 'heat-demand',
  layout: { visibility: 'visible' },
  paint: {
    'circle-color': [
      'match',
      ['get', 'heat_class'],
      'blue', HEAT_CLASS_COLORS.blue,
      'light_blue', HEAT_CLASS_COLORS.light_blue,
      'green', HEAT_CLASS_COLORS.green,
      'yellow', HEAT_CLASS_COLORS.yellow,
      'orange', HEAT_CLASS_COLORS.orange,
      'red', HEAT_CLASS_COLORS.red,
      '#999999', // fallback
    ],
    'circle-radius': [
      'interpolate',
      ['linear'],
      ['zoom'],
      10, 3,
      14, 8,
      18, 14,
    ],
    'circle-stroke-width': 1,
    'circle-stroke-color': '#ffffff',
    'circle-opacity': 0.85,
  },
};

export default function HeatDemandLayer({ town, visible }: HeatDemandLayerProps) {
  const { data } = useLayerData('energy', town);
  const filtered = filterHeatDemandFeatures(data);
  if (!visible || !filtered) return null;
  return (
    <Source id="heat-demand" type="geojson" data={filtered}>
      <Layer {...heatDemandCircleLayer} />
    </Source>
  );
}
