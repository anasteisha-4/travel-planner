import { apiClient } from '@/shared/api';

import type { OnboardingStepData, UserProfileV2 } from '../model/types';

export type DestinationSearchResult = {
  id: string;
  name: string;
  country_code: string;
  lat: number;
  lng: number;
};

export const onboardingV2Api = {
  getProfile: async (): Promise<UserProfileV2> => {
    const response = await apiClient.get('/api/profile/');
    return response.data;
  },

  saveOnboardingStep: async (step: number, data: OnboardingStepData): Promise<UserProfileV2> => {
    const response = await apiClient.post(`/api/profile/onboarding/step/${step}`, data);
    return response.data;
  },

  completeOnboarding: async (): Promise<UserProfileV2> => {
    const response = await apiClient.post('/api/profile/onboarding/complete');
    return response.data;
  },

  searchDestinations: async (query: string, limit = 10): Promise<DestinationSearchResult[]> => {
    const response = await apiClient.get('/api/destinations/search', {
      params: { q: query, limit },
    });
    return response.data;
  },

  fetchDestinationsByIds: async (ids: string[]): Promise<DestinationSearchResult[]> => {
    if (ids.length === 0) return [];
    const response = await apiClient.post('/api/destinations/by-ids', ids);
    return response.data;
  },
};
