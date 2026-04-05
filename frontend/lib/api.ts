import type { LayerResponse } from '@/types/geojson'
import type { KPIResponse } from '@/types/kpi'
import type { TimeseriesResponse } from '@/types/timeseries'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function fetchLayer(domain: string, town = 'aalen', at?: Date | null): Promise<LayerResponse> {
  const params = new URLSearchParams({ town })
  if (at) params.set('at', at.toISOString())
  const res = await fetch(`${API_BASE}/api/layers/${encodeURIComponent(domain)}?${params}`)
  if (!res.ok) throw new Error(`Layer fetch failed: ${res.status}`)
  return res.json() as Promise<LayerResponse>
}

export async function fetchKpi(town: string): Promise<KPIResponse> {
  const res = await fetch(`${API_BASE}/api/kpi?town=${encodeURIComponent(town)}`)
  if (!res.ok) throw new Error(`KPI fetch failed: ${res.status}`)
  return res.json() as Promise<KPIResponse>
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
