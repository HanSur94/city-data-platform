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
import type { Pollutant } from './AirQualityHeatmapLayer';

/** Which data layers are currently drawn in 3D mode (data3d on and the layer on). */
export interface Data3dLayers {
  airQuality: boolean;
  evCharging: boolean;
  parking: boolean;
  heatDemand: boolean;
  trafficFlow: boolean;
}

interface LegendOverlayProps {
  layerVisibility: Record<string, boolean | undefined>;
  trafficFlowVisible?: boolean;
  data3dLayers?: Data3dLayers;
  activePollutant?: Pollutant;
}

const POLLUTANT_LABELS: Record<Pollutant, string> = {
  pm25: 'PM2.5',
  pm10: 'PM10',
  no2: 'NO₂',
  o3: 'O₃',
};

export default function LegendOverlay({
  layerVisibility,
  trafficFlowVisible,
  data3dLayers,
  activePollutant = 'pm25',
}: LegendOverlayProps) {
  const [open, setOpen] = useState(false);

  const data3dLines: string[] = [];
  if (data3dLayers?.airQuality) {
    data3dLines.push(`Luft: Höhe = ${POLLUTANT_LABELS[activePollutant]}-Konzentration, Farbe = EAQI-Stufe`);
  }
  if (data3dLayers?.evCharging) data3dLines.push('E-Laden: Höhe = Ladeleistung (kW)');
  if (data3dLayers?.parking) data3dLines.push('Parken: Höhe = freie Plätze');
  if (data3dLayers?.heatDemand) data3dLines.push('Wärme: Höhe = Wärmebedarf (kWh/m²·a)');
  if (data3dLayers?.trafficFlow) data3dLines.push('Verkehr: Lauflicht = Fahrtrichtung');

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
            {data3dLines.length > 0 && (
              <div>
                <p className="text-[12px] font-semibold mb-1">3D-Daten</p>
                {data3dLines.map((line) => (
                  <p key={line} className="text-[12px] text-slate-600">{line}</p>
                ))}
              </div>
            )}
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
