export interface Attribution {
  source_name: string;
  license: string;
  license_url: string;
  url?: string;
}

export interface LayerResponse {
  '@context': string;
  type: 'FeatureCollection';
  features: GeoJSON.Feature[];
  attribution: Attribution[];
  last_updated: string | null; // ISO datetime string from JSON
  town: string;
  domain: string;
}

export interface AQIFeatureProperties {
  pm25?: number;
  pm10?: number;
  no2?: number;
  o3?: number;
  aqi?: number;
  aqi_tier?: 'good' | 'moderate' | 'poor' | 'bad' | 'very_bad' | 'unknown';
  aqi_color?: string;
  name?: string;
  [key: string]: unknown;
}

export interface TransitFeatureProperties {
  stop_name?: string;
  route_short_name?: string;
  route_type?: number;
  route_type_color?: 'bus' | 'train' | 'tram';
  [key: string]: unknown;
}
