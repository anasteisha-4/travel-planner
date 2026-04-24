import { z } from 'zod';

// Trip-service user profile (v2 — ML onboarding)
export type VacationPreference =
  | 'beach' | 'family' | 'culture' | 'active' | 'nightlife'
  | 'shopping' | 'gastro' | 'nature' | 'romantic' | 'business';

export type VisaTolerance = 'visa_free_only' | 'evisa_ok' | 'any_visa';
export type ClimatePref = 'tropical_warm' | 'mediterranean' | 'continental_mild' | 'cold_snow' | 'dry_desert' | 'any';
export type DurationOption = 'weekend' | 'short' | 'standard' | 'long' | 'extended';
export type LanguageOption = 'ru' | 'en' | 'any';

export type UserProfileV2 = {
  id: string;
  user_id: string;
  vacation_preferences_ranked: VacationPreference[] | null;
  preferred_currency: string;
  budget_min: number | null;
  budget_max: number | null;
  budget_min_usd: number | null;
  budget_max_usd: number | null;
  typical_duration: DurationOption | null;
  typical_duration_days: number | null;
  origin_city_id: number | null;
  origin_city_name: string | null;
  origin_lat: number | null;
  origin_lng: number | null;
  liked_destination_ids: string[] | null;
  liked_destination_names: string[] | null;
  risk_tolerance: number | null;
  visa_tolerance: VisaTolerance | null;
  language_comfort: LanguageOption[] | null;
  crowd_preference: number | null;
  climate_preferences: ClimatePref[] | null;
  free_text_notes: string | null;
  onboarding_completed: boolean;
  onboarding_step: number;
  onboarding_completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type OnboardingStepData = Partial<
  Pick<UserProfileV2,
    | 'vacation_preferences_ranked' | 'preferred_currency' | 'budget_min' | 'budget_max'
    | 'typical_duration' | 'origin_city_id' | 'origin_city_name' | 'origin_lat' | 'origin_lng'
    | 'liked_destination_ids' | 'liked_destination_names' | 'risk_tolerance' | 'visa_tolerance' | 'language_comfort'
    | 'crowd_preference' | 'climate_preferences' | 'free_text_notes'
  >
>;

export const UserProfileSchema = z.object({
  id: z.string(),
  email: z.string().email(),
  login: z.string(),
  yandex_id: z.string().nullable().optional(),
  onboarding_completed: z.boolean().optional(),
});

export type UserProfile = z.infer<typeof UserProfileSchema>;
