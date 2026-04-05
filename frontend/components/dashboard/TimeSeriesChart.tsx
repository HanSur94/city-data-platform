'use client'
import { useMemo } from 'react'
import { format } from 'date-fns'
import {
  AreaChart, Area, LineChart, Line,
  XAxis, YAxis, CartesianGrid,
} from 'recharts'
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart'
import type { TimeseriesPoint } from '@/types/timeseries'

interface TimeSeriesChartProps {
  domain: 'air_quality' | 'weather'
  points: TimeseriesPoint[]
  loading: boolean
  error: boolean
  dateRange: { from: Date; to: Date }
}

// Determine x-axis tick format from range span
function xTickFormat(time: string, from: Date, to: Date): string {
  const spanDays = (to.getTime() - from.getTime()) / (1000 * 60 * 60 * 24)
  return spanDays <= 1
    ? format(new Date(time), 'HH:mm')
    : format(new Date(time), 'dd.MM')
}

export function TimeSeriesChart({ domain, points, loading, error, dateRange }: TimeSeriesChartProps) {
  // Map points to chart-ready data with only the relevant numeric fields
  const chartData = useMemo(() => {
    if (domain === 'air_quality') {
      return points
        .filter(p => p.values.pm25 != null || p.values.pm10 != null)
        .map(p => ({
          time: p.time,
          pm25: typeof p.values.pm25 === 'number' ? p.values.pm25 : null,
          pm10: typeof p.values.pm10 === 'number' ? p.values.pm10 : null,
        }))
    }
    if (domain === 'weather') {
      return points
        .filter(p => p.values.temperature != null)
        .map(p => ({
          time: p.time,
          temperature: typeof p.values.temperature === 'number' ? p.values.temperature : null,
        }))
    }
    return []
  }, [points, domain])

  if (loading) {
    return <div className="h-[200px] rounded bg-secondary animate-pulse" />
  }

  if (error) {
    return (
      <p className="text-[14px] text-muted-foreground py-4">
        Daten konnten nicht geladen werden. Bitte Zeitraum anpassen oder Seite neu laden.
      </p>
    )
  }

  if (chartData.length === 0) {
    return (
      <p className="text-[14px] text-muted-foreground py-4">
        Keine Messwerte im gewählten Zeitraum.
      </p>
    )
  }

  if (domain === 'air_quality') {
    const config = {
      pm25: { label: 'PM2.5', color: 'var(--chart-2)' },
      pm10: { label: 'PM10', color: 'var(--chart-4)' },
    }
    return (
      <ChartContainer config={config} className="min-h-[200px] w-full">
        <AreaChart data={chartData as Record<string, unknown>[]}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="time"
            tickFormatter={(v) => xTickFormat(v, dateRange.from, dateRange.to)}
            tick={{ fontSize: 12 }}
          />
          <YAxis width={35} tick={{ fontSize: 12 }} />
          <ChartTooltip
            content={
              <ChartTooltipContent
                labelFormatter={(label) =>
                  format(new Date(label), 'dd.MM.yyyy HH:mm')
                }
              />
            }
          />
          <Area
            dataKey="pm25"
            stroke="var(--color-pm25)"
            fill="var(--color-pm25)"
            fillOpacity={0.3}
            isAnimationActive={false}
          />
          <Area
            dataKey="pm10"
            stroke="var(--color-pm10)"
            fill="var(--color-pm10)"
            fillOpacity={0.3}
            isAnimationActive={false}
          />
        </AreaChart>
      </ChartContainer>
    )
  }

  if (domain === 'weather') {
    const config = {
      temperature: { label: 'Temperatur', color: 'var(--chart-2)' },
    }
    return (
      <ChartContainer config={config} className="min-h-[200px] w-full">
        <LineChart data={chartData as Record<string, unknown>[]}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="time"
            tickFormatter={(v) => xTickFormat(v, dateRange.from, dateRange.to)}
            tick={{ fontSize: 12 }}
          />
          <YAxis width={35} tick={{ fontSize: 12 }} />
          <ChartTooltip
            content={
              <ChartTooltipContent
                labelFormatter={(label) =>
                  format(new Date(label), 'dd.MM.yyyy HH:mm')
                }
              />
            }
          />
          <Line
            dataKey="temperature"
            stroke="var(--color-temperature)"
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ChartContainer>
    )
  }

  return null
}
