import { apiClient } from '@/shared/api';

export const onboardingApi = {
  updatePreferences: async (preferences: Record<string, unknown>) => {
    const response = await apiClient.put('/api/users/me/preferences', preferences);
    return response.data;
  },
};
