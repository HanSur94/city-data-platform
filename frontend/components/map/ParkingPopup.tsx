'use client';
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
    </div>
  );
}
