import type { Trip, TripCreate, TripUpdate } from '@/entities/trip';
import { tripApi, TripCreateSchema } from '@/entities/trip';
import type { DestinationSearchResult } from '@/entities/destination';
import { expenseApi } from '@/entities/expense';
import { BUDGET_LIMITS, CURRENCIES } from '@/shared/config';
import { sendEvent } from '@/shared/api';
import { localizeDestinationName } from '@/shared/lib';
import { useToast } from '@/shared/ui';
import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useRef, useState } from 'react';

const getTodayStr = () => new Date().toISOString().slice(0, 10);
const hasCyrillic = (value: string) => /[А-Яа-яЁё]/.test(value);

const getDestinationLabel = (dest: DestinationSearchResult, fallback?: string) => {
  const displayName = dest.display_name ?? dest.name_ru ?? localizeDestinationName(dest.name);
  if (fallback?.trim() && hasCyrillic(fallback) && !hasCyrillic(displayName)) {
    return fallback.trim();
  }
  if (fallback?.trim().toLowerCase() === 'москва' && displayName.toLowerCase() === 'москоу') {
    return fallback.trim();
  }
  return displayName;
};

type SelectedDestination = {
  id: string | null;
  lat: number | null;
  lng: number | null;
};

export type TripFormInitialValues = Partial<
  Pick<
    TripCreate,
    'destination' | 'start_date' | 'end_date' | 'budget' | 'currency' | 'people_count' | 'departure_city' | 'notes'
  >
> & {
  destination_id?: string | null;
  destination_lat?: number | null;
  destination_lng?: number | null;
  departure_destination_id?: string | null;
  departure_lat?: number | null;
  departure_lng?: number | null;
};

export type TripFormSnapshot = {
  destination: string;
  start_date: string;
  end_date: string;
  budget: number;
  currency: string;
  people_count: number;
  departure_city: string;
  notes: string;
  destination_id: string | null;
  destination_lat: number | null;
  destination_lng: number | null;
  departure_destination_id: string | null;
  departure_lat: number | null;
  departure_lng: number | null;
};

export type TripCreateAnalyticsContext = {
  source?: 'manual' | 'recommendation' | 'profile' | string;
  recommendation_id?: string | null;
  model_version?: string | null;
};

export const useTripForm = (
  existingTrip?: Trip,
  initialValues?: TripFormInitialValues,
  onSnapshotChange?: (snapshot: TripFormSnapshot) => void,
  analyticsContext?: TripCreateAnalyticsContext
) => {
  const queryClient = useQueryClient();
  const [destination, setDestination] = useState(
    existingTrip?.destination ?? initialValues?.destination ?? ''
  );
  const [selectedDestination, setSelectedDestination] = useState<SelectedDestination>({
    id: existingTrip?.destination_id ?? initialValues?.destination_id ?? null,
    lat: initialValues?.destination_lat ?? null,
    lng: initialValues?.destination_lng ?? null,
  });
  const [startDate, setStartDate] = useState(existingTrip?.start_date ?? initialValues?.start_date ?? '');
  const [endDate, setEndDate] = useState(existingTrip?.end_date ?? initialValues?.end_date ?? '');
  const [currency, setCurrency] = useState(existingTrip?.currency ?? initialValues?.currency ?? 'RUB');
  const [budget, setBudget] = useState<number>(existingTrip?.budget ?? initialValues?.budget ?? 0);
  const [departureCity, setDepartureCity] = useState(
    existingTrip?.departure_city ?? initialValues?.departure_city ?? ''
  );
  const [selectedDepartureCity, setSelectedDepartureCity] = useState<SelectedDestination>({
    id: initialValues?.departure_destination_id ?? null,
    lat: initialValues?.departure_lat ?? null,
    lng: initialValues?.departure_lng ?? null,
  });
  const [peopleCount, setPeopleCount] = useState(
    existingTrip?.people_count ?? initialValues?.people_count ?? 1
  );
  const [notes, setNotes] = useState(existingTrip?.notes ?? initialValues?.notes ?? '');
  const [isLoading, setIsLoading] = useState(false);
  const [isConverting, setIsConverting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const prevCurrencyRef = useRef(existingTrip?.currency ?? 'RUB');
  const { toast } = useToast();

  const todayStr = useMemo(getTodayStr, []);

  const currencySymbol =
    CURRENCIES.find((c) => c.value === currency)?.label.split(' ')[0] ?? currency;

  useEffect(() => {
    onSnapshotChange?.({
      destination,
      start_date: startDate,
      end_date: endDate,
      budget,
      currency,
      people_count: peopleCount,
      departure_city: departureCity,
      notes,
      destination_id: selectedDestination.id,
      destination_lat: selectedDestination.lat,
      destination_lng: selectedDestination.lng,
      departure_destination_id: selectedDepartureCity.id,
      departure_lat: selectedDepartureCity.lat,
      departure_lng: selectedDepartureCity.lng,
    });
  }, [
    budget,
    currency,
    departureCity,
    destination,
    endDate,
    notes,
    onSnapshotChange,
    peopleCount,
    selectedDepartureCity.id,
    selectedDepartureCity.lat,
    selectedDepartureCity.lng,
    selectedDestination.id,
    selectedDestination.lat,
    selectedDestination.lng,
    startDate,
  ]);

  const handleDestinationInput = (value: string) => {
    setDestination(value);
    setSelectedDestination({ id: null, lat: null, lng: null });
  };

  const handleDestinationSelect = (dest: DestinationSearchResult) => {
    setDestination(getDestinationLabel(dest, destination));
    setSelectedDestination({ id: dest.id, lat: dest.lat, lng: dest.lng });
  };

  const handleDepartureCityInput = (value: string) => {
    setDepartureCity(value);
    setSelectedDepartureCity({ id: null, lat: null, lng: null });
  };

  const handleDepartureCitySelect = (dest: DestinationSearchResult) => {
    setDepartureCity(getDestinationLabel(dest, departureCity));
    setSelectedDepartureCity({ id: dest.id, lat: dest.lat, lng: dest.lng });
  };

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
      destination_id: selectedDestination.id,
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
      sendEvent(
        'trip_created',
        {
          destination: data.destination,
          destination_id: data.destination_id,
          currency: data.currency,
          people_count: data.people_count,
          budget: data.budget,
          departure_city: data.departure_city,
          source: analyticsContext?.source ?? 'manual',
          recommendation_id: analyticsContext?.recommendation_id ?? null,
          model_version: analyticsContext?.model_version ?? null,
        },
        'trip',
        trip.id
      );
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
    handleDestinationInput,
    handleDestinationSelect,
    startDate,
    handleStartDateChange,
    endDate,
    setEndDate,
    departureCity,
    handleDepartureCityInput,
    handleDepartureCitySelect,
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
