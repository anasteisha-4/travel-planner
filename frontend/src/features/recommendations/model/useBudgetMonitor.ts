import { useQuery } from '@tanstack/react-query';
import { recommendationsApi } from '../api/recommendations.api';
import type { BudgetMonitorRequest } from './types';

export const useBudgetMonitor = (params: BudgetMonitorRequest | null) => {
  return useQuery({
    queryKey: [
      'budget-monitor',
      params?.trip_id ?? null,
      params?.destination_id ?? null,
      params?.start_date,
      params?.end_date,
      params?.as_of_date ?? null,
      params?.people_count,
      params?.currency,
      params?.trip_budget ?? null,
      params?.expenses
        .map(
          (expense) =>
            `${expense.category}:${expense.amount}:${expense.currency}:${expense.expense_date ?? ''}:${expense.description ?? ''}:${expense.is_one_time ? '1' : '0'}`
        )
        .join('|') ?? '',
      params?.pre_trip_prediction?.total_mid ?? null,
      params?.pre_trip_prediction?.total_min ?? null,
      params?.pre_trip_prediction?.total_max ?? null,
      params?.pre_trip_prediction?.breakdown.travel_to_destination ?? null,
    ],
    queryFn: () => recommendationsApi.getBudgetMonitor(params!),
    enabled: params !== null,
    staleTime: 0,
    retry: 1,
  });
};
