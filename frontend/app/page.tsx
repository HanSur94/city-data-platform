'use client';
import dynamic from 'next/dynamic';
import { useState } from 'react';
import Sidebar from '@/components/sidebar/Sidebar';

const MapView = dynamic(() => import('@/components/map/MapView'), {
  ssr: false,
  loading: () => <div className="flex-1 bg-slate-100 animate-pulse" />,
});

export default function Home() {
  const [layerVisibility, setLayerVisibility] = useState({
    transit: true,
    airQuality: true,
  });

  const toggleLayer = (layer: 'transit' | 'airQuality') => {
    setLayerVisibility(prev => ({ ...prev, [layer]: !prev[layer] }));
  };

  return (
    <main className="flex h-screen overflow-hidden">
      <Sidebar
        layerVisibility={layerVisibility}
        onToggleLayer={toggleLayer}
      />
      <div className="flex-1 relative">
        <MapView layerVisibility={layerVisibility} />
      </div>
    </main>
  );
}
