'use client';
import { useEffect, useRef, useState } from 'react';
import Map from 'react-map-gl/maplibre';
import { Popup } from 'react-map-gl/maplibre';
import { Protocol } from 'pmtiles';
import maplibregl from 'maplibre-gl';
import { format } from 'date-fns';
import { buildMapStyle } from '@/lib/map-styles';
import TransitLayer from './TransitLayer';
import AQILayer from './AQILayer';
import WaterLayer from './WaterLayer';
import WmsOverlayLayer from './WmsOverlayLayer';
import TrafficLayer from './TrafficLayer';
import AutobahnLayer from './AutobahnLayer';
import EnergyLayer from './EnergyLayer';
import CommunityLayer from './CommunityLayer';
import InfrastructureLayer from './InfrastructureLayer';
import FeaturePopup from './FeaturePopup';
import TrafficPopup from './TrafficPopup';
import AutobahnPopup from './AutobahnPopup';
import EnergyPopup from './EnergyPopup';
import CommunityPopup from './CommunityPopup';
import EvChargingPopup from './EvChargingPopup';
import RoadworksPopup from './RoadworksPopup';
import type { LayerResponse } from '@/types/geojson';
import type GeoJSON from 'geojson';

// PMTiles file extracted from Protomaps daily build for Aalen bbox
// Extract command: npx pmtiles extract https://build.protomaps.com/{date}.pmtiles \
//   public/tiles/aalen.pmtiles --bbox=9.8,48.7,10.3,49.0
// Place in frontend/public/tiles/aalen.pmtiles
const PMTILES_URL = 'pmtiles:///tiles/aalen.pmtiles';

interface MapViewProps {
  layerVisibility: {
    transit: boolean;
    airQuality: boolean;
    water: boolean;
    floodHazard: boolean;
    railNoise: boolean;
    lubwEnv: boolean;
    traffic?: boolean;
    autobahn?: boolean;
    energy?: boolean;
  };
  transitData: LayerResponse | null;
  airQualityData: LayerResponse | null;
  transitLastFetched: Date | null;
  airQualityLastFetched: Date | null;
  waterData?: LayerResponse | null;
  waterLastFetched?: Date | null;
  /** When non-null, map is showing a historical snapshot at this timestamp */
  historicalTimestamp?: Date | null;
  town?: string;
  trafficVisible?: boolean;
  autobahnVisible?: boolean;
  mobiDataVisible?: boolean;
  energyVisible?: boolean;
  schoolsVisible?: boolean;
  healthcareVisible?: boolean;
  parksVisible?: boolean;
  wasteVisible?: boolean;
  evChargingVisible?: boolean;
  roadworksVisible?: boolean;
  solarPotentialVisible?: boolean;
}

interface PopupInfo {
  longitude: number;
  latitude: number;
  feature: GeoJSON.Feature;
  domain: 'transit' | 'airQuality' | 'water' | 'traffic' | 'autobahn' | 'energy' | 'community' | 'evCharging' | 'roadworks';
}

