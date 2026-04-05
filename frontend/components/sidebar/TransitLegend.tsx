import { TRANSIT_COLORS } from '@/lib/map-styles';

const ROUTE_TYPES = [
  { key: 'bus',   label: 'Bus' },
  { key: 'train', label: 'Bahn' },
  { key: 'tram',  label: 'Straßenbahn' },
] as const;

export default function TransitLegend() {
  return (
    <div className="px-4">
      <p className="text-[12px] font-normal text-muted-foreground mb-2">ÖPNV (Bus &amp; Bahn)</p>
      <div className="space-y-1">
        {ROUTE_TYPES.map(({ key, label }) => (
          <div key={key} className="flex items-center gap-2">
            <span
              className="inline-block w-6 h-2 rounded-full"
              style={{ background: TRANSIT_COLORS[key] }}
            />
            <span className="text-[12px] font-normal">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
