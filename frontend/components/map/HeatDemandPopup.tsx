'use client';
import { DataSourceSection } from '@/components/map/DataSourceSection';
import { LAYER_METADATA } from '@/lib/layer-metadata';
import type { Feature } from 'geojson';

interface HeatDemandPopupProps {
  feature: Feature;
}

const HEAT_CLASS_COLORS: Record<string, string> = {
  blue: '#2166ac',
  light_blue: '#67a9cf',
  green: '#5aae61',
  yellow: '#fee08b',
  orange: '#f46d43',
  red: '#d73027',
};

const HEAT_CLASS_LABELS: Record<string, string> = {
  blue: 'Sehr niedrig',
  light_blue: 'Niedrig',
  green: 'Mittel',
  yellow: 'Erhoht',
  orange: 'Hoch',
  red: 'Sehr hoch',
};

export default function HeatDemandPopup({ feature }: HeatDemandPopupProps) {
  const props = feature.properties ?? {};
  const kwh = props.heat_demand_kwh_m2_y as number | undefined;
  const heatClass = props.heat_class as string | undefined;
  const source = props.source as string | undefined;

  return (
    <div className="text-sm space-y-1 max-w-[220px]">
      <p className="text-[16px] font-semibold leading-tight">Waermebedarf</p>
      {kwh != null && (
        <p className="text-[14px]">{Math.round(kwh)} kWh/m&sup2;/a</p>
      )}
      {heatClass && (
        <p className="text-[13px] flex items-center gap-1.5">
          <span
            className="inline-block w-3 h-3 rounded-full"
            style={{ background: HEAT_CLASS_COLORS[heatClass] ?? '#999' }}
          />
          {HEAT_CLASS_LABELS[heatClass] ?? heatClass}
        </p>
      )}
      {source && (
        <p className="text-[11px] text-muted-foreground mt-1">Quelle: {source}</p>
      )}
      <DataSourceSection
        sourceName={LAYER_METADATA['heatDemand'].sourceName}
        sourceUrl={LAYER_METADATA['heatDemand'].sourceUrl}
        dataType={LAYER_METADATA['heatDemand'].dataType}
        timestamp={null}
      />
    </div>
  );
}
