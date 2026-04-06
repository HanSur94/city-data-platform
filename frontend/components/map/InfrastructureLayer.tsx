'use client';
import { Source, Layer } from 'react-map-gl/maplibre';
import type { CircleLayerSpecification, SymbolLayerSpecification } from 'react-map-gl/maplibre';
import { useLayerData } from '@/hooks/useLayerData';
import WmsOverlayLayer from './WmsOverlayLayer';
import type { FeatureCollection } from 'geojson';

interface InfrastructureLayerProps {
  town: string;
  evChargingVisible: boolean;
  roadworksVisible: boolean;
  solarPotentialVisible: boolean;
}

function filterByCategory(data: FeatureCollection, category: string): FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: data.features.filter(
      f => f.properties?.category === category
    ),
  };
}

const SOLAR_POTENTIAL_WMS_URL =
  'https://rips-gdi.lubw.baden-wuerttemberg.de/arcgis/services/wms/UIS_0100000003700001/MapServer/WMSServer';

export default function InfrastructureLayer({
  town,
  evChargingVisible,
  roadworksVisible,
  solarPotentialVisible,
}: InfrastructureLayerProps) {
  const { data } = useLayerData('infrastructure', town);

  const makeClusterLayer = (id: string, source: string, color: string): CircleLayerSpecification => ({
    id,
    type: 'circle',
    source,
    filter: ['has', 'point_count'],
    layout: { visibility: 'visible' },
    paint: {
      'circle-color': color,
      'circle-radius': 14,
      'circle-stroke-width': 1,
      'circle-stroke-color': '#ffffff',
    },
  });

  const makeClusterCountLayer = (id: string, source: string): SymbolLayerSpecification => ({
    id,
    type: 'symbol',
    source,
    filter: ['has', 'point_count'],
    layout: {
      'text-field': '{point_count_abbreviated}',
      'text-font': ['Noto Sans Regular'],
      'text-size': 12,
      visibility: 'visible',
    },
  });

  const makePointsLayer = (id: string, source: string, color: string): CircleLayerSpecification => ({
    id,
    type: 'circle',
    source,
    filter: ['!', ['has', 'point_count']],
    layout: { visibility: 'visible' },
    paint: {
      'circle-color': color,
      'circle-radius': 7,
      'circle-stroke-width': 1,
      'circle-stroke-color': '#ffffff',
    },
  });

  const evData: FeatureCollection = data
    ? filterByCategory(data as FeatureCollection, 'ev_charging')
    : { type: 'FeatureCollection', features: [] };

  const roadworksData: FeatureCollection = data
    ? filterByCategory(data as FeatureCollection, 'roadwork')
    : { type: 'FeatureCollection', features: [] };

  return (
    <>
      {evChargingVisible && (
        <Source
          id="infrastructure-ev"
          type="geojson"
          data={evData}
          cluster={true}
          clusterMaxZoom={12}
          clusterRadius={50}
        >
          <Layer {...makeClusterLayer('infrastructure-ev-clusters', 'infrastructure-ev', '#a855f7')} />
          <Layer {...makeClusterCountLayer('infrastructure-ev-cluster-count', 'infrastructure-ev')} />
          <Layer {...makePointsLayer('infrastructure-ev-points', 'infrastructure-ev', '#a855f7')} />
        </Source>
      )}

      {roadworksVisible && (
        <Source
          id="infrastructure-roadworks"
          type="geojson"
          data={roadworksData}
          cluster={true}
          clusterMaxZoom={12}
          clusterRadius={50}
        >
          <Layer {...makeClusterLayer('infrastructure-roadworks-clusters', 'infrastructure-roadworks', '#f97316')} />
          <Layer {...makeClusterCountLayer('infrastructure-roadworks-cluster-count', 'infrastructure-roadworks')} />
          <Layer {...makePointsLayer('infrastructure-roadworks-points', 'infrastructure-roadworks', '#f97316')} />
        </Source>
      )}

      {/* Solar potential WMS overlay — graceful deferral if WMS unavailable */}
      <WmsOverlayLayer
        id="solar-potential-wms"
        wmsUrl={SOLAR_POTENTIAL_WMS_URL}
        layers="0"
        visible={solarPotentialVisible}
        opacity={0.7}
      />
    </>
  );
}
