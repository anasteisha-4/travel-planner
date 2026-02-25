import { apiClient } from './client';

export const authAPI = {
  login: async (credentials: Record<string, unknown>) => {
    const response = await apiClient.post('/api/auth/login', credentials);
    return response.data;
  },
  register: async (userData: Record<string, unknown>) => {
    const response = await apiClient.post('/api/auth/register', userData);
    return response.data;
  },
  logout: async () => {
    const refreshToken = localStorage.getItem('refresh_token');
    if (refreshToken) {
      await apiClient.post('/api/auth/logout', { refresh_token: refreshToken });
    }
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },
  getProfile: async () => {
    const response = await apiClient.get('/api/users/me');
    return response.data;
  },
  updatePreferences: async (preferences: Record<string, unknown>) => {
    const response = await apiClient.put('/api/users/me/preferences', preferences);
    return response.data;
  },
  yandexCallback: async (data: { code: string; redirect_uri: string }) => {
    const response = await apiClient.post('/api/auth/yandex/callback', data);
    return response.data;
  },
  getYandexAuthUrl: (origin: string) => {
    return `${apiClient.defaults.baseURL}/api/auth/yandex/authorize?origin=${encodeURIComponent(origin)}`;
  },
};
