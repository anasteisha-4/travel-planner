import type { ConvertedExpenseSummary } from '@/entities/expense';
import type { PlaceVisit } from '@/entities/place';
import type { Trip } from '@/entities/trip';
import { expenseApi } from '@/entities/expense';
import { placeApi } from '@/entities/place';
import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';

type BudgetTier = 'green' | 'amber' | 'orange' | 'red';
export type BudgetMonitoringStatus = 'under_budget' | 'on_track' | 'risk' | 'over_budget';

const DAY_MS = 1000 * 60 * 60 * 24;

const parseTripDate = (date: string) => new Date(date + 'T00:00:00');

const diffDaysInclusive = (start: Date, end: Date) =>
  Math.max(1, Math.floor((end.getTime() - start.getTime()) / DAY_MS) + 1);

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
      const start = parseTripDate(trip.start_date);
      const end = parseTripDate(trip.end_date);
      return diffDaysInclusive(start, end);
    } catch {
      return 1;
    }
  }, [trip.start_date, trip.end_date]);

  const tripProgress = useMemo(() => {
    try {
      const start = parseTripDate(trip.start_date);
      const end = parseTripDate(trip.end_date);
      const today = new Date();
      const todayAtMidnight = new Date(today.getFullYear(), today.getMonth(), today.getDate());
      const activeEnd = todayAtMidnight < start ? start : todayAtMidnight > end ? end : todayAtMidnight;
      const elapsedDays = diffDaysInclusive(start, activeEnd);
      const remainingDays = Math.max(0, durationDays - elapsedDays);

      return { elapsedDays, remainingDays };
    } catch {
      return { elapsedDays: 1, remainingDays: 0 };
    }
  }, [durationDays, trip.end_date, trip.start_date]);

  const totalSpent = Number(summaryQuery.data?.total ?? '0');
  const avgPerDay = totalSpent / durationDays;
  const burnRatePerDay = totalSpent / tripProgress.elapsedDays;
  const projectedFinalSpend = burnRatePerDay * durationDays;
  const placesVisited = placesQuery.data?.length ?? 0;

  const budget = trip.budget ?? null;
  const budgetPct = budget !== null && budget > 0 ? totalSpent / budget : null;
  const budgetDiff = budget !== null ? budget - totalSpent : null;
  const projectedBudgetPct = budget !== null && budget > 0 ? projectedFinalSpend / budget : null;
  const projectedBudgetDiff = budget !== null ? budget - projectedFinalSpend : null;
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
  const budgetMonitoringStatus: BudgetMonitoringStatus | null =
    projectedBudgetPct === null
      ? null
      : budgetPct !== null && budgetPct > 1
        ? 'over_budget'
        : projectedBudgetPct > 1.05
          ? 'risk'
          : projectedBudgetPct >= 0.85
            ? 'on_track'
            : 'under_budget';

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
    burnRatePerDay,
    projectedFinalSpend,
    elapsedDays: tripProgress.elapsedDays,
    remainingDays: tripProgress.remainingDays,
    durationDays,
    placesVisited,
    currency: trip.currency,
    budget,
    budgetPct,
    budgetDiff,
    projectedBudgetPct,
    projectedBudgetDiff,
    budgetMonitoringStatus,
    budgetTier,
    isOverBudget,
    categoryBreakdown,
    hasConversionErrors: summaryQuery.data?.has_conversion_errors ?? false,
  };
};
