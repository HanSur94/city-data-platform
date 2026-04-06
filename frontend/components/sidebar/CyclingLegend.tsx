const CYCLING_LEGEND = [
  { color: '#1a7c28', label: 'Getrennter Radweg' },
  { color: '#5cb85c', label: 'Radfahrstreifen' },
  { color: '#f0ad4e', label: 'Schutzstreifen' },
  { color: '#e67e22', label: 'Gemeinsamer Weg' },
  { color: '#d9534f', label: 'Keine Radinfrastruktur' },
] as const

export default function CyclingLegend() {
  return (
    <div className="px-4">
      <p className="text-[12px] font-normal text-muted-foreground mb-2">Radinfrastruktur</p>
      <div className="space-y-1">
        {CYCLING_LEGEND.map(({ color, label }) => (
          <div key={label} className="flex items-center gap-2">
            <span
              className="inline-block w-5 h-1 rounded-sm"
              style={{ background: color }}
            />
            <span className="text-[12px] font-normal">{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
