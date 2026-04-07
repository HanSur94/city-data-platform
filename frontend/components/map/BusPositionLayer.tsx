'use client';
import { useState, useEffect, useCallback, useRef } from 'react';
import { Source, Layer, useMap } from 'react-map-gl/maplibre';
import type {
  CircleLayerSpecification,
  SymbolLayerSpecification,
  LineLayerSpecification,
} from 'react-map-gl/maplibre';
import type { FilterSpecification } from 'maplibre-gl';
import { fetchLayer } from '@/lib/api';
import type { FeatureCollection, Feature, LineString, Point } from 'geojson';

// ── Color palette for per-line deterministic colors ──────────────────────────

export const LINE_COLORS = [
  '#e6194b', '#3cb44b', '#4363d8', '#f58231', '#911eb4',
  '#42d4f4', '#f032e6', '#bfef45', '#fabed4', '#469990',
  '#dcbeff', '#9A6324', '#800000', '#aaffc3', '#808000',
];

/** Deterministic color for a line name based on a hash of its characters. */
export function lineColor(name: string): string {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = ((h << 5) - h + name.charCodeAt(i)) | 0;
  return LINE_COLORS[Math.abs(h) % LINE_COLORS.length];
}

// ── Build MapLibre match expression for line colors ───────────────────────────

type MatchExpression = ['match', ['get', string], ...unknown[]];

function buildColorMatchExpr(lineNames: string[], fallback: string): MatchExpression {
  const parts: unknown[] = ['match', ['get', 'line_name']];
  for (const name of lineNames) {
    parts.push(name, lineColor(name));
  }
  parts.push(fallback);
  return parts as MatchExpression;
}

// ── Props ─────────────────────────────────────────────────────────────────────

