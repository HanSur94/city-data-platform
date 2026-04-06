'use client';
import { useMemo } from 'react';
import { Source, Layer } from 'react-map-gl/maplibre';
import type { CircleLayerSpecification, SymbolLayerSpecification, LineLayerSpecification } from 'react-map-gl/maplibre';
import type { LayerResponse } from '@/types/geojson';
import type { Feature } from 'geojson';

interface KocherLayerProps {
  data: LayerResponse | null;
  visible: boolean;
}

const visibility = (v: boolean): 'visible' | 'none' => (v ? 'visible' : 'none');

// Stage-based color expression for gauge pin
const stageColorExpr: CircleLayerSpecification['paint'] & Record<string, unknown> = {
  'circle-radius': 10,
  'circle-color': [
    'step',
    ['coalesce', ['get', 'stage'], 0],
    '#1565C0',  // stage 0: blue (normal)
    1, '#FFC107',  // stage 1: yellow
    2, '#FF9800',  // stage 2: orange
    3, '#F44336',  // stage 3-4: red
  ],
  'circle-opacity': 0.9,
  'circle-stroke-width': 2,
  'circle-stroke-color': '#ffffff',
};

// Gauge pin layer
const kocherGaugeLayer: CircleLayerSpecification = {
  id: 'kocher-gauge',
  type: 'circle',
  source: 'kocher-features',
  layout: { visibility: 'visible' },
  paint: stageColorExpr as CircleLayerSpecification['paint'],
};

// Label layer showing level_cm text below gauge pin
const kocherLabelsLayer: SymbolLayerSpecification = {
  id: 'kocher-gauge-label',
  type: 'symbol',
  source: 'kocher-features',
  layout: {
    visibility: 'visible',
    'text-field': ['concat', ['to-string', ['coalesce', ['get', 'level_cm'], '—']], ' cm'],
    'text-size': 10,
    'text-offset': [0, 1.6],
    'text-anchor': 'top',
  },
  paint: {
    'text-color': '#1565C0',
    'text-halo-color': '#ffffff',
    'text-halo-width': 1,
  },
};

// River line layer colored by warning stage
const kocherRiverLineLayer: LineLayerSpecification = {
  id: 'kocher-river-line',
  type: 'line',
  source: 'kocher-river',
  layout: {
    visibility: 'visible',
    'line-cap': 'round',
    'line-join': 'round',
  },
  paint: {
    'line-color': '#1565C0',
    'line-width': 4,
    'line-opacity': 0.7,
  },
};

// Static GeoJSON for Kocher river path from Oberkochen through Aalen to Huettlingen
const KOCHER_RIVER_GEOJSON: GeoJSON.FeatureCollection = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: {},
      geometry: {
        type: 'LineString',
        coordinates: [
          [10.1045, 48.7853],
          [10.0900, 48.7920],
          [10.0750, 48.8000],
          [10.0650, 48.8100],
          [10.0550, 48.8150],
          [10.0450, 48.8180],
          [10.0350, 48.8200],
          [10.0250, 48.8180],
          [10.0150, 48.8130],
          [10.0050, 48.8080],
          [9.9950, 48.8050],
        ],
      },
    },
  ],
};

export default function KocherLayer({ data, visible }: KocherLayerProps) {
  // Filter LHP features from the water data
  const lhpData = useMemo<LayerResponse | null>(() => {
    if (!data) return null;
    return {
      ...data,
      features: data.features.filter((f: Feature) => {
        const sourceId = f.properties?.source_id;
        return typeof sourceId === 'string' && sourceId.includes('lhp');
      }),
    };
  }, [data]);

  // Derive river line color from the first LHP feature's stage
  const riverLineColor = useMemo(() => {
    if (!lhpData?.features?.length) return '#1565C0';
    const stage = lhpData.features[0]?.properties?.stage;
    if (stage == null || stage === 0) return '#1565C0';
    if (stage === 1) return '#FFC107';
    if (stage === 2) return '#FF9800';
    return '#F44336';
  }, [lhpData]);

  if (!visible) return null;

  const vis = visibility(visible);

  return (
    <>
      {/* LHP gauge point */}
      {lhpData && lhpData.features.length > 0 && (
        <Source id="kocher-features" type="geojson" data={lhpData}>
          <Layer
            {...kocherGaugeLayer}
            layout={{ ...kocherGaugeLayer.layout, visibility: vis }}
          />
          <Layer
            {...kocherLabelsLayer}
            layout={{ ...kocherLabelsLayer.layout, visibility: vis }}
          />
        </Source>
      )}

      {/* Kocher river line */}
      <Source id="kocher-river" type="geojson" data={KOCHER_RIVER_GEOJSON}>
        <Layer
          {...kocherRiverLineLayer}
          layout={{ ...kocherRiverLineLayer.layout, visibility: vis }}
          paint={{
            ...kocherRiverLineLayer.paint,
            'line-color': riverLineColor,
          }}
        />
      </Source>
    </>
  );
}
