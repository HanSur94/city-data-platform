'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import Map, { NavigationControl } from 'react-map-gl/maplibre';
import { Popup } from 'react-map-gl/maplibre';
import type { MapRef } from 'react-map-gl/maplibre';
import { Protocol } from 'pmtiles';
import maplibregl from 'maplibre-gl';
import { format } from 'date-fns';
import { buildMapStyle, buildOrthophotoStyle, buildSatelliteStyle } from '@/lib/map-styles';
import type { BaseLayer } from '@/lib/map-styles';
import TransitLayer from './TransitLayer';
import AQILayer from './AQILayer';
import AirQualityHeatmapLayer from './AirQualityHeatmapLayer';
import type { Pollutant } from './AirQualityHeatmapLayer';
import SensorPopupChart from './SensorPopupChart';
import WaterLayer from './WaterLayer';
import WmsOverlayLayer from './WmsOverlayLayer';
import TrafficLayer from './TrafficLayer';
import TrafficFlowLayer from './TrafficFlowLayer';
import AutobahnLayer from './AutobahnLayer';
import EnergyLayer from './EnergyLayer';
import SolarGlowLayer from './SolarGlowLayer';
import CommunityLayer from './CommunityLayer';
import InfrastructureLayer from './InfrastructureLayer';
import GeospatialOverlayLayer from './GeospatialOverlayLayer';
import BuildingsLayer from './BuildingsLayer';
import KocherLayer from './KocherLayer';
import FeaturePopup from './FeaturePopup';
import TrafficPopup from './TrafficPopup';
import TrafficFlowPopup from './TrafficFlowPopup';
import AutobahnPopup from './AutobahnPopup';
import EnergyPopup from './EnergyPopup';
import CommunityPopup from './CommunityPopup';
import SolarPopup from './SolarPopup';
import EvChargingPopup from './EvChargingPopup';
import EvChargingLiveLayer from './EvChargingLiveLayer';
import RoadworksPopup from './RoadworksPopup';
import KocherPopup from './KocherPopup';
import ParkingLayer from './ParkingLayer';
import ParkingPopup from './ParkingPopup';
import BusPositionLayer from './BusPositionLayer';
import BusRouteLayer from './BusRouteLayer';
import BusPopup from './BusPopup';
import NoiseWmsLayer from './NoiseWmsLayer';
import FernwaermeLayer from './FernwaermeLayer';
import DemographicsGridLayer from './DemographicsGridLayer';
import DemographicsPopup from './DemographicsPopup';
import HeatDemandLayer from './HeatDemandLayer';
import HeatDemandPopup from './HeatDemandPopup';
import UnifiedBuildingPopup from './UnifiedBuildingPopup';
import CyclingLayer from './CyclingLayer';
import CyclingPopup from './CyclingPopup';
import WeatherSkybox from './WeatherSkybox';
import LegendOverlay from './LegendOverlay';
import type { DemographicMetric } from './DemographicsGridLayer';
import type { LayerResponse } from '@/types/geojson';
import type GeoJSON from 'geojson';

// PMTiles file extracted from Protomaps daily build for Aalen bbox
// Extract command: npx pmtiles extract https://build.protomaps.com/{date}.pmtiles \
//   public/tiles/aalen.pmtiles --bbox=9.8,48.7,10.3,49.0
// Place in frontend/public/tiles/aalen.pmtiles
const PMTILES_URL = 'pmtiles:///tiles/aalen.pmtiles';

