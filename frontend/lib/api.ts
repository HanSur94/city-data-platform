import type { LayerResponse } from '@/types/geojson'
import type { KPIResponse } from '@/types/kpi'
import type { TimeseriesResponse } from '@/types/timeseries'
import type { AdminHealthResponse, AdminMonitorResponse } from '@/types/admin'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

// In-flight request sharing: identical GETs issued while one is still pending
// (several hooks/components, React StrictMode double effects) hit the network
// once. This is NOT a cache - the entry is dropped as soon as the request
// settles, so the next poll always reaches the network. The shared value is the
// parsed JSON promise, never a Response (a body can be read only once).
const inFlight = new Map<string, Promise<unknown>>()

function getJsonShared<T>(url: string, errorLabel: string): Promise<T> {
  const pending = inFlight.get(url)
  if (pending) return pending as Promise<T>
  const request = (async () => {
    const res = await fetch(url)
    if (!res.ok) throw new Error(`${errorLabel}: ${res.status}`)
    return (await res.json()) as T
  })().finally(() => {
    inFlight.delete(url)
  })
  inFlight.set(url, request)
  return request
}

export async function fetchLayer(domain: string, town = 'aalen', at?: Date | null, featureType?: string): Promise<LayerResponse> {
  const params = new URLSearchParams({ town })
  if (at) params.set('at', at.toISOString())
  if (featureType) params.set('feature_type', featureType)
  return getJsonShared<LayerResponse>(
    `${API_BASE}/api/layers/${encodeURIComponent(domain)}?${params}`,
    'Layer fetch failed',
  )
}

export async function fetchGridLayer(domain: string, featureType: string, town = 'aalen', at?: Date | null): Promise<LayerResponse> {
  const params = new URLSearchParams({ town, feature_type: featureType })
  if (at) params.set('at', at.toISOString())
  return getJsonShared<LayerResponse>(
    `${API_BASE}/api/layers/${encodeURIComponent(domain)}?${params}`,
    'Grid layer fetch failed',
  )
}

export async function fetchKpi(town: string): Promise<KPIResponse> {
  return getJsonShared<KPIResponse>(
    `${API_BASE}/api/kpi?town=${encodeURIComponent(town)}`,
    'KPI fetch failed',
  )
}

export async function fetchLayerMetadata(
  town: string,
): Promise<Record<string, { last_updated: string | null }>> {
  return getJsonShared<Record<string, { last_updated: string | null }>>(
    `${API_BASE}/api/metadata/layers?town=${encodeURIComponent(town)}`,
    'Layer metadata fetch failed',
  )
}

export async function fetchAdminHealth(town: string): Promise<AdminHealthResponse> {
  const res = await fetch(`${API_BASE}/api/admin/health?town=${encodeURIComponent(town)}`)
  if (!res.ok) throw new Error(`Admin health fetch failed: ${res.status}`)
  return res.json() as Promise<AdminHealthResponse>
}

export async function fetchAdminMonitor(town: string): Promise<AdminMonitorResponse> {
  const res = await fetch(`${API_BASE}/api/admin/monitor?town=${encodeURIComponent(town)}`)
  if (!res.ok) throw new Error(`Admin monitor fetch failed: ${res.status}`)
  return res.json() as Promise<AdminMonitorResponse>
}

export async function fetchTimeseries(
  domain: string,
  town: string,
  start: Date,
  end: Date,
): Promise<TimeseriesResponse> {
  const params = new URLSearchParams({
    town,
    start: start.toISOString(),
    end: end.toISOString(),
  })
  const res = await fetch(`${API_BASE}/api/timeseries/${encodeURIComponent(domain)}?${params}`)
  if (!res.ok) throw new Error(`Timeseries fetch failed: ${res.status}`)
  return res.json() as Promise<TimeseriesResponse>
}
