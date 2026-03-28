import { z } from 'zod';

export const PlaceVisitSchema = z.object({
  id: z.string(),
  trip_id: z.string(),
  user_id: z.string(),
  name: z.string(),
  visited_at: z.string(),
  latitude: z.string(),
  longitude: z.string(),
  notes: z.string().nullable(),
  order: z.number().nullable(),
  created_at: z.string(),
  updated_at: z.string().nullable(),
});

export type PlaceVisit = z.infer<typeof PlaceVisitSchema>;

export const PlaceVisitCreateSchema = z.object({
  name: z.string().min(1),
  visited_at: z.string().min(1),
  latitude: z.string(),
  longitude: z.string(),
  notes: z.string().nullable().optional(),
});

export type PlaceVisitCreate = z.infer<typeof PlaceVisitCreateSchema>;

export const PlaceVisitUpdateSchema = PlaceVisitCreateSchema.partial();

export type PlaceVisitUpdate = z.infer<typeof PlaceVisitUpdateSchema>;

export type PlaceVisitsByDate = {
  date: string;
  places: PlaceVisit[];
};

export const groupPlacesByDate = (places: PlaceVisit[]): PlaceVisitsByDate[] => {
  const map = new Map<string, PlaceVisit[]>();
  for (const place of places) {
    const existing = map.get(place.visited_at) ?? [];
    map.set(place.visited_at, [...existing, place]);
  }
  return Array.from(map.entries()).map(([date, group]) => ({ date, places: group }));
};
