// TypeScript types mirroring KPIResponse from backend/app/schemas/responses.py

export interface Attribution {
  name: string
  url: string
  license?: string
}

export interface AirQualityKPI {
  current_aqi: number | null
  current_pm25: number | null
  current_pm10: number | null
  current_no2: number | null
  current_o3: number | null
  aqi_tier: string | null
  aqi_color: string | null
  last_updated: string | null // ISO 8601 string
}

export interface WeatherKPI {
  temperature: number | null
  condition: string | null
  wind_speed: number | null
  icon: string | null
  last_updated: string | null
}

export interface TransitKPI {
  stop_count: number
  route_count: number
  last_updated: string | null
}

export interface TrafficKPI {
  active_roadworks: number
  flow_status: 'normal' | 'elevated' | 'congested' | null
  last_updated: string | null
}

export interface EnergyKPI {
  renewable_percent: number | null
  generation_mix: Record<string, number>
  wholesale_price_eur_mwh: number | null
  last_updated: string | null
}

export interface KPIResponse {
  town: string
  air_quality: AirQualityKPI
  weather: WeatherKPI
  transit: TransitKPI
  traffic: TrafficKPI | null
  energy: EnergyKPI | null
  attribution: Attribution[]
  last_updated: string | null
}
