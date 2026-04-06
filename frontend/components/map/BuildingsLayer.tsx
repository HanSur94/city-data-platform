'use client';
import { Source, Layer } from 'react-map-gl/maplibre';
import type { FillExtrusionLayerSpecification } from 'maplibre-gl';

interface BuildingsLayerProps {
  visible: boolean;
}

const buildingsLayer: FillExtrusionLayerSpecification = {
  id: 'buildings-3d',
  type: 'fill-extrusion',
  source: 'openmaptiles',
  'source-layer': 'building',
  paint: {
    'fill-extrusion-color': '#d4c4a8',
    'fill-extrusion-height': [
      'coalesce',
      ['get', 'render_height'],
      10,
    ],
    'fill-extrusion-base': [
      'coalesce',
      ['get', 'render_min_height'],
      0,
    ],
    'fill-extrusion-opacity': 0.7,
  },
  minzoom: 14,
};

export default function BuildingsLayer({ visible }: BuildingsLayerProps) {
  if (!visible) return null;

  return (
    <Source
      id="openmaptiles"
      type="vector"
      url="https://tiles.openfreemap.org/planet"
    >
      <Layer {...buildingsLayer} />
    </Source>
  );
}
