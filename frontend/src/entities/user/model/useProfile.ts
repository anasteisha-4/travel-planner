import { useToast } from '@/shared/ui';
import axios from 'axios';
import { useEffect, useRef, useState } from 'react';
import { userApi } from '../api/user.api';
import type { UserProfile } from './types';

export const useProfile = (onUnauthenticated?: () => void) => {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  const onUnauthenticatedRef = useRef(onUnauthenticated);
  useEffect(() => {
    onUnauthenticatedRef.current = onUnauthenticated;
  }, [onUnauthenticated]);

  useEffect(() => {
    const fetchProfile = async () => {
      if (!localStorage.getItem('access_token')) {
        setLoading(false);
        onUnauthenticatedRef.current?.();
        return;
      }
      try {
        const data = await userApi.getProfile();
        if (data.onboarding_completed === false) {
          onUnauthenticatedRef.current?.();
          return;
        }
        setProfile(data);
      } catch (err) {
        if (axios.isAxiosError(err) && err.response?.status === 401) {
          onUnauthenticatedRef.current?.();
          return;
        }
        toast({
          variant: 'destructive',
          title: 'Ошибка',
          description: 'Не удалось загрузить данные профиля',
        });
        onUnauthenticatedRef.current?.();
      } finally {
        setLoading(false);
      }
    };
    fetchProfile();
  }, [toast]);

  return { profile, loading };
};
