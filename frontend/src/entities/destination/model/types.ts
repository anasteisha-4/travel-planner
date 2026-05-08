export type DestinationSearchResult = {
  id: string;
  name: string;
  name_original?: string | null;
  name_ru?: string | null;
  display_name?: string | null;
  country_code: string;
  lat: number;
  lng: number;
};

export type DestinationDetail = DestinationSearchResult & {
  region: string;
  avg_daily_cost_usd: number | null;
  cost_index: number | null;
  safety_score: number | null;
};
