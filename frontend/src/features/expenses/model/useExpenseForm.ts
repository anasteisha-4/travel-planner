import type { Expense, ExpenseCategory } from '@/entities/expense';
import { expenseApi, ExpenseCreateSchema } from '@/entities/expense';
import { useToast } from '@/shared/ui';
import { useEffect, useState } from 'react';

export const useExpenseForm = (tripId: string, existingExpense?: Expense) => {
  const [amount, setAmount] = useState(
    existingExpense?.amount ? String(existingExpense.amount) : ''
  );
  const [currency, setCurrency] = useState(existingExpense?.currency ?? 'EUR');
  const [category, setCategory] = useState<ExpenseCategory>(existingExpense?.category ?? 'food');
  const [description, setDescription] = useState(existingExpense?.description ?? '');
  const [expenseDate, setExpenseDate] = useState(
    existingExpense?.expense_date ?? new Date().toISOString().slice(0, 10)
  );

  useEffect(() => {
    if (existingExpense) {
      setAmount(String(existingExpense.amount));
      setCurrency(existingExpense.currency);
      setCategory(existingExpense.category);
      setDescription(existingExpense.description ?? '');
      setExpenseDate(existingExpense.expense_date ?? new Date().toISOString().slice(0, 10));
    }
  }, [existingExpense]);
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const { toast } = useToast();

  const validate = () => {
    const fieldErrors: Record<string, string> = {};
    if (!amount || Number(amount) <= 0) {
      fieldErrors.amount = 'Введите сумму';
    }
    if (!currency) {
      fieldErrors.currency = 'Выберите валюту';
    }
    if (Object.keys(fieldErrors).length > 0) {
      setErrors(fieldErrors);
      return null;
    }
    const raw = {
      amount: String(amount),
      currency,
      category,
      description: description.trim() || null,
      expense_date: expenseDate || null,
    };
    const result = ExpenseCreateSchema.safeParse(raw);
    if (!result.success) {
      for (const issue of result.error.issues) {
        const field = issue.path[0]?.toString() ?? '';
        if (!fieldErrors[field]) {
          fieldErrors[field] = issue.message;
        }
      }
      setErrors(fieldErrors);
      return null;
    }
    setErrors({});
    return result.data;
  };

  const handleCreate = async (): Promise<Expense | null> => {
    const data = validate();
    if (!data) return null;
    setIsLoading(true);
    try {
      const expense = await expenseApi.createExpense(tripId, data);
      toast({ title: 'Готово', description: 'Расход добавлен' });
      return expense;
    } catch {
      toast({ variant: 'destructive', title: 'Ошибка', description: 'Не удалось добавить расход' });
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdate = async (expenseId: string): Promise<Expense | null> => {
    const data = validate();
    if (!data) return null;
    setIsLoading(true);
    try {
      const expense = await expenseApi.updateExpense(expenseId, data);
      toast({ title: 'Готово', description: 'Расход обновлён' });
      return expense;
    } catch {
      toast({ variant: 'destructive', title: 'Ошибка', description: 'Не удалось обновить расход' });
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  const reset = () => {
    setAmount('');
    setCurrency('EUR');
    setCategory('food');
    setDescription('');
    setExpenseDate(new Date().toISOString().slice(0, 10));
    setErrors({});
  };

  return {
    amount,
    setAmount,
    currency,
    setCurrency,
    category,
    setCategory,
    description,
    setDescription,
    expenseDate,
    setExpenseDate,
    isLoading,
    errors,
    handleCreate,
    handleUpdate,
    reset,
  };
};