interface BusPositionLayerProps {
  town: string;
  visible: boolean;
  hiddenLines?: Set<string>;
  onLinesDiscovered?: (lines: string[]) => void;
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
  lineNames: string[];
} {
  const positions: Feature<Point>[] = [];
  const drivenLines: Feature<LineString>[] = [];
  const remainingLines: Feature<LineString>[] = [];
  const lineNameSet = new Set<string>();

  for (const f of fc.features) {
    if (f.properties?.feature_type !== 'bus_position') continue;
    if (f.geometry?.type !== 'Point') continue;

    const lineName: string = f.properties?.line_name ?? '';
    if (lineName) lineNameSet.add(lineName);

    // Bus dot — include route_type and pre-computed _color for data-driven styling
    positions.push({
      type: 'Feature',
      id: f.properties?.trip_id as string,
      geometry: f.geometry as Point,
      properties: {
        ...f.properties,
        _color: lineColor(lineName),
      },
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
        properties: {
          trip_id: tripId,
          line_name: lineName,
          _color: lineColor(lineName),
        },
      });
    }
    if (remaining.length >= 2) {
      remainingLines.push({
        type: 'Feature',
        geometry: { type: 'LineString', coordinates: remaining },
        properties: {
          trip_id: tripId,
          line_name: lineName,
          _color: lineColor(lineName),
        },
      });
    }
  }

  return {
    positions: { type: 'FeatureCollection', features: positions },
    routesDriven: { type: 'FeatureCollection', features: drivenLines },
    routesRemaining: { type: 'FeatureCollection', features: remainingLines },
    lineNames: [...lineNameSet].sort((a, b) => a.localeCompare(b, undefined, { numeric: true })),
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

const emptyFC: FeatureCollection = { type: 'FeatureCollection', features: [] };

// Animate over the full polling interval so bus dots move at realistic speed.
// The dot travels from old→new position over 30s, matching real-world bus velocity.
const ANIMATION_DURATION = 30_000;

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

/** Build a MapLibre filter to exclude hidden lines. */
function buildHiddenLinesFilter(hiddenLines: Set<string>): FilterSpecification | undefined {
  if (!hiddenLines || hiddenLines.size === 0) return undefined;
  return ['!', ['in', ['get', 'line_name'], ['literal', [...hiddenLines]]]] as FilterSpecification;
}

export default function BusPositionLayer({
  town,
  visible,
  hiddenLines,
  onLinesDiscovered,
}: BusPositionLayerProps) {
  // React state only used for the initial/stable render of <Source> data.
  // During animation, we bypass React state entirely and call map.getSource().setData()
  // imperatively to avoid triggering React re-renders at 60fps.
  const [positions, setPositions] = useState<FeatureCollection>(emptyFC);
  const [routesDriven, setRoutesDriven] = useState<FeatureCollection>(emptyFC);
  const [routesRemaining, setRoutesRemaining] = useState<FeatureCollection>(emptyFC);
  const [lineNames, setLineNames] = useState<string[]>([]);
  const prevFingerprintRef = useRef('');

  // Animation state
  const prevPositionsRef = useRef<FeatureCollection>(emptyFC);
  const nextPositionsRef = useRef<FeatureCollection>(emptyFC);
  const animFrameRef = useRef<number>(0);
  const animStartRef = useRef<number>(0);

  // Track discovered lines to avoid calling onLinesDiscovered on every render
  const prevLinesKeyRef = useRef('');

  // Get the MapLibre map instance for imperative source updates during animation.
  // This avoids React state updates (and thus re-renders) on every animation frame.
  const { current: mapInstance } = useMap();

  const animate = useCallback(() => {
    const elapsed = performance.now() - animStartRef.current;
    const t = Math.min(1, elapsed / ANIMATION_DURATION);
    // Linear interpolation — bus moves at constant speed matching real velocity

    const interpolated = lerpPositions(
      prevPositionsRef.current,
      nextPositionsRef.current,
      t,
    );

    // Imperatively update the MapLibre source — bypasses React state and avoids
    // triggering a React re-render cascade on every animation frame.
    const map = mapInstance?.getMap();
    if (map) {
      const src = map.getSource('bus-positions');
      // GeoJSONSource exposes setData(); the type is a maplibre-gl internal
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (src as any)?.setData(interpolated);
    } else {
      // Map not yet available (first few frames) — fall back to React state
      setPositions(interpolated);
    }

    if (t < 1) {
      animFrameRef.current = requestAnimationFrame(animate);
    } else {
      // Animation finished — sync React state once so the Source JSX reflects
      // the final position for future renders (e.g. visibility toggles).
      setPositions(nextPositionsRef.current);
    }
  }, [mapInstance]);

  const loadData = useCallback(async () => {
    try {
      const json = await fetchLayer('transit', town, null, 'bus_position');
      const fc = json as unknown as FeatureCollection;
      const { positions: pos, routesDriven: dr, routesRemaining: rem, lineNames: names } =
        processBusData(fc);

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
          // Animate transition imperatively (no React state updates during rAF loop)
          animStartRef.current = performance.now();
          animFrameRef.current = requestAnimationFrame(animate);
        } else {
          // First load: set immediately via React state (map source may not exist yet)
          setPositions(pos);
        }

        setRoutesDriven(dr);
        setRoutesRemaining(rem);
      }

      // Report discovered line names (only when they change)
      const namesKey = names.join(',');
      if (namesKey !== prevLinesKeyRef.current) {
        prevLinesKeyRef.current = namesKey;
        setLineNames(names);
        onLinesDiscovered?.(names);
      }
    } catch {
      // Keep last data on error
    }
  }, [town, animate, onLinesDiscovered]);

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

  // Build filter for hidden lines
  const hiddenFilter = hiddenLines && hiddenLines.size > 0
    ? buildHiddenLinesFilter(hiddenLines)
    : undefined;

  // Build data-driven color match expression from discovered line names
  const colorMatchExpr = lineNames.length > 0
    ? buildColorMatchExpr(lineNames, '#6b7280')
    : ('#6b7280' as unknown as MatchExpression);

  // Suppress unused variable warning — colorMatchExpr available for future use
  void colorMatchExpr;

  // Circle layer with per-line colors and delay-based stroke
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const circleLayer = {
    id: 'bus-position-points',
    type: 'circle',
    source: 'bus-positions',
    layout: { visibility: vis },
    paint: {
      'circle-color': ['get', '_color'],
      // Trains (route_type 0,1,2) get radius 10; buses (3) get 8
      'circle-radius': ['match', ['get', 'route_type'], 0, 10, 1, 10, 2, 10, 8],
      'circle-stroke-width': ['match', ['get', 'route_type'], 0, 3, 1, 3, 2, 3, 2],
      // Delay indicated via stroke color: green/yellow/orange/red
      'circle-stroke-color': [
        'step',
        ['coalesce', ['get', 'delay_seconds'], 0],
        '#22c55e',
        120, '#eab308',
        300, '#f97316',
        600, '#ef4444',
      ],
    },
    ...(hiddenFilter ? { filter: hiddenFilter } : {}),
  } as CircleLayerSpecification;

  const labelLayer = {
    id: 'bus-line-labels',
    type: 'symbol',
    source: 'bus-positions',
    layout: {
      'text-field': ['get', 'line_name'],
      'text-font': ['Noto Sans Regular'],
      'text-size': 10,
      'text-offset': [0, 1.8],
      'text-allow-overlap': false,
      visibility: vis,
    },
    paint: {
      'text-color': '#374151',
      'text-halo-color': '#ffffff',
      'text-halo-width': 1,
    },
    ...(hiddenFilter ? { filter: hiddenFilter } : {}),
  } as SymbolLayerSpecification;

  const drivenLineLayer = {
    id: 'bus-route-driven',
    type: 'line',
    source: 'bus-routes-driven',
    layout: { visibility: vis, 'line-cap': 'round', 'line-join': 'round' },
    paint: {
      'line-color': ['get', '_color'],
      'line-opacity': 0.6,
      'line-width': 3,
    },
    ...(hiddenFilter ? { filter: hiddenFilter } : {}),
  } as LineLayerSpecification;

  const remainingLineLayer = {
    id: 'bus-route-remaining',
    type: 'line',
    source: 'bus-routes-remaining',
    layout: {
      visibility: vis,
      'line-cap': 'round',
      'line-join': 'round',
    },
    paint: {
      'line-color': ['get', '_color'],
      'line-opacity': 0.2,
      'line-width': 2,
      'line-dasharray': [2, 2],
    },
    ...(hiddenFilter ? { filter: hiddenFilter } : {}),
  } as LineLayerSpecification;

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
