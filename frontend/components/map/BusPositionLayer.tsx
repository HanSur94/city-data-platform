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
 * Extract bus positions and build route lines from shape coordinates.
 * Each bus feature has coordinates in geometry (current position) and
 * shape_coords in properties for the full route path (road-following
 * geometry from GTFS shapes.txt).
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

/**
 * Smoothly interpolate between old and new bus positions over a duration.
 * Returns a new FeatureCollection at each animation frame with lerped coordinates.
 */
function lerpPositions(
  prev: FeatureCollection,
  next: FeatureCollection,
  t: number, // 0..1
): FeatureCollection {
  // Build lookup of previous positions by trip_id
  const prevMap = new Map<string, [number, number]>();
  for (const f of prev.features) {
    const tid = f.properties?.trip_id;
    const geom = f.geometry as Point | undefined;
    if (tid && geom?.coordinates) {
      prevMap.set(tid, geom.coordinates as [number, number]);
    }
  }

  const features: Feature<Point>[] = next.features.map((f) => {
    const tid = f.properties?.trip_id;
    const newCoords = (f.geometry as Point).coordinates as [number, number];
    const oldCoords = tid ? prevMap.get(tid) : undefined;

    if (oldCoords && t < 1) {
      // Lerp between old and new position
      const lng = oldCoords[0] + (newCoords[0] - oldCoords[0]) * t;
      const lat = oldCoords[1] + (newCoords[1] - oldCoords[1]) * t;
      return {
        ...f,
        geometry: { type: 'Point' as const, coordinates: [lng, lat] },
      };
    }

    return f as Feature<Point>;
  });

  return { type: 'FeatureCollection', features };
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

// Animation duration in ms for bus dot transitions
const ANIMATION_DURATION = 2000;

/**
 * Build a fingerprint string from bus positions so we can skip state updates
 * when the data hasn't actually changed.
 */
function fingerprint(fc: FeatureCollection): string {
  return fc.features
    .map((f) => {
      const p = f.properties;
      const g = f.geometry as Point;
      return `${p?.trip_id}:${g.coordinates[0].toFixed(5)},${g.coordinates[1].toFixed(5)}:${p?.delay_seconds ?? 0}`;
    })
    .join('|');
}

export default function BusPositionLayer({ town, visible }: BusPositionLayerProps) {
  const [positions, setPositions] = useState<FeatureCollection>(emptyFC);
  const [routesDriven, setRoutesDriven] = useState<FeatureCollection>(emptyFC);
  const [routesRemaining, setRoutesRemaining] = useState<FeatureCollection>(emptyFC);
  const prevFingerprintRef = useRef('');

  // Animation state
  const prevPositionsRef = useRef<FeatureCollection>(emptyFC);
  const nextPositionsRef = useRef<FeatureCollection>(emptyFC);
  const animFrameRef = useRef<number>(0);
  const animStartRef = useRef<number>(0);

  const animate = useCallback(() => {
    const elapsed = performance.now() - animStartRef.current;
    const t = Math.min(1, elapsed / ANIMATION_DURATION);
    // Ease-out cubic for smooth deceleration
    const eased = 1 - Math.pow(1 - t, 3);

    const interpolated = lerpPositions(
      prevPositionsRef.current,
      nextPositionsRef.current,
      eased,
    );
    setPositions(interpolated);

    if (t < 1) {
      animFrameRef.current = requestAnimationFrame(animate);
    }
  }, []);

  const loadData = useCallback(async () => {
    try {
      const json = await fetchLayer('transit', town, null, 'bus_position');
      const fc = json as unknown as FeatureCollection;
      const { positions: pos, routesDriven: dr, routesRemaining: rem } = processBusData(fc);

      if (pos.features.length > 0) {
        const fp = fingerprint(pos);
        if (fp === prevFingerprintRef.current) return;
        prevFingerprintRef.current = fp;

        // Start smooth animation from current to new positions
        prevPositionsRef.current = nextPositionsRef.current.features.length > 0
          ? nextPositionsRef.current
          : pos; // First load: no animation
        nextPositionsRef.current = pos;

        // Cancel any running animation
        if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);

        if (prevPositionsRef.current !== pos) {
          // Animate transition
          animStartRef.current = performance.now();
          animFrameRef.current = requestAnimationFrame(animate);
        } else {
          // First load: set immediately
          setPositions(pos);
        }

        setRoutesDriven(dr);
        setRoutesRemaining(rem);
      }
    } catch {
      // Keep last data on error
    }
  }, [town, animate]);

  useEffect(() => {
    if (!visible) return;
    loadData();
    const id = setInterval(loadData, 30_000);
    return () => {
      clearInterval(id);
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [visible, loadData]);

  const vis = visible ? 'visible' : 'none';

  return (
    <>
      <Source id="bus-routes-driven" type="geojson" data={routesDriven}>
        <Layer {...drivenLineLayer} layout={{ ...drivenLineLayer.layout, visibility: vis }} />
      </Source>
      <Source id="bus-routes-remaining" type="geojson" data={routesRemaining}>
        <Layer {...remainingLineLayer} layout={{ ...remainingLineLayer.layout, visibility: vis }} />
      </Source>
      <Source id="bus-positions" type="geojson" data={positions}>
        <Layer {...circleLayer} layout={{ ...circleLayer.layout, visibility: vis }} />
        <Layer {...labelLayer} layout={{ ...labelLayer.layout, visibility: vis }} />
      </Source>
    </>
  );
}
