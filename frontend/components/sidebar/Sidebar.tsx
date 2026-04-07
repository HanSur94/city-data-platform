'use client';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Layers, ChevronLeft, ChevronRight } from 'lucide-react';
import LayerToggle from './LayerToggle';
import PollutantToggle from './PollutantToggle';
import AQILegend from './AQILegend';
import type { Pollutant } from '@/components/map/AirQualityHeatmapLayer';
import TransitLegend from './TransitLegend';
import WaterLegend from './WaterLegend';
import TrafficLegend from './TrafficLegend';
import EnergyLegend from './EnergyLegend';
import HeatDemandLegend from './HeatDemandLegend';
import CyclingLegend from './CyclingLegend';
import FeatureSearch from './FeatureSearch';
import type { SearchResult } from './FeatureSearch';
import { LAYER_METADATA } from '@/lib/layer-metadata';
import { useLayerMetadata } from '@/hooks/useLayerMetadata';

import type { DemographicMetric } from '@/components/map/DemographicsGridLayer';

interface SidebarProps {
  town: string;
  onFeatureSelect: (result: SearchResult) => void;
  layerVisibility: {
    transit: boolean;
    airQuality: boolean;
    water: boolean;
    floodHazard: boolean;
    railNoise: boolean;
    lubwEnv: boolean;
    traffic: boolean;
    autobahn: boolean;
    mobiData: boolean;
    energy: boolean;
    schools?: boolean;
    healthcare?: boolean;
    parks?: boolean;
    waste?: boolean;
    evCharging?: boolean;
    roadworks?: boolean;
    solarPotential?: boolean;
    trafficFlow?: boolean;
    kocher?: boolean;
    parking?: boolean;
    busPosition?: boolean;
    solarGlow?: boolean;
    roadNoise?: boolean;
    fernwaerme?: boolean;
    demographics?: boolean;
    heatDemand?: boolean;
    cycling?: boolean;
  };
  onToggleLayer: (layer: 'transit' | 'airQuality' | 'water' | 'floodHazard' | 'railNoise' | 'lubwEnv' | 'traffic' | 'autobahn' | 'mobiData' | 'energy' | 'schools' | 'healthcare' | 'parks' | 'waste' | 'evCharging' | 'roadworks' | 'solarPotential' | 'trafficFlow' | 'cadastral' | 'hillshade' | 'buildings3d' | 'kocher' | 'parking' | 'busPosition' | 'solarGlow' | 'roadNoise' | 'fernwaerme' | 'demographics' | 'heatDemand' | 'cycling') => void;
  transitError?: boolean;
  airQualityError?: boolean;
  trafficError?: boolean;
  energyError?: boolean;
  baseLayer: 'osm' | 'orthophoto' | 'satellite';
  onBaseLayerChange: (base: 'osm' | 'orthophoto' | 'satellite') => void;
  cadastralVisible?: boolean;
  hillshadeVisible?: boolean;
  buildings3dVisible?: boolean;
  activePollutant?: Pollutant;
  onPollutantChange?: (pollutant: Pollutant) => void;
  noiseMetric?: 'lden' | 'lnight';
  onNoiseMetricChange?: (metric: 'lden' | 'lnight') => void;
  demographicMetric?: DemographicMetric;
  onDemographicMetricChange?: (metric: DemographicMetric) => void;
  collapsed?: boolean;
  onToggle?: () => void;
}

