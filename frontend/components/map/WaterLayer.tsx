'use client';
import { Source, Layer } from 'react-map-gl/maplibre';
import type { CircleLayerSpecification, SymbolLayerSpecification } from 'react-map-gl/maplibre';
import type { LayerResponse } from '@/types/geojson';

interface WaterLayerProps {
  data: LayerResponse | null;
  visible: boolean;
  lubwEnvVisible?: boolean;
}

const visibility = (v: boolean): 'visible' | 'none' => (v ? 'visible' : 'none');

// Pegelonline gauge stations — blue circles
const waterGaugesLayer: CircleLayerSpecification = {
  id: 'water-gauges',
  type: 'circle',
  source: 'water-features',
  filter: ['in', 'pegelonline', ['get', 'source_id']],
  layout: { visibility: 'visible' },
  paint: {
    'circle-radius': 8,
    'circle-color': '#1565C0',
    'circle-opacity': 0.85,
    'circle-stroke-width': 1,
    'circle-stroke-color': '#ffffff',
  },
};

// Naturschutzgebiet features — green circles
const waterNaturschutzLayer: CircleLayerSpecification = {
  id: 'water-naturschutz',
  type: 'circle',
  source: 'water-features',
  filter: ['in', 'naturschutz', ['get', 'source_id']],
  layout: { visibility: 'visible' },
  paint: {
    'circle-radius': 6,
    'circle-color': '#2E7D32',
    'circle-opacity': 0.8,
    'circle-stroke-width': 1,
    'circle-stroke-color': '#ffffff',
  },
};

// Wasserschutzgebiet features — teal circles
const waterWasserschutzLayer: CircleLayerSpecification = {
  id: 'water-wasserschutz',
  type: 'circle',
  source: 'water-features',
  filter: ['in', 'wasserschutz', ['get', 'source_id']],
  layout: { visibility: 'visible' },
  paint: {
    'circle-radius': 6,
    'circle-color': '#00796B',
    'circle-opacity': 0.8,
    'circle-stroke-width': 1,
    'circle-stroke-color': '#ffffff',
  },
};

// Text labels showing level_cm for gauge stations
const waterLabelsLayer: SymbolLayerSpecification = {
  id: 'water-labels',
  type: 'symbol',
  source: 'water-features',
  filter: ['in', 'pegelonline', ['get', 'source_id']],
  layout: {
    visibility: 'visible',
    'text-field': ['concat', ['to-string', ['get', 'level_cm']], 'cm'],
    'text-size': 10,
    'text-offset': [0, 1.4],
    'text-anchor': 'top',
  },
  paint: {
    'text-color': '#1565C0',
    'text-halo-color': '#ffffff',
    'text-halo-width': 1,
  },
};

export default function WaterLayer({ data, visible, lubwEnvVisible = true }: WaterLayerProps) {
  if (!data) return null;

  const gaugeVis = visibility(visible);
  const envVis = visibility(visible && lubwEnvVisible);

  return (
    <Source id="water-features" type="geojson" data={data}>
      <Layer
        {...waterGaugesLayer}
        layout={{ ...waterGaugesLayer.layout, visibility: gaugeVis }}
      />
      <Layer
        {...waterLabelsLayer}
        layout={{ ...waterLabelsLayer.layout, visibility: gaugeVis }}
      />
      <Layer
        {...waterNaturschutzLayer}
        layout={{ ...waterNaturschutzLayer.layout, visibility: envVis }}
      />
      <Layer
        {...waterWasserschutzLayer}
        layout={{ ...waterWasserschutzLayer.layout, visibility: envVis }}
      />
    </Source>
  );
}
