import { useToast } from '@/shared/ui';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { useEffect, useRef } from 'react';
import { userApi } from '../api/user.api';
import type { UserProfile } from './types';

export const useProfile = (onUnauthenticated?: () => void) => {
  const { toast } = useToast();
  const onUnauthenticatedRef = useRef(onUnauthenticated);
  useEffect(() => {
    onUnauthenticatedRef.current = onUnauthenticated;
  }, [onUnauthenticated]);

  const query = useQuery<UserProfile | null>({
    queryKey: ['auth-profile'],
    queryFn: async () => {
      const data = await userApi.getProfile();
      return data;
    },
    enabled: !!localStorage.getItem('access_token'),
    retry: false,
  });

  useEffect(() => {
    if (!localStorage.getItem('access_token')) onUnauthenticatedRef.current?.();
  }, []);

  useEffect(() => {
    if (query.isSuccess && query.data === null) onUnauthenticatedRef.current?.();
  }, [query.isSuccess, query.data]);

  useEffect(() => {
    if (!query.isError) return;
    if (axios.isAxiosError(query.error) && query.error.response?.status === 401) {
      onUnauthenticatedRef.current?.();
      return;
    }
    toast({ variant: 'destructive', title: 'Ошибка', description: 'Не удалось загрузить данные профиля' });
    onUnauthenticatedRef.current?.();
  }, [query.isError, query.error, toast]);

  return { profile: query.data ?? null, loading: query.isLoading };
};
