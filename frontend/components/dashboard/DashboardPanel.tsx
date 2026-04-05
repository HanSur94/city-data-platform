'use client'
import { Wind, Thermometer, Bus } from 'lucide-react'
import { Separator } from '@/components/ui/separator'
import { KpiTile } from './KpiTile'
import { useKpi } from '@/hooks/useKpi'

interface DashboardPanelProps {
  town?: string
  activeDomain: string | null
  onDomainSelect: (domain: string | null) => void
  // Chart slot: rendered below KPI tiles; passed as children to keep this component stable
  children?: React.ReactNode
}

export function DashboardPanel({
  town = 'aalen',
  activeDomain,
  onDomainSelect,
  children,
}: DashboardPanelProps) {
  const { data, loading } = useKpi(town)

  const handleSelect = (domain: string) => {
    // Toggle: clicking active domain closes the detail panel
    onDomainSelect(activeDomain === domain ? null : domain)
  }

  const aqiValue = data?.air_quality?.current_aqi != null
    ? String(Math.round(data.air_quality.current_aqi))
    : null

  const tempValue = data?.weather?.temperature != null
    ? data.weather.temperature.toFixed(1)
    : null

  const routeValue = data?.transit != null
    ? String(data.transit.route_count)
    : null

  return (
    <aside className="hidden lg:flex w-[320px] flex-shrink-0 flex-col h-screen overflow-y-auto border-l bg-background">
      {/* Panel header */}
      <div className="px-4 pt-8 pb-4">
        <h2 className="text-[16px] font-semibold">Übersicht</h2>
      </div>

      {/* KPI section */}
      <div className="px-4 pb-4">
        <h3 className="text-[16px] font-semibold mb-3">Kennzahlen</h3>
        {loading && !data ? (
          <div className="space-y-2">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-[80px] rounded-lg bg-secondary animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="space-y-2">
            <KpiTile
              domain="aqi"
              label="Luftqualität"
              icon={<Wind size={16} />}
              value={aqiValue}
              unit="AQI"
              trend={null}
              active={activeDomain === 'aqi'}
              onSelect={handleSelect}
            />
            <KpiTile
              domain="weather"
              label="Wetter"
              icon={<Thermometer size={16} />}
              value={tempValue}
              unit="°C"
              trend={null}
              active={activeDomain === 'weather'}
              onSelect={handleSelect}
            />
            <KpiTile
              domain="transit"
              label="ÖPNV"
              icon={<Bus size={16} />}
              value={routeValue}
              unit="Linien"
              trend={null}
              active={activeDomain === 'transit'}
              onSelect={handleSelect}
            />
          </div>
        )}
      </div>

      <Separator />

      {/* Chart/detail slot */}
      <div className="flex-1 px-4 py-4">
        <h3 className="text-[16px] font-semibold mb-3">Verlauf</h3>
        {children}
      </div>
    </aside>
  )
}
