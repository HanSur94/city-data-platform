const HEAT_DEMAND_LEGEND = [
  { color: '#2166ac', label: '< 50 kWh/m\u00b2/a (blau)' },
  { color: '#67a9cf', label: '50\u2013100 kWh/m\u00b2/a (hellblau)' },
  { color: '#5aae61', label: '100\u2013150 kWh/m\u00b2/a (gruen)' },
  { color: '#fee08b', label: '150\u2013200 kWh/m\u00b2/a (gelb)' },
  { color: '#f46d43', label: '200\u2013250 kWh/m\u00b2/a (orange)' },
  { color: '#d73027', label: '> 250 kWh/m\u00b2/a (rot)' },
] as const

export default function HeatDemandLegend() {
  return (
    <div className="px-4">
      <p className="text-[12px] font-normal text-muted-foreground mb-2">Waermebedarf</p>
      <div className="space-y-1">
        {HEAT_DEMAND_LEGEND.map(({ color, label }) => (
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
