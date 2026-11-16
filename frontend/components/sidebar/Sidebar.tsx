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
import BusLineFilter from './BusLineFilter';
import { LAYER_METADATA } from '@/lib/layer-metadata';
import {
  DATA_LAYER_KEYS,
  LAYER_BY_KEY,
  LAYER_GROUPS,
  countActive,
  groupSwitchState,
  layerKeysInGroup,
} from '@/lib/layer-registry';
import type { LayerGroupId, LayerKey, LayerVisibility } from '@/lib/layer-registry';
import type { LayerStatus } from '@/lib/api';
import LayerGroupHeader from './LayerGroupHeader';
import { useLayerMetadata } from '@/hooks/useLayerMetadata';

import type { DemographicMetric } from '@/components/map/DemographicsGridLayer';
import { BASE_LAYERS } from '@/lib/map-styles';
import type { BaseLayer } from '@/lib/map-styles';

const BASE_LAYER_LABELS: Record<BaseLayer, string> = {
  dark: 'Dunkel',
  light: 'Hell',
  orthophoto: 'Luftbild (LGL)',
  satellite: 'Satellit (Sentinel-2)',
};

interface SidebarProps {
  town: string;
  onFeatureSelect: (result: SearchResult) => void;
  layerVisibility: LayerVisibility;
  onToggleLayer: (layer: LayerKey) => void;
  onSetLayers: (keys: readonly LayerKey[], on: boolean) => void;
  transitError?: boolean;
  airQualityError?: boolean;
  trafficError?: boolean;
  energyError?: boolean;
  baseLayer: BaseLayer;
  onBaseLayerChange: (base: BaseLayer) => void;
  activePollutant?: Pollutant;
  onPollutantChange?: (pollutant: Pollutant) => void;
  noiseMetric?: 'lden' | 'lnight';
  onNoiseMetricChange?: (metric: 'lden' | 'lnight') => void;
  demographicMetric?: DemographicMetric;
  onDemographicMetricChange?: (metric: DemographicMetric) => void;
  busLines?: string[];
  hiddenBusLines?: Set<string>;
  onToggleBusLine?: (line: string) => void;
  collapsed?: boolean;
  onToggle?: () => void;
}

