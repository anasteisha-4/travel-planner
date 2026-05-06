export type ItineraryGenerateRequest = {
  destination_id: string;
  duration_days: number;
  start_date: string;
  preferred_activities?: string[];
};

export type ItineraryPlace = {
  id: string;
  name: string;
  name_original?: string | null;
  name_ru?: string | null;
  display_name?: string | null;
  category: string;
  lat: number | null;
  lng: number | null;
  address: string | null;
  opening_hours: string | null;
  is_open_at_midday: boolean | null;
  visit_duration_minutes: number | null;
};

export type ItineraryDay = {
  day: number;
  theme: string;
  places: ItineraryPlace[];
};

export type ItineraryGenerateResponse = {
  destination_id: string;
  duration_days: number;
  days: ItineraryDay[];
  activity_tags: string[];
  source: string;
  has_template: boolean;
  message: string | null;
};
