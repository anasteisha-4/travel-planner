import { useQuery } from '@tanstack/react-query';
import { recommendationsApi } from '../api/recommendations.api';
import type { RecommendDestinationRequest } from './types';

export const useDestinationScore = (params: RecommendDestinationRequest | null) => {
  return useQuery({
    queryKey: [
      'recommendation-destination-score',
      params?.destination_id,
      params?.travel_month,
      params?.citizenship_code ?? null,
      params?.model_version ?? null,
    ],
    queryFn: () => recommendationsApi.getDestinationScore(params!),
    enabled: params !== null,
    staleTime: 10 * 60 * 1000,
    retry: 1,
  });
};
