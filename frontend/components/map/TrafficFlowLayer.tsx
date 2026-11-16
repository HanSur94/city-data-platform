'use client';
import { useEffect, useMemo } from 'react';
import { Source, Layer, useMap } from 'react-map-gl/maplibre';
import type { LineLayerSpecification } from 'react-map-gl/maplibre';
import type { ExpressionSpecification } from 'maplibre-gl';
import { useLayerData } from '@/hooks/useLayerData';
import type { LayerResponse } from '@/types/geojson';
import type { Feature } from 'geojson';

interface TrafficFlowLayerProps {
  town: string;
  visible: boolean;
  timestamp?: Date | null;
  /** 3D mode: add a glow beneath the line and a moving white dash on top. */
  extruded?: boolean;
}

// Glow and dash clicks open TrafficFlowPopup like the line (see MapView's layer-id chain).
export const TRAFFIC_FLOW_GLOW_LAYER_ID = 'traffic-flow-glow';
export const TRAFFIC_FLOW_DASH_LAYER_ID = 'traffic-flow-dash';

// Dash animation: at most one dasharray update every DASH_STEP_MS (about 12 per second).
const DASH_STEP_MS = 80;

// MapLibre's "ant path" line-dasharray example sequence (14 steps).
const ANT_PATH_SEQUENCE: number[][] = [
  ...[0, 0.5, 1, 1.5, 2, 2.5, 3].map((s) => [s, 4, 3 - s]),
  ...[0.5, 1, 1.5, 2, 2.5, 3, 3.5].map((s) => [0, s, 3, 4 - s]),
];

function filterTomTomFeatures(data: LayerResponse | null): LayerResponse | null {
  if (!data) return null;
  return {
    ...data,
    features: data.features.filter((f: Feature) =>
      f.properties?.data_source === 'TomTom' && f.geometry?.type === 'LineString'
    ),
  };
}

// Shared by the line and the glow so the colours are identical.
const CONGESTION_COLOR: ExpressionSpecification = [
  'interpolate',
  ['linear'],
  ['coalesce', ['get', 'congestion_ratio'], 1],
  0, '#ef4444',
  0.25, '#ef4444',
  0.26, '#f97316',
  0.50, '#f97316',
  0.51, '#eab308',
  0.75, '#eab308',
  0.76, '#22c55e',
  1.0, '#22c55e',
];

const trafficFlowLineLayer: LineLayerSpecification = {
  id: 'traffic-flow-lines',
  type: 'line',
  source: 'traffic-flow',
  layout: {
    visibility: 'visible',
    'line-cap': 'round',
    'line-join': 'round',
  },
  paint: {
    'line-color': CONGESTION_COLOR,
    'line-width': [
      'interpolate',
      ['linear'],
      ['zoom'],
      10, 4,
      14, 8,
      18, 12,
    ],
    'line-opacity': 0.85,
  },
};

// Module constants so react-map-gl never re-applies the dasharray the animation drives.
const glowLayout: LineLayerSpecification['layout'] = {
  'line-cap': 'round',
  'line-join': 'round',
};
const glowPaint: LineLayerSpecification['paint'] = {
  'line-color': CONGESTION_COLOR,
  'line-width': ['interpolate', ['linear'], ['zoom'], 10, 12, 14, 24, 18, 36],
  'line-blur': ['interpolate', ['linear'], ['zoom'], 10, 6, 14, 12, 18, 18],
  'line-opacity': 0.35,
};
const dashLayout: LineLayerSpecification['layout'] = {
  'line-cap': 'butt',
  'line-join': 'round',
};
const dashPaint: LineLayerSpecification['paint'] = {
  'line-color': '#ffffff',
  'line-width': ['interpolate', ['linear'], ['zoom'], 10, 1.5, 14, 3, 18, 4.5],
  'line-opacity': 0.85,
  'line-dasharray': ANT_PATH_SEQUENCE[0],
  // Step the dash instantly instead of cross-fading between sequence entries.
  'line-dasharray-transition': { duration: 0, delay: 0 },
};

export default function TrafficFlowLayer({ town, visible, timestamp, extruded = false }: TrafficFlowLayerProps) {
  const { data } = useLayerData('traffic', town, timestamp);
  const filtered = useMemo(() => filterTomTomFeatures(data), [data]);
  const { current: mapRef } = useMap();

  // Dash animation: drives the map directly (never React state, which would re-render and
  // re-send the source every frame). Runs only in 3D mode, never while the tab is hidden or
  // the user prefers reduced motion.
  useEffect(() => {
    if (!extruded || !mapRef) return;
    const map = mapRef.getMap();
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    let frame = 0;
    let step = 0;
    let lastUpdate = 0;

    const tick = (now: number) => {
      frame = requestAnimationFrame(tick);
      if (now - lastUpdate < DASH_STEP_MS) return;
      lastUpdate = now;
      step = (step + 1) % ANT_PATH_SEQUENCE.length;
      try {
        if (map.getLayer(TRAFFIC_FLOW_DASH_LAYER_ID)) {
          map.setPaintProperty(TRAFFIC_FLOW_DASH_LAYER_ID, 'line-dasharray', ANT_PATH_SEQUENCE[step]);
        }
      } catch {
        // Style is being swapped (base-map change); the next tick retries.
      }
    };
    const stop = () => {
      if (frame) cancelAnimationFrame(frame);
      frame = 0;
    };
    const sync = () => {
      if (reducedMotion.matches || document.hidden) {
        stop();
      } else if (!frame) {
        frame = requestAnimationFrame(tick);
      }
    };

    sync();
    document.addEventListener('visibilitychange', sync);
    reducedMotion.addEventListener('change', sync);
    return () => {
      stop();
      document.removeEventListener('visibilitychange', sync);
      reducedMotion.removeEventListener('change', sync);
    };
  }, [extruded, mapRef]);

  if (!visible || !filtered) return null;
  return (
    <Source id="traffic-flow" type="geojson" data={filtered}>
      <Layer
        {...trafficFlowLineLayer}
        layout={{ ...trafficFlowLineLayer.layout, visibility: visible ? 'visible' : 'none' }}
      />
      {extruded && (
        <Layer
          id={TRAFFIC_FLOW_GLOW_LAYER_ID}
          type="line"
          beforeId={trafficFlowLineLayer.id}
          layout={glowLayout}
          paint={glowPaint}
        />
      )}
      {extruded && (
        <Layer
          id={TRAFFIC_FLOW_DASH_LAYER_ID}
          type="line"
          layout={dashLayout}
          paint={dashPaint}
        />
      )}
    </Source>
  );
}
