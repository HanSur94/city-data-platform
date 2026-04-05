'use client';
import { Source, Layer } from 'react-map-gl/maplibre';
import type { CircleLayerSpecification, SymbolLayerSpecification } from 'react-map-gl/maplibre';
import type { LayerResponse } from '@/types/geojson';

interface TransitLayerProps {
  data: LayerResponse | null;
  visible: boolean;
}

const visibility = (v: boolean): 'visible' | 'none' => v ? 'visible' : 'none';

const clusterLayer: CircleLayerSpecification = {
  id: 'transit-clusters',
  type: 'circle',
  source: 'transit',
  filter: ['has', 'point_count'],
  layout: { visibility: 'visible' },
  paint: {
    'circle-color': '#f4f5f7',
    'circle-radius': 12,
    'circle-stroke-width': 1,
    'circle-stroke-color': '#9ca3af',
  },
};

const clusterCountLayer: SymbolLayerSpecification = {
  id: 'transit-cluster-count',
  type: 'symbol',
  source: 'transit',
  filter: ['has', 'point_count'],
  layout: {
    'text-field': '{point_count_abbreviated}',
    'text-font': ['Noto Sans Regular'],
    'text-size': 12,
    visibility: 'visible',
  },
};

const unclusteredStopLayer: CircleLayerSpecification = {
  id: 'transit-stops',
  type: 'circle',
  source: 'transit',
  filter: ['!', ['has', 'point_count']],
  layout: { visibility: 'visible' },
  paint: {
    'circle-radius': 4,
    'circle-stroke-width': 1,
    'circle-stroke-color': '#ffffff',
    'circle-color': [
      'match',
      ['get', 'route_type_color'],
      'bus',   '#1565c0',
      'train', '#c62828',
      'tram',  '#2e7d32',
      '#9ca3af',
    ],
  },
};

export default function TransitLayer({ data, visible }: TransitLayerProps) {
  if (!data) return null;
  const vis = visibility(visible);
  return (
    <Source
      id="transit"
      type="geojson"
      data={data}
      cluster={true}
      clusterMaxZoom={13}
      clusterRadius={40}
    >
      <Layer {...clusterLayer} layout={{ ...clusterLayer.layout, visibility: vis }} />
      <Layer {...clusterCountLayer} layout={{ ...clusterCountLayer.layout, visibility: vis }} />
      <Layer {...unclusteredStopLayer} layout={{ ...unclusteredStopLayer.layout, visibility: vis }} />
    </Source>
  );
}
