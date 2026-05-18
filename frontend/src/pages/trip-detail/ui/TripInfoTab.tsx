import { useFeedback } from '@/features/feedback';
import { useItineraryState } from '@/features/itinerary';
import { profileApi } from '@/features/profile';
import { useBudgetMonitor, useBudgetPrediction } from '@/features/recommendations';
import { BudgetMonitoringCard, useTripAnalytics } from '@/features/trips';
import { sendEvent } from '@/shared/api';
import { localizeDestinationName } from '@/shared/lib';
import { useHapticFeedback } from '@/shared/lib/useHapticFeedback';
import { Button } from '@/shared/ui';
import { useQuery } from '@tanstack/react-query';
import { Edit, Loader2, Trash2, User } from 'lucide-react';
import { useEffect, useMemo, useRef } from 'react';
import { useNavigate, useOutletContext } from 'react-router-dom';
import type { TripDetailOutletContext } from './TripDetailPage';

const formatDateFull = (dateStr: string) => {
  if (!dateStr) return '';
  try {
    const date = new Date(dateStr + 'T00:00:00');
    return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' });
  } catch {
    return dateStr;
  }
};

const CURRENCY_LABEL: Record<string, string> = {
  RUB: 'Рубль',
  USD: 'Доллар',
  EUR: 'Евро',
  GBP: 'Фунт',
  CNY: 'Юань',
  TRY: 'Лира',
};

const getTravelMonth = (dateStr: string) => {
  const parsed = new Date(`${dateStr}T00:00:00`);
  return Number.isFinite(parsed.getTime()) ? parsed.getMonth() + 1 : new Date().getMonth() + 1;
};

const getAccommodationTier = (
  budgetMinUsd?: number | null,
  budgetMaxUsd?: number | null
): 'budget' | 'mid' | 'luxury' => {
  const mid = ((budgetMinUsd ?? 0) + (budgetMaxUsd ?? 2000)) / 2;
  if (mid < 800) return 'budget';
  if (mid < 5000) return 'mid';
  return 'luxury';
};

const FIXED_EXPENSE_KEYWORDS =
  /авиа|самолет|самолёт|перелет|перелёт|рейс|поезд|жд|билет|брон|отель|гостиниц|виза|страхов|flight|airfare|airline|train|ticket|booking|hotel|visa|insurance/i;

const getPriceSources = (summary: Record<string, unknown> | null | undefined) => {
  const value = summary?.paid_poi_price_sources;
  return Array.isArray(value) ? value : [];
};

const isEvidenceBackedSource = (source: unknown) =>
  typeof source === 'object' &&
  source !== null &&
  'provider' in source &&
  typeof source.provider === 'string' &&
  !source.provider.startsWith('catalog');

const isCandidatePriceSource = (source: unknown) =>
  typeof source === 'object' &&
  source !== null &&
  'candidate_poi' in source &&
  source.candidate_poi === true;

const isManualForecastExpense = (
  expense: {
    category: string;
    description?: string | null;
    expense_date?: string | null;
    is_one_time?: boolean;
  },
  tripStart: string,
  tripEnd: string
) => {
  if (
    expense.expense_date &&
    (expense.expense_date < tripStart || expense.expense_date > tripEnd)
  ) {
    return false;
  }
  if (expense.is_one_time || expense.category === 'housing') {
    return false;
  }
  if (FIXED_EXPENSE_KEYWORDS.test(`${expense.category} ${expense.description ?? ''}`)) {
    return false;
  }
  return ['food', 'transport', 'other'].includes(expense.category);
};

