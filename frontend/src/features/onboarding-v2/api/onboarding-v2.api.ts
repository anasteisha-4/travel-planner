import { destinationApi, type DestinationSearchResult } from '@/entities/destination';
import { apiClient } from '@/shared/api';

import type { OnboardingStepData, UserProfileV2 } from '../model/types';

export type { DestinationSearchResult };

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

  searchDestinations: destinationApi.searchDestinations,

  fetchDestinationsByIds: destinationApi.fetchDestinationsByIds,
};
