'use client';
import { Badge } from '@/components/ui/badge';
import FreshnessIndicator from './FreshnessIndicator';
import type { Feature } from 'geojson';

interface TrafficPopupProps {
  feature: Feature;
  lastFetched: Date | null;
}

const CONGESTION_LABELS: Record<string, string> = {
  free: 'Freier Fluss',
  moderate: 'Mäßig',
  congested: 'Stau',
};

const CONGESTION_COLORS: Record<string, string> = {
  free: '#22c55e',
  moderate: '#eab308',
  congested: '#ef4444',
};

export default function TrafficPopup({ feature, lastFetched }: TrafficPopupProps) {
  const props = feature.properties ?? {};
  const congestion = props.congestion_level as string | undefined;
  const stationName = props.station_name as string | undefined;
  const roadName = props.road_name as string | undefined;
  const vehicleCountTotal = props.vehicle_count_total as number | undefined;
  const vehicleCountHgv = props.vehicle_count_hgv as number | undefined;
  const speedAvgKmh = props.speed_avg_kmh as number | undefined;

  return (
    <div className="text-sm space-y-1 max-w-[200px]">
      <p className="text-[16px] font-semibold leading-tight">
        {stationName ? `Zaehlstelle ${stationName}` : 'Verkehrszähler'}
      </p>
      {roadName && <p className="text-[14px]">{roadName}</p>}
      {vehicleCountTotal != null && (
        <p className="text-[14px]">Kfz/h: {vehicleCountTotal}</p>
      )}
      {vehicleCountHgv != null && (
        <p className="text-[14px]">SV/h: {vehicleCountHgv}</p>
      )}
      {speedAvgKmh != null && (
        <p className="text-[14px]">{speedAvgKmh} km/h</p>
      )}
      {congestion && (
        <Badge
          style={{
            backgroundColor: CONGESTION_COLORS[congestion] ?? '#9ca3af',
            color: congestion === 'moderate' ? '#000' : '#fff',
          }}
        >
          {CONGESTION_LABELS[congestion] ?? congestion}
        </Badge>
      )}
      <FreshnessIndicator lastFetched={lastFetched} />
    </div>
  );
}