// Pre-build map styles at module scope — singleton objects with stable references.
// react-map-gl's _updateStyle() compares mapStyle by reference (===).
// If a new object is passed on every render, it calls map.setStyle() which tears down
// and rebuilds ALL layers, causing visible flicker. Module-scope singletons guarantee
// the same reference across all renders and component remounts.
const MAP_STYLES: Record<BaseLayer, ReturnType<typeof buildMapStyle>> = {
  osm: buildMapStyle(PMTILES_URL),
  orthophoto: buildOrthophotoStyle(),
  satellite: buildSatelliteStyle(),
};

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
  hiddenBusLines?: Set<string>;
  onBusLinesDiscovered?: (lines: string[]) => void;
  transitData: LayerResponse | null;
  airQualityData: LayerResponse | null;
  airQualityGridData?: LayerResponse | null;
  activePollutant?: Pollutant;
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
  trafficFlowVisible?: boolean;
  kocherVisible?: boolean;
  parkingVisible?: boolean;
  busPositionVisible?: boolean;
  solarGlowVisible?: boolean;
  roadNoiseVisible?: boolean;
  fernwaermeVisible?: boolean;
  demographicsVisible?: boolean;
  heatDemandVisible?: boolean;
  cyclingVisible?: boolean;
  noiseMetric?: 'lden' | 'lnight';
  demographicMetric?: DemographicMetric;
  weatherCondition?: string | null;
  baseLayer?: BaseLayer;
  cadastralVisible?: boolean;
  hillshadeVisible?: boolean;
  buildings3dVisible?: boolean;
  onFlyTo?: (lng: number, lat: number, zoom?: number) => void;
  /** Called when the map is ready, passing the flyTo function */
  onMapReady?: (flyTo: (lng: number, lat: number, zoom?: number) => void) => void;
  /** External popup to display (e.g. from search result selection) */
  externalPopup?: PopupInfo | null;
  onExternalPopupClear?: () => void;
}

export interface PopupInfo {
  longitude: number;
  latitude: number;
  feature: GeoJSON.Feature;
  domain: 'transit' | 'airQuality' | 'water' | 'traffic' | 'trafficFlow' | 'autobahn' | 'energy' | 'community' | 'evCharging' | 'roadworks' | 'kocher' | 'parking' | 'busPosition' | 'solarGlow' | 'demographics' | 'heatDemand' | 'cycling' | 'building';
}

