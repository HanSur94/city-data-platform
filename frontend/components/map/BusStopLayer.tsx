'use client';
import { Source, Layer } from 'react-map-gl/maplibre';
import type { CircleLayerSpecification } from 'react-map-gl/maplibre';
import { useLayerData } from '@/hooks/useLayerData';
import type { FeatureCollection, Feature } from 'geojson';
import { useMemo } from 'react';

interface BusStopLayerProps {
  town: string;
  visible: boolean;
}

const emptyFC: FeatureCollection = { type: 'FeatureCollection', features: [] };

function filterStops(data: FeatureCollection): FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: data.features.filter(
      (f: Feature) => f.properties?.feature_type === 'stop',
    ),
  };
}

const stopCircleLayer: CircleLayerSpecification = {
  id: 'bus-stop-points',
  type: 'circle',
  source: 'bus-stops',
  paint: {
    'circle-radius': 4,
    'circle-color': '#9ca3af',
    'circle-stroke-width': 1.5,
    'circle-stroke-color': '#ffffff',
  },
};

export default function BusStopLayer({ town, visible }: BusStopLayerProps) {
  const { data } = useLayerData('transit', town, undefined, 'stop');

  const stopsData = useMemo(
    () => (data ? filterStops(data as unknown as FeatureCollection) : emptyFC),
    [data],
  );

  const vis = visible ? 'visible' : 'none';

  return (
    <Source id="bus-stops" type="geojson" data={stopsData}>
      <Layer {...stopCircleLayer} layout={{ visibility: vis }} />
    </Source>
  );
}
