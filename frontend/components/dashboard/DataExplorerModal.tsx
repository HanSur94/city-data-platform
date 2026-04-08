'use client'
import { useState, useRef, useEffect, useMemo, useCallback } from 'react'
import { X, Bus, Train } from 'lucide-react'
import { format } from 'date-fns'
import { useKpi } from '@/hooks/useKpi'
import { useTimeseries } from '@/hooks/useTimeseries'
import { TimeSeriesChart } from './TimeSeriesChart'
import { fetchLayer } from '@/lib/api'
import { lineColor } from '@/components/map/BusPositionLayer'
import type { FeatureCollection, Feature } from 'geojson'
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

const DOMAIN_DESCRIPTIONS: Record<string, string> = {
  aqi: 'Aktuelle Luftqualitaetswerte und Verlauf der letzten 24 Stunden.',
  weather: 'Wetterdaten und Temperaturverlauf der letzten 24 Stunden.',
  transit: 'Live-Fahrplan aller aktiven Buslinien mit Position, naechster Halt und Verspaetung.',
  traffic: 'Verkehrsfluss an Zaehlstellen der letzten 24 Stunden (Quelle: BASt).',
  energy: 'Stromerzeugung nach Energietraeger und Boersenpreis der letzten 24 Stunden (Quelle: SMARD / Bundesnetzagentur).',
  demographics: 'Demographische Kennzahlen aus oeffentlichen Statistiken.',
  parking: 'Aktuelle Parkhaus-Belegung und Verfuegbarkeit.',
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

// ── Transit Timetable ─────────────────────────────────────────────────────────

interface BusRow {
  tripId: string
  lineName: string
  destination: string
  routeType: number
  nextStop: string
  prevStop: string
  delaySeconds: number
  progress: number
  departed: boolean
  scheduledDep: string
  scheduledArr: string
  color: string
}

function formatDelay(seconds: number): { text: string; color: string } {
  if (seconds < 60) return { text: 'puenktl.', color: '#22c55e' }
  const min = Math.round(seconds / 60)
  if (min < 3) return { text: `+${min}′`, color: '#22c55e' }
  if (min < 6) return { text: `+${min}′`, color: '#eab308' }
  if (min < 11) return { text: `+${min}′`, color: '#f97316' }
  return { text: `+${min}′`, color: '#ef4444' }
}

function TransitTimetable({ town }: { town: string }) {
  const [rows, setRows] = useState<BusRow[]>([])
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const loadData = useCallback(async () => {
    try {
      const json = await fetchLayer('transit', town, null, 'bus_position')
      const fc = json as unknown as FeatureCollection
      const busRows: BusRow[] = []

      for (const f of fc.features) {
        const p = f.properties ?? {}
        if (p.feature_type !== 'bus_position') continue
        busRows.push({
          tripId: p.trip_id ?? '',
          lineName: p.line_name ?? '?',
          destination: p.destination ?? '',
          routeType: (p.route_type as number) ?? 3,
          nextStop: p.next_stop ?? '',
          prevStop: p.prev_stop ?? '',
          delaySeconds: (p.delay_seconds as number) ?? 0,
          progress: (p.progress as number) ?? 0,
          departed: p.departed !== false,
          scheduledDep: (p.scheduled_departure as string) ?? '',
          scheduledArr: (p.scheduled_arrival as string) ?? '',
          color: lineColor(p.line_name ?? ''),
        })
      }

      // Sort by line name (numeric-aware), then by destination
      busRows.sort((a, b) => {
        const cmp = a.lineName.localeCompare(b.lineName, undefined, { numeric: true })
        return cmp !== 0 ? cmp : a.destination.localeCompare(b.destination)
      })

      setRows(busRows)
      setLastUpdated(new Date())
      setLoading(false)
    } catch {
      setLoading(false)
    }
  }, [town])

  useEffect(() => {
    loadData()
    const id = setInterval(loadData, 30_000)
    return () => clearInterval(id)
  }, [loadData])

  if (loading && rows.length === 0) {
    return (
      <div className="space-y-2">
        {[1, 2, 3, 4, 5].map(i => (
          <div key={i} className="h-10 rounded bg-muted/50 animate-pulse" />
        ))}
      </div>
    )
  }

  if (rows.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Keine aktiven Busse/Bahnen im Moment.
      </p>
    )
  }

  return (
    <div className="space-y-2">
      {lastUpdated && (
        <p className="text-[11px] text-muted-foreground">
          Aktualisiert: {format(lastUpdated, 'HH:mm:ss')} — {rows.length} aktive Fahrten
        </p>
      )}
      <div className="overflow-auto max-h-[400px]">
        <table className="w-full text-[12px]">
          <thead className="sticky top-0 bg-white">
            <tr className="text-left text-muted-foreground border-b">
              <th className="py-1.5 pr-2 font-medium">Linie</th>
              <th className="py-1.5 pr-2 font-medium">Richtung</th>
              <th className="py-1.5 pr-2 font-medium">Naechster Halt</th>
              <th className="py-1.5 pr-2 font-medium text-center">Abf.</th>
              <th className="py-1.5 pr-2 font-medium text-center">Ank.</th>
              <th className="py-1.5 pr-2 font-medium text-center">Versp.</th>
              <th className="py-1.5 font-medium text-center">Fortschritt</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const delay = formatDelay(row.delaySeconds)
              const isTrain = row.routeType <= 2
              return (
                <tr key={row.tripId} className="border-b border-slate-100 hover:bg-slate-50">
                  <td className="py-1.5 pr-2">
                    <span className="inline-flex items-center gap-1">
                      {isTrain
                        ? <Train className="h-3 w-3" style={{ color: row.color }} />
                        : <Bus className="h-3 w-3" style={{ color: row.color }} />
                      }
                      <span className="font-medium" style={{ color: row.color }}>
                        {row.lineName}
                      </span>
                    </span>
                  </td>
                  <td className="py-1.5 pr-2 max-w-[140px] truncate" title={row.destination}>
                    {row.destination}
                  </td>
                  <td className="py-1.5 pr-2 max-w-[120px] truncate" title={row.nextStop}>
                    {row.departed ? row.nextStop : <span className="text-muted-foreground italic">Wartet</span>}
                  </td>
                  <td className="py-1.5 pr-2 text-center text-muted-foreground">
                    {row.scheduledDep}
                  </td>
                  <td className="py-1.5 pr-2 text-center text-muted-foreground">
                    {row.scheduledArr}
                  </td>
                  <td className="py-1.5 pr-2 text-center font-medium" style={{ color: delay.color }}>
                    {delay.text}
                  </td>
                  <td className="py-1.5">
                    <div className="flex items-center gap-1">
                      <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{ width: `${Math.round(row.progress * 100)}%`, backgroundColor: row.color }}
                        />
                      </div>
                      <span className="text-[10px] text-muted-foreground w-7 text-right">
                        {Math.round(row.progress * 100)}%
                      </span>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Data Explorer Modal ───────────────────────────────────────────────────────

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

  // Energy chart data — pivot flat rows (one per source_type) into grouped rows (one per timestamp)
  const energyChartData = useMemo(() => {
    if (domain !== 'energy' || !tsData?.points) return []
    const grouped = new Map<string, Record<string, unknown>>()
    for (const p of tsData.points) {
      const src = p.values.source_type as string | undefined
      const val = typeof p.values.value_kw === 'number' ? p.values.value_kw / 1000 : 0 // kW → MW
      if (!grouped.has(p.time)) {
        const row: Record<string, unknown> = { time: p.time }
        for (const s of ENERGY_SOURCES) row[s] = 0
        row['price'] = null
        grouped.set(p.time, row)
      }
      const row = grouped.get(p.time)!
      if (src === 'price') {
        row['price'] = val
      } else if (src && ENERGY_SOURCES.includes(src)) {
        row[src] = val
      }
    }
    return Array.from(grouped.values()).sort((a, b) =>
      String(a.time).localeCompare(String(b.time))
    )
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

  const handlePointerUp = useCallback(() => {
    dragging.current = false
    window.removeEventListener('pointermove', handlePointerMove)
    window.removeEventListener('pointerup', handlePointerUp)
  }, [handlePointerMove])

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    // Do not start drag when clicking the close button (or any descendant marked data-nodrag)
    const target = e.target as HTMLElement
    if (target.closest('[data-nodrag]')) return

    dragging.current = true
    offset.current = {
      x: e.clientX - position.x,
      y: e.clientY - position.y,
    }
    window.addEventListener('pointermove', handlePointerMove)
    window.addEventListener('pointerup', handlePointerUp)
  }, [position.x, position.y, handlePointerMove, handlePointerUp])

  // Escape key closes the modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  // Cleanup drag listeners on unmount
  useEffect(() => {
    return () => {
      window.removeEventListener('pointermove', handlePointerMove)
      window.removeEventListener('pointerup', handlePointerUp)
    }
  }, [handlePointerMove, handlePointerUp])

  return (
    <div
      className="fixed z-50 bg-white rounded-lg shadow-2xl border border-slate-200 flex flex-col overflow-hidden"
      style={{ top: 0, left: 0, transform: `translate(${position.x}px, ${position.y}px)`, width: 560, height: 520, minWidth: 400, minHeight: 340, maxWidth: '90vw', maxHeight: '85vh', resize: 'both', overflow: 'hidden' }}
    >
      {/* Title bar — draggable */}
      <div
        ref={titleBarRef}
        className="flex items-start justify-between px-4 py-3 bg-slate-50 rounded-t-lg border-b cursor-grab active:cursor-grabbing select-none flex-shrink-0 gap-3"
        onPointerDown={handlePointerDown}
      >
        <div className="min-w-0">
          <div className="text-sm font-semibold text-slate-700">
            {DOMAIN_LABELS[domain] ?? domain} — {town}
          </div>
          {DOMAIN_DESCRIPTIONS[domain] && (
            <div className="text-xs text-slate-400 mt-0.5 leading-snug">
              {DOMAIN_DESCRIPTIONS[domain]}
            </div>
          )}
        </div>
        <button
          data-nodrag
          onPointerDown={(e) => e.stopPropagation()}
          onClick={() => onClose()}
          className="text-slate-400 hover:text-slate-600 transition-colors flex-shrink-0 mt-0.5 p-1 -mr-1 rounded hover:bg-slate-200"
        >
          <X size={18} />
        </button>
      </div>

      {/* Content area — resizable */}
      <div
        className="flex-1 overflow-auto p-4"
      >
        {domain === 'transit' ? (
          <TransitTimetable town={town} />
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
              <div className="space-y-4">
                {/* Energy mix chart */}
                <div>
                  <h4 className="text-xs font-semibold text-slate-600 mb-1">Stromerzeugung nach Energietraeger</h4>
                  <div className="flex flex-wrap gap-x-3 gap-y-1 mb-2">
                    {ENERGY_SOURCES.map(src => (
                      <span key={src} className="flex items-center gap-1 text-[11px] text-slate-500">
                        <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: ENERGY_SOURCE_COLORS[src] }} />
                        {ENERGY_SOURCE_LABELS[src]}
                      </span>
                    ))}
                  </div>
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
                        tick={{ fontSize: 11 }}
                      />
                      <YAxis width={50} tick={{ fontSize: 11 }} unit=" MW" />
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
                </div>

                {/* Price chart */}
                <div>
                  <h4 className="text-xs font-semibold text-slate-600 mb-1">Boersenstrompreis (Day-Ahead)</h4>
                  <ChartContainer
                    config={{ price: { label: 'Preis (EUR/MWh)', color: 'var(--chart-5)' } }}
                    className="min-h-[160px] w-full"
                  >
                    <LineChart data={energyChartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        dataKey="time"
                        tickFormatter={(v) => xTickFormat(v, dateRange.from, dateRange.to)}
                        tick={{ fontSize: 11 }}
                      />
                      <YAxis width={55} tick={{ fontSize: 11 }} unit=" EUR" />
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
                </div>
              </div>
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