export const TripInfoTab = () => {
  const { play } = useHapticFeedback();
  const navigate = useNavigate();
  const trackedBudgetMonitorKeys = useRef<Set<string>>(new Set());
  const trackedBudgetRiskKeys = useRef<Set<string>>(new Set());
  const { trip, isStatusChanging, onStatusChange, onEditOpen, onCancelOpen, onDeleteOpen } =
    useOutletContext<TripDetailOutletContext>();

  const isCancelled = trip.status === 'cancelled';
  const isCompleted = trip.status === 'completed';
  const isActive = trip.status === 'active';
  const isPlanned = trip.status === 'planned';

  const { deleteFeedback } = useFeedback(trip.id, localizeDestinationName(trip.destination));
  const {
    budget,
    budgetMonitoringStatus,
    burnRatePerDay,
    currency,
    daysUntilStart,
    elapsedDays,
    projectedBudgetDiff,
    projectedBudgetPct,
    projectedFinalSpend,
    remainingDays,
    totalSpent,
    durationDays,
    expenses,
  } = useTripAnalytics(trip);
  const { data: profile } = useQuery({
    queryKey: ['profile'],
    queryFn: profileApi.getProfile,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });
  const todayParam = new Date().toISOString().slice(0, 10);
  const { data: itineraryState } = useItineraryState(trip.id);
  const itinerarySummary = useMemo(() => {
    const itinerary = itineraryState?.approved;
    if (!itinerary) return null;
    const today = todayParam;
    const remainingDays = itinerary.days.filter((day) => day.date >= today);
    const remainingItems = remainingDays.flatMap((day) =>
      day.items.filter((item) => !item.is_removed && !item.visited_place_id)
    );
    const priceSources = getPriceSources(itinerary.score_summary);
    const evidenceBackedSourceCount = priceSources.filter(isEvidenceBackedSource).length;
    const hasPriceEvidence = evidenceBackedSourceCount > 0;
    const durations = remainingItems
      .map((item) => item.duration_minutes)
      .filter((value): value is number => typeof value === 'number' && Number.isFinite(value));
    const remainingEntranceFees = remainingItems.reduce(
      (sum, item) => sum + (item.entrance_fee_usd ?? 0),
      0
    );
    return {
      generated_days_count: itinerary.days.length,
      remaining_days_count: remainingDays.length,
      remaining_poi_count: remainingItems.length,
      remaining_food_poi_count: remainingItems.filter((item) => item.category === 'food').length,
      remaining_paid_poi_count: remainingItems.filter((item) => item.entrance_fee_usd !== null)
        .length,
      remaining_estimated_entrance_fees: remainingEntranceFees,
      remaining_evidence_backed_entrance_fees: hasPriceEvidence ? remainingEntranceFees : 0,
      evidence_backed_price_count: evidenceBackedSourceCount,
      candidate_poi_price_count: priceSources.filter(isCandidatePriceSource).length,
      price_estimation_used: Boolean(itinerary.score_summary?.price_estimation_used),
      avg_visit_duration_minutes:
        durations.length > 0
          ? durations.reduce((sum, value) => sum + value, 0) / durations.length
          : null,
    };
  }, [itineraryState?.approved, todayParam]);
  const budgetPredictionParams = useMemo(
    () =>
      trip.destination_id
        ? {
            destination_id: trip.destination_id,
            duration_days: durationDays,
            people_count: trip.people_count,
            travel_month: getTravelMonth(trip.start_date),
            accommodation_tier: getAccommodationTier(
              profile?.budget_min_usd,
              profile?.budget_max_usd
            ),
            currency: trip.currency,
            origin_city_name: profile?.origin_city_name ?? trip.departure_city,
            origin_lat: profile?.origin_lat,
            origin_lng: profile?.origin_lng,
          }
        : null,
    [
      durationDays,
      profile?.budget_max_usd,
      profile?.budget_min_usd,
      profile?.origin_city_name,
      profile?.origin_lat,
      profile?.origin_lng,
      trip.currency,
      trip.departure_city,
      trip.destination_id,
      trip.people_count,
      trip.start_date,
    ]
  );
  const {
    data: budgetPrediction,
    isError: isBudgetPredictionError,
    isFetching: isBudgetPredictionFetching,
    isPending: isBudgetPredictionPending,
    refetch: refetchBudgetPrediction,
  } = useBudgetPrediction(budgetPredictionParams);
  const monitorPreTripPrediction = useMemo(() => {
    if (!budgetPrediction) return null;

    const travelCost = budgetPrediction.breakdown.travel_to_destination ?? 0;
    const hasRealTravelFare =
      budgetPrediction.assumptions.travel_cost_source?.startsWith('travelpayouts') ?? false;
    const unsupportedTravelFallback = hasRealTravelFare ? 0 : travelCost;

    return {
      total_min: Math.max(0, budgetPrediction.total_min - unsupportedTravelFallback),
      total_mid: Math.max(0, budgetPrediction.total_mid - unsupportedTravelFallback),
      total_max: Math.max(0, budgetPrediction.total_max - unsupportedTravelFallback),
      breakdown: {
        ...budgetPrediction.breakdown,
        travel_to_destination: hasRealTravelFare ? travelCost : 0,
      },
      model_version: budgetPrediction.model_version,
    };
  }, [budgetPrediction]);
  const plannedDailyBudget =
    budgetPrediction && monitorPreTripPrediction
      ? (budgetPrediction.daily_recurring_mid ??
        Math.max(
          0,
          monitorPreTripPrediction.total_mid -
            (monitorPreTripPrediction.breakdown.travel_to_destination ?? 0)
        ) / Math.max(budgetPrediction.duration_days, 1))
      : null;
  const manualForecastExpenseCount = expenses.filter((expense) =>
    isManualForecastExpense(expense, trip.start_date, trip.end_date)
  ).length;
  const hasBudgetForecastInput = Boolean(trip.destination_id) || manualForecastExpenseCount >= 2;
  const budgetMonitorParams = useMemo(
    () =>
      !hasBudgetForecastInput || (trip.destination_id && !budgetPrediction)
        ? null
        : {
            trip_id: trip.id,
            destination_id: trip.destination_id,
            start_date: trip.start_date,
            end_date: trip.end_date,
            as_of_date: todayParam,
            people_count: trip.people_count,
            currency: trip.currency,
            trip_budget: trip.budget,
            accommodation_tier: budgetPredictionParams?.accommodation_tier ?? 'mid',
            expenses: expenses.map((expense) => ({
              amount: Number(expense.amount),
              currency: expense.currency,
              category: expense.category,
              expense_date: expense.expense_date,
              description: expense.description,
              is_one_time: expense.is_one_time,
            })),
            pre_trip_prediction: monitorPreTripPrediction,
            itinerary_summary: itinerarySummary,
          },
    [
      budgetPrediction,
      budgetPredictionParams?.accommodation_tier,
      expenses,
      hasBudgetForecastInput,
      itinerarySummary,
      monitorPreTripPrediction,
      todayParam,
      trip.budget,
      trip.currency,
      trip.destination_id,
      trip.end_date,
      trip.id,
      trip.people_count,
      trip.start_date,
    ]
  );
  const {
    data: budgetMonitor,
    isError: isBudgetMonitorError,
    isFetching: isBudgetMonitorFetching,
    isPending: isBudgetMonitorPending,
    refetch: refetchBudgetMonitor,
  } = useBudgetMonitor(budgetMonitorParams);
  const hasBudgetForecastError =
    (Boolean(budgetPredictionParams) && !budgetPrediction && isBudgetPredictionError) ||
    (Boolean(budgetMonitorParams) && !budgetMonitor && isBudgetMonitorError);
  const isBudgetForecastUpdating =
    !hasBudgetForecastError &&
    ((Boolean(budgetPredictionParams) &&
      !budgetPrediction &&
      (isBudgetPredictionPending || isBudgetPredictionFetching)) ||
      (Boolean(budgetMonitorParams) &&
        (isBudgetMonitorPending || (!budgetMonitor && isBudgetMonitorFetching))));
  const isBudgetForecastRetrying =
    hasBudgetForecastError && (isBudgetPredictionFetching || isBudgetMonitorFetching);

  useEffect(() => {
    if (!budgetMonitor) return;
    const key = `${trip.id}:${budgetMonitor.model_version}:${budgetMonitor.projected_final_mid}:${budgetMonitor.risk_status}`;
    if (trackedBudgetMonitorKeys.current.has(key)) return;
    trackedBudgetMonitorKeys.current.add(key);
    sendEvent(
      'budget_monitor_viewed',
      {
        trip_id: trip.id,
        status: trip.status,
        projected_final: budgetMonitor.projected_final_mid,
        currency: budgetMonitor.currency,
        model_version: budgetMonitor.model_version,
        risk_status: budgetMonitor.risk_status,
        used_ml_model: budgetMonitor.used_ml_model,
      },
      'trip',
      trip.id
    );
  }, [budgetMonitor, trip.id, trip.status]);

  useEffect(() => {
    if (!budgetMonitor || !['risk', 'over_budget'].includes(budgetMonitor.risk_status)) return;
    const key = `${trip.id}:${budgetMonitor.risk_status}:${budgetMonitor.projected_final_mid}`;
    if (trackedBudgetRiskKeys.current.has(key)) return;
    trackedBudgetRiskKeys.current.add(key);
    sendEvent(
      'budget_risk_shown',
      {
        trip_id: trip.id,
        risk_status: budgetMonitor.risk_status,
        projected_final: budgetMonitor.projected_final_mid,
        budget: trip.budget,
        currency: budgetMonitor.currency,
      },
      'trip',
      trip.id
    );
  }, [budgetMonitor, trip.budget, trip.id]);

  const handleBudgetForecastRetry = () => {
    if (Boolean(budgetPredictionParams) && (!budgetPrediction || isBudgetPredictionError)) {
      void refetchBudgetPrediction();
      return;
    }
    void refetchBudgetMonitor();
  };

  const handleContinueTrip = async () => {
    await deleteFeedback();
    await onStatusChange('active');
  };

  const cardBase = isCancelled ? 'trip-info-card-muted' : 'trip-info-card';

  return (
    <div className="no-scrollbar flex-1 overflow-y-auto pb-24 pt-4">
      <div className="flex flex-col gap-3">
        {isCancelled && (
          <div className="flex items-start gap-2.5 rounded-2xl border border-red-200 bg-red-50/60 px-4 py-3 dark:border-red-900/50 dark:bg-red-900/20">
            <svg
              className="mt-0.5 h-4 w-4 shrink-0 text-red-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
              />
            </svg>
            <p className="text-[13px] font-medium text-red-600 dark:text-red-400">
              Поездка отменена. Вы можете восстановить ее или удалить навсегда
            </p>
          </div>
        )}

        {/* Dates card */}
        <div className={`${cardBase} flex gap-0`}>
          <div className="flex-1">
            <p className="mb-1 text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
              Начало
            </p>
            <p className="text-[20px] font-bold leading-tight text-stone-900 dark:text-white">
              {formatDateFull(trip.start_date)}
            </p>
          </div>
          <div className="mx-[20px] w-px self-stretch bg-stone-200 dark:bg-stone-700" />
          <div className="flex-1">
            <p className="mb-1 text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
              Конец
            </p>
            <p className="text-[20px] font-bold leading-tight text-stone-900 dark:text-white">
              {formatDateFull(trip.end_date)}
            </p>
          </div>
        </div>

        <div className="flex gap-3">
          <div className={`${cardBase} flex-1`}>
            <p className="mb-1 text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
              Путешественники
            </p>
            <div className="flex items-center gap-1.5">
              <User className="h-5 w-5 text-[#2563EB]" />
              <p className="text-[26px] font-bold leading-none text-stone-900 dark:text-white">
                {trip.people_count}
              </p>
            </div>
            <p className="mt-0.5 text-[12px] font-medium text-stone-400 dark:text-stone-500">
              чел.
            </p>
          </div>

          <div className={`${cardBase} flex-1`}>
            <p className="mb-1 text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
              Бюджет
            </p>
            <p className="text-[22px] font-bold leading-none text-stone-900 dark:text-white">
              {trip.budget ? trip.budget.toLocaleString('ru-RU') : '-'}
            </p>
            <p className="mt-1.5 text-[12px] font-medium text-stone-400 dark:text-stone-500">
              {trip.currency} · {CURRENCY_LABEL[trip.currency] ?? trip.currency}
            </p>
          </div>
        </div>

        {(isActive || isPlanned) && (
          <BudgetMonitoringCard
            budget={budget}
            budgetMonitoringStatus={budgetMonitoringStatus}
            burnRatePerDay={burnRatePerDay}
            currency={currency}
            daysUntilStart={daysUntilStart}
            elapsedDays={elapsedDays}
            hasError={hasBudgetForecastError}
            hasForecastInput={hasBudgetForecastInput}
            peopleCount={trip.people_count}
            plannedDailyBudget={plannedDailyBudget}
            monitor={budgetMonitor}
            isUpdating={isBudgetForecastUpdating || isBudgetForecastRetrying}
            onRetry={handleBudgetForecastRetry}
            projectedBudgetDiff={projectedBudgetDiff}
            projectedBudgetPct={projectedBudgetPct}
            projectedFinalSpend={projectedFinalSpend}
            remainingDays={remainingDays}
            totalSpent={totalSpent}
          />
        )}

        {trip.notes && (
          <div className={cardBase}>
            <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
              Заметки
            </p>
            <p className="whitespace-pre-wrap text-[15px] leading-relaxed text-stone-700 dark:text-stone-300">
              {trip.notes}
            </p>
          </div>
        )}

        {/* Action buttons */}
        <div className="mt-1 flex flex-col gap-2.5">
          {isCancelled && (
            <Button
              className="h-[52px] w-full rounded-2xl shadow-[0_4px_16px_rgba(37,99,235,0.28)]"
              onClick={() => onStatusChange('planned')}
              disabled={isStatusChanging}
            >
              {isStatusChanging && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Восстановить поездку
            </Button>
          )}

          {isCompleted && (
            <Button
              className="h-[52px] w-full rounded-2xl shadow-[0_4px_16px_rgba(37,99,235,0.28)]"
              onClick={handleContinueTrip}
              disabled={isStatusChanging}
            >
              {isStatusChanging && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Продолжить поездку
            </Button>
          )}

          {(isActive || isPlanned) && (
            <>
              <div className="flex gap-2.5">
                <Button
                  className="h-[52px] flex-1 rounded-2xl shadow-[0_4px_16px_rgba(37,99,235,0.28)]"
                  onClick={async () => {
                    const next = isActive ? 'completed' : 'active';
                    await onStatusChange(next);
                    if (next === 'completed')
                      navigate(`/trips/${trip.id}/analytics`, { state: { justCompleted: true } });
                  }}
                  disabled={isStatusChanging}
                >
                  {isStatusChanging && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  {isActive ? 'Завершить' : 'Начать поездку'}
                </Button>
                <Button
                  variant="outline"
                  className="h-[52px] flex-1 rounded-2xl border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-muted))] text-foreground"
                  onClick={onCancelOpen}
                  disabled={isStatusChanging}
                >
                  Отменить
                </Button>
              </div>
              {isActive && (
                <Button
                  variant="outline"
                  className="h-[52px] w-full rounded-2xl border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-muted))] text-foreground"
                  onClick={() => onStatusChange('planned')}
                  disabled={isStatusChanging}
                >
                  Вернуться к планированию
                </Button>
              )}
            </>
          )}

          <div className="flex gap-2.5">
            {!isCancelled && !isCompleted && (
              <Button
                variant="ghost"
                className="h-[52px] flex-1 rounded-2xl border border-[hsl(var(--surface-border))] text-foreground hover:bg-[hsl(var(--surface-muted))]"
                onClick={onEditOpen}
              >
                <Edit className="mr-2 h-4 w-4" />
                Редактировать
              </Button>
            )}
            <button
              type="button"
              className={`flex h-[52px] shrink-0 items-center justify-center rounded-2xl border border-red-100 bg-red-50/70 dark:border-red-900/60 dark:bg-red-900/20 ${isCancelled || isCompleted ? 'w-full flex-1 gap-2' : 'w-[52px]'}`}
              onClick={() => {
                play('error');
                onDeleteOpen();
              }}
            >
              <Trash2 className="h-4 w-4 text-red-500 dark:text-red-400" />
              {(isCancelled || isCompleted) && (
                <span className="text-[15px] font-semibold text-red-500 dark:text-red-400">
                  Удалить поездку
                </span>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
