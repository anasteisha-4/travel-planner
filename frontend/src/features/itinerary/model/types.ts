import type { LLMCandidatePOI, LLMQualityReview } from '@/shared/model';

export type ItineraryGenerateRequest = {
  variant_count?: number;
  pace?: 'relaxed' | 'standard' | 'intense';
  day_start_time?: string;
  day_end_time?: string;
  rest_days_count?: number;
  preferred_activities?: string[];
  allow_external_route?: boolean;
};

export type ItineraryRegenerateRequest = ItineraryGenerateRequest & {
  exclude_signature?: string | null;
};

export type ItineraryItemUpdate = {
  day_id?: string;
  arrival_time?: string;
  departure_time?: string;
  duration_minutes?: number;
  order?: number;
  is_pinned?: boolean;
  is_removed?: boolean;
};

export type ItineraryItemSwapRequest = {
  target_item_id: string;
};

export type ItineraryItemMoveRequest = {
  target_day_id: string;
  target_order: number;
};

export type ItineraryManualItemCreate = {
  day_id: string;
  poi_id?: string | null;
  name: string;
  category?: string | null;
  latitude?: string | null;
  longitude?: string | null;
  arrival_time?: string | null;
  departure_time?: string | null;
  duration_minutes: number;
};

export type ItineraryItem = {
  id: string;
  day_id: string;
  poi_id: string | null;
  name: string;
  category: string | null;
  latitude: string | null;
  longitude: string | null;
  arrival_time: string | null;
  departure_time: string | null;
  duration_minutes: number | null;
  travel_from_previous_minutes: number;
  source: 'generated' | 'manual' | 'external_candidate' | string;
  opening_status: 'open' | 'closed' | 'unknown' | string | null;
  price_tier: string | null;
  entrance_fee_usd: number | null;
  relevance_score: number | null;
  order: number;
  is_pinned: boolean;
  is_removed: boolean;
  visited_place_id: string | null;
  quality_review?: LLMQualityReview | null;
  external_candidate_source?: string | null;
  created_at: string;
  updated_at: string | null;
};

export type ItineraryDay = {
  id: string;
  date: string;
  day_number: number;
  theme: string | null;
  start_time: string | null;
  end_time: string | null;
  quality_review?: LLMQualityReview | null;
  items: ItineraryItem[];
};

export type Itinerary = {
  id: string;
  trip_id: string;
  user_id: string;
  status: 'draft' | 'approved' | 'archived' | string;
  variant_index: number;
  generation_seed: number | null;
  model_version: string;
  route_signature: string | null;
  constraints: Record<string, unknown> | null;
  score_summary: Record<string, unknown> | null;
  quality_model_version?: string | null;
  quality_review?: LLMQualityReview | null;
  candidate_poi?: LLMCandidatePOI[];
  days: ItineraryDay[];
  created_at: string;
  updated_at: string | null;
};

export type ItineraryState = {
  approved: Itinerary | null;
  drafts: Itinerary[];
};
