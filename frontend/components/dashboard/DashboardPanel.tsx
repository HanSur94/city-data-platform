'use client'
import { Wind, Thermometer, Bus, Car, Zap, Users, CircleParking, ChevronLeft, ChevronRight } from 'lucide-react'
import { Separator } from '@/components/ui/separator'
import { KpiTile } from './KpiTile'
import { EnergyMixBar } from './EnergyMixBar'
import { KocherGaugeWidget } from './KocherGaugeWidget'
import { useKpi } from '@/hooks/useKpi'
import { LAYER_METADATA } from '@/lib/layer-metadata'
import { useLayerMetadata } from '@/hooks/useLayerMetadata'

interface DashboardPanelProps {
  town?: string
  onExplore?: (domain: string) => void
  // Chart slot: rendered below KPI tiles; passed as children to keep this component stable
  children?: React.ReactNode
  collapsed?: boolean
  onToggle?: () => void
}

export function DashboardPanel({
  town = 'aalen',
  onExplore,
  children,
  collapsed,
  onToggle,
}: DashboardPanelProps) {
  const { data, loading, refreshing, lastFetched: kpiLastFetched } = useKpi(town)
  const { layerMeta } = useLayerMetadata(town)

  function formatTime(ts: string | Date | null | undefined): string {
    if (!ts) return '--:--';
    try {
      const d = ts instanceof Date ? ts : new Date(ts);
      return d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
    } catch { return '--:--'; }
  }

  const handleSelect = (domain: string) => {
    onExplore?.(domain)
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
    <div className="hidden lg:block relative">
      {/* Toggle button — always visible */}
      <button
        onClick={onToggle}
        className="absolute top-1/2 left-0 -translate-x-full -translate-y-1/2 z-30 flex items-center justify-center w-[28px] h-[48px] bg-white border border-r-0 border-slate-200 rounded-l-md shadow-sm hover:bg-slate-50 transition-colors"
        aria-label={collapsed ? 'Dashboard einblenden' : 'Dashboard ausblenden'}
      >
        {collapsed ? <ChevronLeft className="h-4 w-4 text-slate-600" /> : <ChevronRight className="h-4 w-4 text-slate-600" />}
      </button>
    <aside className={`flex flex-shrink-0 flex-col h-screen overflow-y-auto border-l bg-background transition-all duration-300 ease-in-out ${
      collapsed ? 'w-0 overflow-hidden translate-x-full' : 'w-[320px]'
    }`}>
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
              label="Luftqualitaet"
              icon={<Wind size={16} />}
              value={aqiValue}
              unit="AQI"
              trend={null}

              onSelect={handleSelect}
              refreshing={refreshing}
              sourceAbbrev={LAYER_METADATA['airQuality']?.sourceAbbrev}
              sourceTimestamp={formatTime(layerMeta['airQuality']?.lastUpdated)}
              dataType={LAYER_METADATA['airQuality']?.dataType}
            />
            <KpiTile
              domain="weather"
              label="Wetter"
              icon={<Thermometer size={16} />}
              value={tempValue}
              unit="deg. C"
              trend={null}

              onSelect={handleSelect}
              refreshing={refreshing}
              sourceAbbrev={LAYER_METADATA['water']?.sourceAbbrev}
              sourceTimestamp={formatTime(layerMeta['water']?.lastUpdated)}
              dataType={LAYER_METADATA['water']?.dataType}
            />
            <KpiTile
              domain="transit"
              label="OEPNV"
              icon={<Bus size={16} />}
              value={routeValue}
              unit="Linien"
              trend={null}

              onSelect={handleSelect}
              refreshing={refreshing}
              sourceAbbrev={LAYER_METADATA['transit']?.sourceAbbrev}
              sourceTimestamp={formatTime(layerMeta['transit']?.lastUpdated)}
              dataType={LAYER_METADATA['transit']?.dataType}
            />
            <KpiTile
              domain="traffic"
              icon={<Car className="h-4 w-4" />}
              label="Verkehr"
              value={trafficValue}
              unit={trafficUnit}
              trend={null}

              onSelect={handleSelect}
              refreshing={refreshing}
              sourceAbbrev={LAYER_METADATA['traffic']?.sourceAbbrev}
              sourceTimestamp={formatTime(layerMeta['traffic']?.lastUpdated)}
              dataType={LAYER_METADATA['traffic']?.dataType}
            />
            <KpiTile
              domain="energy"
              icon={<Zap className="h-4 w-4" />}
              label="Energie"
              value={energyValue}
              unit="Erneuerbare am Netz"
              trend={null}

              onSelect={handleSelect}
              refreshing={refreshing}
              sourceAbbrev={LAYER_METADATA['energy']?.sourceAbbrev}
              sourceTimestamp={formatTime(layerMeta['energy']?.lastUpdated)}
              dataType={LAYER_METADATA['energy']?.dataType}
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

                onSelect={handleSelect}
              refreshing={refreshing}
                sourceAbbrev={LAYER_METADATA['demographics']?.sourceAbbrev}
                sourceTimestamp={formatTime(layerMeta['demographics']?.lastUpdated)}
                dataType={LAYER_METADATA['demographics']?.dataType}
              />
            )}
            {data?.water != null && (
              <KocherGaugeWidget water={data.water} />
            )}
            {data?.parking != null && (
              <KpiTile
                domain="parking"
                icon={<CircleParking className="h-4 w-4" />}
                label="Parken"
                value={data.parking.total_free != null ? String(data.parking.total_free) : null}
                unit={data.parking.total_capacity != null ? `von ${data.parking.total_capacity} frei` : 'Parkplaetze'}
                trend={null}

                onSelect={handleSelect}
              refreshing={refreshing}
                sourceAbbrev={LAYER_METADATA['parking']?.sourceAbbrev}
                sourceTimestamp={formatTime(layerMeta['parking']?.lastUpdated)}
                dataType={LAYER_METADATA['parking']?.dataType}
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
    </div>
  )
}