export default function MapView({
  layerVisibility,
  transitData,
  airQualityData,
  transitLastFetched,
  airQualityLastFetched,
  waterData,
  waterLastFetched,
  historicalTimestamp,
  town = 'aalen',
  trafficVisible = false,
  autobahnVisible = false,
  mobiDataVisible: _mobiDataVisible,
  energyVisible = false,
  schoolsVisible = false,
  healthcareVisible = false,
  parksVisible = false,
  wasteVisible = false,
  evChargingVisible = false,
  roadworksVisible = false,
  solarPotentialVisible = false,
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
    <div className="relative w-full h-full">
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
        interactiveLayerIds={[
          'transit-stops', 'aqi-points', 'water-gauges', 'traffic-circles', 'autobahn-markers', 'energy-points',
          'community-schools-points', 'community-healthcare-points', 'community-parks-points', 'community-waste-points',
          'infrastructure-ev-points', 'infrastructure-roadworks-points',
        ]}
        onClick={(e) => {
          const feature = e.features?.[0];
          if (!feature || !e.lngLat) return;
          const layerId = feature.layer?.id ?? '';
          const domain: PopupInfo['domain'] = layerId.startsWith('aqi')
            ? 'airQuality'
            : layerId.startsWith('water')
            ? 'water'
            : layerId.startsWith('traffic')
            ? 'traffic'
            : layerId.startsWith('autobahn')
            ? 'autobahn'
            : layerId.startsWith('energy')
            ? 'energy'
            : layerId === 'infrastructure-ev-points'
            ? 'evCharging'
            : layerId === 'infrastructure-roadworks-points'
            ? 'roadworks'
            : layerId.startsWith('community-')
            ? 'community'
            : 'transit';
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
        <WaterLayer
          data={waterData ?? null}
          visible={layerVisibility.water}
          lubwEnvVisible={layerVisibility.lubwEnv}
        />
        <WmsOverlayLayer
          id="flood-hazard"
          wmsUrl="https://rips-gdi.lubw.baden-wuerttemberg.de/arcgis/services/wms/UIS_0100000003900001/MapServer/WMSServer"
          layers="0,1"
          visible={layerVisibility.floodHazard}
          opacity={0.65}
        />
        <WmsOverlayLayer
          id="rail-noise"
          wmsUrl="https://geoinformation.eisenbahn-bundesamt.de/wms/isophonen"
          layers="isophonen_ek_lden"
          visible={layerVisibility.railNoise}
          opacity={0.6}
        />
        {(trafficVisible ?? layerVisibility.traffic) && (
          <TrafficLayer
            town={town}
            visible={true}
            timestamp={historicalTimestamp}
          />
        )}
        {(autobahnVisible ?? layerVisibility.autobahn) && (
          <AutobahnLayer town={town} visible={true} />
        )}
        {(energyVisible ?? layerVisibility.energy) && (
          <EnergyLayer town={town} visible={true} />
        )}
        <CommunityLayer
          town={town}
          schoolsVisible={schoolsVisible}
          healthcareVisible={healthcareVisible}
          parksVisible={parksVisible}
          wasteVisible={wasteVisible}
        />
        <InfrastructureLayer
          town={town}
          evChargingVisible={evChargingVisible}
          roadworksVisible={roadworksVisible}
          solarPotentialVisible={solarPotentialVisible}
        />
        {popupInfo && (
          <Popup
            longitude={popupInfo.longitude}
            latitude={popupInfo.latitude}
            onClose={() => setPopupInfo(null)}
            closeOnClick={false}
            maxWidth="200px"
            anchor="bottom"
          >
            {popupInfo.domain === 'traffic' ? (
              <TrafficPopup feature={popupInfo.feature} lastFetched={null} />
            ) : popupInfo.domain === 'autobahn' ? (
              <AutobahnPopup feature={popupInfo.feature} />
            ) : popupInfo.domain === 'energy' ? (
              <EnergyPopup feature={popupInfo.feature} />
            ) : popupInfo.domain === 'community' ? (
              <CommunityPopup feature={popupInfo.feature} />
            ) : popupInfo.domain === 'evCharging' ? (
              <EvChargingPopup feature={popupInfo.feature} />
            ) : popupInfo.domain === 'roadworks' ? (
              <RoadworksPopup feature={popupInfo.feature} />
            ) : (
              <FeaturePopup
                feature={popupInfo.feature}
                lastFetched={
                  popupInfo.domain === 'airQuality'
                    ? airQualityLastFetched
                    : popupInfo.domain === 'water'
                    ? (waterLastFetched ?? null)
                    : transitLastFetched
                }
              />
            )}
          </Popup>
        )}
      </Map>
      {historicalTimestamp && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 bg-background/90 border rounded px-3 py-1 text-[12px] font-medium pointer-events-none">
          {format(historicalTimestamp, 'dd.MM.yyyy HH:mm')} Uhr
        </div>
      )}
    </div>
  );
}
