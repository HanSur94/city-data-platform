const TRAFFIC_LEGEND = [
  { color: '#22c55e', label: 'Frei' },
  { color: '#eab308', label: 'Mäßig' },
  { color: '#ef4444', label: 'Stau' },
] as const

const AUTOBAHN_LEGEND = [
  { color: '#f97316', label: 'Baustelle' },
  { color: '#ef4444', label: 'Sperrung' },
] as const

export default function TrafficLegend() {
  return (
    <div className="px-4">
      <p className="text-[12px] font-normal text-muted-foreground mb-2">Verkehr</p>
      <div className="space-y-1 mb-2">
        {TRAFFIC_LEGEND.map(({ color, label }) => (
          <div key={label} className="flex items-center gap-2">
            <span
              className="inline-block w-3 h-3 rounded-full"
              style={{ background: color }}
            />
            <span className="text-[12px] font-normal">{label}</span>
          </div>
        ))}
      </div>
      <p className="text-[12px] font-normal text-muted-foreground mb-1">Autobahn</p>
      <div className="space-y-1">
        {AUTOBAHN_LEGEND.map(({ color, label }) => (
          <div key={label} className="flex items-center gap-2">
            <span
              className="inline-block w-3 h-3 rounded-sm"
              style={{ background: color }}
            />
            <span className="text-[12px] font-normal">{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
