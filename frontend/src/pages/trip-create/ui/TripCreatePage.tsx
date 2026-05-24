import { expenseApi } from '@/entities/expense';
import type { Trip } from '@/entities/trip';
import { profileApi } from '@/features/profile';
import { DestinationValidationCompact, useBudgetPrediction } from '@/features/recommendations';
import { TripForm, type TripFormInitialValues, type TripFormSnapshot } from '@/features/trips';
import { sendEvent } from '@/shared/api';
import { useDebouncedValue } from '@/shared/lib';
import { useHapticFeedback } from '@/shared/lib/useHapticFeedback';
import { AppPageHeader, PageContent, PageLayout } from '@/shared/ui';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, ChevronLeft, Loader2, RotateCcw, Sparkles } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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

const getAccommodationTier = (
  value: string | null,
  restLevel?: string | null,
  budgetLimitUsd?: number | null
): 'budget' | 'mid' | 'luxury' => {
  const requested = value === 'budget' || value === 'luxury' ? value : 'mid';
  const profileTier =
    restLevel === 'economy' ? 'budget' : restLevel === 'luxury' ? 'luxury' : 'mid';

  if (budgetLimitUsd !== null && budgetLimitUsd !== undefined) {
    if (budgetLimitUsd < 900) return 'budget';
    if (budgetLimitUsd < 3000 && (requested === 'luxury' || profileTier === 'luxury')) return 'mid';
  }
  if (restLevel) return profileTier;
  if (!restLevel && requested === 'luxury') return 'mid';
  return requested;
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

const formatBudgetAmount = (value: number, currency: string) => {
  const symbol = CURRENCY_SYMBOLS[currency] ?? currency;
  const amount = Math.round(value).toLocaleString('ru-RU');
  return symbol.length > 1 ? `${symbol} ${amount}` : `${symbol}${amount}`;
};

const BudgetPredictionStateCard = ({
  state,
  onRetry,
}: {
  state: 'empty' | 'loading' | 'error';
  onRetry?: () => void;
}) => {
  const { play } = useHapticFeedback();
  const meta = {
    empty: {
      icon: Sparkles,
      title: 'Выберите параметры поездки',
      subtitle: 'Укажите направление из каталога и даты',
      text: 'После этого Triply рассчитает ваш бюджет',
      headerClassName: 'bg-primary/10',
      labelClassName: 'text-primary',
      titleClassName: 'text-foreground',
      iconClassName: 'bg-primary/10 text-primary',
    },
    loading: {
      icon: Loader2,
      title: 'Считаем прогноз бюджета',
      subtitle: 'Проверяем сезон, длительность и другие особенности направления',
      text: 'Расчёт занимает несколько секунд',
      headerClassName: 'bg-primary/10',
      labelClassName: 'text-primary',
      titleClassName: 'text-foreground',
      iconClassName: 'bg-primary/10 text-primary',
    },
    error: {
      icon: AlertTriangle,
      title: 'Временно недоступен',
      subtitle: 'Можно попробовать ещё раз или продолжить без прогноза',
      text: 'Не удалось рассчитать бюджет по выбранным параметрам',
      headerClassName: 'bg-red-500/10',
      labelClassName: 'text-red-600 dark:text-red-300',
      titleClassName: 'text-red-700 dark:text-red-200',
      iconClassName: 'bg-red-500/10 text-red-600 dark:text-red-300',
    },
  }[state];
  const Icon = meta.icon;

  return (
    <div className="mb-4 overflow-hidden rounded-[24px] border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface))] shadow-[0_18px_44px_rgba(2,8,23,0.08)] transition-[opacity,transform,background-color,border-color] duration-300 ease-out dark:shadow-[0_22px_56px_rgba(0,0,0,0.32)]">
      <div
        className={`border-b border-[hsl(var(--surface-border))] px-4 py-4 ${meta.headerClassName}`}
      >
        <div>
          <p
            className={`text-[11px] font-extrabold uppercase tracking-[0.06em] ${meta.labelClassName}`}
          >
            Прогноз Triply
          </p>
          <p className={`mt-1 text-[26px] font-extrabold tracking-tight ${meta.titleClassName}`}>
            {meta.title}
          </p>
          <p className="mt-1 text-[12px] font-bold text-muted-foreground">{meta.subtitle}</p>
        </div>
      </div>

      <div className="p-4">
        <div className="rounded-2xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-muted))] px-3.5 py-3">
          <div className="flex items-center gap-3">
            <div
              className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${meta.iconClassName}`}
            >
              <Icon className={`h-4.5 w-4.5 ${state === 'loading' ? 'animate-spin' : ''}`} />
            </div>
            <div className="flex min-h-9 min-w-0 flex-1 flex-col justify-center">
              <p className="text-[13px] font-extrabold leading-snug text-foreground">{meta.text}</p>
            </div>
            {state === 'error' && onRetry && (
              <button
                type="button"
                onClick={() => {
                  play('nudge');
                  onRetry();
                }}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-red-500/25 bg-background/70 text-red-600 transition-colors active:scale-95 dark:text-red-300"
                aria-label="Повторить прогноз"
              >
                <RotateCcw className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export const TripCreatePage = () => {
  const { play } = useHapticFeedback();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const trackedBudgetKeys = useRef<Set<string>>(new Set());

  const { data: profile, isLoading: isProfileLoading } = useQuery({
    queryKey: ['profile'],
    queryFn: profileApi.getProfile,
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
  const debouncedFormSnapshot = useDebouncedValue(formSnapshot, 450);
  const handleFormSnapshotChange = useCallback((snapshot: TripFormSnapshot) => {
    setFormSnapshot(snapshot);
  }, []);

  const initialDestinationId = searchParams.get('destination_id')?.trim() || null;
  const previewDestination = debouncedFormSnapshot?.destination ?? initialValues.destination;
  const isInitialDestination =
    normalizeCity(previewDestination) === normalizeCity(initialValues.destination);
  const destinationId = debouncedFormSnapshot
    ? (debouncedFormSnapshot.destination_id ?? (isInitialDestination ? initialDestinationId : null))
    : initialDestinationId;
  const previewStartDate = debouncedFormSnapshot?.start_date ?? initialValues.start_date;
  const previewEndDate = debouncedFormSnapshot?.end_date ?? initialValues.end_date;
  const previewDepartureCity =
    debouncedFormSnapshot?.departure_city ??
    initialValues.departure_city ??
    profile?.origin_city_name;
  const isProfileOrigin =
    normalizeCity(previewDepartureCity) === normalizeCity(profile?.origin_city_name);
  const selectedOriginLat = debouncedFormSnapshot?.departure_lat ?? null;
  const selectedOriginLng = debouncedFormSnapshot?.departure_lng ?? null;
  const budgetDurationDays =
    getDurationDays(previewStartDate, previewEndDate) ?? profile?.typical_duration_days ?? 7;
  const budgetPeopleCount = debouncedFormSnapshot?.people_count ?? initialValues.people_count ?? 1;
  const budgetCurrency =
    debouncedFormSnapshot?.currency ??
    initialValues.currency ??
    profile?.preferred_currency ??
    'RUB';
  const budgetValue = debouncedFormSnapshot?.budget ?? initialValues.budget ?? -1;
  const needsUsdRate = budgetValue > 0 && budgetCurrency !== 'USD';
  const { data: validationRates } = useQuery({
    queryKey: ['exchange-rates', budgetCurrency],
    queryFn: () => expenseApi.getExchangeRates(budgetCurrency),
    enabled: needsUsdRate,
    staleTime: 60 * 60 * 1000,
    retry: 1,
  });
  const isBudgetUnlimited = budgetValue < 0;
  const validationBudgetUsd = isBudgetUnlimited
    ? null
    : budgetCurrency === 'USD'
      ? budgetValue
      : budgetValue === 0
        ? 0
        : validationRates?.rates.USD
          ? budgetValue * validationRates.rates.USD
          : null;
  const budgetAccommodationTier = getAccommodationTier(
    searchParams.get('accommodation_tier'),
    profile?.rest_level,
    validationBudgetUsd
  );
  const validationBudgetPerDayUsd =
    validationBudgetUsd !== null
      ? validationBudgetUsd / Math.max(budgetDurationDays * budgetPeopleCount, 1)
      : null;
  const budgetPredictionParams =
    destinationId && previewStartDate && previewEndDate
      ? {
          destination_id: destinationId,
          duration_days: budgetDurationDays,
          people_count: budgetPeopleCount,
          travel_month: getTravelMonth(previewStartDate),
          accommodation_tier: budgetAccommodationTier,
          currency: budgetCurrency,
          budget_limit_usd: validationBudgetUsd,
          origin_city_name: previewDepartureCity,
          origin_lat: selectedOriginLat ?? (isProfileOrigin ? profile?.origin_lat : null),
          origin_lng: selectedOriginLng ?? (isProfileOrigin ? profile?.origin_lng : null),
        }
      : null;
  const {
    data: budgetPrediction,
    isFetching: isBudgetPredictionFetching,
    isError: isBudgetPredictionError,
    refetch: refetchBudgetPrediction,
  } = useBudgetPrediction(budgetPredictionParams);
  const budgetAssumptions = budgetPrediction?.assumptions;
  const hasBudgetTravelFareData =
    budgetAssumptions?.travel_cost_source?.startsWith('travelpayouts') ?? false;
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
  const budgetRangeItems = budgetPrediction
    ? [
        {
          label: 'Нижняя граница',
          value: formatBudgetAmount(budgetDisplayTotalMin, budgetPrediction.currency),
          className: 'border-border/70 bg-background/50 text-muted-foreground',
        },
        {
          label: 'Прогноз',
          value: formatBudgetAmount(budgetDisplayTotalMid, budgetPrediction.currency),
          className:
            'border-primary/35 bg-primary/10 text-foreground shadow-[0_12px_34px_rgba(37,99,235,0.16)]',
        },
        {
          label: 'Верхняя граница',
          value: formatBudgetAmount(budgetDisplayTotalMax, budgetPrediction.currency),
          className: 'border-border/70 bg-background/50 text-muted-foreground',
        },
      ]
    : [];
  const budgetRouteValue = hasBudgetTravelFareData
    ? `${formatBudgetAmount(budgetTravelCost, budgetPrediction?.currency ?? budgetCurrency)} · ${budgetTravelSource}`
    : budgetTravelSource;
  const budgetDistanceValue =
    budgetAssumptions?.travel_distance_km !== null &&
    budgetAssumptions?.travel_distance_km !== undefined
      ? `${Math.round(budgetAssumptions.travel_distance_km).toLocaleString('ru-RU')} км`
      : 'Расстояние неизвестно';

  useEffect(() => {
    if (!budgetPrediction || !destinationId) return;
    const key = `${destinationId}:${budgetPrediction.duration_days}:${budgetPrediction.people_count}:${budgetPrediction.currency}:${getTravelMonth(previewStartDate)}`;
    if (trackedBudgetKeys.current.has(key)) return;
    trackedBudgetKeys.current.add(key);
    sendEvent(
      'budget_prediction_changed',
      {
        destination_id: destinationId,
        recommendation_id: searchParams.get('recommendation_id') || null,
        model_version: searchParams.get('model_version') || null,
        duration_days: budgetPrediction.duration_days,
        people_count: budgetPrediction.people_count,
        currency: budgetPrediction.currency,
        total_mid: budgetPrediction.total_mid,
        origin_city_name: budgetPrediction.assumptions?.origin_city_name,
        travel_cost_source: budgetPrediction.assumptions?.travel_cost_source,
      },
      'destination',
      destinationId
    );
  }, [budgetPrediction, destinationId, previewStartDate, searchParams]);

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
            onClick={() => {
              play('nudge');
              handleCancel();
            }}
          >
            <ChevronLeft className="h-5 w-5 text-stone-700 dark:text-stone-200" />
          </button>
          <h1 className="text-[22px] font-extrabold tracking-tight text-stone-900 dark:text-white">
            Новая поездка
          </h1>
        </div>
      </AppPageHeader>

      <PageContent pb="pb-28" className="pt-4">
        {!budgetPredictionParams ? (
          <BudgetPredictionStateCard state="empty" />
        ) : isBudgetPredictionFetching && !budgetPrediction ? (
          <BudgetPredictionStateCard state="loading" />
        ) : isBudgetPredictionError && !budgetPrediction ? (
          <BudgetPredictionStateCard state="error" onRetry={() => void refetchBudgetPrediction()} />
        ) : budgetPrediction ? (
          <div className="mb-4 min-h-[184px] origin-top overflow-hidden rounded-[24px] border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface))] shadow-[0_18px_44px_rgba(2,8,23,0.08)] transition-[opacity,transform,background-color,border-color,max-height] duration-500 ease-out animate-in fade-in-0 slide-in-from-top-2 dark:shadow-[0_22px_56px_rgba(0,0,0,0.32)]">
            <div className="border-b border-[hsl(var(--surface-border))] bg-primary/10 px-4 py-4">
              <div>
                <p className="text-[11px] font-extrabold uppercase tracking-[0.06em] text-primary">
                  Прогноз Triply
                </p>
                <p className="mt-1 text-[26px] font-extrabold tracking-tight text-foreground">
                  {formatBudgetAmount(budgetDisplayTotalMid, budgetPrediction.currency)}
                </p>
                <p className="mt-1 text-[12px] font-bold text-muted-foreground">
                  {budgetAssumptions?.duration_days ?? budgetPrediction.duration_days} дн. ·{' '}
                  {budgetAssumptions?.people_count ?? budgetPrediction.people_count} чел.
                </p>
              </div>
            </div>

            <div className="space-y-4 p-4">
              <div className="grid grid-cols-3 gap-2">
                {budgetRangeItems.map((item) => (
                  <div
                    key={item.label}
                    className={`min-h-[70px] rounded-2xl border px-2.5 py-2.5 ${item.className}`}
                  >
                    <p className="text-[10px] font-extrabold uppercase leading-tight tracking-[0.04em]">
                      {item.label}
                    </p>
                    <p className="mt-1.5 text-[13px] font-extrabold leading-tight">{item.value}</p>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-2 gap-2 text-[12px]">
                <div className="rounded-2xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-muted))] px-3 py-2.5">
                  <p className="text-[10px] font-extrabold uppercase tracking-[0.04em] text-muted-foreground">
                    Откуда
                  </p>
                  <p className="mt-1 break-words font-extrabold leading-snug text-foreground">
                    {budgetAssumptions?.origin_city_name ?? 'Не указано'}
                  </p>
                </div>
                <div className="rounded-2xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-muted))] px-3 py-2.5">
                  <p className="text-[10px] font-extrabold uppercase tracking-[0.04em] text-muted-foreground">
                    Расстояние
                  </p>
                  <p className="mt-1 break-words font-extrabold leading-snug text-foreground">
                    {budgetDistanceValue}
                  </p>
                </div>
                <div className="col-span-2 rounded-2xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-muted))] px-3 py-2.5">
                  <p className="text-[10px] font-extrabold uppercase tracking-[0.04em] text-muted-foreground">
                    Дорога
                  </p>
                  <p
                    className="mt-1 break-words font-extrabold leading-snug text-foreground"
                    title={budgetRouteValue}
                  >
                    {budgetRouteValue}
                  </p>
                </div>
              </div>
            </div>
          </div>
        ) : null}
        {isProfileLoading ? null : (
          <TripForm
            initialValues={initialValues}
            onSuccess={handleSuccess}
            onSnapshotChange={handleFormSnapshotChange}
            analyticsContext={{
              source: searchParams.get('recommendation_id') ? 'recommendation' : 'manual',
              recommendation_id: searchParams.get('recommendation_id') || null,
              model_version: searchParams.get('model_version') || null,
            }}
            validationSlot={
              <DestinationValidationCompact
                destinationId={destinationId}
                travelMonth={getTravelMonth(previewStartDate)}
                budgetPerDayUsd={validationBudgetPerDayUsd}
                budgetUnlimited={isBudgetUnlimited}
                citizenshipCode={profile?.citizenship_code}
                durationDays={budgetDurationDays}
                riskTolerance={profile?.risk_tolerance}
                preferredLanguage={
                  profile?.language_comfort?.find((language) => language !== 'any') ?? null
                }
              />
            }
          />
        )}
      </PageContent>
    </PageLayout>
  );
};
