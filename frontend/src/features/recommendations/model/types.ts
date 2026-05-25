import type { LLMQualityReview } from '@/shared/model';

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
  quality_review?: LLMQualityReview | null;
};

export type RecommendationsResponse = {
  recommendation_id: string;
  model_version: string;
  quality_model_version?: string | null;
  quality_review?: LLMQualityReview | null;
  results: ScoredDestination[];
};

export type RecommendRequest = {
  travel_month: number;
  limit?: number;
  exclude_destination_ids?: string[];
  region?: string | null;
  citizenship_code?: string;
};

export type RecommendDestinationRequest = {
  destination_id: string;
  travel_month: number;
  citizenship_code?: string;
  model_version?: string | null;
};

export type BudgetPredictRequest = {
  destination_id: string;
  duration_days: number;
  people_count: number;
  travel_month: number;
  accommodation_tier?: 'hostel' | 'budget' | 'mid' | 'comfort' | 'luxury';
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
  daily_recurring_mid: number;
  one_time_costs: number;
  breakdown: Record<string, number>;
  assumptions: BudgetAssumptions;
  model_version: string;
};

export type BudgetMonitorExpense = {
  amount: number;
  currency: string;
  category: string;
  expense_date?: string | null;
  description?: string | null;
  converted_amount?: number | null;
  is_one_time?: boolean;
};

export type BudgetMonitorItinerarySummary = {
  generated_days_count: number;
  remaining_days_count: number;
  remaining_poi_count: number;
  remaining_food_poi_count: number;
  remaining_paid_poi_count: number;
  remaining_estimated_entrance_fees: number;
  remaining_evidence_backed_entrance_fees?: number;
  evidence_backed_price_count?: number;
  candidate_poi_price_count?: number;
  price_estimation_used?: boolean;
  avg_visit_duration_minutes?: number | null;
};

export type BudgetMonitorRequest = {
  trip_id?: string | null;
  destination_id?: string | null;
  start_date: string;
  end_date: string;
  as_of_date?: string | null;
  people_count: number;
  currency: string;
  trip_budget?: number | null;
  accommodation_tier?: string;
  expenses: BudgetMonitorExpense[];
  pre_trip_prediction?: {
    total_min?: number | null;
    total_mid?: number | null;
    total_max?: number | null;
    breakdown: Record<string, number>;
    model_version?: string | null;
  } | null;
  itinerary_summary?: BudgetMonitorItinerarySummary | null;
};

export type BudgetMonitorCategoryContribution = {
  category: string;
  spent: number;
  remaining_mid: number;
  kind: string;
};

export type BudgetMonitorResponse = {
  currency: string;
  current_spent: number;
  planning_spent: number;
  locked_fixed_costs: number;
  recurring_spent: number;
  optional_activity_spent: number;
  remaining_min: number;
  remaining_mid: number;
  remaining_max: number;
  projected_final_min: number;
  projected_final_mid: number;
  projected_final_max: number;
  budget_limit: number | null;
  budget_gap_mid: number | null;
  budget_usage_projected_pct: number | null;
  risk_status: 'forecast_only' | 'under_budget' | 'on_track' | 'risk' | 'over_budget' | string;
  category_contributions: BudgetMonitorCategoryContribution[];
  assumptions: Record<string, unknown>;
  model_version: string;
  baseline_version: string;
  used_ml_model: boolean;
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
  duration_days?: number | null;
  risk_tolerance?: number | null;
  language_code?: string | null;
  preferred_language?: string | null;
};

export type DestinationValidationResponse = {
  destination_id: string;
  warnings: DestinationValidationWarning[];
  info: Record<string, string | number | boolean | null>;
};

export type RecommendationFilters = {
  month: number;
  region?: string | null;
  citizenship_code?: string | null;
};
