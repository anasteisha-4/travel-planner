import { z } from 'zod';

export const UserPreferencesSchema = z.object({
  travel_types: z.array(z.string()).default([]),
  favorite_destinations: z.string().nullable().optional(),
  currency: z.string().default('RUB'),
  budget_min: z.number().nullable().optional(),
  budget_max: z.number().nullable().optional(),
  trip_duration: z.string().nullable().optional(),
  departure_city: z.string().nullable().optional(),
  additional_info: z.string().nullable().optional(),
});

export type UserPreferences = z.infer<typeof UserPreferencesSchema>;

export const UserProfileSchema = z.object({
  id: z.string(),
  email: z.string().email(),
  login: z.string(),
  yandex_id: z.string().nullable().optional(),
  onboarding_completed: z.boolean().optional(),
  preferences: UserPreferencesSchema.nullable().optional(),
});

export type UserProfile = z.infer<typeof UserProfileSchema>;
