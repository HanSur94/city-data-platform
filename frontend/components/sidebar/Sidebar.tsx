'use client';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Layers } from 'lucide-react';
import LayerToggle from './LayerToggle';
import AQILegend from './AQILegend';
import TransitLegend from './TransitLegend';
import WaterLegend from './WaterLegend';

interface SidebarProps {
  layerVisibility: {
    transit: boolean;
    airQuality: boolean;
    water: boolean;
    floodHazard: boolean;
    railNoise: boolean;
    lubwEnv: boolean;
  };
  onToggleLayer: (layer: 'transit' | 'airQuality' | 'water' | 'floodHazard' | 'railNoise' | 'lubwEnv') => void;
  transitError?: boolean;
  airQualityError?: boolean;
}

export default function Sidebar({ layerVisibility, onToggleLayer, transitError, airQualityError }: SidebarProps) {
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

      {/* Legend */}
      <div className="pt-6 space-y-4">
        <p className="px-4 text-[12px] font-normal text-muted-foreground uppercase tracking-wide">
          Legende
        </p>
        <AQILegend />
        <TransitLegend />
        {layerVisibility.water && <WaterLegend />}
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
