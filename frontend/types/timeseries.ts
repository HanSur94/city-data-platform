// TypeScript types mirroring TimeseriesResponse from backend/app/schemas/responses.py

export interface TimeseriesPoint {
  time: string // ISO 8601
  feature_id: string // UUID string
  values: Record<string, number | string | null>
}

export interface TimeseriesResponse {
  domain: string
  town: string
  start: string
  end: string
  count: number
  points: TimeseriesPoint[]
  attribution: Array<{ name: string; url: string; license?: string }>
  last_updated: string | null
}
