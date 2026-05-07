export type ScoreBreakdown = {
  activity_match?: number;
  budget_fit?: number;
  season_fit?: number;
  visa_effort?: number;
  safety_modulation?: number;
  language_match?: number;
  crowd_fit?: number;
  climate_match?: number;
  origin_proximity?: number;
  liked_similarity?: number;
  liked_dest_similarity?: number;
  connectivity?: number;
  ltr_score?: number;
  ltr_score_raw?: number;
  [key: string]: number | undefined;
};

export type ScoredDestination = {
  destination_id: string;
  name: string;
  name_original?: string | null;
  name_ru?: string | null;
  display_name?: string | null;
  country_code: string;
  region: string;
  score: number;
  score_breakdown: ScoreBreakdown;
  explanation_tags: string[];
  avg_daily_cost_usd: number | null;
  avg_daily_cost?: number | null;
  avg_daily_cost_currency?: string;
  avg_daily_budget_usd?: number | null;
  avg_daily_budget?: number | null;
  avg_daily_budget_currency?: string;
  route_cost_usd?: number | null;
  route_cost_source?: string | null;
  season_score: number | null;
  safety_score: number | null;
};

export type RecommendationsResponse = {
  recommendation_id: string;
  model_version: string;
  results: ScoredDestination[];
};

export type RecommendRequest = {
  travel_month: number;
  limit?: number;
  exclude_destination_ids?: string[];
  region?: string | null;
  citizenship_code?: string;
};

export type BudgetPredictRequest = {
  destination_id: string;
  duration_days: number;
  people_count: number;
  travel_month: number;
  accommodation_tier?: 'hostel' | 'budget' | 'mid' | 'luxury';
  currency?: string;
  budget_limit_usd?: number | null;
  origin_city_name?: string | null;
  origin_lat?: number | null;
  origin_lng?: number | null;
};

export type BudgetAssumptions = {
  duration_days: number;
  people_count: number;
  accommodation_tier: string;
  travel_month: number;
  currency: string;
  origin_city_name: string | null;
  origin_lat: number | null;
  origin_lng: number | null;
  origin_source: 'request' | 'profile' | 'unknown' | string;
  travel_distance_km: number | null;
  travel_cost_source: string;
  origin_iata?: string | null;
  destination_iata?: string | null;
  flight_fare_strategy?: string | null;
  flight_trip_class?: number | null;
  flight_fare_found_at?: string | null;
  flight_fare_expires_at?: string | null;
};

export type BudgetPredictResponse = {
  destination_id: string;
  duration_days: number;
  people_count: number;
  currency: string;
  total_min: number;
  total_mid: number;
  total_max: number;
  daily_cost_usd: number;
  breakdown: Record<string, number>;
  assumptions: BudgetAssumptions;
  model_version: string;
};

export type DestinationValidationStatus = 'suitable' | 'caution' | 'not_recommended';

export type DestinationValidationWarning = {
  type: 'visa' | 'season' | 'budget' | 'safety' | string;
  severity: 'high' | 'medium' | 'low' | string;
  message: string;
};

export type DestinationValidationRequest = {
  destination_id: string;
  citizenship_code?: string;
  travel_month: number;
  budget_per_day_usd?: number | null;
  display_currency?: string | null;
};

export type DestinationValidationResponse = {
  destination_id: string;
  warnings: DestinationValidationWarning[];
  info: Record<string, string | number | boolean | null>;
};

export type RecommendationFilters = {
  month: number;
  region?: string | null;
};
