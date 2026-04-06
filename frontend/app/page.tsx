'use client'
import { Suspense, useState } from 'react'
import dynamic from 'next/dynamic'
import Sidebar from '@/components/sidebar/Sidebar'
import { DashboardPanel } from '@/components/dashboard/DashboardPanel'
import { TimeSlider } from '@/components/dashboard/TimeSlider'
import { DateRangePicker } from '@/components/dashboard/DateRangePicker'
import { DomainDetailPanel } from '@/components/dashboard/DomainDetailPanel'
import { TimeSeriesChart } from '@/components/dashboard/TimeSeriesChart'
import { useLayerData } from '@/hooks/useLayerData'
import { useGridLayerData } from '@/hooks/useGridLayerData'
import { useUrlState } from '@/hooks/useUrlState'
import { useTimeseries } from '@/hooks/useTimeseries'
import type { Pollutant } from '@/components/map/AirQualityHeatmapLayer'

const MapView = dynamic(() => import('@/components/map/MapView'), {
  ssr: false,
  loading: () => <div className="flex-1 bg-slate-100 animate-pulse" />,
})

// Inner component — safe to use useSearchParams (wrapped in Suspense by Home)
function HomeInner() {
  const { state, update } = useUrlState()

  const town = state.town   // 'aalen' (from URL or default)
  const dateRange = { from: state.from, to: state.to }
  const historicalTimestamp = state.ts  // Date | null

  // Layer visibility driven by URL params
  const layerVisibility = {
    transit: state.layers.includes('transit'),
    airQuality: state.layers.includes('aqi'),
    water: state.layers.includes('water'),
    floodHazard: state.layers.includes('flood'),
    railNoise: state.layers.includes('rail_noise'),
    lubwEnv: state.layers.includes('lubw_env'),
    traffic: state.layers.includes('traffic'),
    autobahn: state.layers.includes('autobahn'),
    mobiData: state.layers.includes('mobidata'),
    energy: state.layers.includes('energy'),
    schools: state.layers.includes('schools'),
    healthcare: state.layers.includes('healthcare'),
    parks: state.layers.includes('parks'),
    waste: state.layers.includes('waste'),
    evCharging: state.layers.includes('ev_charging'),
    roadworks: state.layers.includes('roadworks'),
    solarPotential: state.layers.includes('solar_potential'),
    trafficFlow: state.layers.includes('traffic_flow'),
    kocher: state.layers.includes('kocher'),
    parking: state.layers.includes('parking'),
    busPosition: state.layers.includes('bus_position'),
    cadastral: state.layers.includes('cadastral'),
    hillshade: state.layers.includes('hillshade'),
    buildings3d: state.layers.includes('buildings3d'),
  }

  const LAYER_KEYS: Record<string, string> = {
    transit: 'transit',
    airQuality: 'aqi',
    water: 'water',
    floodHazard: 'flood',
    railNoise: 'rail_noise',
    lubwEnv: 'lubw_env',
    traffic: 'traffic',
    autobahn: 'autobahn',
    mobiData: 'mobidata',
    energy: 'energy',
    schools: 'schools',
    healthcare: 'healthcare',
    parks: 'parks',
    waste: 'waste',
    evCharging: 'ev_charging',
    roadworks: 'roadworks',
    solarPotential: 'solar_potential',
    trafficFlow: 'traffic_flow',
    kocher: 'kocher',
    parking: 'parking',
    busPosition: 'bus_position',
    cadastral: 'cadastral',
    hillshade: 'hillshade',
    buildings3d: 'buildings3d',
  }

  const toggleLayer = (layer: keyof typeof LAYER_KEYS) => {
    const key = LAYER_KEYS[layer]
    const current = state.layers
    const next = current.includes(key)
      ? current.filter(l => l !== key)
      : [...current, key]
    update({ layers: next.join(',') || null })
  }

  // Pollutant toggle state for air quality heatmap grid
  const [activePollutant, setActivePollutant] = useState<Pollutant>('pm25')

  // Data hooks — pass historicalTimestamp for time slider historical support
  const transit = useLayerData('transit', town, historicalTimestamp)
  const airQuality = useLayerData('air_quality', town, historicalTimestamp)
  const airQualityGrid = useGridLayerData('air_quality', 'air_grid', town, historicalTimestamp)
  const water = useLayerData('water', town, historicalTimestamp)
  const traffic = useLayerData('traffic', town, historicalTimestamp)
  const energy = useLayerData('energy', town)

  // Default chart data (shown when no activeDomain detail panel open)
  const aqiTs = useTimeseries('air_quality', dateRange.from, dateRange.to, town)

  const activeDomain = state.domain  // 'aqi' | 'weather' | 'transit' | 'traffic' | 'energy' | null

  const handleDomainSelect = (domain: string | null) => {
    update({ domain: domain ?? null })
  }

  const handleDateRangeChange = (range: { from: Date; to: Date }) => {
    update({
      from: range.from.toISOString().split('T')[0],
      to: range.to.toISOString().split('T')[0],
    })
  }

  const handleTimeSliderChange = (ts: Date | null) => {
    update({ ts: ts ? ts.toISOString() : null })
  }

  const handleBaseLayerChange = (base: 'osm' | 'orthophoto' | 'satellite') => {
    update({ base: base === 'osm' ? null : base })
  }

  // Dashboard panel chart slot: DomainDetailPanel if activeDomain, else default AQI chart
  const chartSlot = activeDomain ? (
    <DomainDetailPanel
      domain={activeDomain}
      dateRange={dateRange}
      town={town}
      onBack={() => handleDomainSelect(null)}
    />
  ) : (
    <div className="flex flex-col gap-4">
      <DateRangePicker value={dateRange} onChange={handleDateRangeChange} />
      <TimeSeriesChart
        domain="air_quality"
        points={aqiTs.data?.points ?? []}
        loading={aqiTs.loading}
        error={aqiTs.error}
        dateRange={dateRange}
      />
    </div>
  )

  return (
    <main className="flex h-screen overflow-hidden">
      {/* Left sidebar — 280px fixed, collapses to drawer on tablet/mobile */}
      <Sidebar
        layerVisibility={layerVisibility}
        onToggleLayer={toggleLayer}
        transitError={transit.error}
        airQualityError={airQuality.error}
        trafficError={traffic.error}
        energyError={energy.error}
        baseLayer={state.baseLayer}
        onBaseLayerChange={handleBaseLayerChange}
        cadastralVisible={layerVisibility.cadastral}
        hillshadeVisible={layerVisibility.hillshade}
        buildings3dVisible={layerVisibility.buildings3d}
        activePollutant={activePollutant}
        onPollutantChange={setActivePollutant}
      />

      {/* Map column — flex-1, fills space between sidebar and dashboard panel */}
      <div className="flex-1 flex flex-col min-w-0 relative">
        {/* Map view fills remaining height above time slider */}
        <div className="flex-1 relative min-h-0">
          <MapView
            layerVisibility={layerVisibility}
            transitData={transit.data}
            airQualityData={airQuality.data}
            airQualityGridData={airQualityGrid.data}
            activePollutant={activePollutant}
            transitLastFetched={transit.lastFetched}
            airQualityLastFetched={airQuality.lastFetched}
            waterData={water.data}
            waterLastFetched={water.lastFetched}
            historicalTimestamp={historicalTimestamp}
            town={town}
            trafficVisible={layerVisibility.traffic}
            autobahnVisible={layerVisibility.autobahn}
            energyVisible={layerVisibility.energy}
            schoolsVisible={layerVisibility.schools}
            healthcareVisible={layerVisibility.healthcare}
            parksVisible={layerVisibility.parks}
            wasteVisible={layerVisibility.waste}
            evChargingVisible={layerVisibility.evCharging}
            roadworksVisible={layerVisibility.roadworks}
            solarPotentialVisible={layerVisibility.solarPotential}
            trafficFlowVisible={layerVisibility.trafficFlow}
            kocherVisible={layerVisibility.kocher}
            parkingVisible={layerVisibility.parking}
            busPositionVisible={layerVisibility.busPosition}
            baseLayer={state.baseLayer}
            cadastralVisible={layerVisibility.cadastral}
            hillshadeVisible={layerVisibility.hillshade}
            buildings3dVisible={layerVisibility.buildings3d}
          />
        </div>

        {/* Time slider — pinned below map, full map column width */}
        <TimeSlider value={historicalTimestamp} onChange={handleTimeSliderChange} />
      </div>

      {/* Right dashboard panel — 320px, hidden on tablet/mobile (hidden lg:flex inside component) */}
      <DashboardPanel
        town={town}
        activeDomain={activeDomain}
        onDomainSelect={handleDomainSelect}
      >
        {chartSlot}
      </DashboardPanel>
    </main>
  )
}

// Outer shell: Suspense boundary required for useSearchParams in production builds
export default function Home() {
  return (
    <Suspense fallback={null}>
      <HomeInner />
    </Suspense>
  )
}
