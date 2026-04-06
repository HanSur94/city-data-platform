'use client'
import { useMemo } from 'react'
import { ChevronLeft } from 'lucide-react'
import { format } from 'date-fns'
import { useKpi } from '@/hooks/useKpi'
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts'
import { Button } from '@/components/ui/button'
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart'
import { TimeSeriesChart } from './TimeSeriesChart'
import { useTimeseries } from '@/hooks/useTimeseries'

const DOMAIN_TITLES: Record<string, string> = {
  aqi: 'Luftqualität — Messverlauf',
  weather: 'Wetter — Temperaturverlauf',
  transit: 'ÖPNV',
  traffic: 'Verkehr — Zaehlstellen & Stoerungen',
  energy: 'Energie — Erzeugungsmix & Preise',
  demographics: 'Demografie — Bevoelkerung & Arbeitsmarkt',
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
  'solar',
  'wind_onshore',
  'wind_offshore',
  'hydro',
  'biomass',
  'gas',
  'lignite',
  'hard_coal',
  'nuclear',
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

interface DomainDetailPanelProps {
  domain: string
  dateRange: { from: Date; to: Date }
  town?: string
  onBack: () => void
}

export function DomainDetailPanel({ domain, dateRange, town = 'aalen', onBack }: DomainDetailPanelProps) {
  const chartDomain = CHART_DOMAIN[domain]
  const { data: kpiData } = useKpi(town)
  const { data, loading, error } = useTimeseries(
    domain === 'traffic' ? 'traffic'
    : domain === 'energy' ? 'energy'
    : chartDomain ?? 'air_quality',
    dateRange.from,
    dateRange.to,
    town,
  )

  // For energy domain: build chart-ready data with all sources normalized to 0 if missing
  const energyChartData = useMemo(() => {
    if (domain !== 'energy' || !data?.points) return []
    return data.points.map(p => {
      const row: Record<string, unknown> = { time: p.time }
      for (const src of ENERGY_SOURCES) {
        row[src] = typeof p.values[src] === 'number' ? p.values[src] : 0
      }
      row['price'] = typeof p.values['price'] === 'number' ? p.values['price'] : null
      return row
    })
  }, [data, domain])

  // For traffic domain: build chart-ready data
  const trafficChartData = useMemo(() => {
    if (domain !== 'traffic' || !data?.points) return []
    return data.points.map(p => ({
      time: p.time,
      flow: typeof p.values['flow'] === 'number' ? p.values['flow'] : null,
    }))
  }, [data, domain])

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" onClick={onBack} className="px-2">
          <ChevronLeft size={16} />
          Zurück
        </Button>
        <span className="text-[16px] font-semibold">
          {DOMAIN_TITLES[domain] ?? domain}
        </span>
      </div>

      {domain === 'transit' ? (
        <p className="text-[14px] text-muted-foreground">
          ÖPNV-Daten sind statisch (GTFS). Zeitverlauf ist nicht verfügbar.
        </p>
      ) : domain === 'traffic' ? (
        <>
          {loading ? (
            <div className="h-[200px] rounded bg-secondary animate-pulse" />
          ) : error ? (
            <p className="text-[14px] text-muted-foreground py-4">
              Daten konnten nicht geladen werden. Bitte Zeitraum anpassen oder Seite neu laden.
            </p>
          ) : trafficChartData.length === 0 ? (
            <p className="text-[14px] text-muted-foreground py-4">
              Keine Messwerte im gewählten Zeitraum.
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
            <p className="text-[14px] text-muted-foreground py-4">
              Daten konnten nicht geladen werden. Bitte Zeitraum anpassen oder Seite neu laden.
            </p>
          ) : energyChartData.length === 0 ? (
            <p className="text-[14px] text-muted-foreground py-4">
              Keine Messwerte im gewählten Zeitraum.
            </p>
          ) : (
            <>
              {/* Stacked area chart for generation mix */}
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

              {/* Line chart for wholesale price */}
              <ChartContainer
                config={{ price: { label: 'Preis (EUR/MWh)', color: 'var(--chart-5)' } }}
                className="min-h-[160px] w-full"
              >
                <LineChart data={energyChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="time"
                    tickFormatter={(v) => xTickFormat(v, dateRange.from, dateRange.to)}
                    tick={{ fontSize: 12 }}
                  />
                  <YAxis width={50} tick={{ fontSize: 12 }} unit=" €" />
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
      ) : domain === 'demographics' ? (
        <>
          {kpiData?.demographics ? (
            <div className="flex flex-col gap-3">
              <div className="grid grid-cols-2 gap-2">
                <StatCard
                  label="Bevölkerung"
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
                  label="Über 65"
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
                Quelle: Wegweiser Kommune, Statistik BW, Zensus 2022, Bundesagentur für Arbeit
              </p>
            </div>
          ) : (
            <p className="text-[14px] text-muted-foreground py-4">
              Keine Demographiedaten verfügbar.
            </p>
          )}
        </>
      ) : chartDomain ? (
        <TimeSeriesChart
          domain={chartDomain}
          points={data?.points ?? []}
          loading={loading}
          error={error}
          dateRange={dateRange}
        />
      ) : null}

      {/* Attribution */}
      {data?.attribution && data.attribution.length > 0 && (
        <div className="text-[12px] text-muted-foreground space-y-1">
          {data.attribution.map((a, i) => (
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
  )
}
