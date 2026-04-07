'use client';
import { DataSourceSection } from '@/components/map/DataSourceSection';
import { CrossDomainSection } from '@/components/map/CrossDomainSection';
import { LAYER_METADATA } from '@/lib/layer-metadata';
import type { Feature } from 'geojson';

interface ParkingPopupProps {
  feature: Feature;
}

function occupancyColor(pct: number): string {
  if (pct >= 80) return '#ef4444';  // red
  if (pct >= 50) return '#eab308';  // yellow
  return '#22c55e';                  // green
}

export default function ParkingPopup({ feature }: ParkingPopupProps) {
  const props = feature.properties ?? {};
  const featureId = (props.feature_id as string) ?? (feature.id as string) ?? null;
  const name = props.name as string | undefined;
  const freeSpots = props.free_spots as number | undefined;
  const totalSpots = props.total_spots as number | undefined;
  const occupancyPct = props.occupancy_pct as number | undefined;

  return (
    <div className="text-sm space-y-1 max-w-[200px]">
      <p className="text-[16px] font-semibold leading-tight">
        Parkhaus {name ?? 'Unbekannt'}
      </p>
      {freeSpots != null && totalSpots != null && (
        <p className="text-[14px]">
          {freeSpots}/{totalSpots} frei
        </p>
      )}
      {occupancyPct != null && (
        <p className="text-[14px]" style={{ color: occupancyColor(occupancyPct) }}>
          Auslastung: {Math.round(occupancyPct)}%
        </p>
      )}
      <DataSourceSection
        sourceName={LAYER_METADATA['parking'].sourceName}
        sourceUrl={LAYER_METADATA['parking'].sourceUrl}
        dataType={LAYER_METADATA['parking'].dataType}
        timestamp={(props.fetched_at as string) ?? null}
      />
      <CrossDomainSection featureId={featureId} ownDomain="infrastructure" />
    </div>
  );
}
