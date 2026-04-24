import { apiClient } from '@/shared/api';
import { queryClient } from '@/shared/lib/query-client';
import { useMutation } from '@tanstack/react-query';
import { userApi } from '../api/user.api';

export const useDeleteAccount = (onSuccess: () => void, onError: () => void) => {
  const mutation = useMutation({
    mutationFn: async () => {
      await userApi.deleteAccount();
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          await apiClient.post('/api/auth/logout', { refresh_token: refreshToken });
        } catch {
          // cleanup regardless
        }
      }
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      queryClient.clear();
    },
    onSuccess,
    onError,
  });

  return { deleteAccount: mutation.mutate, isLoading: mutation.isPending };
};
