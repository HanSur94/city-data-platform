'use client';
import { useMemo } from 'react';
import { Source, Layer } from 'react-map-gl/maplibre';
import type { LineLayerSpecification } from 'react-map-gl/maplibre';
import { useLayerData } from '@/hooks/useLayerData';
import type { FeatureCollection, Feature } from 'geojson';

interface BusRouteLayerProps {
  town: string;
  visible: boolean;
}

const emptyFC: FeatureCollection = { type: 'FeatureCollection', features: [] };

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
    'line-color': [
      'match',
      ['get', 'route_type_color'],
      'bus',   '#1565c0',
      'train', '#c62828',
      'tram',  '#2e7d32',
      '#9ca3af',  // fallback gray
    ] as unknown as string,
    'line-opacity': 0.35,
    'line-width': [
      'match',
      ['get', 'route_type_color'],
      'train', 3,
      'tram',  2.5,
      2,  // bus default
    ] as unknown as number,
  },
};

export default function BusRouteLayer({ town, visible }: BusRouteLayerProps) {
  const { data } = useLayerData('transit', town, undefined, 'shape');

  // Memoize filtered shapes so Source doesn't get a new data object on every
  // parent re-render — avoids unnecessary MapLibre setData() calls and flicker.
  const shapesData = useMemo(
    () => (data ? filterShapes(data as unknown as FeatureCollection) : emptyFC),
    [data],
  );

  const vis = visible ? 'visible' : 'none';

  return (
    <Source id="bus-routes" type="geojson" data={shapesData}>
      <Layer {...routeLineLayer} layout={{ ...routeLineLayer.layout, visibility: vis }} />
    </Source>
  );
}
