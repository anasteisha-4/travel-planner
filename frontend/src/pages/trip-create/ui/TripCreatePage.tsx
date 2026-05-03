import type { Trip } from '@/entities/trip';
import { expenseApi } from '@/entities/expense';
import { profileApi } from '@/features/profile';
import { DestinationValidationCompact, useBudgetPrediction } from '@/features/recommendations';
import { TripForm, type TripFormInitialValues, type TripFormSnapshot } from '@/features/trips';
import { AppPageHeader, PageContent, PageLayout } from '@/shared/ui';
import { useQuery } from '@tanstack/react-query';
import { ChevronLeft } from 'lucide-react';
import { useCallback, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

const getParamNumber = (value: string | null): number | undefined => {
  if (!value) return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : undefined;
};

const getDurationDays = (startDate?: string, endDate?: string) => {
  if (!startDate || !endDate) return undefined;
  const start = new Date(`${startDate}T00:00:00`);
  const end = new Date(`${endDate}T00:00:00`);
  const diffMs = end.getTime() - start.getTime();
  if (!Number.isFinite(diffMs) || diffMs < 0) return undefined;
  return Math.floor(diffMs / 86_400_000) + 1;
};

const getTravelMonth = (startDate?: string) => {
  if (!startDate) return new Date().getMonth() + 1;
  const parsed = new Date(`${startDate}T00:00:00`);
  return Number.isFinite(parsed.getTime()) ? parsed.getMonth() + 1 : new Date().getMonth() + 1;
};

const getAccommodationTier = (value: string | null): 'budget' | 'mid' | 'luxury' => {
  if (value === 'budget' || value === 'luxury') return value;
  return 'mid';
};

const normalizeCity = (value?: string | null) => value?.trim().toLowerCase() ?? '';

const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: '$',
  EUR: '€',
  RUB: '₽',
  GBP: '£',
  TRY: '₺',
  THB: '฿',
  AED: 'AED',
  KZT: '₸',
  GEL: '₾',
  AMD: '֏',
  JPY: '¥',
  CNY: '¥',
};

