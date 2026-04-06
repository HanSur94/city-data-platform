'use client';
import type { Pollutant } from '@/components/map/AirQualityHeatmapLayer';

interface PollutantToggleProps {
  activePollutant: Pollutant;
  onPollutantChange: (pollutant: Pollutant) => void;
}

const POLLUTANTS: { key: Pollutant; label: string }[] = [
  { key: 'pm25', label: 'PM2.5' },
  { key: 'pm10', label: 'PM10' },
  { key: 'no2', label: 'NO2' },
  { key: 'o3', label: 'O3' },
];

/**
 * Row of pill-style toggle buttons for switching between pollutants
 * on the air quality heatmap grid (REQ-AIR-03).
 */
export default function PollutantToggle({ activePollutant, onPollutantChange }: PollutantToggleProps) {
  return (
    <div className="flex gap-1 px-4 pb-2">
      {POLLUTANTS.map(({ key, label }) => (
        <button
          key={key}
          type="button"
          onClick={() => onPollutantChange(key)}
          className={`
            px-2 py-0.5 rounded-full text-[10px] font-medium transition-colors
            ${activePollutant === key
              ? 'bg-primary text-primary-foreground'
              : 'bg-secondary text-muted-foreground hover:bg-secondary/80'
            }
          `}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
