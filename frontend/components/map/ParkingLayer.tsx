'use client';
import { Source, Layer } from 'react-map-gl/maplibre';
import type { CircleLayerSpecification, SymbolLayerSpecification } from 'react-map-gl/maplibre';
import { useLayerData } from '@/hooks/useLayerData';
import type { FeatureCollection } from 'geojson';

interface ParkingLayerProps {
  town: string;
  visible: boolean;
}

function filterByCategory(data: FeatureCollection, category: string): FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: data.features.filter(
      f => f.properties?.category === category
    ),
  };
}

const circleLayer: CircleLayerSpecification = {
  id: 'parking-points',
  type: 'circle',
  source: 'parking-features',
  layout: { visibility: 'visible' },
  paint: {
    'circle-color': [
      'step',
      ['get', 'occupancy_pct'],
      '#22c55e',  // green: occupancy < 50 (>50% free)
      50, '#eab308',  // yellow: occupancy 50-79 (20-50% free)
      80, '#ef4444',  // red: occupancy >= 80 (<20% free)
    ],
    'circle-radius': 10,
    'circle-stroke-width': 2,
    'circle-stroke-color': '#ffffff',
  },
};

const labelLayer: SymbolLayerSpecification = {
  id: 'parking-labels',
  type: 'symbol',
  source: 'parking-features',
  layout: {
    'text-field': ['to-string', ['get', 'free_spots']],
    'text-font': ['Noto Sans Regular'],
    'text-size': 11,
    'text-offset': [0, 1.5],
    'text-allow-overlap': false,
    visibility: 'visible',
  },
  paint: {
    'text-color': '#374151',
    'text-halo-color': '#ffffff',
    'text-halo-width': 1,
  },
};

export default function ParkingLayer({ town, visible }: ParkingLayerProps) {
  const { data } = useLayerData('infrastructure', town);

  if (!visible) return null;

  const parkingData: FeatureCollection = data
    ? filterByCategory(data as FeatureCollection, 'parking')
    : { type: 'FeatureCollection', features: [] };

  return (
    <Source
      id="parking-features"
      type="geojson"
      data={parkingData}
    >
      <Layer {...circleLayer} />
      <Layer {...labelLayer} />
    </Source>
  );
}
