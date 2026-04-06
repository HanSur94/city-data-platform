const ENERGY_LEGEND = [
  { color: '#eab308', label: 'Solar' },
  { color: '#3b82f6', label: 'Wind' },
  { color: '#22c55e', label: 'Batterie' },
  { color: '#f59e0b', label: 'Dach-Solar' },
] as const

export default function EnergyLegend() {
  return (
    <div className="px-4">
      <p className="text-[12px] font-normal text-muted-foreground mb-2">Erneuerbare Anlagen</p>
      <div className="space-y-1">
        {ENERGY_LEGEND.map(({ color, label }) => (
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
  )
}
