'use client';
import { useState, useEffect, useCallback, useRef } from 'react';
import { Source, Layer, useMap } from 'react-map-gl/maplibre';
import type {
  SymbolLayerSpecification,
  LineLayerSpecification,
} from 'react-map-gl/maplibre';
import type { FilterSpecification, FillExtrusionLayerSpecification } from 'maplibre-gl';
import { fetchLayer } from '@/lib/api';
import type { FeatureCollection, Feature, LineString, Point, Polygon } from 'geojson';

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

// ── 3D bus rectangle polygon generator ────────────────────────────────────────

/** Approximate metres per degree at a given latitude. */
function metersPerDeg(lat: number): { lon: number; lat: number } {
  const latRad = (lat * Math.PI) / 180;
  return { lon: 111_320 * Math.cos(latRad), lat: 111_132 };
}

/**
 * Create a small rectangular polygon centred at [lon, lat], rotated by bearing.
 * lengthM / widthM are in metres. Bearing is clockwise from north in degrees.
 */
function busRectPoly(
  lon: number,
  lat: number,
  bearing: number,
  lengthM: number,
  widthM: number,
): [number, number][] {
  const m = metersPerDeg(lat);
  const halfL = lengthM / 2;
  const halfW = widthM / 2;
  // Corner offsets in local metres (length along bearing, width perpendicular)
  const corners = [
    [-halfL, -halfW],
    [halfL, -halfW],
    [halfL, halfW],
    [-halfL, halfW],
  ];
  const rad = (bearing * Math.PI) / 180; // bearing: clockwise from north (0=N, 90=E)
  const cosB = Math.cos(rad);
  const sinB = Math.sin(rad);
  // dx = along bus length (forward), dy = perpendicular (sideways)
  // Geographic bearing: forward = (sin(B), cos(B)) in (east, north)
  return corners.map(([dx, dy]) => {
    const rx = dx * sinB + dy * cosB;  // east offset in metres
    const ry = dx * cosB - dy * sinB;  // north offset in metres
    return [lon + rx / m.lon, lat + ry / m.lat] as [number, number];
  });
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
  busPolygons: FeatureCollection;
  routesDriven: FeatureCollection;
  routesRemaining: FeatureCollection;
  lineNames: string[];
} {
  const positions: Feature<Point>[] = [];
  const busPolys: Feature<Polygon>[] = [];
  const drivenLines: Feature<LineString>[] = [];
  const remainingLines: Feature<LineString>[] = [];
  const lineNameSet = new Set<string>();

  for (const f of fc.features) {
    if (f.properties?.feature_type !== 'bus_position') continue;
    if (f.geometry?.type !== 'Point') continue;

    const lineName: string = f.properties?.line_name ?? '';
    if (lineName) lineNameSet.add(lineName);

    const color = lineColor(lineName);
    const bearing = (f.properties?.bearing as number) ?? 0;
    const routeType = (f.properties?.route_type as number) ?? 3;
    const [lon, lat] = (f.geometry as Point).coordinates;

    // Bus label point
    positions.push({
      type: 'Feature',
      id: f.properties?.trip_id as string,
      geometry: f.geometry as Point,
      properties: {
        ...f.properties,
        _color: color,
      },
    });

    // 3D bus rectangle polygon — trains are longer
    const length = routeType <= 2 ? 18 : 12; // metres
    const width = routeType <= 2 ? 5 : 4;
    const corners = busRectPoly(lon, lat, bearing, length, width);
    corners.push(corners[0]); // close ring
    busPolys.push({
      type: 'Feature',
      geometry: { type: 'Polygon', coordinates: [corners] },
      properties: {
        trip_id: f.properties?.trip_id,
        line_name: lineName,
        _color: color,
        route_type: routeType,
        delay_seconds: f.properties?.delay_seconds ?? 0,
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
    busPolygons: { type: 'FeatureCollection', features: busPolys },
    routesDriven: { type: 'FeatureCollection', features: drivenLines },
    routesRemaining: { type: 'FeatureCollection', features: remainingLines },
    lineNames: [...lineNameSet].sort((a, b) => a.localeCompare(b, undefined, { numeric: true })),
  };
}

/**
 * Compute bearing in degrees (0-360) from point 1 to point 2.
 * Uses the forward azimuth formula for WGS84 coordinates.
 */
function calcBearing(lon1: number, lat1: number, lon2: number, lat2: number): number {
  const toRad = Math.PI / 180;
  const rlat1 = lat1 * toRad;
  const rlat2 = lat2 * toRad;
  const dlon = (lon2 - lon1) * toRad;
  const x = Math.sin(dlon) * Math.cos(rlat2);
  const y = Math.cos(rlat1) * Math.sin(rlat2) - Math.sin(rlat1) * Math.cos(rlat2) * Math.cos(dlon);
  return ((Math.atan2(x, y) * 180) / Math.PI + 360) % 360;
}

/**
 * Walk along a shape polyline at a given progress fraction (0..1).
 * Returns [lon, lat, bearing] — bearing follows the current segment direction.
 */
function shapeWalk(coords: [number, number][], progress: number): [number, number, number] {
  if (coords.length === 0) return [0, 0, 0];
  if (coords.length === 1 || progress <= 0) {
    const brng = coords.length >= 2 ? calcBearing(coords[0][0], coords[0][1], coords[1][0], coords[1][1]) : 0;
    return [coords[0][0], coords[0][1], brng];
  }
  if (progress >= 1) {
    const last = coords[coords.length - 1];
    const prev = coords[coords.length - 2];
    return [last[0], last[1], calcBearing(prev[0], prev[1], last[0], last[1])];
  }

  // Compute cumulative segment lengths
  let totalDist = 0;
  const segLens: number[] = [];
  for (let i = 1; i < coords.length; i++) {
    const dx = coords[i][0] - coords[i - 1][0];
    const dy = coords[i][1] - coords[i - 1][1];
    const len = Math.sqrt(dx * dx + dy * dy);
    segLens.push(len);
    totalDist += len;
  }
  if (totalDist === 0) return [coords[0][0], coords[0][1], 0];

  const target = progress * totalDist;
  let cum = 0;
  for (let i = 0; i < segLens.length; i++) {
    if (cum + segLens[i] >= target) {
      const frac = segLens[i] === 0 ? 0 : (target - cum) / segLens[i];
      const lon = coords[i][0] + frac * (coords[i + 1][0] - coords[i][0]);
      const lat = coords[i][1] + frac * (coords[i + 1][1] - coords[i][1]);
      const brng = calcBearing(coords[i][0], coords[i][1], coords[i + 1][0], coords[i + 1][1]);
      return [lon, lat, brng];
    }
    cum += segLens[i];
  }
  const last = coords[coords.length - 1];
  const prev = coords[coords.length - 2];
  return [last[0], last[1], calcBearing(prev[0], prev[1], last[0], last[1])];
}

/**
 * Smoothly interpolate between old and new bus positions over a duration.
 * Uses shape-aware interpolation: lerps progress along the route shape
 * so buses follow actual road geometry during animation.
 */
function lerpPositions(
  prev: FeatureCollection,
  next: FeatureCollection,
  t: number, // 0..1
): FeatureCollection {
  // Build lookup of previous progress + shape by trip_id
  const prevMap = new Map<string, { progress: number }>();
  for (const f of prev.features) {
    const tid = f.properties?.trip_id;
    if (tid) {
      prevMap.set(tid, {
        progress: (f.properties?.progress as number) ?? 0,
      });
    }
  }

  const features: Feature<Point>[] = next.features.map((f) => {
    const tid = f.properties?.trip_id;
    const prevData = tid ? prevMap.get(tid) : undefined;
    const newProgress = (f.properties?.progress as number) ?? 0;

    // Try shape-aware interpolation
    const shapeRaw = f.properties?.shape_coords;
    if (prevData && t < 1 && shapeRaw) {
      let coords: [number, number][];
      try {
        coords = typeof shapeRaw === 'string' ? JSON.parse(shapeRaw) : shapeRaw;
      } catch {
        coords = [];
      }

      if (coords.length >= 2) {
        // Lerp progress value, then walk the shape at that progress
        const interpProgress = prevData.progress + (newProgress - prevData.progress) * t;
        const [lng, lat, brng] = shapeWalk(coords, interpProgress);
        return {
          ...f,
          geometry: { type: 'Point' as const, coordinates: [lng, lat] },
          properties: { ...f.properties, bearing: brng },
        };
      }
    }

    // Fallback: simple coordinate lerp (no shape available)
    if (prevData && t < 1) {
      const newCoords = (f.geometry as Point).coordinates as [number, number];
      const oldFeature = prev.features.find(pf => pf.properties?.trip_id === tid);
      if (oldFeature) {
        const oldCoords = (oldFeature.geometry as Point).coordinates as [number, number];
        const lng = oldCoords[0] + (newCoords[0] - oldCoords[0]) * t;
        const lat = oldCoords[1] + (newCoords[1] - oldCoords[1]) * t;
        const brng = calcBearing(oldCoords[0], oldCoords[1], newCoords[0], newCoords[1]);
        return {
          ...f,
          geometry: { type: 'Point' as const, coordinates: [lng, lat] },
          properties: { ...f.properties, bearing: brng },
        };
      }
    }

    return f as Feature<Point>;
  });

  return { type: 'FeatureCollection', features };
}

/**
 * Generate 3D bus polygon features from a point-based positions FeatureCollection.
 * Each point becomes a small rotated rectangle polygon for fill-extrusion rendering.
 */
function buildBusPolygons(positions: FeatureCollection): FeatureCollection {
  const polys: Feature<Polygon>[] = [];
  for (const f of positions.features) {
    if (f.geometry?.type !== 'Point') continue;
    const [lon, lat] = (f.geometry as Point).coordinates;
    const bearing = (f.properties?.bearing as number) ?? 0;
    const routeType = (f.properties?.route_type as number) ?? 3;
    const length = routeType <= 2 ? 18 : 12;
    const width = routeType <= 2 ? 5 : 4;
    const corners = busRectPoly(lon, lat, bearing, length, width);
    corners.push(corners[0]);
    polys.push({
      type: 'Feature',
      geometry: { type: 'Polygon', coordinates: [corners] },
      properties: {
        trip_id: f.properties?.trip_id,
        line_name: f.properties?.line_name,
        _color: f.properties?._color,
        route_type: routeType,
        delay_seconds: f.properties?.delay_seconds ?? 0,
      },
    });
  }
  return { type: 'FeatureCollection', features: polys };
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
  const [positions, setPositions] = useState<FeatureCollection>(emptyFC);
  const [busPolygons, setBusPolygons] = useState<FeatureCollection>(emptyFC);
  const [routesDriven, setRoutesDriven] = useState<FeatureCollection>(emptyFC);
  const [routesRemaining, setRoutesRemaining] = useState<FeatureCollection>(emptyFC);
  const [lineNames, setLineNames] = useState<string[]>([]);
  const prevFingerprintRef = useRef('');

  // Animation state
  const prevPositionsRef = useRef<FeatureCollection>(emptyFC);
  const nextPositionsRef = useRef<FeatureCollection>(emptyFC);
  const animFrameRef = useRef<number>(0);
  const animStartRef = useRef<number>(0);

  const prevLinesKeyRef = useRef('');

  const { current: mapInstance } = useMap();

  const animate = useCallback(() => {
    const elapsed = performance.now() - animStartRef.current;
    const t = Math.min(1, elapsed / ANIMATION_DURATION);

    const interpolated = lerpPositions(
      prevPositionsRef.current,
      nextPositionsRef.current,
      t,
    );

    // Build 3D polygons from interpolated positions
    const polys = buildBusPolygons(interpolated);

    const map = mapInstance?.getMap();
    if (map) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (map.getSource('bus-positions') as any)?.setData(interpolated);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (map.getSource('bus-polygons') as any)?.setData(polys);
    } else {
      setPositions(interpolated);
      setBusPolygons(polys);
    }

    if (t < 1) {
      animFrameRef.current = requestAnimationFrame(animate);
    } else {
      setPositions(nextPositionsRef.current);
      setBusPolygons(buildBusPolygons(nextPositionsRef.current));
    }
  }, [mapInstance]);

  const loadData = useCallback(async () => {
    try {
      const json = await fetchLayer('transit', town, null, 'bus_position');
      const fc = json as unknown as FeatureCollection;
      const {
        positions: pos,
        busPolygons: polys,
        routesDriven: dr,
        routesRemaining: rem,
        lineNames: names,
      } = processBusData(fc);

      if (pos.features.length > 0) {
        const fp = fingerprint(pos);
        if (fp === prevFingerprintRef.current) return;
        prevFingerprintRef.current = fp;

        prevPositionsRef.current = nextPositionsRef.current.features.length > 0
          ? nextPositionsRef.current
          : pos;
        nextPositionsRef.current = pos;

        if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);

        if (prevPositionsRef.current !== pos) {
          animStartRef.current = performance.now();
          animFrameRef.current = requestAnimationFrame(animate);
        } else {
          setPositions(pos);
          setBusPolygons(polys);
        }

        setRoutesDriven(dr);
        setRoutesRemaining(rem);
      }

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

  const hiddenFilter = hiddenLines && hiddenLines.size > 0
    ? buildHiddenLinesFilter(hiddenLines)
    : undefined;

  // Suppress unused — lineNames used for discovery callback
  void lineNames;

  // 3D extruded bus rectangles
  const busExtrusionLayer = {
    id: 'bus-position-3d',
    type: 'fill-extrusion',
    source: 'bus-polygons',
    paint: {
      'fill-extrusion-color': ['get', '_color'] as unknown,
      'fill-extrusion-height': [
        'match', ['get', 'route_type'],
        0, 6, 1, 6, 2, 6, // trains taller
        4, // buses
      ] as unknown,
      'fill-extrusion-base': 0,
      'fill-extrusion-opacity': 0.9,
    },
    ...(hiddenFilter ? { filter: hiddenFilter } : {}),
  } as FillExtrusionLayerSpecification;

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
      <Source id="bus-polygons" type="geojson" data={busPolygons}>
        <Layer {...busExtrusionLayer} />
      </Source>
      <Source id="bus-positions" type="geojson" data={positions}>
        <Layer {...labelLayer} />
      </Source>
    </>
  );
}
