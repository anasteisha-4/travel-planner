import type { Trip, TripCreate, TripUpdate } from '@/entities/trip';
import { tripApi, TripCreateSchema } from '@/entities/trip';
import { BUDGET_LIMITS } from '@/shared/config';
import { useToast } from '@/shared/ui';
import { useMemo, useState } from 'react';

const getTodayStr = () => new Date().toISOString().slice(0, 10);

export const useTripForm = (existingTrip?: Trip) => {
  const [title, setTitle] = useState(existingTrip?.title ?? '');
  const [destination, setDestination] = useState(existingTrip?.destination ?? '');
  const [startDate, setStartDate] = useState(existingTrip?.start_date ?? '');
  const [endDate, setEndDate] = useState(existingTrip?.end_date ?? '');
  const [currency, setCurrency] = useState(existingTrip?.currency ?? 'RUB');
  const [budget, setBudget] = useState<[number, number]>(() => {
    const config = BUDGET_LIMITS[existingTrip?.currency ?? 'RUB'] ?? BUDGET_LIMITS.RUB;
    if (existingTrip?.budget != null) {
      return [config.min, existingTrip.budget];
    }
    return [config.min, Math.round(config.max * 0.3)];
  });
  const [peopleCount, setPeopleCount] = useState(existingTrip?.people_count ?? 1);
  const [notes, setNotes] = useState(existingTrip?.notes ?? '');
  const [showNotes, setShowNotes] = useState(!!existingTrip?.notes);
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const { toast } = useToast();

  const todayStr = useMemo(getTodayStr, []);

  const budgetConfig = BUDGET_LIMITS[currency] ?? BUDGET_LIMITS.RUB;

  const handleStartDateChange = (value: string) => {
    setStartDate(value);
    if (endDate && value && endDate < value) {
      setEndDate(value);
    }
  };

  const handleCurrencyChange = (value: string) => {
    setCurrency(value);
    const config = BUDGET_LIMITS[value] ?? BUDGET_LIMITS.RUB;
    setBudget([config.min, Math.round(config.max * 0.3)]);
  };

  const incrementPeople = () => setPeopleCount((p) => Math.min(p + 1, 20));
  const decrementPeople = () => setPeopleCount((p) => Math.max(p - 1, 1));

  const validate = (): TripCreate | null => {
    const fieldErrors: Record<string, string> = {};
    const trimmedTitle = title.trim();
    const trimmedDestination = destination.trim();

    if (!trimmedTitle) {
      fieldErrors.title = 'Введите название поездки';
    }
    if (!trimmedDestination) {
      fieldErrors.destination = 'Укажите направление';
    }
    if (!startDate) {
      fieldErrors.start_date = 'Выберите дату начала';
    } else if (startDate < todayStr) {
      fieldErrors.start_date = 'Дата начала уже прошла';
    }
    if (!endDate) {
      fieldErrors.end_date = 'Выберите дату окончания';
    } else if (startDate && endDate < startDate) {
      fieldErrors.end_date = 'Дата окончания не может быть раньше начала';
    }

    if (Object.keys(fieldErrors).length > 0) {
      setErrors(fieldErrors);
      return null;
    }

    const raw = {
      title: trimmedTitle,
      destination: trimmedDestination,
      start_date: startDate,
      end_date: endDate,
      budget: budget[1] > 0 ? budget[1] : null,
      currency,
      people_count: peopleCount,
      notes: notes.trim() || null,
    };

    const result = TripCreateSchema.safeParse(raw);
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

  const handleCreate = async (): Promise<Trip | null> => {
    const data = validate();
    if (!data) return null;

    setIsLoading(true);
    try {
      const trip = await tripApi.createTrip(data);
      toast({ title: 'Готово', description: 'Поездка создана' });
      return trip;
    } catch {
      toast({ variant: 'destructive', title: 'Ошибка', description: 'Не удалось создать поездку' });
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdate = async (id: string): Promise<Trip | null> => {
    const data = validate();
    if (!data) return null;

    const updateData: TripUpdate = { ...data };

    setIsLoading(true);
    try {
      const trip = await tripApi.updateTrip(id, updateData);
      toast({ title: 'Готово', description: 'Поездка обновлена' });
      return trip;
    } catch {
      toast({
        variant: 'destructive',
        title: 'Ошибка',
        description: 'Не удалось обновить поездку',
      });
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  return {
    title,
    setTitle,
    destination,
    setDestination,
    startDate,
    handleStartDateChange,
    endDate,
    setEndDate,
    budget,
    setBudget,
    currency,
    handleCurrencyChange,
    peopleCount,
    incrementPeople,
    decrementPeople,
    notes,
    setNotes,
    showNotes,
    setShowNotes,
    isLoading,
    errors,
    todayStr,
    budgetConfig,
    handleCreate,
    handleUpdate,
  };
};
