'use client';
import { Source, Layer } from 'react-map-gl/maplibre';

interface FernwaermeLayerProps {
  visible: boolean;
}

/**
 * Hardcoded Fernwaerme (district heating) coverage polygons for known Aalen neighborhoods.
 * Provider: Stadtwerke Aalen.
 */
const FERNWAERME_GEOJSON: GeoJSON.FeatureCollection = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: { name: 'Schlossaecker', provider: 'Stadtwerke Aalen' },
      geometry: {
        type: 'Polygon',
        coordinates: [[
          [10.076, 48.841],
          [10.084, 48.841],
          [10.084, 48.845],
          [10.076, 48.845],
          [10.076, 48.841],
        ]],
      },
    },
    {
      type: 'Feature',
      properties: { name: 'Weisse Steige', provider: 'Stadtwerke Aalen' },
      geometry: {
        type: 'Polygon',
        coordinates: [[
          [10.091, 48.845],
          [10.099, 48.845],
          [10.099, 48.849],
          [10.091, 48.849],
          [10.091, 48.845],
        ]],
      },
    },
    {
      type: 'Feature',
      properties: { name: 'Maiergasse/Talschule', provider: 'Stadtwerke Aalen' },
      geometry: {
        type: 'Polygon',
        coordinates: [[
          [10.089, 48.836],
          [10.097, 48.836],
          [10.097, 48.840],
          [10.089, 48.840],
          [10.089, 48.836],
        ]],
      },
    },
    {
      type: 'Feature',
      properties: { name: 'Ostalbklinikum', provider: 'Stadtwerke Aalen' },
      geometry: {
        type: 'Polygon',
        coordinates: [[
          [10.074, 48.828],
          [10.082, 48.828],
          [10.082, 48.832],
          [10.074, 48.832],
          [10.074, 48.828],
        ]],
      },
    },
  ],
};

export default function FernwaermeLayer({ visible }: FernwaermeLayerProps) {
  if (!visible) return null;

  return (
    <Source id="fernwaerme-coverage" type="geojson" data={FERNWAERME_GEOJSON}>
      <Layer
        id="fernwaerme-fill"
        type="fill"
        paint={{
          'fill-color': 'rgba(255, 120, 50, 0.25)',
        }}
      />
      <Layer
        id="fernwaerme-outline"
        type="line"
        paint={{
          'line-color': 'rgba(255, 120, 50, 0.8)',
          'line-width': 2,
        }}
      />
    </Source>
  );
}