export default function MapView({
  layerVisibility,
  transitData,
  airQualityData,
  airQualityGridData,
  activePollutant = 'pm25',
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
  trafficFlowVisible = false,
  kocherVisible = false,
  parkingVisible = false,
  busPositionVisible = false,
  solarGlowVisible = false,
  roadNoiseVisible = false,
  fernwaermeVisible = false,
  demographicsVisible = false,
  heatDemandVisible = false,
  cyclingVisible = false,
  noiseMetric = 'lden',
  demographicMetric = 'population',
  weatherCondition = null,
  baseLayer = 'osm',
  cadastralVisible = false,
  hillshadeVisible = false,
  buildings3dVisible = true,
  hiddenBusLines,
  onBusLinesDiscovered,
  onMapReady,
  externalPopup,
  onExternalPopupClear,
}: MapViewProps) {
  // Register PMTiles protocol BEFORE Map renders (Pitfall 3)
  // Register at module scope to avoid double-registration on re-renders
  const protocolRef = useRef<Protocol | null>(null);
  const mapRef = useRef<MapRef | null>(null);
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

  // Expose flyTo function to parent via onMapReady callback
  const flyToFn = useCallback((lng: number, lat: number, zoom = 17) => {
    mapRef.current?.flyTo({ center: [lng, lat], zoom, duration: 1500 });
  }, []);

  const mapReadyCalledRef = useRef(false);
  useEffect(() => {
    if (onMapReady && !mapReadyCalledRef.current) {
      mapReadyCalledRef.current = true;
      onMapReady(flyToFn);
    }
  }, [onMapReady, flyToFn]);

  // Handle external popup (e.g. from search result)
  useEffect(() => {
    if (externalPopup) {
      setPopupInfo(externalPopup);
      onExternalPopupClear?.();
    }
  }, [externalPopup, onExternalPopupClear]);

  // Auto-tilt map when 3D buildings are toggled
  useEffect(() => {
    if (buildings3dVisible) {
      mapRef.current?.easeTo({ pitch: 45, duration: 500 });
    } else {
      mapRef.current?.easeTo({ pitch: 0, duration: 500 });
    }
  }, [buildings3dVisible]);

  const [popupInfo, setPopupInfo] = useState<PopupInfo | null>(null);

  // Track bus popup position — update coordinates as the bus dot animates
  useEffect(() => {
    if (!popupInfo || popupInfo.domain !== 'busPosition') return;
    const tripId = popupInfo.feature.properties?.trip_id;
    if (!tripId) return;

    let raf: number;
    const track = () => {
      const map = mapRef.current?.getMap();
      if (!map) { raf = requestAnimationFrame(track); return; }
      const features = map.querySourceFeatures('bus-positions', {
        filter: ['==', ['get', 'trip_id'], tripId],
      });
      if (features.length > 0 && features[0].geometry.type === 'Point') {
        const [lng, lat] = features[0].geometry.coordinates;
        setPopupInfo((prev) => {
          if (!prev || prev.domain !== 'busPosition') return prev;
          // Skip update if position unchanged (within ~1m precision) — avoids full map re-render
          if (
            Math.abs(prev.longitude - lng) < 0.00001 &&
            Math.abs(prev.latitude - lat) < 0.00001
          ) {
            return prev; // Same reference = no re-render
          }
          return { ...prev, longitude: lng, latitude: lat, feature: features[0] as GeoJSON.Feature };
        });
      }
      raf = requestAnimationFrame(track);
    };
    raf = requestAnimationFrame(track);
    return () => cancelAnimationFrame(raf);
  }, [popupInfo?.domain, popupInfo?.feature.properties?.trip_id]);

  // Look up the pre-built singleton style — guaranteed stable reference.
  const mapStyle = MAP_STYLES[baseLayer];

  return (
    <div className="relative w-full h-full">
      <Map
        ref={mapRef}
        initialViewState={{
          longitude: 10.0918,
          latitude: 48.8374,
          zoom: 13,
          pitch: 45,
        }}
        minZoom={8}
        maxZoom={18}
        style={{ width: '100%', height: '100%' }}
        mapStyle={mapStyle}
        attributionControl={{ compact: false }}
        interactiveLayerIds={[
          'transit-stops', 'aqi-points', 'water-gauges', 'traffic-circles', 'traffic-flow-lines', 'autobahn-markers', 'energy-points', 'kocher-gauge', 'kocher-river-line',
          'community-schools-points', 'community-healthcare-points', 'community-parks-points', 'community-waste-points',
          'infrastructure-ev-points', 'infrastructure-roadworks-points', 'parking-points', 'bus-position-points',
          'solar-glow-points', 'ev-charging-live-points',
          'heat-demand-points', 'cycling-infra-lines',
          'buildings-3d',
        ]}
        onClick={(e) => {
          const feature = e.features?.[0];
          if (!feature || !e.lngLat) return;
          const layerId = feature.layer?.id ?? '';
          const domain: PopupInfo['domain'] = layerId === 'heat-demand-points'
            ? 'heatDemand'
            : layerId === 'cycling-infra-lines'
            ? 'cycling'
            : layerId === 'solar-glow-points'
            ? 'solarGlow'
            : layerId === 'ev-charging-live-points'
            ? 'evCharging'
            : layerId.startsWith('kocher')
            ? 'kocher'
            : layerId.startsWith('aqi')
            ? 'airQuality'
            : layerId.startsWith('water')
            ? 'water'
            : layerId === 'traffic-flow-lines'
            ? 'trafficFlow'
            : layerId.startsWith('traffic')
            ? 'traffic'
            : layerId.startsWith('autobahn')
            ? 'autobahn'
            : layerId.startsWith('energy')
            ? 'energy'
            : layerId === 'bus-position-points'
            ? 'busPosition'
            : layerId === 'parking-points'
            ? 'parking'
            : layerId === 'infrastructure-ev-points'
            ? 'evCharging'
            : layerId === 'infrastructure-roadworks-points'
            ? 'roadworks'
            : layerId.startsWith('community-')
            ? 'community'
            : layerId === 'buildings-3d'
            ? 'building'
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
        <AirQualityHeatmapLayer data={airQualityGridData ?? null} visible={layerVisibility.airQuality} activePollutant={activePollutant} />
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
        {trafficFlowVisible && (
          <TrafficFlowLayer town={town} visible={true} timestamp={historicalTimestamp} />
        )}
        {(autobahnVisible ?? layerVisibility.autobahn) && (
          <AutobahnLayer town={town} visible={true} />
        )}
        {(energyVisible ?? layerVisibility.energy) && (
          <EnergyLayer town={town} visible={true} />
        )}
        {solarGlowVisible && (
          <SolarGlowLayer town={town} visible={true} />
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
        {evChargingVisible && (
          <EvChargingLiveLayer town={town} visible={true} />
        )}
        {parkingVisible && (
          <ParkingLayer town={town} visible={true} />
        )}
        <BusRouteLayer town={town} visible={busPositionVisible} />
        <BusPositionLayer
          town={town}
          visible={busPositionVisible}
          hiddenLines={hiddenBusLines}
          onLinesDiscovered={onBusLinesDiscovered}
        />
        <NoiseWmsLayer visible={roadNoiseVisible} noiseMetric={noiseMetric} />
        <FernwaermeLayer visible={fernwaermeVisible} />
        {heatDemandVisible && (
          <HeatDemandLayer town={town} visible={true} />
        )}
        {cyclingVisible && (
          <CyclingLayer town={town} visible={true} />
        )}
        <DemographicsGridLayer town={town} visible={demographicsVisible} activeMetric={demographicMetric} />
        <GeospatialOverlayLayer
          cadastralVisible={cadastralVisible}
          hillshadeVisible={hillshadeVisible}
        />
        <BuildingsLayer visible={buildings3dVisible} />
        <NavigationControl position="top-right" showCompass={true} showZoom={true} visualizePitch={true} />
        <WeatherSkybox condition={weatherCondition ?? null} />
        <KocherLayer data={waterData ?? null} visible={kocherVisible} />
        {popupInfo && (
          <Popup
            longitude={popupInfo.longitude}
            latitude={popupInfo.latitude}
            onClose={() => setPopupInfo(null)}
            closeOnClick={false}
            maxWidth="320px"
            anchor="bottom"
          >
            {popupInfo.domain === 'airQuality' ? (
              <div>
                <FeaturePopup
                  feature={popupInfo.feature}
                  lastFetched={airQualityLastFetched}
                />
                <SensorPopupChart
                  featureId={String(popupInfo.feature.properties?.feature_id ?? popupInfo.feature.id ?? '')}
                  town={town}
                />
              </div>
            ) : popupInfo.domain === 'kocher' ? (
              <KocherPopup feature={popupInfo.feature} />
            ) : popupInfo.domain === 'trafficFlow' ? (
              <TrafficFlowPopup feature={popupInfo.feature} />
            ) : popupInfo.domain === 'traffic' ? (
              <TrafficPopup feature={popupInfo.feature} lastFetched={null} />
            ) : popupInfo.domain === 'autobahn' ? (
              <AutobahnPopup feature={popupInfo.feature} />
            ) : popupInfo.domain === 'solarGlow' ? (
              <SolarPopup feature={popupInfo.feature} />
            ) : popupInfo.domain === 'energy' ? (
              <EnergyPopup feature={popupInfo.feature} />
            ) : popupInfo.domain === 'community' ? (
              <CommunityPopup feature={popupInfo.feature} />
            ) : popupInfo.domain === 'evCharging' ? (
              <EvChargingPopup feature={popupInfo.feature} />
            ) : popupInfo.domain === 'busPosition' ? (
              <BusPopup feature={popupInfo.feature} />
            ) : popupInfo.domain === 'parking' ? (
              <ParkingPopup feature={popupInfo.feature} />
            ) : popupInfo.domain === 'roadworks' ? (
              <RoadworksPopup feature={popupInfo.feature} />
            ) : popupInfo.domain === 'heatDemand' ? (
              <HeatDemandPopup feature={popupInfo.feature} />
            ) : popupInfo.domain === 'cycling' ? (
              <CyclingPopup feature={popupInfo.feature} />
            ) : popupInfo.domain === 'demographics' ? (
              <DemographicsPopup feature={popupInfo.feature} />
            ) : popupInfo.domain === 'building' ? (
              <UnifiedBuildingPopup
                feature={popupInfo.feature}
                longitude={popupInfo.longitude}
                latitude={popupInfo.latitude}
              />
            ) : (
              <FeaturePopup
                feature={popupInfo.feature}
                lastFetched={
                  popupInfo.domain === 'water'
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
      <LegendOverlay
        layerVisibility={layerVisibility}
        trafficFlowVisible={trafficFlowVisible}
      />
    </div>
  );
}
