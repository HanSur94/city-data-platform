'use client';
import { useState, useEffect, useCallback } from 'react';
import { Source, Layer } from 'react-map-gl/maplibre';
import type { LineLayerSpecification } from 'react-map-gl/maplibre';
import type { FeatureCollection } from 'geojson';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

interface CyclingLayerProps {
  town: string;
  visible: boolean;
}

const INFRA_TYPE_COLORS: Record<string, string> = {
  separated: '#1a7c28',
  lane: '#5cb85c',
  advisory: '#f0ad4e',
  shared: '#e67e22',
  none: '#d9534f',
};

const cyclingLineLayer: LineLayerSpecification = {
  id: 'cycling-infra-lines',
  type: 'line',
  source: 'cycling-infra',
  layout: {
    visibility: 'visible',
    'line-cap': 'round',
    'line-join': 'round',
  },
  paint: {
    'line-color': [
      'match',
      ['get', 'infra_type'],
      'separated', INFRA_TYPE_COLORS.separated,
      'lane', INFRA_TYPE_COLORS.lane,
      'advisory', INFRA_TYPE_COLORS.advisory,
      'shared', INFRA_TYPE_COLORS.shared,
      'none', INFRA_TYPE_COLORS.none,
      '#999999', // fallback
    ],
    'line-width': [
      'match',
      ['get', 'infra_type'],
      'separated', 3,
      'lane', 3,
      2, // default for advisory, shared, none
    ],
    'line-opacity': 0.85,
  },
};

export default function CyclingLayer({ town, visible }: CyclingLayerProps) {
  const [data, setData] = useState<FeatureCollection>({
    type: 'FeatureCollection',
    features: [],
  });

  const loadData = useCallback(async () => {
    try {
      const params = new URLSearchParams({ town, source: 'cycling' });
      const res = await fetch(`${API_BASE}/api/layers/infrastructure?${params}`);
      if (!res.ok) return;
      const json = await res.json() as FeatureCollection;
      setData(json);
    } catch {
      // silently ignore fetch errors; keep last data
    }
  }, [town]);

  useEffect(() => {
    if (!visible) return;
    loadData();
    const id = setInterval(loadData, 60_000);
    return () => clearInterval(id);
  }, [visible, loadData]);

  if (!visible) return null;

  return (
    <Source id="cycling-infra" type="geojson" data={data}>
      <Layer {...cyclingLineLayer} />
    </Source>
  );
}
