'use client'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'

const SOURCE_COLORS: Record<string, string> = {
  solar: '#eab308',
  wind_onshore: '#3b82f6',
  wind_offshore: '#3b82f6',
  hydro: '#06b6d4',
  biomass: '#22c55e',
  gas: '#f97316',
  lignite: '#6b7280',
  hard_coal: '#6b7280',
  nuclear: '#8b5cf6',
}

const SOURCE_LABELS: Record<string, string> = {
  solar: 'Solar',
  wind_onshore: 'Wind (Land)',
  wind_offshore: 'Wind (See)',
  hydro: 'Wasser',
  biomass: 'Biomasse',
  gas: 'Gas',
  lignite: 'Braunkohle',
  hard_coal: 'Steinkohle',
  nuclear: 'Kern',
}

interface EnergyMixBarProps {
  mix: Record<string, number>
  compact?: boolean
}

export function EnergyMixBar({ mix, compact = false }: EnergyMixBarProps) {
  const sources = Object.keys(SOURCE_COLORS)
  const total = sources.reduce((sum, key) => sum + (mix[key] ?? 0), 0)

  if (total === 0) {
    return (
      <div className="text-[12px] text-muted-foreground py-1">
        Keine Daten verfügbar
      </div>
    )
  }

  // Normalize to percentages for display
  const data = [
    sources.reduce(
      (obj, key) => {
        obj[key] = mix[key] ?? 0
        return obj
      },
      {} as Record<string, number>,
    ),
  ]

  if (compact) {
    return (
      <div style={{ height: 24, width: '100%' }}>
        <ResponsiveContainer width="100%" height={24}>
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 0, right: 0, bottom: 0, left: 0 }}
            barSize={24}
          >
            <XAxis type="number" hide domain={[0, 'auto']} />
            <YAxis type="category" hide />
            <Tooltip
              formatter={(value, name) => [
                `${Math.round(Number(value))} MW`,
                SOURCE_LABELS[String(name)] ?? String(name),
              ]}
            />
            {sources.map((key) => (
              <Bar
                key={key}
                dataKey={key}
                stackId="mix"
                fill={SOURCE_COLORS[key]}
                isAnimationActive={false}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    )
  }

  return (
    <div style={{ height: 40, width: '100%' }}>
      <ResponsiveContainer width="100%" height={40}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 0, right: 0, bottom: 0, left: 0 }}
          barSize={40}
        >
          <XAxis type="number" hide domain={[0, 'auto']} />
          <YAxis type="category" hide />
          <Tooltip
            formatter={(value, name) => [
              `${Math.round(Number(value))} MW`,
              SOURCE_LABELS[String(name)] ?? String(name),
            ]}
          />
          {sources.map((key) => (
            <Bar
              key={key}
              dataKey={key}
              stackId="mix"
              fill={SOURCE_COLORS[key]}
              isAnimationActive={false}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
      <div className="flex flex-wrap gap-x-2 gap-y-0.5 mt-1">
        {sources
          .filter((key) => (mix[key] ?? 0) > 0)
          .map((key) => (
            <div key={key} className="flex items-center gap-1">
              <span
                className="inline-block w-2 h-2 rounded-sm flex-shrink-0"
                style={{ background: SOURCE_COLORS[key] }}
              />
              <span className="text-[10px] text-muted-foreground">
                {SOURCE_LABELS[key] ?? key}
              </span>
            </div>
          ))}
      </div>
    </div>
  )
}
