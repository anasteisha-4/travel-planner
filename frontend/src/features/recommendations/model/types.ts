export type ScoreBreakdown = {
  activity_match: number;
  budget_fit: number;
  season: number;
  safety: number;
  visa: number;
  language: number;
  crowd: number;
  climate: number;
  connectivity: number;
  [key: string]: number;
};

export type ScoredDestination = {
  destination_id: string;
  name: string;
  country_code: string;
  region: string;
  score: number;
  score_breakdown: ScoreBreakdown;
  explanation_tags: string[];
  avg_daily_cost_usd: number | null;
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
  accommodation_tier?: 'budget' | 'mid' | 'luxury';
  currency?: string;
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
  model_version: string;
};

export type RecommendationFilters = {
  month: number;
  region?: string | null;
};
