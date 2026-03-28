import type { ConvertedExpenseSummary } from '@/entities/expense';
import type { PlaceVisit } from '@/entities/place';
import type { Trip } from '@/entities/trip';
import { expenseApi } from '@/entities/expense';
import { placeApi } from '@/entities/place';
import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';

type BudgetTier = 'green' | 'amber' | 'orange' | 'red';

export const useTripAnalytics = (trip: Trip) => {
  const summaryQuery = useQuery<ConvertedExpenseSummary>({
    queryKey: ['expenses-summary', trip.id, trip.currency],
    queryFn: () => expenseApi.getConvertedSummary(trip.id, trip.currency),
  });

  const placesQuery = useQuery<PlaceVisit[]>({
    queryKey: ['places', trip.id],
    queryFn: () => placeApi.getPlaces(trip.id),
  });

  const durationDays = useMemo(() => {
    try {
      const start = new Date(trip.start_date + 'T00:00:00');
      const end = new Date(trip.end_date + 'T00:00:00');
      return Math.max(1, Math.round((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)));
    } catch {
      return 1;
    }
  }, [trip.start_date, trip.end_date]);

  const totalSpent = Number(summaryQuery.data?.total ?? '0');
  const avgPerDay = totalSpent / durationDays;
  const placesVisited = placesQuery.data?.length ?? 0;

  const budget = trip.budget ?? null;
  const budgetPct = budget !== null && budget > 0 ? totalSpent / budget : null;
  const budgetDiff = budget !== null ? budget - totalSpent : null;
  const isOverBudget = budgetPct !== null && budgetPct > 1;
  const budgetTier: BudgetTier | null =
    budgetPct === null
      ? null
      : budgetPct < 0.5
        ? 'green'
        : budgetPct < 0.9
          ? 'amber'
          : budgetPct <= 1.0
            ? 'orange'
            : 'red';

  const categoryBreakdown = useMemo(
    () =>
      Object.entries(summaryQuery.data?.by_category ?? {})
        .map(([category, val]) => ({ category, amount: Number(val) }))
        .filter(({ amount }) => amount > 0)
        .sort((a, b) => b.amount - a.amount),
    [summaryQuery.data?.by_category],
  );

  return {
    loading: summaryQuery.isLoading || placesQuery.isLoading,
    totalSpent,
    avgPerDay,
    durationDays,
    placesVisited,
    currency: trip.currency,
    budget,
    budgetPct,
    budgetDiff,
    budgetTier,
    isOverBudget,
    categoryBreakdown,
    hasConversionErrors: summaryQuery.data?.has_conversion_errors ?? false,
  };
};
