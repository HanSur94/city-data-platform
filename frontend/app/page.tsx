'use client'
import { Suspense, useCallback, useRef, useState } from 'react'
import dynamic from 'next/dynamic'
import Sidebar from '@/components/sidebar/Sidebar'
import { DashboardPanel } from '@/components/dashboard/DashboardPanel'
import { TimeSlider } from '@/components/dashboard/TimeSlider'
import { DateRangePicker } from '@/components/dashboard/DateRangePicker'
import { TimeSeriesChart } from '@/components/dashboard/TimeSeriesChart'
import { DataExplorerModal } from '@/components/dashboard/DataExplorerModal'
import { useKpi } from '@/hooks/useKpi'
import { useLayerData } from '@/hooks/useLayerData'
import { useGridLayerData } from '@/hooks/useGridLayerData'
import { useUrlState } from '@/hooks/useUrlState'
import { useTimeseries } from '@/hooks/useTimeseries'
import type { Pollutant } from '@/components/map/AirQualityHeatmapLayer'
import type { DemographicMetric } from '@/components/map/DemographicsGridLayer'
import type { PopupInfo } from '@/components/map/MapView'
import { nextUrlLayers, visibilityFromUrl } from '@/lib/layer-registry'
import type { LayerKey } from '@/lib/layer-registry'
import { DEFAULT_BASE_LAYER } from '@/lib/map-styles'
import type { BaseLayer } from '@/lib/map-styles'
import type { SearchResult } from '@/components/sidebar/FeatureSearch'

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

  // Layer visibility driven by URL params; the registry is the single source of layers
  const layerVisibility = visibilityFromUrl(state.layers)

  // One URL update per call. An empty list is written as an empty string (not null):
  // a missing `layers` parameter would bring the default layer set back.
  const setLayers = (keys: readonly LayerKey[], on: boolean) => {
    update({ layers: nextUrlLayers(state.layers, keys, on).join(',') })
  }

  const toggleLayer = (layer: LayerKey) => {
    setLayers([layer], !layerVisibility[layer])
  }

  // Map flyTo function ref, set by MapView's onMapReady callback
  const flyToRef = useRef<((lng: number, lat: number, zoom?: number) => void) | null>(null)
  const [pendingPopup, setPendingPopup] = useState<PopupInfo | null>(null)

  const handleMapReady = useCallback((flyTo: (lng: number, lat: number, zoom?: number) => void) => {
    flyToRef.current = flyTo
  }, [])

  const handleFeatureSelect = useCallback((result: SearchResult) => {
    // Fly to location
    flyToRef.current?.(result.longitude, result.latitude, 17)
    // After a short delay for the fly animation, set popup
    setTimeout(() => {
      setPendingPopup({
        longitude: result.longitude,
        latitude: result.latitude,
        feature: {
          type: 'Feature',
          geometry: { type: 'Point', coordinates: [result.longitude, result.latitude] },
          properties: {
            feature_id: result.id,
            name: result.name,
            stop_name: result.name,
            semantic_id: result.semantic_id,
            domain: result.domain,
          },
        },
        domain: result.domain === 'infrastructure' ? 'evCharging'
          : result.domain === 'transit' ? 'transit'
          : result.domain === 'air_quality' ? 'airQuality'
          : result.domain === 'traffic' ? 'traffic'
          : result.domain === 'energy' ? 'energy'
          : result.domain === 'community' ? 'community'
          : result.domain === 'water' ? 'water'
          : result.domain === 'demographics' ? 'demographics'
          : result.domain === 'buildings' ? 'building'
          : 'transit',
      })
    }, 800)
  }, [])

  const handleClearExternalPopup = useCallback(() => {
    setPendingPopup(null)
  }, [])

  // Sidebar collapse state
  const [leftCollapsed, setLeftCollapsed] = useState(false)
  const [rightCollapsed, setRightCollapsed] = useState(false)

  // Data explorer modals state
  const [openModals, setOpenModals] = useState<Array<{ domain: string; id: string; position: { x: number; y: number } }>>([])

  const handleCloseModal = (id: string) => setOpenModals(prev => prev.filter(m => m.id !== id))

  // Pollutant toggle state for air quality heatmap grid
  const [activePollutant, setActivePollutant] = useState<Pollutant>('pm25')

  // Noise metric toggle state for road noise WMS layer
  const [noiseMetric, setNoiseMetric] = useState<'lden' | 'lnight'>('lden')

  // Demographic metric toggle state for demographics grid layer
  const [demographicMetric, setDemographicMetric] = useState<DemographicMetric>('population')

  // Bus line filter state
  const [busLines, setBusLines] = useState<string[]>([])
  const [hiddenBusLines, setHiddenBusLines] = useState<Set<string>>(new Set())

  const handleToggleBusLine = useCallback((line: string) => {
    setHiddenBusLines(prev => {
      const next = new Set(prev)
      if (next.has(line)) {
        next.delete(line)
      } else {
        next.add(line)
      }
      return next
    })
  }, [])

  // KPI data — used for weather condition on map skybox
  const { data: kpiData } = useKpi(town)

  // Data hooks — pass historicalTimestamp for time slider historical support
  // Each hook fetches only while a layer that consumes its data is switched on.
  // Transit: only stops are needed page-wide (clusters); shapes and bus
  // positions are fetched by their own layer components.
  const transit = useLayerData('transit', town, historicalTimestamp, 'stop', {
    enabled: layerVisibility.transit,
  })
  const airQuality = useLayerData('air_quality', town, historicalTimestamp, undefined, {
    enabled: layerVisibility.airQuality,
  })
  const airQualityGrid = useGridLayerData('air_quality', 'air_grid', town, historicalTimestamp, {
    enabled: layerVisibility.airQuality,
  })
  // Water data feeds the water layer and the Kocher layer.
  const water = useLayerData('water', town, historicalTimestamp, undefined, {
    enabled: layerVisibility.water || layerVisibility.kocher,
  })

  // Default chart data (shown when no activeDomain detail panel open)
  const aqiTs = useTimeseries('air_quality', dateRange.from, dateRange.to, town)

  const handleDomainSelect = (domain: string | null) => {
    if (!domain) return
    // Check if already open
    if (openModals.some(m => m.domain === domain)) return
    // Stagger position so multiple modals don't stack exactly
    const offset = openModals.length * 30
    setOpenModals(prev => [...prev, {
      domain,
      id: `${domain}-${Date.now()}`,
      position: { x: 200 + offset, y: 100 + offset },
    }])
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

  const handleBaseLayerChange = (base: BaseLayer) => {
    update({ base: base === DEFAULT_BASE_LAYER ? null : base })
  }

  // Dashboard panel chart slot: always show default AQI chart with date range picker
  const chartSlot = (
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
        town={town}
        onFeatureSelect={handleFeatureSelect}
        layerVisibility={layerVisibility}
        onToggleLayer={toggleLayer}
        onSetLayers={setLayers}
        transitError={transit.error}
        airQualityError={airQuality.error}
        baseLayer={state.baseLayer}
        onBaseLayerChange={handleBaseLayerChange}
        activePollutant={activePollutant}
        onPollutantChange={setActivePollutant}
        noiseMetric={noiseMetric}
        onNoiseMetricChange={setNoiseMetric}
        demographicMetric={demographicMetric}
        onDemographicMetricChange={setDemographicMetric}
        busLines={busLines}
        hiddenBusLines={hiddenBusLines}
        onToggleBusLine={handleToggleBusLine}
        collapsed={leftCollapsed}
        onToggle={() => setLeftCollapsed(v => !v)}
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
            weatherCondition={kpiData?.weather?.icon ?? null}
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
            solarGlowVisible={layerVisibility.solarGlow}
            roadNoiseVisible={layerVisibility.roadNoise}
            fernwaermeVisible={layerVisibility.fernwaerme}
            demographicsVisible={layerVisibility.demographics}
            heatDemandVisible={layerVisibility.heatDemand}
            cyclingVisible={layerVisibility.cycling}
            policeVisible={layerVisibility.police}
            noiseMetric={noiseMetric}
            demographicMetric={demographicMetric}
            baseLayer={state.baseLayer}
            cadastralVisible={layerVisibility.cadastral}
            hillshadeVisible={layerVisibility.hillshade}
            buildings3dVisible={layerVisibility.buildings3d}
            terrain3dVisible={layerVisibility.terrain3d}
            data3dVisible={layerVisibility.data3d}
            hiddenBusLines={hiddenBusLines}
            onBusLinesDiscovered={setBusLines}
            onMapReady={handleMapReady}
            externalPopup={pendingPopup}
            onExternalPopupClear={handleClearExternalPopup}
          />
        </div>

        {/* Time slider — pinned below map, full map column width */}
        <TimeSlider value={historicalTimestamp} onChange={handleTimeSliderChange} />
      </div>

      {/* Right dashboard panel — 320px, hidden on tablet/mobile (hidden lg:flex inside component) */}
      <DashboardPanel
        town={town}
        onExplore={handleDomainSelect}
        collapsed={rightCollapsed}
        onToggle={() => setRightCollapsed(v => !v)}
      >
        {chartSlot}
      </DashboardPanel>

      {/* Data explorer modals */}
      {openModals.map(modal => (
        <DataExplorerModal
          key={modal.id}
          domain={modal.domain}
          town={town}
          onClose={() => handleCloseModal(modal.id)}
          initialPosition={modal.position}
        />
      ))}
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
