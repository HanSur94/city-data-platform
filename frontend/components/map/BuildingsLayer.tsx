'use client';
import { Layer } from 'react-map-gl/maplibre';
import type { FillExtrusionLayerSpecification } from 'maplibre-gl';

interface BuildingsLayerProps {
  visible: boolean;
}

const buildingsLayer: FillExtrusionLayerSpecification = {
  id: 'buildings-3d',
  type: 'fill-extrusion',
  source: 'protomaps',
  'source-layer': 'buildings',
  paint: {
    'fill-extrusion-color': '#d4c4a8',
    'fill-extrusion-height': [
      'coalesce',
      ['get', 'height'],
      10,
    ],
    'fill-extrusion-base': 0,
    'fill-extrusion-opacity': 0.7,
  },
  minzoom: 13,
};

export default function BuildingsLayer({ visible }: BuildingsLayerProps) {
  return (
    <Layer
      {...buildingsLayer}
      layout={{ visibility: visible ? 'visible' : 'none' }}
    />
  );
}
