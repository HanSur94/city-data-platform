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

export interface DemographicsKPI {
  population: number | null
  population_year: number | null
  age_under_18_pct: number | null
  age_over_65_pct: number | null
  unemployment_rate: number | null
  last_updated: string | null
}

export interface WaterKPI {
  level_cm: number | null
  flow_m3s: number | null
  stage: number | null
  trend: 'rising' | 'falling' | 'stable' | null
  gauge_name: string | null
  last_updated: string | null
}

export interface ParkingKPI {
  total_free: number | null
  total_capacity: number | null
  garage_count: number
  availability_pct: number | null
  last_updated: string | null
}

export interface KPIResponse {
  town: string
  air_quality: AirQualityKPI
  weather: WeatherKPI
  transit: TransitKPI
  traffic: TrafficKPI | null
  energy: EnergyKPI | null
  demographics: DemographicsKPI | null
  water: WaterKPI | null
  parking: ParkingKPI | null
  attribution: Attribution[]
  last_updated: string | null
}
