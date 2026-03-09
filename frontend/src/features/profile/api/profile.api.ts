import { apiClient } from '@/shared/api';

type PreferencesData = {
  travel_types: string[];
  favorite_destinations: string | null;
  currency: string;
  budget_min: number | null;
  budget_max: number | null;
  trip_duration: string | null;
  departure_city: string | null;
  additional_info: string | null;
};

export const profileApi = {
  getPreferences: async (): Promise<PreferencesData> => {
    const response = await apiClient.get('/api/users/me/preferences');
    return response.data;
  },

  updatePreferences: async (data: PreferencesData): Promise<PreferencesData> => {
    const response = await apiClient.put('/api/users/me/preferences', data);
    return response.data;
  },
};
