'use client'
import { Wind, Thermometer, Bus, Car, Zap, Users } from 'lucide-react'
import { Separator } from '@/components/ui/separator'
import { KpiTile } from './KpiTile'
import { EnergyMixBar } from './EnergyMixBar'
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

  const trafficValue = data?.traffic != null
    ? `${data.traffic.active_roadworks} aktiv`
    : null

  const trafficUnit = data?.traffic?.flow_status === 'elevated'
    ? 'Oe Auslastung: erhoeht'
    : data?.traffic?.flow_status === 'congested'
    ? 'Oe Auslastung: hoch'
    : 'Oe Auslastung: normal'

  const energyValue = data?.energy?.renewable_percent != null
    ? `${Math.round(data.energy.renewable_percent)}%`
    : null

  const demographicsValue = data?.demographics?.population != null
    ? data.demographics.population.toLocaleString('de-DE')
    : null

  const demographicsUnit = data?.demographics?.population_year != null
    ? `Einw. (${data.demographics.population_year})`
    : 'Einw.'

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
            {[1, 2, 3, 4, 5].map(i => (
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
            <KpiTile
              domain="traffic"
              icon={<Car className="h-4 w-4" />}
              label="Verkehr"
              value={trafficValue}
              unit={trafficUnit}
              trend={null}
              active={activeDomain === 'traffic'}
              onSelect={handleSelect}
            />
            <KpiTile
              domain="energy"
              icon={<Zap className="h-4 w-4" />}
              label="Energie"
              value={energyValue}
              unit="Erneuerbare am Netz"
              trend={null}
              active={activeDomain === 'energy'}
              onSelect={handleSelect}
            >
              {data?.energy?.generation_mix && Object.keys(data.energy.generation_mix).length > 0 && (
                <EnergyMixBar mix={data.energy.generation_mix} compact />
              )}
            </KpiTile>
            {data?.demographics != null && (
              <KpiTile
                domain="demographics"
                icon={<Users className="h-4 w-4" />}
                label="Demografie"
                value={demographicsValue}
                unit={demographicsUnit}
                trend={null}
                active={activeDomain === 'demographics'}
                onSelect={handleSelect}
              />
            )}
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
