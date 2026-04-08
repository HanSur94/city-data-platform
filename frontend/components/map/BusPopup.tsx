'use client';
import { DataSourceSection } from '@/components/map/DataSourceSection';
import { CrossDomainSection } from '@/components/map/CrossDomainSection';
import { LAYER_METADATA } from '@/lib/layer-metadata';
import type { Feature } from 'geojson';

interface BusPopupProps {
  feature: Feature;
  isFollowing?: boolean;
  onToggleFollow?: () => void;
}

function delayColor(seconds: number): string {
  if (seconds >= 600) return '#ef4444';   // red
  if (seconds >= 300) return '#f97316';   // orange
  if (seconds >= 120) return '#eab308';   // yellow
  return '#22c55e';                        // green
}

function formatDelay(seconds: number): string {
  if (seconds < 60) return 'puenktlich';
  const minutes = Math.round(seconds / 60);
  return `+${minutes} Min`;
}

export default function BusPopup({ feature, isFollowing = false, onToggleFollow }: BusPopupProps) {
  const props = feature.properties ?? {};
  const featureId = (props.feature_id as string) ?? (feature.id as string) ?? null;
  const lineName = props.line_name as string | undefined;
  const destination = props.destination as string | undefined;
  const delaySeconds = (props.delay_seconds as number) ?? 0;
  const nextStop = props.next_stop as string | undefined;
  const prevStop = props.prev_stop as string | undefined;
  const routeType = (props.route_type as number) ?? 3;
  const scheduledDep = props.scheduled_departure as string | undefined;
  const scheduledArr = props.scheduled_arrival as string | undefined;
  const originStop = props.origin_stop as string | undefined;
  const totalStops = props.total_stops as number | undefined;
  const progress = (props.progress as number) ?? 0;

  const vehicleType = routeType <= 2 ? 'Zug' : 'Bus';

  return (
    <div className="text-sm space-y-1 max-w-[240px]">
      <div className="flex items-center gap-2">
        <span className="text-[16px] font-semibold leading-tight">
          Linie {lineName ?? '?'}
        </span>
        <span className="text-[11px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">
          {vehicleType}
        </span>
      </div>
      {destination && (
        <p className="text-[13px] text-muted-foreground">
          Richtung {destination}
        </p>
      )}
      <p
        className="text-[14px] font-medium"
        style={{ color: delayColor(delaySeconds) }}
      >
        {formatDelay(delaySeconds)}
      </p>
      {(scheduledDep || scheduledArr) && (
        <div className="text-[12px] text-muted-foreground flex gap-3">
          {scheduledDep && <span>Abfahrt: {scheduledDep}</span>}
          {scheduledArr && <span>Ankunft: {scheduledArr}</span>}
        </div>
      )}
      {originStop && (
        <p className="text-[12px] text-muted-foreground">
          Von: {originStop}
        </p>
      )}
      {prevStop && (
        <p className="text-[13px]">
          Letzter Halt: {prevStop}
        </p>
      )}
      {nextStop && (
        <p className="text-[13px]">
          Naechster Halt: {nextStop}
        </p>
      )}
      {totalStops != null && totalStops > 0 && (
        <div className="pt-1">
          <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
            <span>{Math.round(progress * 100)}%</span>
            <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 rounded-full transition-all"
                style={{ width: `${Math.round(progress * 100)}%` }}
              />
            </div>
            <span>{totalStops} Halte</span>
          </div>
        </div>
      )}
      {onToggleFollow && (
        <button
          onClick={onToggleFollow}
          className={`w-full mt-1 px-2 py-1 text-[12px] font-medium rounded border transition-colors ${
            isFollowing
              ? 'bg-blue-500 text-white border-blue-500 hover:bg-blue-600'
              : 'bg-white text-slate-600 border-slate-300 hover:bg-slate-50'
          }`}
        >
          {isFollowing ? 'Folgen beenden' : 'Folgen'}
        </button>
      )}
      <DataSourceSection
        sourceName={LAYER_METADATA['busPosition'].sourceName}
        sourceUrl={LAYER_METADATA['busPosition'].sourceUrl}
        dataType={LAYER_METADATA['busPosition'].dataType}
        timestamp={null}
      />
      <CrossDomainSection featureId={featureId} ownDomain="transit" />
    </div>
  );
}
