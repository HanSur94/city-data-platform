'use client';
import { Badge } from '@/components/ui/badge';
import { DataSourceSection } from '@/components/map/DataSourceSection';
import { LAYER_METADATA } from '@/lib/layer-metadata';
import TrafficFlowPopupChart from '@/components/map/TrafficFlowPopupChart';
import type { Feature } from 'geojson';

interface TrafficFlowPopupProps {
  feature: Feature;
  featureId: string;
  town: string;
}

const CONGESTION_LABELS: Record<string, string> = {
  free: 'Freier Verkehr',
  moderate: 'Maessiger Verkehr',
  congested: 'Stau',
};

const CONGESTION_COLORS: Record<string, string> = {
  free: '#22c55e',
  moderate: '#eab308',
  congested: '#ef4444',
};

export default function TrafficFlowPopup({ feature, featureId, town }: TrafficFlowPopupProps) {
  const props = feature.properties ?? {};
  const roadName = props.road_name as string | undefined;
  const speedAvgKmh = props.speed_avg_kmh as number | undefined;
  const freeflowKmh = props.freeflow_kmh as number | undefined;
  const congestionRatio = props.congestion_ratio as number | undefined;
  const congestionLevel = props.congestion_level as string | undefined;
  const confidence = props.confidence as number | undefined;

  return (
    <div className="text-sm space-y-1 max-w-[200px]">
      <p className="text-[16px] font-semibold leading-tight">
        {roadName ?? 'Strassenabschnitt'}
      </p>
      {speedAvgKmh != null && (
        <p className="text-[14px]">Geschwindigkeit: {Math.round(speedAvgKmh)} km/h</p>
      )}
      {freeflowKmh != null && (
        <p className="text-[14px]">Frei-Fluss: {Math.round(freeflowKmh)} km/h</p>
      )}
      {congestionRatio != null && (
        <p className="text-[14px]">Auslastung: {Math.round(congestionRatio * 100)}%</p>
      )}
      {confidence != null && (
        <p className="text-[14px] text-muted-foreground">Konfidenz: {Math.round(confidence * 100)}%</p>
      )}
      {congestionLevel && (
        <Badge
          style={{
            backgroundColor: CONGESTION_COLORS[congestionLevel] ?? '#9ca3af',
            color: congestionLevel === 'moderate' ? '#000' : '#fff',
          }}
        >
          {CONGESTION_LABELS[congestionLevel] ?? congestionLevel}
        </Badge>
      )}
      <DataSourceSection
        sourceName={LAYER_METADATA['trafficFlow'].sourceName}
        sourceUrl={LAYER_METADATA['trafficFlow'].sourceUrl}
        dataType={LAYER_METADATA['trafficFlow'].dataType}
        timestamp={(props.measured_at as string) ?? (props.fetched_at as string) ?? null}
      />
      <TrafficFlowPopupChart featureId={featureId} town={town} freeflowKmh={freeflowKmh ?? null} />
    </div>
  );
}
