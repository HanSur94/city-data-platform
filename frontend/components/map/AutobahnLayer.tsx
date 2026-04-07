'use client';
import { useEffect } from 'react';
import { Source, Layer, useMap } from 'react-map-gl/maplibre';
import type {
  CircleLayerSpecification,
  SymbolLayerSpecification,
} from 'react-map-gl/maplibre';
import { useLayerData } from '@/hooks/useLayerData';
import type { LayerResponse } from '@/types/geojson';
import type { Feature } from 'geojson';

interface AutobahnLayerProps {
  town: string;
  visible: boolean;
}

const visibility = (v: boolean): 'visible' | 'none' => (v ? 'visible' : 'none');

// Background circle — orange for roadworks, red for closures
const circleLayer: CircleLayerSpecification = {
  id: 'autobahn-markers-bg',
  type: 'circle',
  source: 'autobahn',
  paint: {
    'circle-radius': 14,
    'circle-color': [
      'match',
      ['get', 'type'],
      'closure', '#ef4444',
      '#f97316',
    ],
    'circle-stroke-width': 2.5,
    'circle-stroke-color': '#ffffff',
  },
};

// Icon symbol on top of circle — construction/closure icons
const symbolLayer: SymbolLayerSpecification = {
  id: 'autobahn-markers',
  type: 'symbol',
  source: 'autobahn',
  layout: {
    'text-field': [
      'match',
      ['get', 'type'],
      'closure', '✕',
      '🔧',
    ],
    'text-size': [
      'match',
      ['get', 'type'],
      'closure', 14,
      12,
    ],
    'text-allow-overlap': true,
    visibility: 'visible',
  },
  paint: {
    'text-color': '#ffffff',
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
        {...circleLayer}
        layout={{ visibility: vis }}
      />
      <Layer
        {...symbolLayer}
        layout={{ ...symbolLayer.layout, visibility: vis }}
      />
    </Source>
  );
}
