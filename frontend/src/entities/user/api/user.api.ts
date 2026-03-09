import { apiClient } from '@/shared/api';
import type { UserProfile } from '../model/types';
import { UserProfileSchema } from '../model/types';

export const userApi = {
  getProfile: async (): Promise<UserProfile> => {
    const response = await apiClient.get('/api/users/me');
    return UserProfileSchema.parse(response.data);
  },
};
