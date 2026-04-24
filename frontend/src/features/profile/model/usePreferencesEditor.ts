import { useToast } from '@/shared/ui';
import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import type { UserProfileV2 } from '@/entities/user';
import { profileApi } from '../api/profile.api';

const KNOWN_VACATION_PREFS = new Set([
  'beach', 'family', 'culture', 'active', 'nightlife',
  'shopping', 'gastro', 'nature', 'romantic', 'business',
]);

const checkHasProfile = (data: Partial<UserProfileV2>) =>
  data.onboarding_completed === true ||
  (data.vacation_preferences_ranked ?? []).some((id) => KNOWN_VACATION_PREFS.has(id)) ||
  (data.budget_min !== null && data.budget_min !== undefined) ||
  (data.budget_max !== null && data.budget_max !== undefined) ||
  !!data.typical_duration ||
  !!data.origin_city_name ||
  !!data.risk_tolerance ||
  !!data.visa_tolerance ||
  !!data.crowd_preference ||
  (data.language_comfort ?? []).length > 0 ||
  (data.climate_preferences ?? []).length > 0 ||
  !!data.free_text_notes ||
  (data.liked_destination_ids ?? []).length > 0;

export const usePreferences = () => {
  const { toast } = useToast();

  const query = useQuery<UserProfileV2>({
    queryKey: ['profile'],
    queryFn: () => profileApi.getProfile(),
  });

  useEffect(() => {
    if (query.isError) {
      toast({ variant: 'destructive', title: 'Ошибка', description: 'Не удалось загрузить профиль' });
    }
  }, [query.isError, toast]);

  const profile = query.data ?? null;

  return {
    profile,
    hasPreferences: profile ? checkHasProfile(profile) : false,
    isFetching: query.isLoading,
    refetch: query.refetch,
  };
};
