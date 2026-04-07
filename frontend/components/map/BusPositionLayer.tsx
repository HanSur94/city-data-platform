'use client';
import { useState, useEffect, useCallback, useRef } from 'react';
import { Source, Layer } from 'react-map-gl/maplibre';
import type {
  CircleLayerSpecification,
  SymbolLayerSpecification,
  LineLayerSpecification,
} from 'react-map-gl/maplibre';
import { fetchLayer } from '@/lib/api';
import type { FeatureCollection, Feature, LineString, Point } from 'geojson';

interface BusPositionLayerProps {
  town: string;
  visible: boolean;
}

/**
 * Extract bus positions and build route lines from stop coordinates.
 * Each bus feature has coordinates in geometry (current position) and
 * shape_coords or stop positions in properties for the full route path.
 */
function processBusData(fc: FeatureCollection): {
  positions: FeatureCollection;
  routesDriven: FeatureCollection;
  routesRemaining: FeatureCollection;
} {
  const positions: Feature<Point>[] = [];
  const drivenLines: Feature<LineString>[] = [];
  const remainingLines: Feature<LineString>[] = [];

  for (const f of fc.features) {
    if (f.properties?.feature_type !== 'bus_position') continue;
    if (f.geometry?.type !== 'Point') continue;

    // Bus dot
    positions.push({
      type: 'Feature',
      id: f.properties?.trip_id as string,
      geometry: f.geometry as Point,
      properties: { ...f.properties },
    });

    // Route path from shape_coords (stored as JSON string in properties)
    const coordsRaw = f.properties?.shape_coords;
    const progress = (f.properties?.progress as number) ?? 0.5;
    if (!coordsRaw) continue;

    let coords: [number, number][];
    try {
      coords = typeof coordsRaw === 'string' ? JSON.parse(coordsRaw) : coordsRaw;
    } catch {
      continue;
    }
    if (!Array.isArray(coords) || coords.length < 2) continue;

    // Split route into driven (before bus) and remaining (after bus)
    const splitIdx = Math.max(1, Math.round(progress * (coords.length - 1)));
    const driven = coords.slice(0, splitIdx + 1);
    const remaining = coords.slice(splitIdx);

    const tripId = f.properties?.trip_id ?? '';

    if (driven.length >= 2) {
      drivenLines.push({
        type: 'Feature',
        geometry: { type: 'LineString', coordinates: driven },
        properties: { trip_id: tripId, line_name: f.properties?.line_name ?? '' },
      });
    }
    if (remaining.length >= 2) {
      remainingLines.push({
        type: 'Feature',
        geometry: { type: 'LineString', coordinates: remaining },
        properties: { trip_id: tripId, line_name: f.properties?.line_name ?? '' },
      });
    }
  }

  return {
    positions: { type: 'FeatureCollection', features: positions },
    routesDriven: { type: 'FeatureCollection', features: drivenLines },
    routesRemaining: { type: 'FeatureCollection', features: remainingLines },
  };
}

const circleLayer: CircleLayerSpecification = {
  id: 'bus-position-points',
  type: 'circle',
  source: 'bus-positions',
  layout: { visibility: 'visible' },
  paint: {
    'circle-color': [
      'step',
      ['coalesce', ['get', 'delay_seconds'], 0],
      '#22c55e',
      120, '#eab308',
      300, '#f97316',
      600, '#ef4444',
    ],
    'circle-radius': 8,
    'circle-stroke-width': 2,
    'circle-stroke-color': '#ffffff',
  },
};

const labelLayer: SymbolLayerSpecification = {
  id: 'bus-line-labels',
  type: 'symbol',
  source: 'bus-positions',
  layout: {
    'text-field': ['get', 'line_name'],
    'text-font': ['Noto Sans Regular'],
    'text-size': 10,
    'text-offset': [0, 1.8],
    'text-allow-overlap': false,
    visibility: 'visible',
  },
  paint: {
    'text-color': '#374151',
    'text-halo-color': '#ffffff',
    'text-halo-width': 1,
  },
};

const drivenLineLayer: LineLayerSpecification = {
  id: 'bus-route-driven',
  type: 'line',
  source: 'bus-routes-driven',
  layout: { visibility: 'visible', 'line-cap': 'round', 'line-join': 'round' },
  paint: {
    'line-color': '#6366f1',
    'line-opacity': 0.6,
    'line-width': 3,
  },
};

const remainingLineLayer: LineLayerSpecification = {
  id: 'bus-route-remaining',
  type: 'line',
  source: 'bus-routes-remaining',
  layout: {
    visibility: 'visible',
    'line-cap': 'round',
    'line-join': 'round',
  },
  paint: {
    'line-color': '#6366f1',
    'line-opacity': 0.2,
    'line-width': 2,
    'line-dasharray': [2, 2],
  },
};

const emptyFC: FeatureCollection = { type: 'FeatureCollection', features: [] };

export default function BusPositionLayer({ town, visible }: BusPositionLayerProps) {
  const [positions, setPositions] = useState<FeatureCollection>(emptyFC);
  const [routesDriven, setRoutesDriven] = useState<FeatureCollection>(emptyFC);
  const [routesRemaining, setRoutesRemaining] = useState<FeatureCollection>(emptyFC);
  const prevDataRef = useRef<FeatureCollection>(emptyFC);

  const loadData = useCallback(async () => {
    try {
      const json = await fetchLayer('transit', town);
      const fc = json as unknown as FeatureCollection;
      const { positions: pos, routesDriven: dr, routesRemaining: rem } = processBusData(fc);

      // Only update if we actually got data — prevents flash to empty
      if (pos.features.length > 0) {
        setPositions(pos);
        setRoutesDriven(dr);
        setRoutesRemaining(rem);
        prevDataRef.current = pos;
      } else if (prevDataRef.current.features.length > 0) {
        // Keep previous data visible if new fetch returned empty
        // (transient state between backend refreshes)
      }
    } catch {
      // Keep last data on error
    }
  }, [town]);

  useEffect(() => {
    if (!visible) return;
    loadData();
    const id = setInterval(loadData, 30_000);
    return () => clearInterval(id);
  }, [visible, loadData]);

  if (!visible) return null;

  return (
    <>
      <Source id="bus-routes-driven" type="geojson" data={routesDriven}>
        <Layer {...drivenLineLayer} />
      </Source>
      <Source id="bus-routes-remaining" type="geojson" data={routesRemaining}>
        <Layer {...remainingLineLayer} />
      </Source>
      <Source id="bus-positions" type="geojson" data={positions}>
        <Layer {...circleLayer} />
        <Layer {...labelLayer} />
      </Source>
    </>
  );
}
