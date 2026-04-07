'use client'
import { useState, useRef, useEffect, useMemo, useCallback } from 'react'
import { X } from 'lucide-react'
import { format } from 'date-fns'
import { useKpi } from '@/hooks/useKpi'
import { useTimeseries } from '@/hooks/useTimeseries'
import { TimeSeriesChart } from './TimeSeriesChart'
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts'
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart'

const DOMAIN_LABELS: Record<string, string> = {
  aqi: 'Luftqualitaet',
  weather: 'Wetter',
  transit: 'OEPNV',
  traffic: 'Verkehr',
  energy: 'Energie',
  demographics: 'Demografie',
  parking: 'Parken',
}

const CHART_DOMAIN: Record<string, 'air_quality' | 'weather'> = {
  aqi: 'air_quality',
  weather: 'weather',
}

const ENERGY_SOURCE_COLORS: Record<string, string> = {
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

const ENERGY_SOURCES = [
  'solar', 'wind_onshore', 'wind_offshore', 'hydro',
  'biomass', 'gas', 'lignite', 'hard_coal', 'nuclear',
]

const ENERGY_SOURCE_LABELS: Record<string, string> = {
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

function xTickFormat(time: string, from: Date, to: Date): string {
  const spanDays = (to.getTime() - from.getTime()) / (1000 * 60 * 60 * 24)
  return spanDays <= 1
    ? format(new Date(time), 'HH:mm')
    : format(new Date(time), 'dd.MM')
}

interface StatCardProps {
  label: string
  value: string | null
  unit?: string
}

function StatCard({ label, value, unit }: StatCardProps) {
  return (
    <div className="rounded-lg border bg-muted/30 px-4 py-3">
      <div className="text-xs text-muted-foreground mb-1">{label}</div>
      <div className="text-xl font-semibold leading-none">
        {value ?? '—'}
        {unit && value !== null && <span className="text-sm font-normal text-muted-foreground ml-1">{unit}</span>}
      </div>
    </div>
  )
}

interface DataExplorerModalProps {
  domain: string
  town: string
  onClose: () => void
  initialPosition: { x: number; y: number }
}

export function DataExplorerModal({ domain, town, onClose, initialPosition }: DataExplorerModalProps) {
  const [position, setPosition] = useState(initialPosition)
  const dragging = useRef(false)
  const offset = useRef({ x: 0, y: 0 })
  const titleBarRef = useRef<HTMLDivElement>(null)

  // Date range: last 24 hours
  const dateRange = useMemo(() => ({
    from: new Date(Date.now() - 86400000),
    to: new Date(),
  }), [])

  const chartDomain = CHART_DOMAIN[domain]
  const { data: kpiData } = useKpi(town)
  const { data: tsData, loading, error } = useTimeseries(
    domain === 'traffic' ? 'traffic'
    : domain === 'energy' ? 'energy'
    : chartDomain ?? 'air_quality',
    dateRange.from,
    dateRange.to,
    town,
  )

  // Energy chart data
  const energyChartData = useMemo(() => {
    if (domain !== 'energy' || !tsData?.points) return []
    return tsData.points.map(p => {
      const row: Record<string, unknown> = { time: p.time }
      for (const src of ENERGY_SOURCES) {
        row[src] = typeof p.values[src] === 'number' ? p.values[src] : 0
      }
      row['price'] = typeof p.values['price'] === 'number' ? p.values['price'] : null
      return row
    })
  }, [tsData, domain])

  // Traffic chart data
  const trafficChartData = useMemo(() => {
    if (domain !== 'traffic' || !tsData?.points) return []
    return tsData.points.map(p => ({
      time: p.time,
      flow: typeof p.values['flow'] === 'number' ? p.values['flow'] : null,
    }))
  }, [tsData, domain])

  // Drag handlers
  const handlePointerMove = useCallback((e: PointerEvent) => {
    if (!dragging.current) return
    setPosition({
      x: e.clientX - offset.current.x,
      y: e.clientY - offset.current.y,
    })
  }, [])

  const handlePointerUp = useCallback((e: PointerEvent) => {
    dragging.current = false
    if (titleBarRef.current) {
      titleBarRef.current.releasePointerCapture(e.pointerId)
    }
    window.removeEventListener('pointermove', handlePointerMove)
    window.removeEventListener('pointerup', handlePointerUp)
  }, [handlePointerMove])

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    dragging.current = true
    offset.current = {
      x: e.clientX - position.x,
      y: e.clientY - position.y,
    }
    if (titleBarRef.current) {
      titleBarRef.current.setPointerCapture(e.pointerId)
    }
    window.addEventListener('pointermove', handlePointerMove)
    window.addEventListener('pointerup', handlePointerUp)
  }, [position.x, position.y, handlePointerMove, handlePointerUp])

  // Cleanup listeners on unmount
  useEffect(() => {
    return () => {
      window.removeEventListener('pointermove', handlePointerMove)
      window.removeEventListener('pointerup', handlePointerUp)
    }
  }, [handlePointerMove, handlePointerUp])

  return (
    <div
      className="fixed z-50 bg-white rounded-lg shadow-2xl border border-slate-200 flex flex-col w-[480px] h-[400px]"
      style={{ top: 0, left: 0, transform: `translate(${position.x}px, ${position.y}px)` }}
    >
      {/* Title bar — draggable */}
      <div
        ref={titleBarRef}
        className="flex items-center justify-between px-4 py-2 bg-slate-50 rounded-t-lg border-b cursor-grab active:cursor-grabbing select-none flex-shrink-0"
        onPointerDown={handlePointerDown}
      >
        <span className="text-sm font-semibold text-slate-700">
          {DOMAIN_LABELS[domain] ?? domain}
        </span>
        <button
          onClick={(e) => { e.stopPropagation(); onClose() }}
          className="text-slate-400 hover:text-slate-600 transition-colors"
        >
          <X size={20} />
        </button>
      </div>

      {/* Content area — resizable */}
      <div
        className="flex-1 overflow-auto p-4"
        style={{ resize: 'both', minWidth: 360, minHeight: 300, maxWidth: '90vw', maxHeight: '80vh' }}
      >
        {domain === 'transit' ? (
          <p className="text-sm text-muted-foreground">
            OEPNV-Daten sind statisch (GTFS). Zeitverlauf ist nicht verfuegbar.
          </p>
        ) : domain === 'demographics' ? (
          <>
            {kpiData?.demographics ? (
              <div className="flex flex-col gap-3">
                <div className="grid grid-cols-2 gap-2">
                  <StatCard
                    label="Bevoelkerung"
                    value={kpiData.demographics.population != null
                      ? kpiData.demographics.population.toLocaleString('de-DE')
                      : null}
                    unit={kpiData.demographics.population_year != null
                      ? `(${kpiData.demographics.population_year})`
                      : undefined}
                  />
                  <StatCard
                    label="Unter 18"
                    value={kpiData.demographics.age_under_18_pct != null
                      ? kpiData.demographics.age_under_18_pct.toFixed(1)
                      : null}
                    unit="%"
                  />
                  <StatCard
                    label="Ueber 65"
                    value={kpiData.demographics.age_over_65_pct != null
                      ? kpiData.demographics.age_over_65_pct.toFixed(1)
                      : null}
                    unit="%"
                  />
                  <StatCard
                    label="Arbeitslosenquote"
                    value={kpiData.demographics.unemployment_rate != null
                      ? kpiData.demographics.unemployment_rate.toFixed(1)
                      : null}
                    unit="%"
                  />
                </div>
                <p className="text-[11px] text-muted-foreground">
                  Quelle: Wegweiser Kommune, Statistik BW, Zensus 2022, Bundesagentur fuer Arbeit
                </p>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Keine Demographiedaten verfuegbar.
              </p>
            )}
          </>
        ) : domain === 'parking' ? (
          <>
            {kpiData?.parking ? (
              <div className="flex flex-col gap-3">
                <div className="grid grid-cols-2 gap-2">
                  <StatCard
                    label="Freie Plaetze"
                    value={kpiData.parking.total_free != null
                      ? String(kpiData.parking.total_free)
                      : null}
                  />
                  <StatCard
                    label="Kapazitaet"
                    value={kpiData.parking.total_capacity != null
                      ? String(kpiData.parking.total_capacity)
                      : null}
                  />
                  <StatCard
                    label="Verfuegbarkeit"
                    value={kpiData.parking.availability_pct != null
                      ? kpiData.parking.availability_pct.toFixed(1)
                      : null}
                    unit="%"
                  />
                  <StatCard
                    label="Parkhaeuser"
                    value={String(kpiData.parking.garage_count)}
                  />
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Keine Parkdaten verfuegbar.
              </p>
            )}
          </>
        ) : domain === 'traffic' ? (
          <>
            {loading ? (
              <div className="h-[200px] rounded bg-secondary animate-pulse" />
            ) : error ? (
              <p className="text-sm text-muted-foreground py-4">
                Daten konnten nicht geladen werden.
              </p>
            ) : trafficChartData.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4">
                Keine Messwerte im gewaehlten Zeitraum.
              </p>
            ) : (
              <ChartContainer
                config={{ flow: { label: 'Verkehrsfluss', color: 'var(--chart-1)' } }}
                className="min-h-[200px] w-full"
              >
                <LineChart data={trafficChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="time"
                    tickFormatter={(v) => xTickFormat(v, dateRange.from, dateRange.to)}
                    tick={{ fontSize: 12 }}
                  />
                  <YAxis width={40} tick={{ fontSize: 12 }} />
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
                    dataKey="flow"
                    stroke="var(--color-flow)"
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ChartContainer>
            )}
          </>
        ) : domain === 'energy' ? (
          <>
            {loading ? (
              <div className="h-[200px] rounded bg-secondary animate-pulse" />
            ) : error ? (
              <p className="text-sm text-muted-foreground py-4">
                Daten konnten nicht geladen werden.
              </p>
            ) : energyChartData.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4">
                Keine Messwerte im gewaehlten Zeitraum.
              </p>
            ) : (
              <>
                <ChartContainer
                  config={Object.fromEntries(
                    ENERGY_SOURCES.map(src => [src, { label: ENERGY_SOURCE_LABELS[src] ?? src, color: ENERGY_SOURCE_COLORS[src] }])
                  )}
                  className="min-h-[200px] w-full"
                >
                  <AreaChart data={energyChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="time"
                      tickFormatter={(v) => xTickFormat(v, dateRange.from, dateRange.to)}
                      tick={{ fontSize: 12 }}
                    />
                    <YAxis width={45} tick={{ fontSize: 12 }} unit=" MW" />
                    <ChartTooltip
                      content={
                        <ChartTooltipContent
                          labelFormatter={(label) =>
                            format(new Date(label), 'dd.MM.yyyy HH:mm')
                          }
                        />
                      }
                    />
                    {ENERGY_SOURCES.map(src => (
                      <Area
                        key={src}
                        dataKey={src}
                        stackId="mix"
                        stroke={ENERGY_SOURCE_COLORS[src]}
                        fill={ENERGY_SOURCE_COLORS[src]}
                        fillOpacity={0.7}
                        isAnimationActive={false}
                      />
                    ))}
                  </AreaChart>
                </ChartContainer>

                <ChartContainer
                  config={{ price: { label: 'Preis (EUR/MWh)', color: 'var(--chart-5)' } }}
                  className="min-h-[160px] w-full mt-4"
                >
                  <LineChart data={energyChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="time"
                      tickFormatter={(v) => xTickFormat(v, dateRange.from, dateRange.to)}
                      tick={{ fontSize: 12 }}
                    />
                    <YAxis width={50} tick={{ fontSize: 12 }} unit=" EUR" />
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
                      dataKey="price"
                      stroke="var(--color-price)"
                      dot={false}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ChartContainer>
              </>
            )}
          </>
        ) : chartDomain ? (
          <TimeSeriesChart
            domain={chartDomain}
            points={tsData?.points ?? []}
            loading={loading}
            error={error}
            dateRange={dateRange}
          />
        ) : null}

        {/* Attribution */}
        {tsData?.attribution && tsData.attribution.length > 0 && (
          <div className="text-[12px] text-muted-foreground space-y-1 mt-3">
            {tsData.attribution.map((a, i) => (
              <div key={i}>
                Quelle:{' '}
                <a href={a.url} target="_blank" rel="noopener noreferrer" className="underline">
                  {a.name}
                </a>
                {a.license && ` (${a.license})`}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
