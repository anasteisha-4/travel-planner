import type { Trip, TripCreate, TripUpdate } from '@/entities/trip';
import { tripApi, TripCreateSchema } from '@/entities/trip';
import { expenseApi } from '@/entities/expense';
import { BUDGET_LIMITS, CURRENCIES } from '@/shared/config';
import { sendEvent } from '@/shared/api';
import { useToast } from '@/shared/ui';
import { useQueryClient } from '@tanstack/react-query';
import { useMemo, useRef, useState } from 'react';

const getTodayStr = () => new Date().toISOString().slice(0, 10);

export const useTripForm = (existingTrip?: Trip) => {
  const queryClient = useQueryClient();
  const [destination, setDestination] = useState(existingTrip?.destination ?? '');
  const [startDate, setStartDate] = useState(existingTrip?.start_date ?? '');
  const [endDate, setEndDate] = useState(existingTrip?.end_date ?? '');
  const [currency, setCurrency] = useState(existingTrip?.currency ?? 'RUB');
  const [budget, setBudget] = useState<number>(existingTrip?.budget ?? 0);
  const [departureCity, setDepartureCity] = useState(existingTrip?.departure_city ?? '');
  const [peopleCount, setPeopleCount] = useState(existingTrip?.people_count ?? 1);
  const [notes, setNotes] = useState(existingTrip?.notes ?? '');
  const [isLoading, setIsLoading] = useState(false);
  const [isConverting, setIsConverting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const prevCurrencyRef = useRef(existingTrip?.currency ?? 'RUB');
  const { toast } = useToast();

  const todayStr = useMemo(getTodayStr, []);

  const currencySymbol =
    CURRENCIES.find((c) => c.value === currency)?.label.split(' ')[0] ?? currency;

  const handleStartDateChange = (value: string) => {
    setStartDate(value);
    if (endDate && value && endDate < value) {
      setEndDate(value);
    }
  };

  const handleCurrencyChange = async (newCurrency: string) => {
    const prevCurrency = prevCurrencyRef.current;
    setCurrency(newCurrency);
    prevCurrencyRef.current = newCurrency;

    if (budget > 0 && prevCurrency !== newCurrency) {
      setIsConverting(true);
      try {
        const rates = await queryClient.fetchQuery({
          queryKey: ['exchange-rates', prevCurrency],
          queryFn: () => expenseApi.getExchangeRates(prevCurrency),
          staleTime: 60 * 60 * 1000,
        });
        const rate = rates.rates[newCurrency];
        if (rate) {
          const maxForCurrency = BUDGET_LIMITS[newCurrency]?.max ?? BUDGET_LIMITS['USD'].max;
          setBudget(Math.min(Math.round(budget * rate), maxForCurrency));
        }
      } catch {
        // keep original budget on error
      } finally {
        setIsConverting(false);
      }
    }
  };

  const incrementPeople = () => setPeopleCount((p) => Math.min(p + 1, 20));
  const decrementPeople = () => setPeopleCount((p) => Math.max(p - 1, 1));

  const validate = (): TripCreate | null => {
    const fieldErrors: Record<string, string> = {};
    const trimmedDestination = destination.trim();

    if (!departureCity.trim()) {
      fieldErrors.departure_city = 'Укажите город отправления';
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
      destination: trimmedDestination,
      start_date: startDate,
      end_date: endDate,
      budget: budget > 0 ? budget : null,
      currency,
      people_count: peopleCount,
      departure_city: departureCity.trim() || null,
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
      queryClient.invalidateQueries({ queryKey: ['trips'] });
      sendEvent('trip_created', { destination: data.destination, currency: data.currency, people_count: data.people_count }, 'trip', trip.id);
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
      queryClient.invalidateQueries({ queryKey: ['trips'] });
      queryClient.invalidateQueries({ queryKey: ['trip', id] });
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
    destination,
    setDestination,
    startDate,
    handleStartDateChange,
    endDate,
    setEndDate,
    departureCity,
    setDepartureCity,
    budget,
    setBudget,
    currency,
    currencySymbol,
    handleCurrencyChange,
    peopleCount,
    incrementPeople,
    decrementPeople,
    notes,
    setNotes,
    isLoading,
    isConverting,
    errors,
    clearError: (field: string) =>
      setErrors((prev) => {
        const next = { ...prev };
        delete next[field];
        return next;
      }),
    todayStr,
    handleCreate,
    handleUpdate,
  };
};
