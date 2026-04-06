'use client';
import { Badge } from '@/components/ui/badge';
import { DataSourceSection } from '@/components/map/DataSourceSection';
import { LAYER_METADATA } from '@/lib/layer-metadata';
import type { Feature } from 'geojson';

interface KocherPopupProps {
  feature: Feature;
}

const STAGE_LABELS: Record<number, string> = {
  0: 'Normal',
  1: 'Vorwarnung',
  2: 'Meldepegel',
  3: 'Hochwasser',
  4: 'Extremhochwasser',
};

const STAGE_COLORS: Record<number, string> = {
  0: '#1565C0',
  1: '#FFC107',
  2: '#FF9800',
  3: '#F44336',
  4: '#F44336',
};

const TREND_LABELS: Record<string, string> = {
  rising: 'steigend',
  falling: 'fallend',
  stable: 'stabil',
};

export default function KocherPopup({ feature }: KocherPopupProps) {
  const props = feature.properties ?? {};
  const stationName = props.station_name as string | undefined;
  const river = props.river as string | undefined;
  const levelCm = props.level_cm as number | undefined;
  const flowM3s = props.flow_m3s as number | undefined;
  const stage = props.stage as number | undefined;
  const trend = props.trend as string | undefined;
  const attribution = props.attribution as string | undefined;

  return (
    <div className="text-sm space-y-1 max-w-[200px]">
      <p className="text-[16px] font-semibold leading-tight">
        {stationName ?? 'Pegelstation'}
      </p>
      {river && (
        <p className="text-[12px] text-muted-foreground">{river}</p>
      )}
      {levelCm != null && (
        <p className="text-[14px]">Wasserstand: {Math.round(levelCm)} cm</p>
      )}
      {flowM3s != null && (
        <p className="text-[14px]">Abfluss: {flowM3s.toFixed(1)} m&sup3;/s</p>
      )}
      {stage != null && (
        <div className="flex items-center gap-1">
          <span className="text-[14px]">Warnstufe:</span>
          <Badge
            style={{
              backgroundColor: STAGE_COLORS[stage] ?? '#9ca3af',
              color: stage >= 1 && stage <= 2 ? '#000' : '#fff',
            }}
          >
            {stage} - {STAGE_LABELS[stage] ?? `Stufe ${stage}`}
          </Badge>
        </div>
      )}
      {trend && (
        <p className="text-[14px]">Trend: {TREND_LABELS[trend] ?? trend}</p>
      )}
      {attribution && (
        <p className="text-[11px] text-muted-foreground mt-1">{attribution}</p>
      )}
      <DataSourceSection
        sourceName={LAYER_METADATA['kocher'].sourceName}
        sourceUrl={LAYER_METADATA['kocher'].sourceUrl}
        dataType={LAYER_METADATA['kocher'].dataType}
        timestamp={(props.measured_at as string) ?? (props.fetched_at as string) ?? null}
      />
    </div>
  );
}
