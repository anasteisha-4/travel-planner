import type { ConvertedExpenseSummary, Expense } from '@/entities/expense';
import { expenseApi } from '@/entities/expense';
import { useToast } from '@/shared/ui';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect } from 'react';

export const useExpenses = (tripId: string, budgetCurrency: string) => {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const expensesQuery = useQuery<Expense[]>({
    queryKey: ['expenses', tripId],
    queryFn: () => expenseApi.getExpenses(tripId),
    enabled: !!tripId,
  });

  const summaryQuery = useQuery<ConvertedExpenseSummary>({
    queryKey: ['expenses-summary', tripId, budgetCurrency],
    queryFn: () => expenseApi.getConvertedSummary(tripId, budgetCurrency),
    enabled: !!tripId,
  });

  useEffect(() => {
    if (expensesQuery.isError || summaryQuery.isError) {
      toast({ variant: 'destructive', title: 'Ошибка', description: 'Не удалось загрузить расходы' });
    }
  }, [expensesQuery.isError, summaryQuery.isError, toast]);

  const removeMutation = useMutation({
    mutationFn: (expenseId: string) => expenseApi.deleteExpense(expenseId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['expenses', tripId] });
      queryClient.invalidateQueries({ queryKey: ['expenses-summary', tripId] });
    },
    onError: () => {
      toast({ variant: 'destructive', title: 'Ошибка', description: 'Не удалось удалить расход' });
    },
  });

  const refetch = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['expenses', tripId] });
    queryClient.invalidateQueries({ queryKey: ['expenses-summary', tripId] });
  }, [queryClient, tripId]);

  const removeExpense = useCallback(
    async (expenseId: string) => {
      try {
        await removeMutation.mutateAsync(expenseId);
        return true;
      } catch {
        return false;
      }
    },
    [removeMutation],
  );

  return {
    expenses: expensesQuery.data ?? [],
    convertedSummary: summaryQuery.data ?? null,
    loading: expensesQuery.isLoading || summaryQuery.isLoading,
    refetch,
    removeExpense,
  };
};
