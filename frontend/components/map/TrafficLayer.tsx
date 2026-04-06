'use client';
import { Source, Layer } from 'react-map-gl/maplibre';
import type { CircleLayerSpecification } from 'react-map-gl/maplibre';
import { useLayerData } from '@/hooks/useLayerData';
import type { LayerResponse } from '@/types/geojson';
import type { Feature } from 'geojson';

interface TrafficLayerProps {
  town: string;
  visible: boolean;
  timestamp?: Date | null;
}

const visibility = (v: boolean): 'visible' | 'none' => (v ? 'visible' : 'none');

const trafficCircleLayer: CircleLayerSpecification = {
  id: 'traffic-circles',
  type: 'circle',
  source: 'traffic',
  filter: ['!', ['in', ['get', 'type'], ['literal', ['roadwork', 'closure']]]],
  layout: { visibility: 'visible' },
  paint: {
    'circle-color': [
      'match',
      ['get', 'congestion_level'],
      'free', '#22c55e',
      'moderate', '#eab308',
      'congested', '#ef4444',
      '#9ca3af',
    ],
    'circle-radius': [
      'interpolate',
      ['linear'],
      ['coalesce', ['get', 'vehicle_count_total'], 0],
      0, 6,
      2000, 16,
    ],
    'circle-stroke-width': 1,
    'circle-stroke-color': '#ffffff',
  },
};

function filterTrafficFeatures(data: LayerResponse | null): LayerResponse | null {
  if (!data) return null;
  return {
    ...data,
    features: data.features.filter((f: Feature) => {
      const type = f.properties?.type as string | undefined;
      return type !== 'roadwork' && type !== 'closure';
    }),
  };
}

export default function TrafficLayer({ town, visible, timestamp }: TrafficLayerProps) {
  const { data } = useLayerData('traffic', town, timestamp);
  const filtered = filterTrafficFeatures(data);
  if (!visible || !filtered) return null;
  const vis = visibility(visible);
  return (
    <Source id="traffic" type="geojson" data={filtered}>
      <Layer
        {...trafficCircleLayer}
        layout={{ ...trafficCircleLayer.layout, visibility: vis }}
      />
    </Source>
  );
}