export default function Sidebar({ town, onFeatureSelect, layerVisibility, onToggleLayer, onSetLayers, transitError, airQualityError, trafficError, energyError, baseLayer, onBaseLayerChange, activePollutant, onPollutantChange, noiseMetric, onNoiseMetricChange, demographicMetric, onDemographicMetricChange, busLines, hiddenBusLines, onToggleBusLine, collapsed, onToggle }: SidebarProps) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { layerMeta } = useLayerMetadata(town);

  // Connector status of a layer; external WMS layers carry none (the connector does not describe what the map draws).
  const statusFor = (key: LayerKey): LayerStatus | undefined => {
    const entry = LAYER_BY_KEY[key];
    if (entry.externalWms || !entry.metadataKey) return undefined;
    return layerMeta[entry.metadataKey]?.status;
  };

  const toggleProps = (key: LayerKey) => {
    const entry = LAYER_BY_KEY[key];
    const metadata = entry.metadataKey ? LAYER_METADATA[entry.metadataKey] : undefined;
    return {
      id: `layer-${key}`,
      label: entry.label,
      checked: layerVisibility[key],
      onCheckedChange: () => onToggleLayer(key),
      metadata,
      dataType: metadata?.dataType,
      status: statusFor(key),
      lastUpdated: entry.metadataKey ? layerMeta[entry.metadataKey]?.lastUpdated : undefined,
    };
  };

  const onGroupToggle = (keys: readonly LayerKey[]) => {
    onSetLayers(keys, groupSwitchState(keys, layerVisibility) !== 'on');
  };

  const renderGroupHeader = (groupId: LayerGroupId) => {
    const group = LAYER_GROUPS.find((g) => g.id === groupId);
    const keys = layerKeysInGroup(groupId);
    return (
      <LayerGroupHeader
        id={`layer-group-${groupId}`}
        title={group?.title ?? groupId}
        activeCount={countActive(keys, layerVisibility)}
        total={keys.length}
        state={groupSwitchState(keys, layerVisibility)}
        noDataCount={keys.filter((key) => statusFor(key) === 'never_fetched').length}
        onToggle={() => onGroupToggle(keys)}
      />
    );
  };

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

      {/* Master switch: all data layers */}
      <div className="pt-2">
        <LayerGroupHeader
          id="layer-group-all"
          title="Alle Ebenen"
          variant="master"
          activeCount={countActive(DATA_LAYER_KEYS, layerVisibility)}
          total={DATA_LAYER_KEYS.length}
          state={groupSwitchState(DATA_LAYER_KEYS, layerVisibility)}
          onToggle={() => onGroupToggle(DATA_LAYER_KEYS)}
        />
      </div>

      <Separator className="mt-2" />

      {/* Umwelt */}
      {renderGroupHeader('environment')}
      <div>
        <LayerToggle {...toggleProps('airQuality')} freshnessError={airQualityError} />
        {layerVisibility.airQuality && activePollutant && onPollutantChange && (
          <PollutantToggle activePollutant={activePollutant} onPollutantChange={onPollutantChange} />
        )}
        <LayerToggle {...toggleProps('water')} />
        <LayerToggle {...toggleProps('kocher')} />
        <LayerToggle {...toggleProps('floodHazard')} />
        <LayerToggle {...toggleProps('railNoise')} />
        <LayerToggle {...toggleProps('lubwEnv')} />
        <LayerToggle {...toggleProps('roadNoise')} />
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

      {/* Verkehr */}
      {renderGroupHeader('transport')}
      <div>
        <LayerToggle {...toggleProps('transit')} freshnessError={transitError} />
        <LayerToggle {...toggleProps('busPosition')} />
        {layerVisibility.busPosition && busLines && busLines.length > 0 && onToggleBusLine && hiddenBusLines && (
          <BusLineFilter
            lines={busLines}
            hiddenLines={hiddenBusLines}
            onToggle={onToggleBusLine}
          />
        )}
        <LayerToggle {...toggleProps('traffic')} freshnessError={trafficError} />
        <LayerToggle {...toggleProps('trafficFlow')} />
        <LayerToggle {...toggleProps('autobahn')} />
        <LayerToggle {...toggleProps('cycling')} />
      </div>

      <Separator className="mt-6" />

      {/* Energie */}
      {renderGroupHeader('energy')}
      <div>
        <LayerToggle {...toggleProps('energy')} freshnessError={energyError} />
        <LayerToggle {...toggleProps('solarGlow')} />
        <LayerToggle {...toggleProps('fernwaerme')} />
        <LayerToggle {...toggleProps('heatDemand')} />
      </div>

      <Separator className="mt-6" />

      {/* Gemeinwesen */}
      {renderGroupHeader('community')}
      <div>
        <LayerToggle {...toggleProps('schools')} />
        <LayerToggle {...toggleProps('healthcare')} />
        <LayerToggle {...toggleProps('parks')} />
        <LayerToggle {...toggleProps('waste')} />
        <LayerToggle {...toggleProps('police')} dataType="SCRAPED" />
        <LayerToggle {...toggleProps('demographics')} />
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

      {/* Infrastruktur */}
      {renderGroupHeader('infrastructure')}
      <div>
        <LayerToggle {...toggleProps('roadworks')} />
        <LayerToggle {...toggleProps('evCharging')} />
        <LayerToggle {...toggleProps('solarPotential')} />
        <LayerToggle {...toggleProps('parking')} />
      </div>

      <Separator className="mt-6" />

      {/* Karte & Overlays */}
      {renderGroupHeader('mapOverlays')}
      <div>
        <p className="px-4 text-[11px] text-muted-foreground mb-1">Basiskarte</p>
        {BASE_LAYERS.map((base) => (
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
              {BASE_LAYER_LABELS[base]}
            </span>
          </label>
        ))}
        <p className="px-4 text-[11px] text-muted-foreground mb-1 mt-3">Overlays</p>
        <LayerToggle {...toggleProps('cadastral')} />
        <LayerToggle {...toggleProps('hillshade')} />
      </div>

      <Separator className="mt-6" />

      {/* 3D */}
      {renderGroupHeader('threeD')}
      <div>
        <LayerToggle {...toggleProps('buildings3d')} />
        <LayerToggle {...toggleProps('terrain3d')} />
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
