'use client';
import { useMemo } from 'react';
import { Source, Layer } from 'react-map-gl/maplibre';
import type { CircleLayerSpecification } from 'react-map-gl/maplibre';
import type { ExpressionSpecification } from 'maplibre-gl';
import { useLayerData } from '@/hooks/useLayerData';
import type { FeatureCollection } from 'geojson';
import ColumnLayer from './ColumnLayer';
import { columnsFromPoints } from '@/lib/extrude';

interface EvChargingLiveLayerProps {
  town: string;
  visible: boolean;
  /** 3D mode: draw extruded columns instead of the flat status circles. */
  extruded?: boolean;
  /** Insert the columns beneath this layer (the first label layer). */
  beforeId?: string;
}

// Clicks on the columns open EvChargingPopup (see MapView's layer-id chain).
export const EV_CHARGING_COLUMNS_LAYER_ID = 'ev-charging-columns-3d';

// 3D tuning: hexagonal column, height grows with sqrt(power_kw).
const EV_COLUMN_RADIUS_M = 22;
const EV_COLUMN_SIDES = 6;
const EV_COLUMN_BASE_M = 15;
const EV_COLUMN_M_PER_SQRT_KW = 12;
const EV_COLUMN_MAX_M = 250;
const EV_COLUMN_OPACITY = 0.9;

// Shared by the flat circles and the columns so the colours are identical.
const EV_STATUS_COLOR: ExpressionSpecification = [
  'match',
  ['get', 'status'],
  'AVAILABLE', '#22c55e',
  'OCCUPIED', '#ef4444',
  'INOPERATIVE', '#9ca3af',
  '#9ca3af',
];

function filterOcpdb(data: FeatureCollection): FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: data.features.filter(
      f => f.properties?.source === 'ocpdb'
    ),
  };
}

function evColumnHeight(properties: Record<string, unknown>): number {
  const kw = properties.power_kw;
  if (typeof kw !== 'number' || !Number.isFinite(kw) || kw < 0) return EV_COLUMN_BASE_M;
  return Math.min(EV_COLUMN_MAX_M, EV_COLUMN_BASE_M + EV_COLUMN_M_PER_SQRT_KW * Math.sqrt(kw));
}

const evChargingLivePointsLayer: CircleLayerSpecification = {
  id: 'ev-charging-live-points',
  type: 'circle',
  source: 'ev-charging-live',
  layout: { visibility: 'visible' },
  paint: {
    'circle-color': EV_STATUS_COLOR,
    'circle-radius': [
      'interpolate',
      ['linear'],
      ['get', 'power_kw'],
      11, 6,
      22, 8,
      50, 10,
      150, 14,
    ],
    'circle-stroke-width': 2,
    'circle-stroke-color': '#ffffff',
  },
};

export const EV_CHARGING_LIVE_INTERACTIVE_LAYER_IDS = ['ev-charging-live-points'];

export default function EvChargingLiveLayer({
  town,
  visible,
  extruded = false,
  beforeId,
}: EvChargingLiveLayerProps) {
  const { data } = useLayerData('infrastructure', town);

  const ocpdbData = useMemo(
    () => (data ? filterOcpdb(data as FeatureCollection) : null),
    [data],
  );
  const columns = useMemo(
    () =>
      extruded && ocpdbData
        ? columnsFromPoints(ocpdbData.features, {
            footprint: { radiusMeters: EV_COLUMN_RADIUS_M, sides: EV_COLUMN_SIDES },
            height: evColumnHeight,
          })
        : null,
    [extruded, ocpdbData],
  );

  if (!visible || !ocpdbData) return null;

  if (extruded) {
    return (
      <ColumnLayer
        id={EV_CHARGING_COLUMNS_LAYER_ID}
        data={columns}
        colorExpression={EV_STATUS_COLOR}
        opacity={EV_COLUMN_OPACITY}
        beforeId={beforeId}
      />
    );
  }

  return (
    <Source
      id="ev-charging-live"
      type="geojson"
      data={ocpdbData}
    >
      <Layer {...evChargingLivePointsLayer} />
    </Source>
  );
}
