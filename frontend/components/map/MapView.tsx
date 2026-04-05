'use client';
import { useEffect, useRef, useState } from 'react';
import Map from 'react-map-gl/maplibre';
import { Popup } from 'react-map-gl/maplibre';
import { Protocol } from 'pmtiles';
import maplibregl from 'maplibre-gl';
import { buildMapStyle } from '@/lib/map-styles';
import TransitLayer from './TransitLayer';
import AQILayer from './AQILayer';
import FeaturePopup from './FeaturePopup';
import type { LayerResponse } from '@/types/geojson';
import type GeoJSON from 'geojson';

// PMTiles file extracted from Protomaps daily build for Aalen bbox
// Extract command: npx pmtiles extract https://build.protomaps.com/{date}.pmtiles \
//   public/tiles/aalen.pmtiles --bbox=9.8,48.7,10.3,49.0
// Place in frontend/public/tiles/aalen.pmtiles
const PMTILES_URL = 'pmtiles:///tiles/aalen.pmtiles';

interface MapViewProps {
  layerVisibility: { transit: boolean; airQuality: boolean };
  transitData: LayerResponse | null;
  airQualityData: LayerResponse | null;
  transitLastFetched: Date | null;
  airQualityLastFetched: Date | null;
}

interface PopupInfo {
  longitude: number;
  latitude: number;
  feature: GeoJSON.Feature;
  domain: 'transit' | 'airQuality';
}

export default function MapView({
  layerVisibility,
  transitData,
  airQualityData,
  transitLastFetched,
  airQualityLastFetched,
}: MapViewProps) {
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

  const [popupInfo, setPopupInfo] = useState<PopupInfo | null>(null);

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
      interactiveLayerIds={['transit-stops', 'aqi-points']}
      onClick={(e) => {
        const feature = e.features?.[0];
        if (!feature || !e.lngLat) return;
        const domain = feature.layer?.id?.startsWith('aqi') ? 'airQuality' : 'transit';
        setPopupInfo({
          longitude: e.lngLat.lng,
          latitude: e.lngLat.lat,
          feature: feature as GeoJSON.Feature,
          domain,
        });
      }}
    >
      <TransitLayer data={transitData} visible={layerVisibility.transit} />
      <AQILayer data={airQualityData} visible={layerVisibility.airQuality} />
      {popupInfo && (
        <Popup
          longitude={popupInfo.longitude}
          latitude={popupInfo.latitude}
          onClose={() => setPopupInfo(null)}
          closeOnClick={false}
          maxWidth="200px"
          anchor="bottom"
        >
          <FeaturePopup
            feature={popupInfo.feature}
            lastFetched={popupInfo.domain === 'airQuality' ? airQualityLastFetched : transitLastFetched}
          />
        </Popup>
      )}
    </Map>
  );
}
