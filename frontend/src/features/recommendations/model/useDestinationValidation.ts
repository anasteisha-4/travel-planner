import { useQuery } from '@tanstack/react-query';
import { recommendationsApi } from '../api/recommendations.api';
import type { DestinationValidationRequest } from './types';

export const useDestinationValidation = (params: DestinationValidationRequest | null) => {
  return useQuery({
    queryKey: [
      'destination-validation',
      params?.destination_id,
      params?.citizenship_code ?? null,
      params?.travel_month,
      params?.budget_per_day_usd ?? null,
    ],
    queryFn: () => recommendationsApi.validateDestination(params!),
    enabled: params !== null,
    staleTime: 10 * 60 * 1000,
    placeholderData: (previousData) => previousData,
    retry: 1,
  });
};
