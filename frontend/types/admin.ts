// TypeScript types mirroring AdminHealthResponse from backend/app/api/admin_health.py

export interface AdminHealthItem {
  id: string
  domain: string
  connector_class: string
  last_successful_fetch: string | null
  validation_error_count: number
  status: 'green' | 'yellow' | 'red' | 'never_fetched'
  staleness_seconds: number | null
  poll_interval: number | null
  threshold_yellow: number
  threshold_red: number
}

export interface AdminHealthSummary {
  green: number
  yellow: number
  red: number
  never_fetched: number
}

export interface AdminHealthResponse {
  town: string
  town_display_name: string
  checked_at: string
  summary: AdminHealthSummary
  connectors: AdminHealthItem[]
}
