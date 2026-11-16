'use client';
import { useMemo } from 'react';
import { Source, Layer } from 'react-map-gl/maplibre';
import type { CircleLayerSpecification } from 'react-map-gl/maplibre';
import type { ExpressionSpecification } from 'maplibre-gl';
import { useLayerData } from '@/hooks/useLayerData';
import type { LayerResponse } from '@/types/geojson';
import type { Feature } from 'geojson';
import ColumnLayer from './ColumnLayer';
import { columnsFromPoints } from '@/lib/extrude';

interface HeatDemandLayerProps {
  town: string;
  visible: boolean;
  /** 3D mode: draw extruded columns instead of the flat circles. */
  extruded?: boolean;
  /** Insert the columns beneath this layer (the first label layer). */
  beforeId?: string;
}

// Clicks on the columns open HeatDemandPopup (see MapView's layer-id chain).
export const HEAT_DEMAND_COLUMNS_LAYER_ID = 'heat-demand-columns-3d';

// 3D tuning: axis-aligned square of the building's floor area, height = demand.
const HEAT_COLUMN_MIN_RADIUS_M = 8;
const HEAT_COLUMN_MAX_RADIUS_M = 25;
const HEAT_COLUMN_M_PER_KWH = 0.6;
const HEAT_COLUMN_MIN_M = 5;
const HEAT_COLUMN_MAX_M = 400;
const HEAT_COLUMN_OPACITY = 0.85;

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

// A square with centre-to-corner radius r has area 2 r^2, so r = sqrt(area_m2 / 2) gives a
// square of the building's floor area.
function heatColumnRadius(properties: Record<string, unknown>): number {
  const area = properties.area_m2;
  if (typeof area !== 'number' || !Number.isFinite(area) || area <= 0) return HEAT_COLUMN_MIN_RADIUS_M;
  return clamp(Math.sqrt(area / 2), HEAT_COLUMN_MIN_RADIUS_M, HEAT_COLUMN_MAX_RADIUS_M);
}

function heatColumnHeight(properties: Record<string, unknown>): number {
  const kwh = properties.heat_demand_kwh_m2_y;
  if (typeof kwh !== 'number' || !Number.isFinite(kwh)) return HEAT_COLUMN_MIN_M;
  return clamp(HEAT_COLUMN_M_PER_KWH * kwh, HEAT_COLUMN_MIN_M, HEAT_COLUMN_MAX_M);
}

function filterHeatDemandFeatures(data: LayerResponse | null): LayerResponse | null {
  if (!data) return null;
  return {
    ...data,
    features: data.features.filter((f: Feature) =>
      f.properties?.feature_type === 'heat_demand'
    ),
  };
}

const HEAT_CLASS_COLORS: Record<string, string> = {
  blue: '#2166ac',
  light_blue: '#67a9cf',
  green: '#5aae61',
  yellow: '#fee08b',
  orange: '#f46d43',
  red: '#d73027',
};

// Shared by the flat circles and the columns so the colours are identical.
const HEAT_CLASS_COLOR: ExpressionSpecification = [
  'match',
  ['get', 'heat_class'],
  'blue', HEAT_CLASS_COLORS.blue,
  'light_blue', HEAT_CLASS_COLORS.light_blue,
  'green', HEAT_CLASS_COLORS.green,
  'yellow', HEAT_CLASS_COLORS.yellow,
  'orange', HEAT_CLASS_COLORS.orange,
  'red', HEAT_CLASS_COLORS.red,
  '#999999', // fallback
];

const heatDemandCircleLayer: CircleLayerSpecification = {
  id: 'heat-demand-points',
  type: 'circle',
  source: 'heat-demand',
  layout: { visibility: 'visible' },
  paint: {
    'circle-color': HEAT_CLASS_COLOR,
    'circle-radius': [
      'interpolate',
      ['linear'],
      ['zoom'],
      10, 3,
      14, 8,
      18, 14,
    ],
    'circle-stroke-width': 1,
    'circle-stroke-color': '#ffffff',
    'circle-opacity': 0.85,
  },
};

export default function HeatDemandLayer({ town, visible, extruded = false, beforeId }: HeatDemandLayerProps) {
  const { data } = useLayerData('energy', town);
  const filtered = useMemo(() => filterHeatDemandFeatures(data), [data]);
  const columns = useMemo(
    () =>
      extruded && filtered
        ? columnsFromPoints(filtered.features, {
            footprint: { radiusMeters: heatColumnRadius, sides: 4, rotationDeg: 45 },
            height: heatColumnHeight,
          })
        : null,
    [extruded, filtered],
  );

  if (!visible || !filtered) return null;

  if (extruded) {
    return (
      <ColumnLayer
        id={HEAT_DEMAND_COLUMNS_LAYER_ID}
        data={columns}
        colorExpression={HEAT_CLASS_COLOR}
        opacity={HEAT_COLUMN_OPACITY}
        beforeId={beforeId}
      />
    );
  }

  return (
    <Source id="heat-demand" type="geojson" data={filtered}>
      <Layer {...heatDemandCircleLayer} />
    </Source>
  );
}
