import { useQuery } from '@tanstack/react-query';
import { recommendationsApi } from '../api/recommendations.api';
import type { RecommendationFilters } from './types';

export const useRecommendations = (filters: RecommendationFilters) => {
  const citizenshipCode = filters.citizenship_code ?? 'RU';

  return useQuery({
    queryKey: ['recommendations', filters.month, filters.region ?? null, citizenshipCode],
    queryFn: () =>
      recommendationsApi.getRecommendations({
        travel_month: filters.month,
        region: filters.region ?? null,
        limit: 20,
        citizenship_code: citizenshipCode,
      }),
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });
};
