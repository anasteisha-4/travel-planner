import { z } from 'zod';

export const UserProfileSchema = z.object({
  id: z.string(),
  email: z.email(),
  login: z.string(),
  yandex_id: z.string().optional(),
  onboarding_completed: z.boolean().optional(),
});

export type UserProfile = z.infer<typeof UserProfileSchema>;
