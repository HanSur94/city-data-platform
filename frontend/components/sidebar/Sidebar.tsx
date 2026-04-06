'use client';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Layers } from 'lucide-react';
import LayerToggle from './LayerToggle';
import AQILegend from './AQILegend';
import TransitLegend from './TransitLegend';
import WaterLegend from './WaterLegend';
import TrafficLegend from './TrafficLegend';
import EnergyLegend from './EnergyLegend';

interface SidebarProps {
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
  };
  onToggleLayer: (layer: 'transit' | 'airQuality' | 'water' | 'floodHazard' | 'railNoise' | 'lubwEnv' | 'traffic' | 'autobahn' | 'mobiData' | 'energy' | 'schools' | 'healthcare' | 'parks' | 'waste' | 'evCharging' | 'roadworks' | 'solarPotential' | 'trafficFlow' | 'cadastral' | 'hillshade' | 'buildings3d' | 'kocher' | 'parking' | 'busPosition') => void;
  transitError?: boolean;
  airQualityError?: boolean;
  trafficError?: boolean;
  energyError?: boolean;
  baseLayer: 'osm' | 'orthophoto' | 'satellite';
  onBaseLayerChange: (base: 'osm' | 'orthophoto' | 'satellite') => void;
  cadastralVisible?: boolean;
  hillshadeVisible?: boolean;
  buildings3dVisible?: boolean;
}

export default function Sidebar({ layerVisibility, onToggleLayer, transitError, airQualityError, trafficError, energyError, baseLayer, onBaseLayerChange, cadastralVisible, hillshadeVisible, buildings3dVisible }: SidebarProps) {
  const [drawerOpen, setDrawerOpen] = useState(false);

  const content = (
    <div className="flex flex-col h-full bg-white w-[280px]">
      {/* Header */}
      <div className="px-4 pt-8 pb-6">
        <h1 className="text-[16px] font-semibold leading-[1.2]">Stadtdaten Aalen</h1>
      </div>
      <Separator />

      {/* Layer toggles */}
      <div className="pt-6">
        <p className="px-4 text-[12px] font-normal text-muted-foreground uppercase tracking-wide mb-2">
          Ebenen
        </p>
        <LayerToggle
          id="transit-toggle"
          label="ÖPNV (Bus & Bahn)"
          checked={layerVisibility.transit}
          onCheckedChange={() => onToggleLayer('transit')}
          freshnessError={transitError}
        />
        <LayerToggle
          id="bus-position-toggle"
          label="Bus-Positionen (live)"
          checked={layerVisibility.busPosition ?? false}
          onCheckedChange={() => onToggleLayer('busPosition')}
        />
        <LayerToggle
          id="aqi-toggle"
          label="Luftqualität"
          checked={layerVisibility.airQuality}
          onCheckedChange={() => onToggleLayer('airQuality')}
          freshnessError={airQualityError}
        />
        <LayerToggle
          id="water-toggle"
          label="Pegel & Gewässer"
          checked={layerVisibility.water}
          onCheckedChange={() => onToggleLayer('water')}
        />
        <LayerToggle
          id="kocher-toggle"
          label="Kocher Pegel (LHP)"
          checked={layerVisibility.kocher ?? false}
          onCheckedChange={() => onToggleLayer('kocher')}
        />
        <LayerToggle
          id="flood-toggle"
          label="Hochwassergefahr (HQ100)"
          checked={layerVisibility.floodHazard}
          onCheckedChange={() => onToggleLayer('floodHazard')}
        />
        <LayerToggle
          id="rail-noise-toggle"
          label="Bahnlärm (Lden)"
          checked={layerVisibility.railNoise}
          onCheckedChange={() => onToggleLayer('railNoise')}
        />
        <LayerToggle
          id="lubw-env-toggle"
          label="Schutzgebiete (LUBW)"
          checked={layerVisibility.lubwEnv}
          onCheckedChange={() => onToggleLayer('lubwEnv')}
        />
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
        />
        <LayerToggle
          id="traffic-flow-toggle"
          label="Verkehrsfluss (TomTom)"
          checked={layerVisibility.trafficFlow ?? false}
          onCheckedChange={() => onToggleLayer('trafficFlow')}
        />
        <LayerToggle
          id="autobahn-toggle"
          label="Autobahn-Stoerungen (A7/A6)"
          checked={layerVisibility.autobahn}
          onCheckedChange={() => onToggleLayer('autobahn')}
        />
        <LayerToggle
          id="mobidata-toggle"
          label="MobiData BW"
          checked={layerVisibility.mobiData}
          onCheckedChange={() => onToggleLayer('mobiData')}
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
        />
        <LayerToggle
          id="healthcare-toggle"
          label="Gesundheit"
          checked={layerVisibility.healthcare ?? false}
          onCheckedChange={() => onToggleLayer('healthcare')}
        />
        <LayerToggle
          id="parks-toggle"
          label="Parks & Spielplaetze"
          checked={layerVisibility.parks ?? false}
          onCheckedChange={() => onToggleLayer('parks')}
        />
        <LayerToggle
          id="waste-toggle"
          label="Wertstoffhoefe"
          checked={layerVisibility.waste ?? false}
          onCheckedChange={() => onToggleLayer('waste')}
        />
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
        />
        <LayerToggle
          id="ev-toggle"
          label="E-Ladesaeulen (BNetzA)"
          checked={layerVisibility.evCharging ?? false}
          onCheckedChange={() => onToggleLayer('evCharging')}
        />
        <LayerToggle
          id="solar-toggle"
          label="Solarpotenzial Daecher"
          checked={layerVisibility.solarPotential ?? false}
          onCheckedChange={() => onToggleLayer('solarPotential')}
        />
        <LayerToggle
          id="parking-toggle"
          label="Parkhaeuser"
          checked={layerVisibility.parking ?? false}
          onCheckedChange={() => onToggleLayer('parking')}
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
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex flex-col border-r border-slate-200 h-screen overflow-y-auto">
        {content}
      </aside>

      {/* Tablet/mobile: floating toggle button */}
      <div className="lg:hidden fixed bottom-4 left-4 z-50">
        <Button
          variant="secondary"
          size="icon"
          onClick={() => setDrawerOpen(v => !v)}
          aria-label="Ebenen öffnen"
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
