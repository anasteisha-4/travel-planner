import { queryClient } from '@/shared/lib/query-client';
import { apiClient } from '@/shared/api';
import type { AuthCredentials, RegisterCredentials } from '../model/types';
import { AuthResponseSchema } from '../model/types';

export const authApi = {
  login: async (credentials: AuthCredentials) => {
    const response = await apiClient.post('/api/auth/login', credentials);
    return AuthResponseSchema.parse(response.data);
  },
  register: async (userData: RegisterCredentials) => {
    const response = await apiClient.post('/api/auth/register', userData);
    return AuthResponseSchema.parse(response.data);
  },
  logout: async () => {
    const refreshToken = localStorage.getItem('refresh_token');
    if (refreshToken) {
      await apiClient.post('/api/auth/logout', { refresh_token: refreshToken });
    }
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    queryClient.clear();
  },
  yandexCallback: async (data: { code: string; redirect_uri: string }) => {
    const response = await apiClient.post('/api/auth/yandex/callback', data);
    return AuthResponseSchema.parse(response.data);
  },
  getYandexAuthUrl: (origin: string) => {
    return `${apiClient.defaults.baseURL}/api/auth/yandex/authorize?origin=${encodeURIComponent(origin)}`;
  },
  forgotPassword: async (email: string) => {
    const response = await apiClient.post('/api/auth/password/forgot', { email });
    return response.data as { message: string };
  },
  resetPassword: async (data: {
    token: string;
    new_password: string;
    confirm_password: string;
  }) => {
    const response = await apiClient.post('/api/auth/password/reset', data);
    return response.data as { message: string };
  },
};