export const TripCreatePage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const hasRecommendationPrefill = searchParams.has('destination');
  const { data: profile, isLoading: isProfileLoading } = useQuery({
    queryKey: ['profile'],
    queryFn: profileApi.getProfile,
    enabled: hasRecommendationPrefill,
    retry: 1,
  });

  const initialValues = useMemo<TripFormInitialValues>(() => {
    const budget = getParamNumber(searchParams.get('budget'));
    const peopleCount = getParamNumber(searchParams.get('people_count'));

    return {
      destination: searchParams.get('destination') ?? undefined,
      start_date: searchParams.get('start_date') ?? undefined,
      end_date: searchParams.get('end_date') ?? undefined,
      budget: budget ?? null,
      currency: searchParams.get('currency') ?? profile?.preferred_currency ?? undefined,
      people_count: peopleCount,
      departure_city: searchParams.get('departure_city') ?? profile?.origin_city_name ?? undefined,
      destination_id: searchParams.get('destination_id'),
    };
  }, [profile?.origin_city_name, profile?.preferred_currency, searchParams]);

  const [formSnapshot, setFormSnapshot] = useState<TripFormSnapshot | null>(null);
  const handleFormSnapshotChange = useCallback((snapshot: TripFormSnapshot) => {
    setFormSnapshot(snapshot);
  }, []);

  const initialDestinationId = searchParams.get('destination_id');
  const previewDestination = formSnapshot?.destination ?? initialValues.destination;
  const isInitialDestination = normalizeCity(previewDestination) === normalizeCity(initialValues.destination);
  const destinationId = formSnapshot
    ? formSnapshot.destination_id ?? (isInitialDestination ? initialDestinationId : null)
    : initialDestinationId;
  const previewStartDate = formSnapshot?.start_date ?? initialValues.start_date;
  const previewEndDate = formSnapshot?.end_date ?? initialValues.end_date;
  const previewDepartureCity = formSnapshot?.departure_city ?? initialValues.departure_city ?? profile?.origin_city_name;
  const isProfileOrigin = normalizeCity(previewDepartureCity) === normalizeCity(profile?.origin_city_name);
  const selectedOriginLat = formSnapshot?.departure_lat ?? null;
  const selectedOriginLng = formSnapshot?.departure_lng ?? null;
  const budgetDurationDays = getDurationDays(previewStartDate, previewEndDate) ?? profile?.typical_duration_days ?? 7;
  const budgetPeopleCount = formSnapshot?.people_count ?? initialValues.people_count ?? 1;
  const budgetCurrency = formSnapshot?.currency ?? initialValues.currency ?? profile?.preferred_currency ?? 'RUB';
  const budgetValue = formSnapshot?.budget ?? initialValues.budget ?? 0;
  const budgetAccommodationTier = getAccommodationTier(searchParams.get('accommodation_tier'));
  const needsUsdRate = budgetValue > 0 && budgetCurrency !== 'USD';
  const { data: validationRates } = useQuery({
    queryKey: ['exchange-rates', budgetCurrency],
    queryFn: () => expenseApi.getExchangeRates(budgetCurrency),
    enabled: needsUsdRate,
    staleTime: 60 * 60 * 1000,
    retry: 1,
  });
  const validationBudgetUsd = budgetValue > 0
    ? budgetCurrency === 'USD'
      ? budgetValue
      : validationRates?.rates.USD
        ? budgetValue * validationRates.rates.USD
        : null
    : null;
  const validationBudgetPerDayUsd = validationBudgetUsd !== null
    ? validationBudgetUsd / Math.max(budgetDurationDays * budgetPeopleCount, 1)
    : null;
  const { data: budgetPrediction } = useBudgetPrediction(
    destinationId
      ? {
          destination_id: destinationId,
          duration_days: budgetDurationDays,
          people_count: budgetPeopleCount,
          travel_month: getTravelMonth(previewStartDate),
          accommodation_tier: budgetAccommodationTier,
          currency: budgetCurrency,
          origin_city_name: previewDepartureCity,
          origin_lat: selectedOriginLat ?? (isProfileOrigin ? profile?.origin_lat : null),
          origin_lng: selectedOriginLng ?? (isProfileOrigin ? profile?.origin_lng : null),
        }
      : null
  );
  const budgetAssumptions = budgetPrediction?.assumptions;
  const hasBudgetTravelFareData = budgetAssumptions?.travel_cost_source?.startsWith('travelpayouts') ?? false;
  const budgetTravelCost = budgetPrediction?.breakdown.travel_to_destination ?? 0;
  const budgetDisplayTotalMid = budgetPrediction
    ? Math.max(0, budgetPrediction.total_mid - (hasBudgetTravelFareData ? 0 : budgetTravelCost))
    : 0;
  const budgetDisplayTotalMin = budgetPrediction
    ? Math.max(0, budgetPrediction.total_min - (hasBudgetTravelFareData ? 0 : budgetTravelCost))
    : 0;
  const budgetDisplayTotalMax = budgetPrediction
    ? Math.max(0, budgetPrediction.total_max - (hasBudgetTravelFareData ? 0 : budgetTravelCost))
    : 0;
  const budgetFlightFareStrategy = budgetAssumptions?.flight_fare_strategy;
  const budgetTravelSource = hasBudgetTravelFareData
    ? `кэш Aviasales · ${
        budgetFlightFareStrategy === 'business_comfort'
          ? 'бизнес'
          : budgetFlightFareStrategy === 'typical_economy'
            ? 'средний тариф'
            : 'дешевый тариф'
      }`
    : 'нет данных по стоимости пути';

  const handleSuccess = (trip: Trip) => {
    navigate(`/trips/${trip.id}`, { replace: true });
  };

  const handleCancel = () => {
    navigate(-1);
  };

  return (
    <PageLayout fullScreen>
      <AppPageHeader pb="pb-3">
        <div className="flex items-center gap-3">
          <button
            type="button"
            className="flex h-9 w-9 shrink-0 items-center justify-center"
            onClick={handleCancel}
          >
            <ChevronLeft className="h-5 w-5 text-stone-700 dark:text-stone-200" />
          </button>
          <h1 className="text-[22px] font-extrabold tracking-tight text-stone-900 dark:text-white">
            Новая поездка
          </h1>
        </div>
      </AppPageHeader>

      <PageContent pb="pb-5" className="pt-5">
        {budgetPrediction && (
          <div className="mb-4 rounded-2xl border border-blue-100 bg-blue-50/70 p-4 dark:border-blue-900/40 dark:bg-blue-950/30">
            <div className="mb-3 flex items-start justify-between gap-3">
              <div>
                <p className="text-[11px] font-extrabold uppercase tracking-[0.06em] text-blue-600 dark:text-blue-300">
                  Прогноз Triply
                </p>
                <p className="mt-1 text-[22px] font-extrabold tracking-tight text-stone-900 dark:text-white">
                  {(CURRENCY_SYMBOLS[budgetPrediction.currency] ?? budgetPrediction.currency)}
                  {Math.round(budgetDisplayTotalMid).toLocaleString('ru-RU')}
                </p>
              </div>
              <div className="text-right text-[12px] font-bold text-stone-500 dark:text-stone-400">
                p10 {Math.round(budgetDisplayTotalMin).toLocaleString('ru-RU')}
                <br />
                p90 {Math.round(budgetDisplayTotalMax).toLocaleString('ru-RU')}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 text-[12px]">
              <span className="truncate text-stone-500 dark:text-stone-400">
                {budgetAssumptions?.duration_days ?? budgetPrediction.duration_days} дн. · {budgetAssumptions?.people_count ?? budgetPrediction.people_count} чел
              </span>
              <span className="truncate text-right text-stone-500 dark:text-stone-400">
                {budgetAssumptions?.origin_city_name ?? 'origin не указан'}
              </span>
              <span className="truncate text-stone-500 dark:text-stone-400" title={budgetTravelSource}>
                {hasBudgetTravelFareData
                  ? `дорога: ${Math.round(budgetTravelCost).toLocaleString('ru-RU')} ${budgetPrediction.currency} · ${budgetTravelSource}`
                  : budgetTravelSource}
              </span>
              <span className="truncate text-right text-stone-500 dark:text-stone-400">
                {budgetAssumptions?.travel_distance_km !== null && budgetAssumptions?.travel_distance_km !== undefined
                  ? `${Math.round(budgetAssumptions.travel_distance_km).toLocaleString('ru-RU')} км`
                  : 'без расстояния'}
              </span>
            </div>
          </div>
        )}
        {isProfileLoading ? null : (
          <TripForm
            initialValues={initialValues}
            onSuccess={handleSuccess}
            onSnapshotChange={handleFormSnapshotChange}
            validationSlot={
              <DestinationValidationCompact
                destinationId={destinationId}
                travelMonth={getTravelMonth(previewStartDate)}
                budgetPerDayUsd={validationBudgetPerDayUsd}
              />
            }
          />
        )}
      </PageContent>
    </PageLayout>
  );
};
