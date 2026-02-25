import { useToast } from '@/shared/ui';
import axios from 'axios';
import { useEffect, useState } from 'react';
import { userApi } from '../api/user.api';
import type { UserProfile } from './types';

export const useProfile = (onUnauthenticated?: () => void) => {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  useEffect(() => {
    const fetchProfile = async () => {
      if (!localStorage.getItem('access_token')) {
        setLoading(false);
        if (onUnauthenticated) onUnauthenticated();
        return;
      }
      try {
        const data = await userApi.getProfile();
        // Return false to let the caller handle redirection based on profile completeness or presence
        if (data.onboarding_completed === false && onUnauthenticated) {
            onUnauthenticated();
            return;
        }
        setProfile(data);
      } catch (err) {
        if (axios.isAxiosError(err) && err.response?.status === 401) {
          if (onUnauthenticated) onUnauthenticated();
          return;
        }
        toast({ variant: 'destructive', title: 'Ошибка', description: 'Не удалось загрузить данные профиля' });
        if (onUnauthenticated) onUnauthenticated();
      } finally {
        setLoading(false);
      }
    };
    fetchProfile();
  }, [toast, onUnauthenticated]);

  return { profile, loading };
};
