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
