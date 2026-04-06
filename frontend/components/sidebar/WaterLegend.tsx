const WATER_LEGEND = [
  { color: '#1565C0', label: 'Pegelstation (Neckar)' },
  { color: '#2E7D32', label: 'Naturschutzgebiet' },
  { color: '#00796B', label: 'Wasserschutzgebiet' },
] as const;

export default function WaterLegend() {
  return (
    <div className="px-4">
      <p className="text-[12px] font-normal text-muted-foreground mb-2">Pegel &amp; Gewässer</p>
      <div className="space-y-1">
        {WATER_LEGEND.map(({ color, label }) => (
          <div key={label} className="flex items-center gap-2">
            <span
              className="inline-block w-3 h-3 rounded-full"
              style={{ background: color }}
            />
            <span className="text-[12px] font-normal">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
