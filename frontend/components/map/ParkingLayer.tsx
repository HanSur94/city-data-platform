'use client';
import { useMemo } from 'react';
import { Source, Layer } from 'react-map-gl/maplibre';
import type { CircleLayerSpecification, SymbolLayerSpecification } from 'react-map-gl/maplibre';
import type { ExpressionSpecification } from 'maplibre-gl';
import { useLayerData } from '@/hooks/useLayerData';
import type { Feature, FeatureCollection, Point } from 'geojson';
import ColumnLayer from './ColumnLayer';
import { columnsFromPoints, spreadApproximate } from '@/lib/extrude';

interface ParkingLayerProps {
  town: string;
  visible: boolean;
  /** 3D mode: draw extruded columns instead of the flat circles + labels. */
  extruded?: boolean;
  /** Insert the columns beneath this layer (the first label layer). */
  beforeId?: string;
}

// Clicks on the columns open ParkingPopup (see MapView's layer-id chain).
export const PARKING_COLUMNS_LAYER_ID = 'parking-columns-3d';

// 3D tuning: round column, height grows with the free spots.
const PARKING_COLUMN_RADIUS_M = 30;
const PARKING_COLUMN_SIDES = 16;
// Two radii plus a 15 m gap: garages sharing an approximate position stand on a ring.
const PARKING_MIN_SEPARATION_M = 75;
const PARKING_COLUMN_BASE_M = 15;
const PARKING_COLUMN_M_PER_SPOT = 1.2;
const PARKING_COLUMN_MAX_M = 200;
const PARKING_COLUMN_OPACITY = 0.85;

// Occupancy colours of the flat circles (green < 50 %, yellow 50-79 %, red >= 80 %).
const PARKING_OCCUPANCY_COLOR: ExpressionSpecification = [
  'step',
  ['get', 'occupancy_pct'],
  '#22c55e',
  50, '#eab308',
  80, '#ef4444',
];

// Columns: occupancy colours when known, else blue (open) / grey (closed).
const PARKING_COLUMN_COLOR: ExpressionSpecification = [
  'case',
  ['==', ['typeof', ['get', 'occupancy_pct']], 'number'],
  PARKING_OCCUPANCY_COLOR,
  ['==', ['get', 'is_open'], false],
  '#9ca3af',
  '#3b82f6',
];

function parkingColumnHeight(properties: Record<string, unknown>): number {
  const free = properties.free_spots;
  if (typeof free !== 'number' || !Number.isFinite(free) || free < 0) return PARKING_COLUMN_BASE_M;
  return Math.min(PARKING_COLUMN_MAX_M, PARKING_COLUMN_BASE_M + PARKING_COLUMN_M_PER_SPOT * free);
}

function parkingSortKey(properties: Record<string, unknown>): string {
  return `${properties.garage_code ?? ''}|${properties.name ?? ''}`;
}

function filterByCategory(data: FeatureCollection, category: string): FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: data.features.filter(
      f => f.properties?.category === category
    ),
  };
}

const circleLayer: CircleLayerSpecification = {
  id: 'parking-points',
  type: 'circle',
  source: 'parking-features',
  layout: { visibility: 'visible' },
  paint: {
    'circle-color': PARKING_OCCUPANCY_COLOR,
    'circle-radius': 10,
    'circle-stroke-width': 2,
    'circle-stroke-color': '#ffffff',
  },
};

const labelLayer: SymbolLayerSpecification = {
  id: 'parking-labels',
  type: 'symbol',
  source: 'parking-features',
  layout: {
    'text-field': ['to-string', ['get', 'free_spots']],
    'text-font': ['Noto Sans Regular'],
    'text-size': 11,
    'text-offset': [0, 1.5],
    'text-allow-overlap': false,
    visibility: 'visible',
  },
  paint: {
    'text-color': '#374151',
    'text-halo-color': '#ffffff',
    'text-halo-width': 1,
  },
};

// Free-spot number in 3D mode: same layout and paint as the flat label. MapLibre places a
// symbol on a polygon at its interior point, i.e. at the column base.
const labelLayer3d: SymbolLayerSpecification = {
  ...labelLayer,
  id: 'parking-labels-3d',
  source: PARKING_COLUMNS_LAYER_ID + '-source',
};

export default function ParkingLayer({ town, visible, extruded = false, beforeId }: ParkingLayerProps) {
  const { data } = useLayerData('infrastructure', town);

  const parkingData = useMemo<FeatureCollection>(
    () =>
      data
        ? filterByCategory(data as FeatureCollection, 'parking')
        : { type: 'FeatureCollection', features: [] },
    [data],
  );
  const columns = useMemo(() => {
    if (!extruded) return null;
    const points = parkingData.features.filter(
      (f): f is Feature<Point, Record<string, unknown>> => f.geometry?.type === 'Point',
    );
    return columnsFromPoints(
      spreadApproximate(points, {
        flagProperty: 'location_approximate',
        minSeparationMeters: PARKING_MIN_SEPARATION_M,
        sortKey: parkingSortKey,
      }),
      {
        footprint: { radiusMeters: PARKING_COLUMN_RADIUS_M, sides: PARKING_COLUMN_SIDES },
        height: parkingColumnHeight,
      },
    );
  }, [extruded, parkingData]);

  if (!visible) return null;

  if (extruded) {
    return (
      <ColumnLayer
        id={PARKING_COLUMNS_LAYER_ID}
        data={columns}
        colorExpression={PARKING_COLUMN_COLOR}
        opacity={PARKING_COLUMN_OPACITY}
        beforeId={beforeId}
      >
        <Layer {...labelLayer3d} />
      </ColumnLayer>
    );
  }

  return (
    <Source
      id="parking-features"
      type="geojson"
      data={parkingData}
    >
      <Layer {...circleLayer} />
      <Layer {...labelLayer} />
    </Source>
  );
}
