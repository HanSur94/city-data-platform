/**
 * Pure geometry helpers for the 3D data layers (extruded columns and grid cells).
 *
 * No React or MapLibre runtime imports on purpose: the file is executed directly by
 * Node type stripping in the geometry check, and has no town-specific constants.
 */
import type { Feature, FeatureCollection, Point, Polygon, Position } from 'geojson';

const EARTH_RADIUS_M = 6371008.8;
const METERS_PER_DEGREE = (Math.PI * EARTH_RADIUS_M) / 180;

type Props = Record<string, unknown>;
type PointFeature = Feature<Point, Props>;

/** [lng, lat] moved dxMeters east and dyMeters north. */
export function offsetLngLat(
  lng: number,
  lat: number,
  dxMeters: number,
  dyMeters: number,
): [number, number] {
  const dLat = dyMeters / METERS_PER_DEGREE;
  const dLng = dxMeters / (METERS_PER_DEGREE * Math.cos((lat * Math.PI) / 180));
  return [lng + dLng, lat + dLat];
}

/**
 * Closed counter-clockwise ring (sides + 1 positions) of a regular polygon.
 * Vertex k sits at rotationDeg + 360 * k / sides, counter-clockwise from east.
 * rotationDeg 45 with 4 sides gives an axis-aligned square.
 */
export function regularPolygon(
  lng: number,
  lat: number,
  radiusMeters: number,
  sides: number,
  rotationDeg = 0,
): Position[] {
  const ring: Position[] = [];
  for (let k = 0; k < sides; k++) {
    const angle = ((rotationDeg + (360 * k) / sides) * Math.PI) / 180;
    ring.push(
      offsetLngLat(lng, lat, radiusMeters * Math.cos(angle), radiusMeters * Math.sin(angle)),
    );
  }
  ring.push([ring[0][0], ring[0][1]]);
  return ring;
}

/** Closed counter-clockwise rectangle centred on the point (SW, SE, NE, NW, SW). */
export function cellFromPoint(
  lng: number,
  lat: number,
  widthDeg: number,
  heightDeg: number,
): Position[] {
  const w = widthDeg / 2;
  const h = heightDeg / 2;
  return [
    [lng - w, lat - h],
    [lng + w, lat - h],
    [lng + w, lat + h],
    [lng - w, lat + h],
    [lng - w, lat - h],
  ];
}

function axisSpacing(values: number[]): number | null {
  const unique = Array.from(new Set(values.map((v) => Math.round(v * 1e7)))).sort((a, b) => a - b);
  if (unique.length < 2) return null;
  let min = Infinity;
  for (let i = 1; i < unique.length; i++) {
    const d = unique[i] - unique[i - 1];
    if (d > 0 && d < min) min = d;
  }
  return Number.isFinite(min) ? min / 1e7 : null;
}

/**
 * Grid spacing in degrees per axis, measured from the data (smallest positive
 * coordinate difference). An axis with fewer than two unique values borrows the
 * other axis's spacing; null when neither axis has one.
 */
export function gridSpacing(points: PointFeature[]): { dLng: number; dLat: number } | null {
  const lngs: number[] = [];
  const lats: number[] = [];
  for (const f of points) {
    if (f.geometry?.type !== 'Point') continue;
    const [lng, lat] = f.geometry.coordinates;
    if (!Number.isFinite(lng) || !Number.isFinite(lat)) continue;
    lngs.push(lng);
    lats.push(lat);
  }
  const dLng = axisSpacing(lngs);
  const dLat = axisSpacing(lats);
  if (dLng === null && dLat === null) return null;
  return { dLng: dLng ?? (dLat as number), dLat: dLat ?? (dLng as number) };
}

function haversineM(a: Position, b: Position): number {
  const rad = Math.PI / 180;
  const dLat = (b[1] - a[1]) * rad;
  const dLng = (b[0] - a[0]) * rad;
  const s =
    Math.sin(dLat / 2) ** 2 + Math.cos(a[1] * rad) * Math.cos(b[1] * rad) * Math.sin(dLng / 2) ** 2;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.min(1, Math.sqrt(s)));
}

