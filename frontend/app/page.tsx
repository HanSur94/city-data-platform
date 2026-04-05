'use client';
import dynamic from 'next/dynamic';
import { useState } from 'react';
import Sidebar from '@/components/sidebar/Sidebar';
import { useLayerData } from '@/hooks/useLayerData';
import type { LayerResponse } from '@/types/geojson';

const MapView = dynamic(() => import('@/components/map/MapView'), {
  ssr: false,
  loading: () => <div className="flex-1 bg-slate-100 animate-pulse" />,
});

export default function Home() {
  const [layerVisibility, setLayerVisibility] = useState({ transit: true, airQuality: true });
  const toggleLayer = (layer: 'transit' | 'airQuality') =>
    setLayerVisibility(prev => ({ ...prev, [layer]: !prev[layer] }));

  const transit = useLayerData('transit');
  const airQuality = useLayerData('air_quality');

  return (
    <main className="flex h-screen overflow-hidden">
      <Sidebar
        layerVisibility={layerVisibility}
        onToggleLayer={toggleLayer}
        transitError={transit.error}
        airQualityError={airQuality.error}
      />
      <div className="flex-1 relative">
        <MapView
          layerVisibility={layerVisibility}
          transitData={transit.data}
          airQualityData={airQuality.data}
          transitLastFetched={transit.lastFetched}
          airQualityLastFetched={airQuality.lastFetched}
        />
      </div>
    </main>
  );
}
