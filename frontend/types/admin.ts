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

// Types for /api/admin/monitor endpoint

export interface HypertableStats {
  table_name: string
  row_count: number
  disk_size_bytes: number
  chunk_count: number
  compression_ratio: number | null
  oldest_timestamp: string | null
  newest_timestamp: string | null
  retention_policy: string | null
}

export interface ConnectorHealthInfo {
  connector_class: string
  domain: string
  status: 'green' | 'yellow' | 'red' | 'never_fetched'
  last_successful_fetch: string | null
  poll_interval_seconds: number | null
  validation_error_count: number
}

export interface FeatureDomainCount {
  domain: string
  total_features: number
  with_semantic_id: number
  with_address: number
}

export interface SystemInfo {
  db_ok: boolean
  timescaledb_version: string | null
  postgis_version: string | null
  total_db_size: string
  total_db_size_bytes: number
  server_uptime_seconds: number
}

export interface AdminMonitorResponse {
  town: string
  checked_at: string
  system_info: SystemInfo
  hypertable_stats: HypertableStats[]
  connector_health: ConnectorHealthInfo[]
  feature_registry: FeatureDomainCount[]
}
