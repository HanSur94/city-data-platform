const WATER_LEGEND = [
  { color: '#1565C0', label: 'Pegelstation (Neckar)' },
  { color: '#2E7D32', label: 'Naturschutzgebiet' },
  { color: '#00796B', label: 'Wasserschutzgebiet' },
] as const;

const KOCHER_STAGE_LEGEND = [
  { color: '#1565C0', label: 'Normal (Stufe 0)', type: 'circle' },
  { color: '#FFC107', label: 'Vorwarnung (Stufe 1)', type: 'circle' },
  { color: '#FF9800', label: 'Meldepegel (Stufe 2)', type: 'circle' },
  { color: '#F44336', label: 'Hochwasser (Stufe 3-4)', type: 'circle' },
  { color: '#1565C0', label: 'Kocher Flusslauf', type: 'line' },
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
      <p className="text-[12px] font-normal text-muted-foreground mb-2 mt-3">Kocher (LHP)</p>
      <div className="space-y-1">
        {KOCHER_STAGE_LEGEND.map(({ color, label, type }) => (
          <div key={label} className="flex items-center gap-2">
            {type === 'circle' ? (
              <span
                className="inline-block w-3 h-3 rounded-full"
                style={{ background: color }}
              />
            ) : (
              <span
                className="inline-block w-4 h-[3px] rounded"
                style={{ background: color }}
              />
            )}
            <span className="text-[12px] font-normal">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
