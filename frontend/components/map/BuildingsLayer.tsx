'use client';
import { Layer } from 'react-map-gl/maplibre';
import type { FillExtrusionLayerSpecification } from 'maplibre-gl';

interface BuildingsLayerProps {
  visible: boolean;
}

export default function BuildingsLayer({ visible }: BuildingsLayerProps) {
  // Protomaps PMTiles includes 'buildings' source-layer with 'height' property from OSM
  // fill-extrusion renders 3D building volumes
  const layerSpec: FillExtrusionLayerSpecification = {
    id: 'buildings-3d',
    type: 'fill-extrusion',
    source: 'protomaps',
    'source-layer': 'buildings',
    paint: {
      'fill-extrusion-color': '#d4c4a8',
      'fill-extrusion-height': [
        'coalesce',
        ['get', 'height'],
        10, // Default 10m for buildings without height data
      ],
      'fill-extrusion-base': 0,
      'fill-extrusion-opacity': visible ? 0.7 : 0,
    },
    minzoom: 14,
  };

  return <Layer {...layerSpec} />;
}