export default function Sidebar({ town, onFeatureSelect, layerVisibility, onToggleLayer, transitError, airQualityError, trafficError, energyError, baseLayer, onBaseLayerChange, cadastralVisible, hillshadeVisible, buildings3dVisible, activePollutant, onPollutantChange, noiseMetric, onNoiseMetricChange, demographicMetric, onDemographicMetricChange, collapsed, onToggle }: SidebarProps) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { layerMeta } = useLayerMetadata();

  const content = (
    <div className="flex flex-col h-full bg-white w-[280px]">
      {/* Header */}
      <div className="px-4 pt-8 pb-6">
        <h1 className="text-[16px] font-semibold leading-[1.2]">Stadtdaten Aalen</h1>
      </div>
      <Separator />

      {/* Feature search */}
      <div className="pt-4">
        <FeatureSearch town={town} onSelect={onFeatureSelect} />
      </div>

      <Separator />

      {/* Layer toggles */}
      <div className="pt-6">
        <p className="px-4 text-[12px] font-normal text-muted-foreground uppercase tracking-wide mb-2">
          Ebenen
        </p>
        <LayerToggle
          id="transit-toggle"
          label="OEPNV (Bus & Bahn)"
          checked={layerVisibility.transit}
          onCheckedChange={() => onToggleLayer('transit')}
          freshnessError={transitError}
          layerKey="transit"
          dataType={LAYER_METADATA['transit']?.dataType}
          isStale={layerMeta['transit']?.isStale}
          metadata={LAYER_METADATA['transit']}
          lastUpdated={layerMeta['transit']?.lastUpdated}
        />
        <LayerToggle
          id="bus-position-toggle"
          label="Bus-Positionen (live)"
          checked={layerVisibility.busPosition ?? false}
          onCheckedChange={() => onToggleLayer('busPosition')}
          layerKey="busPosition"
          dataType={LAYER_METADATA['busPosition']?.dataType}
          isStale={layerMeta['busPosition']?.isStale}
          metadata={LAYER_METADATA['busPosition']}
          lastUpdated={layerMeta['busPosition']?.lastUpdated}
        />
        <LayerToggle
          id="aqi-toggle"
          label="Luftqualitaet"
          checked={layerVisibility.airQuality}
          onCheckedChange={() => onToggleLayer('airQuality')}
          freshnessError={airQualityError}
          layerKey="airQuality"
          dataType={LAYER_METADATA['airQuality']?.dataType}
          isStale={layerMeta['airQuality']?.isStale}
          metadata={LAYER_METADATA['airQuality']}
          lastUpdated={layerMeta['airQuality']?.lastUpdated}
        />
        {layerVisibility.airQuality && activePollutant && onPollutantChange && (
          <PollutantToggle activePollutant={activePollutant} onPollutantChange={onPollutantChange} />
        )}
        <LayerToggle
          id="water-toggle"
          label="Pegel & Gewaesser"
          checked={layerVisibility.water}
          onCheckedChange={() => onToggleLayer('water')}
          layerKey="water"
          dataType={LAYER_METADATA['water']?.dataType}
          isStale={layerMeta['water']?.isStale}
          metadata={LAYER_METADATA['water']}
          lastUpdated={layerMeta['water']?.lastUpdated}
        />
        <LayerToggle
          id="kocher-toggle"
          label="Kocher Pegel (LHP)"
          checked={layerVisibility.kocher ?? false}
          onCheckedChange={() => onToggleLayer('kocher')}
          layerKey="kocher"
          dataType={LAYER_METADATA['kocher']?.dataType}
          isStale={layerMeta['kocher']?.isStale}
          metadata={LAYER_METADATA['kocher']}
          lastUpdated={layerMeta['kocher']?.lastUpdated}
        />
        <LayerToggle
          id="flood-toggle"
          label="Hochwassergefahr (HQ100)"
          checked={layerVisibility.floodHazard}
          onCheckedChange={() => onToggleLayer('floodHazard')}
        />
        <LayerToggle
          id="rail-noise-toggle"
          label="Bahnlaerm (Lden)"
          checked={layerVisibility.railNoise}
          onCheckedChange={() => onToggleLayer('railNoise')}
        />
        <LayerToggle
          id="lubw-env-toggle"
          label="Schutzgebiete (LUBW)"
          checked={layerVisibility.lubwEnv}
          onCheckedChange={() => onToggleLayer('lubwEnv')}
        />
        <LayerToggle
          id="road-noise-toggle"
          label="Strassenlaerm (LUBW)"
          checked={layerVisibility.roadNoise ?? false}
          onCheckedChange={() => onToggleLayer('roadNoise')}
          layerKey="roadNoise"
          dataType={LAYER_METADATA['roadNoise']?.dataType}
          isStale={layerMeta['roadNoise']?.isStale}
          metadata={LAYER_METADATA['roadNoise']}
          lastUpdated={layerMeta['roadNoise']?.lastUpdated}
        />
        {layerVisibility.roadNoise && noiseMetric && onNoiseMetricChange && (
          <div className="px-6 pb-1 flex gap-2">
            {(['lden', 'lnight'] as const).map((m) => (
              <button
                key={m}
                className={`text-[11px] px-2 py-0.5 rounded ${noiseMetric === m ? 'bg-primary text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
                onClick={() => onNoiseMetricChange(m)}
              >
                {m === 'lden' ? 'LDEN (Tag)' : 'LNight (Nacht)'}
              </button>
            ))}
          </div>
        )}
      </div>

      <Separator className="mt-6" />

      {/* Verkehr group */}
      <div className="pt-2">
        <p className="px-4 text-[12px] font-normal text-muted-foreground uppercase tracking-wide mb-2 mt-6">Verkehr</p>
        <LayerToggle
          id="traffic-toggle"
          label="Verkehrszaehlstellen (BASt)"
          checked={layerVisibility.traffic}
          onCheckedChange={() => onToggleLayer('traffic')}
          freshnessError={trafficError}
          layerKey="traffic"
          dataType={LAYER_METADATA['traffic']?.dataType}
          isStale={layerMeta['traffic']?.isStale}
          metadata={LAYER_METADATA['traffic']}
          lastUpdated={layerMeta['traffic']?.lastUpdated}
        />
        <LayerToggle
          id="traffic-flow-toggle"
          label="Verkehrsfluss (TomTom)"
          checked={layerVisibility.trafficFlow ?? false}
          onCheckedChange={() => onToggleLayer('trafficFlow')}
          layerKey="trafficFlow"
          dataType={LAYER_METADATA['trafficFlow']?.dataType}
          isStale={layerMeta['trafficFlow']?.isStale}
          metadata={LAYER_METADATA['trafficFlow']}
          lastUpdated={layerMeta['trafficFlow']?.lastUpdated}
        />
        <LayerToggle
          id="autobahn-toggle"
          label="Autobahn-Stoerungen (A7/A6)"
          checked={layerVisibility.autobahn}
          onCheckedChange={() => onToggleLayer('autobahn')}
          layerKey="autobahn"
          dataType={LAYER_METADATA['autobahn']?.dataType}
          isStale={layerMeta['autobahn']?.isStale}
          metadata={LAYER_METADATA['autobahn']}
          lastUpdated={layerMeta['autobahn']?.lastUpdated}
        />
        <LayerToggle
          id="mobidata-toggle"
          label="MobiData BW"
          checked={layerVisibility.mobiData}
          onCheckedChange={() => onToggleLayer('mobiData')}
          layerKey="mobiData"
          dataType={LAYER_METADATA['mobiData']?.dataType}
          isStale={layerMeta['mobiData']?.isStale}
          metadata={LAYER_METADATA['mobiData']}
          lastUpdated={layerMeta['mobiData']?.lastUpdated}
        />
        <LayerToggle
          id="cycling-toggle"
          label="Radinfrastruktur (OSM)"
          checked={layerVisibility.cycling ?? false}
          onCheckedChange={() => onToggleLayer('cycling')}
          layerKey="cycling"
          dataType={LAYER_METADATA['cycling']?.dataType}
          isStale={layerMeta['cycling']?.isStale}
          metadata={LAYER_METADATA['cycling']}
          lastUpdated={layerMeta['cycling']?.lastUpdated}
        />
      </div>

      <Separator className="mt-6" />

      {/* Energie group */}
      <div className="pt-2">
        <p className="px-4 text-[12px] font-normal text-muted-foreground uppercase tracking-wide mb-2 mt-6">Energie</p>
        <LayerToggle
          id="energy-toggle"
          label="Erneuerbare Anlagen (MaStR)"
          checked={layerVisibility.energy}
          onCheckedChange={() => onToggleLayer('energy')}
          freshnessError={energyError}
          layerKey="energy"
          dataType={LAYER_METADATA['energy']?.dataType}
          isStale={layerMeta['energy']?.isStale}
          metadata={LAYER_METADATA['energy']}
          lastUpdated={layerMeta['energy']?.lastUpdated}
        />
        <LayerToggle
          id="solar-glow-toggle"
          label="Solar-Erzeugung (live)"
          checked={layerVisibility.solarGlow ?? false}
          onCheckedChange={() => onToggleLayer('solarGlow')}
          layerKey="solarGlow"
          dataType={LAYER_METADATA['solarGlow']?.dataType}
          isStale={layerMeta['solarGlow']?.isStale}
          metadata={LAYER_METADATA['solarGlow']}
          lastUpdated={layerMeta['solarGlow']?.lastUpdated}
        />
        <LayerToggle
          id="fernwaerme-toggle"
          label="Fernwaerme-Netz"
          checked={layerVisibility.fernwaerme ?? false}
          onCheckedChange={() => onToggleLayer('fernwaerme')}
          layerKey="fernwaerme"
          dataType={LAYER_METADATA['fernwaerme']?.dataType}
          isStale={layerMeta['fernwaerme']?.isStale}
          metadata={LAYER_METADATA['fernwaerme']}
          lastUpdated={layerMeta['fernwaerme']?.lastUpdated}
        />
        <LayerToggle
          id="heat-demand-toggle"
          label="Waermebedarf (KEA-BW)"
          checked={layerVisibility.heatDemand ?? false}
          onCheckedChange={() => onToggleLayer('heatDemand')}
          layerKey="heatDemand"
          dataType={LAYER_METADATA['heatDemand']?.dataType}
          isStale={layerMeta['heatDemand']?.isStale}
          metadata={LAYER_METADATA['heatDemand']}
          lastUpdated={layerMeta['heatDemand']?.lastUpdated}
        />
      </div>

      <Separator className="mt-6" />

      {/* Gemeinwesen group */}
      <div className="pt-2">
        <p className="px-4 text-[12px] font-normal text-muted-foreground uppercase tracking-wide mb-2 mt-6">Gemeinwesen</p>
        <LayerToggle
          id="schools-toggle"
          label="Schulen & Kitas"
          checked={layerVisibility.schools ?? false}
          onCheckedChange={() => onToggleLayer('schools')}
          layerKey="schools"
          dataType={LAYER_METADATA['schools']?.dataType}
          isStale={layerMeta['schools']?.isStale}
          metadata={LAYER_METADATA['schools']}
          lastUpdated={layerMeta['schools']?.lastUpdated}
        />
        <LayerToggle
          id="healthcare-toggle"
          label="Gesundheit"
          checked={layerVisibility.healthcare ?? false}
          onCheckedChange={() => onToggleLayer('healthcare')}
          layerKey="healthcare"
          dataType={LAYER_METADATA['healthcare']?.dataType}
          isStale={layerMeta['healthcare']?.isStale}
          metadata={LAYER_METADATA['healthcare']}
          lastUpdated={layerMeta['healthcare']?.lastUpdated}
        />
        <LayerToggle
          id="parks-toggle"
          label="Parks & Spielplaetze"
          checked={layerVisibility.parks ?? false}
          onCheckedChange={() => onToggleLayer('parks')}
          layerKey="parks"
          dataType={LAYER_METADATA['parks']?.dataType}
          isStale={layerMeta['parks']?.isStale}
          metadata={LAYER_METADATA['parks']}
          lastUpdated={layerMeta['parks']?.lastUpdated}
        />
        <LayerToggle
          id="waste-toggle"
          label="Wertstoffhoefe"
          checked={layerVisibility.waste ?? false}
          onCheckedChange={() => onToggleLayer('waste')}
          layerKey="waste"
          dataType={LAYER_METADATA['waste']?.dataType}
          isStale={layerMeta['waste']?.isStale}
          metadata={LAYER_METADATA['waste']}
          lastUpdated={layerMeta['waste']?.lastUpdated}
        />
        <LayerToggle
          id="demographics-toggle"
          label="Demografie (Zensus)"
          checked={layerVisibility.demographics ?? false}
          onCheckedChange={() => onToggleLayer('demographics')}
          layerKey="demographics"
          dataType={LAYER_METADATA['demographics']?.dataType}
          isStale={layerMeta['demographics']?.isStale}
          metadata={LAYER_METADATA['demographics']}
          lastUpdated={layerMeta['demographics']?.lastUpdated}
        />
        {layerVisibility.demographics && demographicMetric && onDemographicMetricChange && (
          <div className="px-6 pb-1 flex flex-wrap gap-1">
            {([
              { key: 'population' as const, label: 'Einwohner' },
              { key: 'age' as const, label: 'Alter' },
              { key: 'rent' as const, label: 'Miete' },
              { key: 'heating' as const, label: 'Heizung' },
            ]).map(({ key, label }) => (
              <button
                key={key}
                className={`text-[11px] px-2 py-0.5 rounded ${demographicMetric === key ? 'bg-primary text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
                onClick={() => onDemographicMetricChange(key)}
              >
                {label}
              </button>
            ))}
          </div>
        )}
      </div>

      <Separator className="mt-6" />

      {/* Infrastruktur group */}
      <div className="pt-2">
        <p className="px-4 text-[12px] font-normal text-muted-foreground uppercase tracking-wide mb-2 mt-6">Infrastruktur</p>
        <LayerToggle
          id="roadworks-toggle"
          label="Baustellen (OSM)"
          checked={layerVisibility.roadworks ?? false}
          onCheckedChange={() => onToggleLayer('roadworks')}
          layerKey="roadworks"
          dataType={LAYER_METADATA['roadworks']?.dataType}
          isStale={layerMeta['roadworks']?.isStale}
          metadata={LAYER_METADATA['roadworks']}
          lastUpdated={layerMeta['roadworks']?.lastUpdated}
        />
        <LayerToggle
          id="ev-toggle"
          label="E-Ladesaeulen (live)"
          checked={layerVisibility.evCharging ?? false}
          onCheckedChange={() => onToggleLayer('evCharging')}
          layerKey="evCharging"
          dataType={LAYER_METADATA['evCharging']?.dataType}
          isStale={layerMeta['evCharging']?.isStale}
          metadata={LAYER_METADATA['evCharging']}
          lastUpdated={layerMeta['evCharging']?.lastUpdated}
        />
        <LayerToggle
          id="solar-toggle"
          label="Solarpotenzial Daecher"
          checked={layerVisibility.solarPotential ?? false}
          onCheckedChange={() => onToggleLayer('solarPotential')}
          layerKey="solarPotential"
          dataType={LAYER_METADATA['solarPotential']?.dataType}
          isStale={layerMeta['solarPotential']?.isStale}
          metadata={LAYER_METADATA['solarPotential']}
          lastUpdated={layerMeta['solarPotential']?.lastUpdated}
        />
        <LayerToggle
          id="parking-toggle"
          label="Parkhaeuser"
          checked={layerVisibility.parking ?? false}
          onCheckedChange={() => onToggleLayer('parking')}
          layerKey="parking"
          dataType={LAYER_METADATA['parking']?.dataType}
          isStale={layerMeta['parking']?.isStale}
          metadata={LAYER_METADATA['parking']}
          lastUpdated={layerMeta['parking']?.lastUpdated}
        />
      </div>

      <Separator className="mt-6" />

      {/* Geospatial group */}
      <div className="pt-2">
        <p className="px-4 text-[12px] font-normal text-muted-foreground uppercase tracking-wide mb-2 mt-6">Geospatial</p>
        <p className="px-4 text-[11px] text-muted-foreground mb-1">Basiskarte</p>
        {(['osm', 'orthophoto', 'satellite'] as const).map((base) => (
          <label key={base} className="flex items-center gap-2 px-4 py-1.5 cursor-pointer hover:bg-slate-50">
            <input
              type="radio"
              name="base-layer"
              value={base}
              checked={baseLayer === base}
              onChange={() => onBaseLayerChange(base)}
              className="accent-primary"
            />
            <span className="text-[13px]">
              {base === 'osm' ? 'OpenStreetMap' : base === 'orthophoto' ? 'Luftbild (LGL)' : 'Satellit (Sentinel-2)'}
            </span>
          </label>
        ))}
        <p className="px-4 text-[11px] text-muted-foreground mb-1 mt-3">Overlays</p>
        <LayerToggle
          id="cadastral-toggle"
          label="Kataster (ALKIS)"
          checked={cadastralVisible ?? false}
          onCheckedChange={() => onToggleLayer('cadastral')}
        />
        <LayerToggle
          id="hillshade-toggle"
          label="Gelaenderelief (DGM)"
          checked={hillshadeVisible ?? false}
          onCheckedChange={() => onToggleLayer('hillshade')}
        />
        <p className="px-4 text-[11px] text-muted-foreground mb-1 mt-3">3D</p>
        <LayerToggle
          id="buildings3d-toggle"
          label="3D Gebaeude (LoD1)"
          checked={buildings3dVisible ?? false}
          onCheckedChange={() => onToggleLayer('buildings3d')}
        />
      </div>

      <Separator className="mt-6" />

      {/* Legend */}
      <div className="pt-6 space-y-4">
        <p className="px-4 text-[12px] font-normal text-muted-foreground uppercase tracking-wide">
          Legende
        </p>
        <AQILegend />
        <TransitLegend />
        {layerVisibility.water && <WaterLegend />}
        {(layerVisibility.traffic || layerVisibility.autobahn || layerVisibility.trafficFlow) && (
          <TrafficLegend trafficFlowVisible={layerVisibility.trafficFlow} />
        )}
        {layerVisibility.energy && <EnergyLegend />}
        {layerVisibility.heatDemand && <HeatDemandLegend />}
        {layerVisibility.cycling && <CyclingLegend />}
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <div className="hidden lg:block relative">
        <aside
          className={`flex flex-col border-r border-slate-200 h-screen overflow-y-auto transition-all duration-300 ease-in-out ${
            collapsed ? 'w-0 overflow-hidden -translate-x-full' : 'w-[280px]'
          }`}
        >
          {content}
        </aside>
        {/* Toggle button — always visible */}
        <button
          onClick={onToggle}
          className="absolute top-1/2 right-0 translate-x-full -translate-y-1/2 z-30 flex items-center justify-center w-[28px] h-[48px] bg-white border border-l-0 border-slate-200 rounded-r-md shadow-sm hover:bg-slate-50 transition-colors"
          aria-label={collapsed ? 'Sidebar einblenden' : 'Sidebar ausblenden'}
        >
          {collapsed ? <ChevronRight className="h-4 w-4 text-slate-600" /> : <ChevronLeft className="h-4 w-4 text-slate-600" />}
        </button>
      </div>

      {/* Tablet/mobile: floating toggle button */}
      <div className="lg:hidden fixed bottom-4 left-4 z-50">
        <Button
          variant="secondary"
          size="icon"
          onClick={() => setDrawerOpen(v => !v)}
          aria-label="Ebenen oeffnen"
        >
          <Layers className="h-5 w-5" />
        </Button>
      </div>

      {/* Tablet/mobile: overlay drawer */}
      {drawerOpen && (
        <>
          <div
            className="lg:hidden fixed inset-0 z-40 bg-black/20"
            onClick={() => setDrawerOpen(false)}
          />
          <aside className="lg:hidden fixed left-0 top-0 bottom-0 z-50 overflow-y-auto border-r border-slate-200 shadow-lg">
            {content}
          </aside>
        </>
      )}
    </>
  );
}
