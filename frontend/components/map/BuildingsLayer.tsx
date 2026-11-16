'use client';
import { useMemo } from 'react';
import { Layer } from 'react-map-gl/maplibre';
import type { ExpressionSpecification, FillExtrusionLayerSpecification } from 'maplibre-gl';
import { BUILDING_PALETTES, PROTOMAPS_SOURCE_ID } from '@/lib/map-styles';
import type { BaseLayer } from '@/lib/map-styles';

interface BuildingsLayerProps {
  visible: boolean;
  baseLayer: BaseLayer;
  /** Insert beneath this layer (the first label layer) so labels stay on top. */
  beforeId?: string;
}

// Layer id is listed in MapView's interactiveLayerIds and drives UnifiedBuildingPopup.
const BUILDINGS_LAYER_ID = 'buildings-3d';
const DEFAULT_HEIGHT = 9;

export default function BuildingsLayer({ visible, baseLayer, beforeId }: BuildingsLayerProps) {
  const paint = useMemo((): NonNullable<FillExtrusionLayerSpecification['paint']> => {
    const palette = BUILDING_PALETTES[baseLayer];
    const height: ExpressionSpecification = ['coalesce', ['get', 'height'], DEFAULT_HEIGHT];
    const color: ExpressionSpecification = [
      'interpolate',
      ['linear'],
      height,
      ...palette.stops.flatMap(([h, c]) => [h, c]),
    ] as ExpressionSpecification;
    return {
      'fill-extrusion-color': color,
      'fill-extrusion-height': height,
      'fill-extrusion-base': ['coalesce', ['get', 'min_height'], 0],
      'fill-extrusion-opacity': ['interpolate', ['linear'], ['zoom'], 13, 0, 14, palette.opacity],
      'fill-extrusion-vertical-gradient': true,
    };
  }, [baseLayer]);

  return (
    <Layer
      id={BUILDINGS_LAYER_ID}
      type="fill-extrusion"
      source={PROTOMAPS_SOURCE_ID}
      source-layer="buildings"
      minzoom={13}
      paint={paint}
      layout={{ visibility: visible ? 'visible' : 'none' }}
      beforeId={beforeId}
    />
  );
}
