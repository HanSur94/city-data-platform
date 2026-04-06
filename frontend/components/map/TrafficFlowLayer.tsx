'use client';
import { Source, Layer } from 'react-map-gl/maplibre';
import type { LineLayerSpecification } from 'react-map-gl/maplibre';
import { useLayerData } from '@/hooks/useLayerData';
import type { LayerResponse } from '@/types/geojson';
import type { Feature } from 'geojson';

interface TrafficFlowLayerProps {
  town: string;
  visible: boolean;
  timestamp?: Date | null;
}

function filterTomTomFeatures(data: LayerResponse | null): LayerResponse | null {
  if (!data) return null;
  return {
    ...data,
    features: data.features.filter((f: Feature) =>
      f.properties?.data_source === 'TomTom' && f.geometry?.type === 'LineString'
    ),
  };
}

const trafficFlowLineLayer: LineLayerSpecification = {
  id: 'traffic-flow-lines',
  type: 'line',
  source: 'traffic-flow',
  layout: {
    visibility: 'visible',
    'line-cap': 'round',
    'line-join': 'round',
  },
  paint: {
    'line-color': [
      'interpolate',
      ['linear'],
      ['coalesce', ['get', 'congestion_ratio'], 1],
      0, '#ef4444',
      0.25, '#ef4444',
      0.26, '#f97316',
      0.50, '#f97316',
      0.51, '#eab308',
      0.75, '#eab308',
      0.76, '#22c55e',
      1.0, '#22c55e',
    ],
    'line-width': [
      'interpolate',
      ['linear'],
      ['zoom'],
      10, 2,
      14, 5,
      18, 8,
    ],
    'line-opacity': 0.85,
  },
};

export default function TrafficFlowLayer({ town, visible, timestamp }: TrafficFlowLayerProps) {
  const { data } = useLayerData('traffic', town, timestamp);
  const filtered = filterTomTomFeatures(data);
  if (!visible || !filtered) return null;
  return (
    <Source id="traffic-flow" type="geojson" data={filtered}>
      <Layer
        {...trafficFlowLineLayer}
        layout={{ ...trafficFlowLineLayer.layout, visibility: visible ? 'visible' : 'none' }}
      />
    </Source>
  );
}
