'use client'
import { useMemo } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Droplets, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { AreaChart, Area } from 'recharts'
import { ChartContainer } from '@/components/ui/chart'
import { useTimeseries } from '@/hooks/useTimeseries'
import type { WaterKPI } from '@/types/kpi'

interface KocherGaugeWidgetProps {
  water: WaterKPI | null
}

function getLevelColor(level: number | null): string {
  if (level == null) return '#4CAF50'
  if (level < 80) return '#4CAF50'
  if (level <= 120) return '#FFC107'
  if (level <= 160) return '#FF9800'
  return '#F44336'
}

function getBarWidthPercent(level: number | null): number {
  if (level == null) return 0
  return Math.min((level / 200) * 100, 100)
}

function getTrendInfo(trend: WaterKPI['trend']): { icon: React.ReactNode; label: string } | null {
  if (trend === 'rising') return { icon: <TrendingUp size={14} />, label: 'steigend' }
  if (trend === 'falling') return { icon: <TrendingDown size={14} />, label: 'fallend' }
  if (trend === 'stable') return { icon: <Minus size={14} />, label: 'stabil' }
  return null
}

export function KocherGaugeWidget({ water }: KocherGaugeWidgetProps) {
  const sevenDaysAgo = useMemo(() => {
    const d = new Date()
    d.setDate(d.getDate() - 7)
    return d
  }, [])
  const now = useMemo(() => new Date(), [])

  const { data: tsData } = useTimeseries('water', sevenDaysAgo, now)

  const sparklineData = useMemo(() => {
    if (!tsData?.points) return []
    return tsData.points
      .filter(p => p.values.level_cm != null)
      .map(p => ({
        time: p.time,
        level: typeof p.values.level_cm === 'number' ? p.values.level_cm : null,
      }))
  }, [tsData])

  if (water == null) {
    return (
      <Card className="p-4">
        <CardContent className="p-0 flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground"><Droplets size={16} /></span>
            <span className="text-[16px] font-semibold">Kocher Pegel</span>
          </div>
          <span className="text-[14px] text-muted-foreground">Keine Daten</span>
        </CardContent>
      </Card>
    )
  }

  const levelColor = getLevelColor(water.level_cm)
  const barWidth = getBarWidthPercent(water.level_cm)
  const trendInfo = getTrendInfo(water.trend)

  const chartConfig = {
    level: { label: 'Wasserstand', color: levelColor },
  }

  return (
    <Card className="p-4">
      <CardContent className="p-0 flex flex-col gap-2">
        {/* Header */}
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground"><Droplets size={16} /></span>
          <span className="text-[16px] font-semibold">Kocher Pegel</span>
        </div>

        {/* Level value */}
        <div className="flex items-baseline gap-1">
          <span className="text-[28px] font-semibold leading-none">
            {water.level_cm != null ? Math.round(water.level_cm) : '—'}
          </span>
          <span className="text-[12px] text-muted-foreground">cm</span>
        </div>

        {/* Color bar */}
        <div className="w-full h-2 rounded-full bg-secondary overflow-hidden">
          <div
            className="h-full rounded-full transition-all"
            style={{
              width: `${barWidth}%`,
              backgroundColor: levelColor,
            }}
          />
        </div>

        {/* Trend indicator */}
        {trendInfo && (
          <span className="flex items-center gap-1 text-[12px] text-muted-foreground">
            {trendInfo.icon}
            {trendInfo.label}
          </span>
        )}

        {/* Warning badge */}
        {water.stage != null && water.stage >= 1 && (
          <Badge
            style={{
              backgroundColor: water.stage >= 3 ? '#F44336' : '#FF9800',
              color: '#fff',
            }}
          >
            Warnstufe {water.stage}
          </Badge>
        )}

        {/* Sparkline */}
        {sparklineData.length > 1 && (
          <ChartContainer config={chartConfig} className="h-[40px] w-full">
            <AreaChart data={sparklineData as Record<string, unknown>[]}>
              <Area
                dataKey="level"
                stroke={levelColor}
                fill={levelColor}
                fillOpacity={0.2}
                isAnimationActive={false}
                dot={false}
              />
            </AreaChart>
          </ChartContainer>
        )}

        {/* Gauge name */}
        {water.gauge_name && (
          <span className="text-[11px] text-muted-foreground">{water.gauge_name}</span>
        )}
      </CardContent>
    </Card>
  )
}
