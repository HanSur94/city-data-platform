'use client';
import { Source, Layer } from 'react-map-gl/maplibre';
import type { CircleLayerSpecification, SymbolLayerSpecification } from 'react-map-gl/maplibre';
import { useLayerData } from '@/hooks/useLayerData';
import type { FeatureCollection, Feature } from 'geojson';
import { useMemo } from 'react';

interface PoliceLayerProps {
  town: string;
  visible: boolean;
}

const emptyFC: FeatureCollection = { type: 'FeatureCollection', features: [] };

function filterPolice(data: FeatureCollection): FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: data.features.filter(
      (f: Feature) => f.properties?.feature_type === 'police_report',
    ),
  };
}

const circleLayer: CircleLayerSpecification = {
  id: 'police-reports-bg',
  type: 'circle',
  source: 'police-reports',
  paint: {
    'circle-radius': 12,
    'circle-color': '#1d4ed8',
    'circle-stroke-width': 2,
    'circle-stroke-color': '#ffffff',
  },
};

const symbolLayer: SymbolLayerSpecification = {
  id: 'police-reports-icon',
  type: 'symbol',
  source: 'police-reports',
  layout: {
    'text-field': '!',
    'text-size': 14,
    'text-allow-overlap': true,
    'text-font': ['Noto Sans Bold'],
    visibility: 'visible',
  },
  paint: {
    'text-color': '#ffffff',
  },
};

export default function PoliceLayer({ town, visible }: PoliceLayerProps) {
  const { data } = useLayerData('police', town);

  const policeData = useMemo(
    () => (data ? filterPolice(data as unknown as FeatureCollection) : emptyFC),
    [data],
  );

  const vis = visible ? 'visible' : 'none';

  return (
    <Source id="police-reports" type="geojson" data={policeData}>
      <Layer {...circleLayer} layout={{ visibility: vis }} />
      <Layer {...symbolLayer} layout={{ ...symbolLayer.layout, visibility: vis }} />
    </Source>
  );
}
