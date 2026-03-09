import { BUDGET_LIMITS } from '@/shared/config';
import { useToast } from '@/shared/ui';
import { useCallback, useEffect, useState } from 'react';
import { profileApi } from '../api/profile.api';

type PreferencesData = {
  travel_types: string[];
  favorite_destinations: string | null;
  currency: string;
  budget_min: number | null;
  budget_max: number | null;
  trip_duration: string | null;
  departure_city: string | null;
  additional_info: string | null;
};

const EMPTY_PREFERENCES: PreferencesData = {
  travel_types: [],
  favorite_destinations: null,
  currency: 'RUB',
  budget_min: null,
  budget_max: null,
  trip_duration: null,
  departure_city: null,
  additional_info: null,
};

const checkHasPreferences = (data: PreferencesData) =>
  data.travel_types.length > 0 ||
  !!data.favorite_destinations ||
  data.budget_min !== null ||
  data.budget_max !== null ||
  !!data.trip_duration ||
  !!data.departure_city ||
  !!data.additional_info;

export const usePreferences = () => {
  const [preferences, setPreferences] = useState<PreferencesData>(EMPTY_PREFERENCES);
  const [isFetching, setIsFetching] = useState(true);
  const { toast } = useToast();

  const refetch = useCallback(async () => {
    setIsFetching(true);
    try {
      const data = await profileApi.getPreferences();
      setPreferences(data);
    } catch {
      toast({
        variant: 'destructive',
        title: 'Ошибка',
        description: 'Не удалось загрузить предпочтения',
      });
    } finally {
      setIsFetching(false);
    }
  }, [toast]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return {
    preferences,
    hasPreferences: checkHasPreferences(preferences),
    isFetching,
    refetch,
  };
};

export const usePreferencesEditor = (initialData: PreferencesData) => {
  const [step, setStep] = useState(1);
  const [travelTypes, setTravelTypes] = useState<string[]>(initialData.travel_types);
  const [destinations, setDestinations] = useState(initialData.favorite_destinations ?? '');
  const [currency, setCurrency] = useState(initialData.currency ?? 'RUB');
  const [budgetRange, setBudgetRange] = useState<[number, number]>(() => {
    if (initialData.budget_min !== null && initialData.budget_max !== null) {
      return [initialData.budget_min, initialData.budget_max];
    }
    const config = BUDGET_LIMITS[initialData.currency ?? 'RUB'] ?? BUDGET_LIMITS.RUB;
    return [config.min, Math.round(config.max * 0.4)];
  });
  const [tripDuration, setTripDuration] = useState<string | null>(initialData.trip_duration);
  const [departureCity, setDepartureCity] = useState(initialData.departure_city ?? '');
  const [additionalInfo, setAdditionalInfo] = useState(initialData.additional_info ?? '');
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();

  const reset = useCallback((data: PreferencesData) => {
    setStep(1);
    setTravelTypes(data.travel_types);
    setDestinations(data.favorite_destinations ?? '');
    setCurrency(data.currency ?? 'RUB');
    setTripDuration(data.trip_duration);
    setDepartureCity(data.departure_city ?? '');
    setAdditionalInfo(data.additional_info ?? '');
    if (data.budget_min !== null && data.budget_max !== null) {
      setBudgetRange([data.budget_min, data.budget_max]);
    } else {
      const config = BUDGET_LIMITS[data.currency ?? 'RUB'] ?? BUDGET_LIMITS.RUB;
      setBudgetRange([config.min, Math.round(config.max * 0.4)]);
    }
  }, []);

  const toggleTravelType = (id: string) => {
    setTravelTypes((prev) => (prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]));
  };

  const handleCurrencyChange = (v: string) => {
    setCurrency(v);
    const config = BUDGET_LIMITS[v] ?? BUDGET_LIMITS.RUB;
    setBudgetRange([config.min, Math.round(config.max * 0.4)]);
  };

  const handleSave = async (): Promise<boolean> => {
    setIsLoading(true);
    try {
      await profileApi.updatePreferences({
        travel_types: travelTypes,
        favorite_destinations: destinations || null,
        currency,
        budget_min: budgetRange[0] || null,
        budget_max: budgetRange[1] || null,
        trip_duration: tripDuration,
        departure_city: departureCity || null,
        additional_info: additionalInfo || null,
      });
      toast({ title: 'Готово', description: 'Предпочтения сохранены' });
      return true;
    } catch {
      toast({
        variant: 'destructive',
        title: 'Ошибка',
        description: 'Не удалось сохранить предпочтения',
      });
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const budgetConfig = BUDGET_LIMITS[currency] ?? BUDGET_LIMITS.RUB;

  return {
    step,
    setStep,
    travelTypes,
    toggleTravelType,
    destinations,
    setDestinations,
    currency,
    handleCurrencyChange,
    budgetRange,
    setBudgetRange,
    tripDuration,
    setTripDuration,
    departureCity,
    setDepartureCity,
    additionalInfo,
    setAdditionalInfo,
    isLoading,
    handleSave,
    budgetConfig,
    reset,
  };
};
