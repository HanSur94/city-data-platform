'use client';
import { Source, Layer } from 'react-map-gl/maplibre';
import type { CircleLayerSpecification } from 'react-map-gl/maplibre';
import { useLayerData } from '@/hooks/useLayerData';
import type { FeatureCollection } from 'geojson';

interface EvChargingLiveLayerProps {
  town: string;
  visible: boolean;
}

function filterOcpdb(data: FeatureCollection): FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: data.features.filter(
      f => f.properties?.source === 'ocpdb'
    ),
  };
}

const evChargingLivePointsLayer: CircleLayerSpecification = {
  id: 'ev-charging-live-points',
  type: 'circle',
  source: 'ev-charging-live',
  layout: { visibility: 'visible' },
  paint: {
    'circle-color': [
      'match',
      ['get', 'status'],
      'AVAILABLE', '#22c55e',
      'OCCUPIED', '#ef4444',
      'INOPERATIVE', '#9ca3af',
      '#9ca3af',
    ],
    'circle-radius': [
      'interpolate',
      ['linear'],
      ['get', 'power_kw'],
      11, 6,
      22, 8,
      50, 10,
      150, 14,
    ],
    'circle-stroke-width': 2,
    'circle-stroke-color': '#ffffff',
  },
};

export const EV_CHARGING_LIVE_INTERACTIVE_LAYER_IDS = ['ev-charging-live-points'];

export default function EvChargingLiveLayer({ town, visible }: EvChargingLiveLayerProps) {
  const { data } = useLayerData('infrastructure', town);
  if (!visible || !data) return null;

  const ocpdbData = filterOcpdb(data as FeatureCollection);

  return (
    <Source
      id="ev-charging-live"
      type="geojson"
      data={ocpdbData}
    >
      <Layer {...evChargingLivePointsLayer} />
    </Source>
  );
}
