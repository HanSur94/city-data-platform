'use client';
import { DataSourceSection } from '@/components/map/DataSourceSection';
import { LAYER_METADATA } from '@/lib/layer-metadata';
import type { Feature } from 'geojson';

interface BusPopupProps {
  feature: Feature;
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

export default function BusPopup({ feature }: BusPopupProps) {
  const props = feature.properties ?? {};
  const lineName = props.line_name as string | undefined;
  const destination = props.destination as string | undefined;
  const delaySeconds = (props.delay_seconds as number) ?? 0;
  const nextStop = props.next_stop as string | undefined;

  return (
    <div className="text-sm space-y-1 max-w-[220px]">
      <p className="text-[16px] font-semibold leading-tight">
        Linie {lineName ?? '?'}
      </p>
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
      {nextStop && (
        <p className="text-[13px]">
          Naechster Halt: {nextStop}
        </p>
      )}
      <DataSourceSection
        sourceName={LAYER_METADATA['busPosition'].sourceName}
        sourceUrl={LAYER_METADATA['busPosition'].sourceUrl}
        dataType={LAYER_METADATA['busPosition'].dataType}
        timestamp={null}
      />
    </div>
  );
}
