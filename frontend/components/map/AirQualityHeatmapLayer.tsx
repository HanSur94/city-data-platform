'use client';
import { useMemo } from 'react';
import { Source, Layer } from 'react-map-gl/maplibre';
import type { HeatmapLayerSpecification } from 'react-map-gl/maplibre';
import type { Feature, FeatureCollection, Point } from 'geojson';
import type { LayerResponse } from '@/types/geojson';
import { EAQI_BREAKPOINTS, eaqiColorExpression } from '@/lib/map-styles';
import { cellFromPoint, columnsFromPoints, gridSpacing } from '@/lib/extrude';
import ColumnLayer from './ColumnLayer';

export type Pollutant = 'pm25' | 'pm10' | 'no2' | 'o3';

interface AirQualityHeatmapLayerProps {
  data: LayerResponse | null;
  visible: boolean;
  activePollutant: Pollutant;
  /** 3D mode: draw the grid as extruded EAQI cells instead of the heatmap. */
  extruded?: boolean;
  /** Insert the cells beneath this layer (the first label layer). */
  beforeId?: string;
}

// Cells are not clickable (the sensor popup does not fit a grid cell, see MapView), so this
// id is deliberately absent from MapView's interactiveLayerIds.
export const AIR_QUALITY_CELLS_LAYER_ID = 'air-quality-cells-3d';

// 3D tuning: cell size is the measured grid spacing times the inset (leaves a small gap).
// Slender bars, not tiles: at 0.92 the field is a solid slab that hides the city beneath.
const AIR_CELL_INSET = 0.3;
const AIR_CELL_BASE_M = 10;
// Height at the top of the EAQI 'moderate' band of the pollutant.
const AIR_CELL_MODERATE_TOP_M = 500;
const AIR_CELL_MAX_M = 1500;
const AIR_CELL_OPACITY = 0.75;

const POLLUTANTS: readonly Pollutant[] = ['pm25', 'pm10', 'no2', 'o3'];

function airCellHeight(pollutant: Pollutant, value: unknown): number {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) return AIR_CELL_BASE_M;
  const moderateTop = EAQI_BREAKPOINTS[pollutant][2];
  return Math.min(
    AIR_CELL_MAX_M,
    AIR_CELL_BASE_M + (value * (AIR_CELL_MODERATE_TOP_M - AIR_CELL_BASE_M)) / moderateTop,
  );
}

function buildAirCells(data: LayerResponse): FeatureCollection | null {
  const points = data.features.filter(
    (f): f is Feature<Point, Record<string, unknown>> => f.geometry?.type === 'Point',
  );
  const spacing = gridSpacing(points);
  if (!spacing) return null;
  return columnsFromPoints(points, {
    footprint: (lng, lat) =>
      cellFromPoint(lng, lat, spacing.dLng * AIR_CELL_INSET, spacing.dLat * AIR_CELL_INSET),
    height: (p) => airCellHeight('pm25', p.pm25),
    extra: (p) =>
      Object.fromEntries(POLLUTANTS.map((pol) => [`height_${pol}`, airCellHeight(pol, p[pol])])),
  });
}

const visibility = (v: boolean): 'visible' | 'none' => v ? 'visible' : 'none';

/**
 * WHO-based thresholds for normalizing pollutant values to 0-1 weight.
 * Values at or above `veryUnhealthy` map to weight 1.0.
 */
const POLLUTANT_THRESHOLDS: Record<Pollutant, { good: number; moderate: number; unhealthy: number; veryUnhealthy: number }> = {
  pm25: { good: 15, moderate: 30, unhealthy: 55, veryUnhealthy: 75 },
  pm10: { good: 45, moderate: 90, unhealthy: 180, veryUnhealthy: 250 },
  no2:  { good: 40, moderate: 100, unhealthy: 200, veryUnhealthy: 300 },
  o3:   { good: 60, moderate: 120, unhealthy: 180, veryUnhealthy: 240 },
};

/**
 * Build a MapLibre heatmap layer spec for the active pollutant.
 * The heatmap-weight expression maps the pollutant value through the
 * WHO threshold breakpoints to produce a 0-1 normalized weight.
 */
function buildHeatmapLayer(pollutant: Pollutant): HeatmapLayerSpecification {
  const t = POLLUTANT_THRESHOLDS[pollutant];
  return {
    id: 'air-grid-heatmap',
    type: 'heatmap',
    source: 'air-quality-grid',
    layout: { visibility: 'visible' },
    paint: {
      'heatmap-weight': [
        'interpolate', ['linear'],
        ['coalesce', ['get', pollutant], 0],
        0,                0,
        t.good,           0.25,
        t.moderate,       0.5,
        t.unhealthy,      0.75,
        t.veryUnhealthy,  1.0,
      ],
      'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 8, 0.6, 14, 1.2],
      'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 8, 25, 12, 50, 16, 80],
      'heatmap-color': [
        'interpolate', ['linear'], ['heatmap-density'],
        0,    'rgba(0,228,0,0)',
        0.2,  '#00e400',   // green
        0.4,  '#ffff00',   // yellow
        0.6,  '#ff7e00',   // orange
        0.8,  '#ff0000',   // red
        1.0,  '#8f3f97',   // purple
      ],
      'heatmap-opacity': 0.5,
    },
  };
}

export default function AirQualityHeatmapLayer({
  data,
  visible,
  activePollutant,
  extruded = false,
  beforeId,
}: AirQualityHeatmapLayerProps) {
  const layerSpec = useMemo(() => buildHeatmapLayer(activePollutant), [activePollutant]);
  // Geometry depends on the data only: switching the pollutant must not rebuild it.
  const cells = useMemo(() => (extruded && data ? buildAirCells(data) : null), [extruded, data]);
  const cellColor = useMemo(() => eaqiColorExpression(activePollutant), [activePollutant]);

  if (!data) return null;

  return (
    <>
      <Source id="air-quality-grid" type="geojson" data={data}>
        <Layer {...layerSpec} layout={{ ...layerSpec.layout, visibility: visibility(visible && !extruded) }} />
      </Source>
      {extruded && (
        <ColumnLayer
          id={AIR_QUALITY_CELLS_LAYER_ID}
          data={cells}
          heightProperty={`height_${activePollutant}`}
          colorExpression={cellColor}
          opacity={AIR_CELL_OPACITY}
          beforeId={beforeId}
          visible={visible}
        />
      )}
    </>
  );
}
