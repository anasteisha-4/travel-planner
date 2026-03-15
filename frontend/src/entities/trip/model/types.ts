import { z } from 'zod';

export const TripStatusEnum = z.enum(['planned', 'active', 'completed', 'cancelled']);

export const TripSchema = z.object({
  id: z.string(),
  user_id: z.string(),
  destination: z.string(),
  start_date: z.string(),
  end_date: z.string(),
  budget: z.number().nullable(),
  currency: z.string(),
  people_count: z.number(),
  status: TripStatusEnum,
  departure_city: z.string().nullable().optional(),
  trip_type: z.string().nullable().optional(),
  season: z.string().nullable().optional(),
  notes: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string().nullable(),
});

export type Trip = z.infer<typeof TripSchema>;
export type TripStatus = z.infer<typeof TripStatusEnum>;

export const TripCreateSchema = z.object({
  destination: z.string().min(1),
  start_date: z.string().min(1),
  end_date: z.string().min(1),
  budget: z.number().nullable().optional(),
  currency: z.string().optional(),
  people_count: z.number().min(1).optional(),
  departure_city: z.string().min(1),
  notes: z.string().nullable().optional(),
});

export type TripCreate = z.infer<typeof TripCreateSchema>;

export const TripUpdateSchema = TripCreateSchema.partial().extend({
  status: TripStatusEnum.optional(),
});

export type TripUpdate = z.infer<typeof TripUpdateSchema>;
