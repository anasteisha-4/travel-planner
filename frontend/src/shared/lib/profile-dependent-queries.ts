import type { QueryClient } from '@tanstack/react-query';

export const invalidateProfileDependentQueries = (queryClient: QueryClient) => {
  queryClient.invalidateQueries({ queryKey: ['recommendations'], refetchType: 'active' });
  queryClient.invalidateQueries({ queryKey: ['recommendation-destination-score'], refetchType: 'active' });
  queryClient.invalidateQueries({ queryKey: ['budget-prediction'], refetchType: 'active' });
  queryClient.invalidateQueries({ queryKey: ['destination-validation'], refetchType: 'active' });
};
