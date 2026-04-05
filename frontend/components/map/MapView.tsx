'use client';
import { useEffect, useRef } from 'react';
import Map from 'react-map-gl/maplibre';
import { Protocol } from 'pmtiles';
import maplibregl from 'maplibre-gl';
import { buildMapStyle } from '@/lib/map-styles';

// PMTiles file extracted from Protomaps daily build for Aalen bbox
// Extract command: npx pmtiles extract https://build.protomaps.com/{date}.pmtiles \
//   public/tiles/aalen.pmtiles --bbox=9.8,48.7,10.3,49.0
// Place in frontend/public/tiles/aalen.pmtiles
const PMTILES_URL = 'pmtiles:///tiles/aalen.pmtiles';

interface MapViewProps {
  layerVisibility: { transit: boolean; airQuality: boolean };
  children?: React.ReactNode;
}

export default function MapView({ layerVisibility, children }: MapViewProps) {
  // Register PMTiles protocol BEFORE Map renders (Pitfall 3)
  // Register at module scope to avoid double-registration on re-renders
  const protocolRef = useRef<Protocol | null>(null);
  useEffect(() => {
    if (protocolRef.current) return;
    const protocol = new Protocol();
    maplibregl.addProtocol('pmtiles', protocol.tile);
    protocolRef.current = protocol;
    return () => {
      maplibregl.removeProtocol('pmtiles');
      protocolRef.current = null;
    };
  }, []);

  const mapStyle = buildMapStyle(PMTILES_URL);

  return (
    <Map
      initialViewState={{
        longitude: 10.0918,
        latitude: 48.8374,
        zoom: 13,
      }}
      minZoom={8}
      maxZoom={18}
      style={{ width: '100%', height: '100%' }}
      mapStyle={mapStyle}
      attributionControl={{ compact: false }}
    >
      {children}
    </Map>
  );
}