export { haversineM };

/**
 * Moves features that share one position and are flagged (flagProperty truthy)
 * onto a ring around that position so that neighbours are at least
 * minSeparationMeters apart. Ring order follows sortKey (ties: input index), so
 * the same feature lands on the same spot on every call. Input is not mutated.
 */
export function spreadApproximate(
  features: PointFeature[],
  options: {
    flagProperty: string;
    minSeparationMeters: number;
    sortKey: (properties: Props) => string;
  },
): PointFeature[] {
  const { flagProperty, minSeparationMeters, sortKey } = options;
  const groups = new Map<string, number[]>();
  features.forEach((f, index) => {
    if (f.geometry?.type !== 'Point' || !f.properties?.[flagProperty]) return;
    const [lng, lat] = f.geometry.coordinates;
    if (!Number.isFinite(lng) || !Number.isFinite(lat)) return;
    const key = `${Math.round(lng * 1e6)}|${Math.round(lat * 1e6)}`;
    const list = groups.get(key);
    if (list) list.push(index);
    else groups.set(key, [index]);
  });

  const moved = new Map<number, [number, number]>();
  for (const indices of groups.values()) {
    const n = indices.length;
    if (n < 2) continue;
    const sorted = [...indices].sort((a, b) => {
      const ka = sortKey(features[a].properties ?? {});
      const kb = sortKey(features[b].properties ?? {});
      if (ka < kb) return -1;
      if (ka > kb) return 1;
      return a - b;
    });
    const radius = minSeparationMeters / (2 * Math.sin(Math.PI / n));
    const [lng, lat] = (features[sorted[0]].geometry as Point).coordinates;
    sorted.forEach((featureIndex, k) => {
      const bearing = ((360 * k) / n) * (Math.PI / 180); // clockwise from north
      moved.set(featureIndex, offsetLngLat(lng, lat, radius * Math.sin(bearing), radius * Math.cos(bearing)));
    });
  }

  return features.map((f, index) => {
    const position = moved.get(index);
    if (!position) return f;
    return { ...f, properties: { ...f.properties }, geometry: { type: 'Point', coordinates: position } };
  });
}

type Footprint =
  | { radiusMeters: number | ((properties: Props) => number); sides: number; rotationDeg?: number }
  | ((lng: number, lat: number, properties: Props) => Position[]);

/**
 * Polygon column per Point feature. Non-Point features and features with
 * non-finite coordinates or height are skipped. Properties are copied and extended
 * with extra(), height_m and the centre the column was built around.
 */
export function columnsFromPoints(
  features: Feature[],
  options: {
    footprint: Footprint;
    height: (properties: Props) => number;
    extra?: (properties: Props) => Props;
  },
): FeatureCollection<Polygon, Props> {
  const out: Feature<Polygon, Props>[] = [];
  for (const f of features) {
    if (f.geometry?.type !== 'Point') continue;
    const [lng, lat] = f.geometry.coordinates;
    if (!Number.isFinite(lng) || !Number.isFinite(lat)) continue;
    const properties = (f.properties ?? {}) as Props;
    const height = options.height(properties);
    if (!Number.isFinite(height)) continue;

    let ring: Position[];
    if (typeof options.footprint === 'function') {
      ring = options.footprint(lng, lat, properties);
    } else {
      const { radiusMeters, sides, rotationDeg = 0 } = options.footprint;
      const radius = typeof radiusMeters === 'function' ? radiusMeters(properties) : radiusMeters;
      if (!Number.isFinite(radius)) continue;
      ring = regularPolygon(lng, lat, radius, sides, rotationDeg);
    }

    const feature: Feature<Polygon, Props> = {
      type: 'Feature',
      properties: {
        ...properties,
        ...(options.extra ? options.extra(properties) : {}),
        height_m: height,
        _center_lng: lng,
        _center_lat: lat,
      },
      geometry: { type: 'Polygon', coordinates: [ring] },
    };
    if (f.id !== undefined) feature.id = f.id;
    out.push(feature);
  }
  return { type: 'FeatureCollection', features: out };
}
