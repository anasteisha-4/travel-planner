import type { ConvertedExpenseSummary, Expense } from '@/entities/expense';
import { expenseApi } from '@/entities/expense';
import { useToast } from '@/shared/ui';
import { useCallback, useEffect, useState } from 'react';

export const useExpenses = (tripId: string, budgetCurrency: string) => {
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [convertedSummary, setConvertedSummary] = useState<ConvertedExpenseSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  const fetchAll = useCallback(async () => {
    if (!tripId) return;
    setLoading(true);
    try {
      const [expensesData, summaryData] = await Promise.all([
        expenseApi.getExpenses(tripId),
        expenseApi.getConvertedSummary(tripId, budgetCurrency),
      ]);
      setExpenses(expensesData);
      setConvertedSummary(summaryData);
    } catch {
      toast({
        variant: 'destructive',
        title: 'Ошибка',
        description: 'Не удалось загрузить расходы',
      });
    } finally {
      setLoading(false);
    }
  }, [tripId, budgetCurrency, toast]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const removeExpense = async (expenseId: string) => {
    try {
      await expenseApi.deleteExpense(expenseId);
      await fetchAll();
    } catch {
      toast({
        variant: 'destructive',
        title: 'Ошибка',
        description: 'Не удалось удалить расход',
      });
    }
  };

  return { expenses, convertedSummary, loading, refetch: fetchAll, removeExpense };
};
