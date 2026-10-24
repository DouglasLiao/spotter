export type RiskLevel = 'Low' | 'Moderate' | 'High' | 'Severe' | 'No Travel' | 'Unknown'

export interface LocationGeo {
  name?: string
  address?: string
  formatted_address?: string
  lat: number
  lon: number
}

export interface WeatherData {
  wind_mph?: number | null
  wind_speed_mph?: number
  rain_in_hr?: number | null
  rain_in_per_hr?: number
  snow_in_hr?: number | null
  snow_in_per_hr?: number
  available?: boolean
  unavailable_reason?: string | null
  forecast_time?: string | null
}

export interface CheckpointRisk {
  level?: RiskLevel
  overall_risk_label?: RiskLevel
  score?: number
  overall_risk_level?: number | null
  reasons?: string[]
  load_reason?: string
  load_penalty_applied: boolean
}

export type HeatmapMetric = 'none' | 'risk' | 'wind' | 'precip'

export interface HourlyForecastItem {
  available: boolean
  unavailable_reason?: string | null
  forecast_time?: string | null
  hour: number
  time: string
  wind_mph: number | null
  rain_in_hr: number | null
  snow_in_hr: number | null
  risk_level?: number | null
  risk_label?: RiskLevel
  load_penalty_applied?: boolean
}

export interface Checkpoint {
  index: number
  lat: number
  lon: number
  distance_from_start_miles?: number
  distance_from_origin_miles?: number
  segment_miles?: number
  eta?: string
  eta_iso?: string
  weather: WeatherData
  risk: CheckpointRisk
  hourly_forecast?: HourlyForecastItem[]
}

export interface RouteRiskSummary {
  severe_miles: number
  high_miles: number
  moderate_miles: number
  low_miles: number
  no_travel_miles: number
  weather_complete?: boolean
  unknown_miles?: number
  average_risk_score?: number | null
  weighted_risk_score?: number
  average_risk_label?: string
  max_risk_level?: RiskLevel
  highest_risk_level?: RiskLevel
}

export interface RouteOption {
  id: string | number
  name: string
  summary?: string
  distance_meters?: number
  distance_miles: number
  duration_seconds: number
  duration_hours?: number
  duration_formatted?: string
  coordinates: [number, number][]
  is_recommended: boolean
  recommendation_reason: string
  risk_summary: RouteRiskSummary
  checkpoints: Checkpoint[]
}

export interface RoutePlanRequest {
  origin: string
  destination: string
  departure_time?: string
  load_weight: number
  sample_interval_miles?: number
}

export interface RoutePlanResponse {
  origin: LocationGeo
  destination: LocationGeo
  departure_time: string
  load_weight: number
  sample_interval_miles: number
  recommended_route_id: string | number | null
  warnings: string[]
  corridor: WeatherCorridor
  routes: RouteOption[]
}

export interface ApiErrorResponse {
  error?: string
  origin?: string[]
  destination?: string[]
  load_weight?: string[]
  sample_interval_miles?: string[]
  departure_time?: string[]
}

export interface WeatherCorridor {
  half_width_miles: number
  grid_spacing_miles: number
  max_points?: number
  points: { lat: number; lon: number; hourly_forecast: HourlyForecastItem[] }[]
}
