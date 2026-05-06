import { useQuery } from '@tanstack/react-query';
import { recommendationsApi } from '../api/recommendations.api';
import type { BudgetPredictRequest } from './types';

export const useBudgetPrediction = (params: BudgetPredictRequest | null) => {
  return useQuery({
    queryKey: [
      'budget-prediction',
      params?.destination_id,
      params?.duration_days,
      params?.people_count,
      params?.travel_month,
      params?.accommodation_tier ?? null,
      params?.currency ?? null,
      params?.origin_city_name ?? null,
      params?.origin_lat ?? null,
      params?.origin_lng ?? null,
    ],
    queryFn: () => recommendationsApi.getBudgetPrediction(params!),
    enabled: params !== null,
    staleTime: 10 * 60 * 1000,
    placeholderData: (previousData) => previousData,
    retry: 1,
  });
};
