'use client';
import { Source, Layer } from 'react-map-gl/maplibre';
import type { SymbolLayerSpecification } from 'react-map-gl/maplibre';
import { useLayerData } from '@/hooks/useLayerData';
import type { LayerResponse } from '@/types/geojson';
import type { Feature } from 'geojson';

interface AutobahnLayerProps {
  town: string;
  visible: boolean;
}

const visibility = (v: boolean): 'visible' | 'none' => (v ? 'visible' : 'none');

const autobahnSymbolLayer: SymbolLayerSpecification = {
  id: 'autobahn-markers',
  type: 'symbol',
  source: 'autobahn',
  layout: {
    'text-field': [
      'match',
      ['get', 'type'],
      'closure', '✗',
      '⚠',
    ],
    'text-size': 20,
    'text-allow-overlap': true,
    visibility: 'visible',
  },
  paint: {
    'text-color': [
      'match',
      ['get', 'type'],
      'closure', '#ef4444',
      '#f97316',
    ],
    'text-halo-color': '#ffffff',
    'text-halo-width': 2,
  },
};

function filterAutobahnFeatures(data: LayerResponse | null): LayerResponse | null {
  if (!data) return null;
  return {
    ...data,
    features: data.features.filter((f: Feature) => {
      const type = f.properties?.type as string | undefined;
      return type === 'roadwork' || type === 'closure';
    }),
  };
}

export default function AutobahnLayer({ town, visible }: AutobahnLayerProps) {
  const { data } = useLayerData('traffic', town);
  const filtered = filterAutobahnFeatures(data);
  if (!visible || !filtered) return null;
  const vis = visibility(visible);
  return (
    <Source id="autobahn" type="geojson" data={filtered}>
      <Layer
        {...autobahnSymbolLayer}
        layout={{ ...autobahnSymbolLayer.layout, visibility: vis }}
      />
    </Source>
  );
}
