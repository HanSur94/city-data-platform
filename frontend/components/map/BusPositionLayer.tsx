'use client';
import { useState, useEffect, useCallback } from 'react';
import { Source, Layer } from 'react-map-gl/maplibre';
import type { CircleLayerSpecification, SymbolLayerSpecification } from 'react-map-gl/maplibre';
import { fetchLayer } from '@/lib/api';
import type { FeatureCollection, Feature } from 'geojson';

interface BusPositionLayerProps {
  town: string;
  visible: boolean;
}

function filterBusPositions(fc: FeatureCollection): FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: fc.features
      .filter((f: Feature) => f.properties?.feature_type === 'bus_position')
      .map((f: Feature) => ({
        ...f,
        id: f.properties?.trip_id as string,
      })),
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
      ['get', 'delay_seconds'],
      '#22c55e',   // green: delay < 120s (2min)
      120, '#eab308',  // yellow: 2-5min
      300, '#f97316',  // orange: 5-10min
      600, '#ef4444',  // red: >= 10min
    ],
    'circle-radius': 7,
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

export default function BusPositionLayer({ town, visible }: BusPositionLayerProps) {
  const [busData, setBusData] = useState<FeatureCollection>({
    type: 'FeatureCollection',
    features: [],
  });

  const loadData = useCallback(async () => {
    try {
      const json = await fetchLayer('transit', town);
      const filtered = filterBusPositions(json as unknown as FeatureCollection);
      setBusData(filtered);
    } catch {
      // silently ignore fetch errors; keep last data
    }
  }, [town]);

  useEffect(() => {
    if (!visible) return;
    loadData();
    // 30s refresh interval per REQ-BUS-06
    const id = setInterval(loadData, 30_000);
    return () => clearInterval(id);
  }, [visible, loadData]);

  if (!visible) return null;

  return (
    <Source
      id="bus-positions"
      type="geojson"
      data={busData}
    >
      <Layer {...circleLayer} />
      <Layer {...labelLayer} />
    </Source>
  );
}
