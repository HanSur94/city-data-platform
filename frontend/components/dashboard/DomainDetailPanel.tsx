'use client'
import { ChevronLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { TimeSeriesChart } from './TimeSeriesChart'
import { useTimeseries } from '@/hooks/useTimeseries'

const DOMAIN_TITLES: Record<string, string> = {
  aqi: 'Luftqualität — Messverlauf',
  weather: 'Wetter — Temperaturverlauf',
  transit: 'ÖPNV',
}

const CHART_DOMAIN: Record<string, 'air_quality' | 'weather'> = {
  aqi: 'air_quality',
  weather: 'weather',
}

interface DomainDetailPanelProps {
  domain: string // 'aqi' | 'weather' | 'transit'
  dateRange: { from: Date; to: Date }
  town?: string
  onBack: () => void
}

export function DomainDetailPanel({ domain, dateRange, town = 'aalen', onBack }: DomainDetailPanelProps) {
  const chartDomain = CHART_DOMAIN[domain]
  const { data, loading, error } = useTimeseries(
    chartDomain ?? 'air_quality', // fallback (transit has no timeseries)
    dateRange.from,
    dateRange.to,
    town,
  )

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
