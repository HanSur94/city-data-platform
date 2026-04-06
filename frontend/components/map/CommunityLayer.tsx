'use client';
import { Source, Layer } from 'react-map-gl/maplibre';
import type { CircleLayerSpecification, SymbolLayerSpecification } from 'react-map-gl/maplibre';
import { useLayerData } from '@/hooks/useLayerData';
import type { FeatureCollection } from 'geojson';

interface CommunityLayerProps {
  town: string;
  schoolsVisible: boolean;
  healthcareVisible: boolean;
  parksVisible: boolean;
  wasteVisible: boolean;
}

function filterByCategory(data: FeatureCollection, category: string): FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: data.features.filter(
      f => f.properties?.category === category
    ),
  };
}

export default function CommunityLayer({
  town,
  schoolsVisible,
  healthcareVisible,
  parksVisible,
  wasteVisible,
}: CommunityLayerProps) {
  const { data } = useLayerData('community', town);

  if (!data) return null;

  const schoolsData = filterByCategory(data as FeatureCollection, 'school');
  const healthcareData = filterByCategory(data as FeatureCollection, 'healthcare');
  const parksData = filterByCategory(data as FeatureCollection, 'park');
  const wasteData = filterByCategory(data as FeatureCollection, 'waste');

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

  return (
    <>
      {schoolsVisible && (
        <Source
          id="community-schools"
          type="geojson"
          data={schoolsData}
          cluster={true}
          clusterMaxZoom={12}
          clusterRadius={50}
        >
          <Layer {...makeClusterLayer('community-schools-clusters', 'community-schools', '#3b82f6')} />
          <Layer {...makeClusterCountLayer('community-schools-cluster-count', 'community-schools')} />
          <Layer {...makePointsLayer('community-schools-points', 'community-schools', '#3b82f6')} />
        </Source>
      )}

      {healthcareVisible && (
        <Source
          id="community-healthcare"
          type="geojson"
          data={healthcareData}
          cluster={true}
          clusterMaxZoom={12}
          clusterRadius={50}
        >
          <Layer {...makeClusterLayer('community-healthcare-clusters', 'community-healthcare', '#ef4444')} />
          <Layer {...makeClusterCountLayer('community-healthcare-cluster-count', 'community-healthcare')} />
          <Layer {...makePointsLayer('community-healthcare-points', 'community-healthcare', '#ef4444')} />
        </Source>
      )}

      {parksVisible && (
        <Source
          id="community-parks"
          type="geojson"
          data={parksData}
          cluster={true}
          clusterMaxZoom={12}
          clusterRadius={50}
        >
          <Layer {...makeClusterLayer('community-parks-clusters', 'community-parks', '#22c55e')} />
          <Layer {...makeClusterCountLayer('community-parks-cluster-count', 'community-parks')} />
          <Layer {...makePointsLayer('community-parks-points', 'community-parks', '#22c55e')} />
        </Source>
      )}

      {wasteVisible && (
        <Source
          id="community-waste"
          type="geojson"
          data={wasteData}
          cluster={true}
          clusterMaxZoom={12}
          clusterRadius={50}
        >
          <Layer {...makeClusterLayer('community-waste-clusters', 'community-waste', '#92400e')} />
          <Layer {...makeClusterCountLayer('community-waste-cluster-count', 'community-waste')} />
          <Layer {...makePointsLayer('community-waste-points', 'community-waste', '#92400e')} />
        </Source>
      )}
    </>
  );
}
