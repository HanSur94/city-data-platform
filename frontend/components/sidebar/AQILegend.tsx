import { AQI_TIER_COLORS } from '@/lib/map-styles';

const TIERS = [
  { key: 'good',     label: 'Gut' },
  { key: 'moderate', label: 'Moderat' },
  { key: 'poor',     label: 'Schlecht' },
  { key: 'bad',      label: 'Sehr schlecht' },
  { key: 'very_bad', label: 'Gefährlich' },
] as const;

export default function AQILegend() {
  return (
    <div className="px-4">
      <p className="text-[12px] font-normal text-muted-foreground mb-2">Luftqualität (AQI)</p>
      <div className="flex rounded overflow-hidden h-4 mb-1">
        {TIERS.map(({ key }) => (
          <div key={key} className="flex-1" style={{ background: AQI_TIER_COLORS[key] }} />
        ))}
      </div>
      <div className="flex justify-between">
        {TIERS.map(({ key, label }) => (
          <span key={key} className="text-[10px] text-muted-foreground">{label}</span>
        ))}
      </div>
    </div>
  );
}
