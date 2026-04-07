'use client';
import { useState } from 'react';
import { Map as MapIcon, X } from 'lucide-react';
import AQILegend from '@/components/sidebar/AQILegend';
import TransitLegend from '@/components/sidebar/TransitLegend';
import WaterLegend from '@/components/sidebar/WaterLegend';
import TrafficLegend from '@/components/sidebar/TrafficLegend';
import EnergyLegend from '@/components/sidebar/EnergyLegend';
import HeatDemandLegend from '@/components/sidebar/HeatDemandLegend';
import CyclingLegend from '@/components/sidebar/CyclingLegend';

interface LegendOverlayProps {
  layerVisibility: Record<string, boolean | undefined>;
  trafficFlowVisible?: boolean;
}

export default function LegendOverlay({ layerVisibility, trafficFlowVisible }: LegendOverlayProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="absolute bottom-4 left-4 z-20">
      {/* Expanded panel */}
      {open && (
        <div className="absolute bottom-12 left-0 w-[260px] max-h-[60vh] overflow-y-auto bg-white/95 backdrop-blur border border-slate-200 rounded-lg shadow-lg p-4">
          {/* Close button */}
          <button
            onClick={() => setOpen(false)}
            className="absolute top-2 right-2 p-1 rounded hover:bg-slate-100 transition-colors"
            aria-label="Legende schliessen"
          >
            <X className="h-4 w-4 text-slate-500" />
          </button>

          <p className="text-[13px] font-semibold mb-3">Legende</p>

          <div className="space-y-4">
            <AQILegend />
            <TransitLegend />
            {layerVisibility.water && <WaterLegend />}
            {(layerVisibility.traffic || layerVisibility.autobahn || trafficFlowVisible) && (
              <TrafficLegend trafficFlowVisible={trafficFlowVisible} />
            )}
            {layerVisibility.energy && <EnergyLegend />}
            {layerVisibility.heatDemand && <HeatDemandLegend />}
            {layerVisibility.cycling && <CyclingLegend />}
          </div>
        </div>
      )}

      {/* Toggle button */}
      <button
        onClick={() => setOpen(v => !v)}
        className={`flex items-center gap-2 px-3 py-2 rounded-lg border shadow-sm transition-colors ${
          open ? 'bg-primary text-white border-primary' : 'bg-white border-slate-200 hover:bg-slate-50 text-slate-700'
        }`}
        aria-label="Legende anzeigen"
      >
        <MapIcon className="h-4 w-4" />
        <span className="text-[13px] font-medium">Legende</span>
      </button>
    </div>
  );
}
