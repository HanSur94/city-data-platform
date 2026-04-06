'use client';
import { Source, Layer } from 'react-map-gl/maplibre';
import type { LineLayerSpecification } from 'react-map-gl/maplibre';
import { useLayerData } from '@/hooks/useLayerData';
import type { FeatureCollection, Feature } from 'geojson';

interface BusRouteLayerProps {
  town: string;
  visible: boolean;
}

function filterShapes(data: FeatureCollection): FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: data.features.filter(
      (f: Feature) => f.properties?.feature_type === 'shape'
    ),
  };
}

const routeLineLayer: LineLayerSpecification = {
  id: 'bus-route-lines',
  type: 'line',
  source: 'bus-routes',
  layout: {
    visibility: 'visible',
    'line-cap': 'round',
    'line-join': 'round',
  },
  paint: {
    'line-color': '#6366f1',
    'line-opacity': 0.25,
    'line-width': 2,
  },
};

export default function BusRouteLayer({ town, visible }: BusRouteLayerProps) {
  const { data } = useLayerData('transit', town);

  if (!visible || !data) return null;

  const shapesData = filterShapes(data as unknown as FeatureCollection);

  return (
    <Source id="bus-routes" type="geojson" data={shapesData}>
      <Layer {...routeLineLayer} />
    </Source>
  );
}
