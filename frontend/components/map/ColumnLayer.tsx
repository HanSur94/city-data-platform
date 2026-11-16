'use client';
import { useMemo } from 'react';
import type { ReactNode } from 'react';
import { Source, Layer } from 'react-map-gl/maplibre';
import type { ExpressionSpecification, FillExtrusionLayerSpecification } from 'maplibre-gl';
import type { FeatureCollection } from 'geojson';

interface ColumnLayerProps {
  /** Layer id; the source id is `${id}-source`. */
  id: string;
  /** Polygon features (see columnsFromPoints) or null while loading. */
  data: FeatureCollection | null;
  /** Feature property holding the extrusion height in metres. */
  heightProperty?: string;
  colorExpression: ExpressionSpecification | string;
  opacity?: number;
  /** Insert beneath this layer (the first label layer) so labels stay on top. */
  beforeId?: string;
  visible?: boolean;
  /** Extra layers that share the source (e.g. labels), rendered after the extrusion. */
  children?: ReactNode;
}

/**
 * Reusable extruded-polygon layer. fill-extrusion-base stays 0 so MapLibre keeps its
 * terrain basement and the columns stand on the terrain like buildings-3d.
 */
export default function ColumnLayer({
  id,
  data,
  heightProperty = 'height_m',
  colorExpression,
  opacity = 0.85,
  beforeId,
  visible = true,
  children,
}: ColumnLayerProps) {
  const paint = useMemo(
    (): NonNullable<FillExtrusionLayerSpecification['paint']> => ({
      'fill-extrusion-color': colorExpression,
      'fill-extrusion-height': ['get', heightProperty],
      'fill-extrusion-base': 0,
      'fill-extrusion-opacity': opacity,
      'fill-extrusion-vertical-gradient': true,
    }),
    [colorExpression, heightProperty, opacity],
  );

  if (!data) return null;

  return (
    <Source id={`${id}-source`} type="geojson" data={data}>
      <Layer
        id={id}
        type="fill-extrusion"
        paint={paint}
        layout={{ visibility: visible ? 'visible' : 'none' }}
        beforeId={beforeId}
      />
      {children}
    </Source>
  );
}
