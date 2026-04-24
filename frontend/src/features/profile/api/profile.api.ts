import { apiClient } from '@/shared/api';
import type { UserProfileV2 } from '@/entities/user';

export const profileApi = {
  getProfile: async (): Promise<UserProfileV2> => {
    const response = await apiClient.get('/api/profile/');
    return response.data;
  },

  updateProfile: async (data: Partial<UserProfileV2>): Promise<UserProfileV2> => {
    const response = await apiClient.put('/api/profile/', data);
    return response.data;
  },

  patchProfile: async (data: Partial<UserProfileV2>): Promise<UserProfileV2> => {
    const response = await apiClient.patch('/api/profile/', data);
    return response.data;
  },
};
