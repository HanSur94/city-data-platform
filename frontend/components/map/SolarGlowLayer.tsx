'use client';
import { Source, Layer } from 'react-map-gl/maplibre';
import type { CircleLayerSpecification } from 'react-map-gl/maplibre';
import { useLayerData } from '@/hooks/useLayerData';
import type { FeatureCollection } from 'geojson';

interface SolarGlowLayerProps {
  town: string;
  visible: boolean;
}

function filterSolar(data: FeatureCollection): FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: data.features.filter(
      f => {
        const t = f.properties?.installation_type as string | undefined;
        return t != null && t.startsWith('solar_');
      }
    ),
  };
}

const solarGlowPointsLayer: CircleLayerSpecification = {
  id: 'solar-glow-points',
  type: 'circle',
  source: 'solar-glow',
  layout: { visibility: 'visible' },
  paint: {
    'circle-color': [
      'interpolate',
      ['linear'],
      ['get', 'current_output_kw'],
      0, '#6b7280',
      0.1, '#fbbf24',
      5, '#fbbf24',
      20, '#f59e0b',
      50, '#ef4444',
    ],
    'circle-radius': [
      'interpolate',
      ['linear'],
      ['get', 'current_output_kw'],
      0, 4,
      10, 8,
      50, 14,
      200, 20,
    ],
    'circle-opacity': 0.8,
    'circle-blur': 0.4,
    'circle-stroke-width': 0,
  },
};

export const SOLAR_GLOW_INTERACTIVE_LAYER_IDS = ['solar-glow-points'];

export default function SolarGlowLayer({ town, visible }: SolarGlowLayerProps) {
  const { data } = useLayerData('energy', town);
  if (!visible || !data) return null;

  const solarData = filterSolar(data as FeatureCollection);

  return (
    <Source
      id="solar-glow"
      type="geojson"
      data={solarData}
    >
      <Layer {...solarGlowPointsLayer} />
    </Source>
  );
}
