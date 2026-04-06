'use client';
import { Source, Layer } from 'react-map-gl/maplibre';
import type { CircleLayerSpecification, SymbolLayerSpecification } from 'react-map-gl/maplibre';
import { useLayerData } from '@/hooks/useLayerData';

interface EnergyLayerProps {
  town: string;
  visible: boolean;
}

const visibility = (v: boolean): 'visible' | 'none' => (v ? 'visible' : 'none');

const clusterLayer: CircleLayerSpecification = {
  id: 'energy-clusters',
  type: 'circle',
  source: 'energy',
  filter: ['has', 'point_count'],
  layout: { visibility: 'visible' },
  paint: {
    'circle-color': '#f59e0b',
    'circle-radius': 14,
    'circle-stroke-width': 1,
    'circle-stroke-color': '#ffffff',
  },
};

const clusterCountLayer: SymbolLayerSpecification = {
  id: 'energy-cluster-count',
  type: 'symbol',
  source: 'energy',
  filter: ['has', 'point_count'],
  layout: {
    'text-field': '{point_count_abbreviated}',
    'text-font': ['Noto Sans Regular'],
    'text-size': 12,
    visibility: 'visible',
  },
};

const energyPointsLayer: CircleLayerSpecification = {
  id: 'energy-points',
  type: 'circle',
  source: 'energy',
  filter: ['!', ['has', 'point_count']],
  layout: { visibility: 'visible' },
  paint: {
    'circle-color': [
      'match',
      ['get', 'installation_type'],
      'solar_rooftop', '#f59e0b',
      'solar_ground', '#eab308',
      'wind', '#3b82f6',
      'battery', '#22c55e',
      '#9ca3af',
    ],
    'circle-radius': 7,
    'circle-stroke-width': 1,
    'circle-stroke-color': '#ffffff',
  },
};

export default function EnergyLayer({ town, visible }: EnergyLayerProps) {
  const { data } = useLayerData('energy', town);
  if (!visible || !data) return null;
  const vis = visibility(visible);
  return (
    <Source
      id="energy"
      type="geojson"
      data={data}
      cluster={true}
      clusterMaxZoom={10}
      clusterRadius={50}
    >
      <Layer
        {...clusterLayer}
        layout={{ ...clusterLayer.layout, visibility: vis }}
      />
      <Layer
        {...clusterCountLayer}
        layout={{ ...clusterCountLayer.layout, visibility: vis }}
      />
      <Layer
        {...energyPointsLayer}
        layout={{ ...energyPointsLayer.layout, visibility: vis }}
      />
    </Source>
  );
}
