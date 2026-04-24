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
    ],
    queryFn: () => recommendationsApi.getBudgetPrediction(params!),
    enabled: params !== null,
    staleTime: 10 * 60 * 1000,
    retry: 1,
  });
};
