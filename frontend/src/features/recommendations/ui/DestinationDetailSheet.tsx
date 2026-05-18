import type { UserProfileV2 } from '@/entities/user';
import { sendEvent } from '@/shared/api';
import { getCountryFlag, localizeDestinationName } from '@/shared/lib';
import { cn } from '@/shared/lib/utils';
import { AdaptiveSheet, Button } from '@/shared/ui';
import { useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, CheckCircle2, Plane, ShieldAlert } from 'lucide-react';
import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import type {
  DestinationValidationResponse,
  DestinationValidationStatus,
  DestinationValidationWarning,
  ScoredDestination,
} from '../model/types';
import { useBudgetPrediction } from '../model/useBudgetPrediction';
import { useDestinationValidation } from '../model/useDestinationValidation';

const BREAKDOWN_LABELS: Record<string, string> = {
  activity_match: 'Активности',
  budget_fit: 'Бюджет',
  season_fit: 'Сезон',
  safety_modulation: 'Безопасность',
  visa_effort: 'Виза',
  language_match: 'Язык',
  crowd_fit: 'Людность',
  climate_match: 'Климат',
  origin_proximity: 'Близость',
  liked_similarity: 'Похожее на ваши места',
  liked_dest_similarity: 'Похожее на ваши места',
  connectivity: 'Доступность',
};

const TAG_REASON_LABELS: Record<string, string> = {
  visa_free: 'Безвизовый или самый простой въезд',
  easy_visa: 'Визовые условия не выглядят сложными',
  beach: 'Есть выраженный пляжный сценарий',
  skiing: 'Подходит для горнолыжного отдыха',
  hot_springs: 'Есть термальные источники',
  mountains: 'Есть горный и природный сценарий',
  safe: 'Хороший уровень безопасности',
  affordable: 'Стоимость ниже многих альтернатив',
  premium: 'Подходит для премиального формата',
  perfect_season: 'Сейчас сильный сезон для поездки',
  great_match: 'Хорошо совпадает с вашими интересами',
};

const FALLBACK_REASON_LABELS: Record<string, string> = {
  season_score: 'Сезон',
  safety_score: 'Безопасность',
  avg_daily_cost: 'Стоимость',
};

const TYPICAL_DURATION_MAP: Record<string, number> = {
  weekend: 3,
  short: 5,
  standard: 7,
  long: 14,
  extended: 21,
};

const STATUS_META: Record<
  DestinationValidationStatus,
  { label: string; className: string; icon: typeof CheckCircle2 }
> = {
  suitable: {
    label: 'Подходит',
    className: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
    icon: CheckCircle2,
  },
  caution: {
    label: 'Есть ограничения',
    className: 'border-amber-500/35 bg-amber-500/10 text-amber-700 dark:text-amber-300',
    icon: AlertTriangle,
  },
  not_recommended: {
    label: 'Не рекомендуется',
    className: 'border-red-500/35 bg-red-500/10 text-red-700 dark:text-red-300',
    icon: ShieldAlert,
  },
};

type TripParams = {
  duration_days: number;
  people_count: number;
  accommodation_tier: 'budget' | 'mid' | 'luxury';
};

type DestinationDetailSheetProps = {
  destination: ScoredDestination | null;
  month: number;
  recommendationId?: string;
  modelVersion?: string;
  open: boolean;
  isLoading?: boolean;
  onClose: () => void;
};

const formatDateParam = (date: Date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const getSuggestedTripDates = (month: number, durationDays: number) => {
  const today = new Date();
  const currentMonth = today.getMonth() + 1;
  const year = month < currentMonth ? today.getFullYear() + 1 : today.getFullYear();
  const start = month === currentMonth ? today : new Date(year, month - 1, 1);
  const end = new Date(start);
  end.setDate(start.getDate() + durationDays - 1);

  return {
    startDate: formatDateParam(start),
    endDate: formatDateParam(end),
  };
};

const statusFromWarning = (warning?: DestinationValidationWarning): DestinationValidationStatus => {
  if (!warning) return 'suitable';
  if (warning.severity === 'high') return 'not_recommended';
  return 'caution';
};

const statusFromScore = (score: number | undefined): DestinationValidationStatus => {
  if (score === undefined) return 'caution';
  if (score < 0.3) return 'not_recommended';
  if (score < 0.6) return 'caution';
  return 'suitable';
};

const getOverallStatus = (statuses: DestinationValidationStatus[]): DestinationValidationStatus => {
  if (statuses.includes('not_recommended')) return 'not_recommended';
  if (statuses.includes('caution')) return 'caution';
  return 'suitable';
};

const formatPercent = (value: unknown) =>
  typeof value === 'number' ? `${Math.round(value * 100)}%` : 'нет данных';

const clampPercent = (value: number) => Math.max(0, Math.min(100, Math.round(value * 100)));

const formatDailyCost = (amount: number, currency: string) => {
  try {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency,
      maximumFractionDigits: 0,
    }).format(Math.round(amount));
  } catch {
    return `${Math.round(amount).toLocaleString('ru-RU')} ${currency}`;
  }
};

const formatVisa = (value: unknown) => {
  if (typeof value !== 'string') return 'нет данных';
  const labels: Record<string, string> = {
    visa_free: 'без визы',
    evisa: 'электронная виза',
    visa_on_arrival: 'виза по прибытии',
    visa_required: 'нужна виза',
    no_admission: 'въезд закрыт',
    unknown: 'нужно проверить',
  };
  return labels[value] ?? value.replace(/_/g, ' ');
};

type RecommendationReason = {
  key: string;
  label: string;
  value: number;
  note?: string;
};

const getTopReasons = (destination: ScoredDestination): RecommendationReason[] => {
  const factorReasons = Object.entries(destination.score_breakdown)
    .filter(
      (entry): entry is [string, number] =>
        entry[0] in BREAKDOWN_LABELS && typeof entry[1] === 'number'
    )
    .sort((a, b) => b[1] - a[1])
    .map(([key, value]) => ({
      key,
      label: BREAKDOWN_LABELS[key],
      value,
    }));

  const tagReasons = destination.explanation_tags
    .filter((tag) => tag in TAG_REASON_LABELS)
    .map((tag) => ({
      key: `tag:${tag}`,
      label: TAG_REASON_LABELS[tag],
      value: 0.75,
      note: 'по признакам направления',
    }));

  const fallbackReasons: RecommendationReason[] = [];
  if (typeof destination.season_score === 'number') {
    fallbackReasons.push({
      key: 'fallback:season',
      label: FALLBACK_REASON_LABELS.season_score,
      value: destination.season_score,
    });
  }
  if (typeof destination.safety_score === 'number') {
    fallbackReasons.push({
      key: 'fallback:safety',
      label: FALLBACK_REASON_LABELS.safety_score,
      value: destination.safety_score,
    });
  }
  if (
    typeof destination.avg_daily_budget === 'number' ||
    typeof destination.avg_daily_cost === 'number' ||
    typeof destination.avg_daily_cost_usd === 'number'
  ) {
    const dailyCost =
      destination.avg_daily_budget ?? destination.avg_daily_cost ?? destination.avg_daily_cost_usd;
    const dailyCostCurrency =
      destination.avg_daily_budget_currency ?? destination.avg_daily_cost_currency ?? 'USD';
    const dailyCostUsd = destination.avg_daily_budget_usd ?? destination.avg_daily_cost_usd;
    fallbackReasons.push({
      key: 'fallback:cost',
      label: FALLBACK_REASON_LABELS.avg_daily_cost,
      value:
        dailyCostUsd === undefined || dailyCostUsd === null
          ? 0.6
          : dailyCostUsd < 60
            ? 0.85
            : dailyCostUsd < 140
              ? 0.68
              : 0.52,
      note:
        typeof dailyCost === 'number'
          ? `${formatDailyCost(dailyCost, dailyCostCurrency)}/день`
          : undefined,
    });
  }

  const uniqueReasons = [...factorReasons, ...tagReasons, ...fallbackReasons].filter(
    (reason, index, reasons) => reasons.findIndex((item) => item.label === reason.label) === index
  );

  if (uniqueReasons.length === 0) {
    return [
      {
        key: 'fallback:score',
        label: 'Общая совместимость',
        value: destination.score,
      },
    ];
  }

  return uniqueReasons.slice(0, 4);
};

const ValidationBlock = ({
  data,
  destination,
  isLoading,
  isError,
}: {
  data?: DestinationValidationResponse;
  destination: ScoredDestination;
  isLoading: boolean;
  isError: boolean;
}) => {
  if (isLoading) {
    return (
      <div className="flex h-[355.88px] flex-col items-stretch gap-0.5">
        <div className="h-full animate-pulse rounded-t-[24px] bg-[hsl(var(--surface-muted))]" />
        {[0, 1, 2, 3].map((key) => (
          <div key={key} className="h-full animate-pulse bg-[hsl(var(--surface-muted))]" />
        ))}
        <div className="h-full animate-pulse rounded-b-[24px] bg-[hsl(var(--surface-muted))]" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-3 text-[13px] font-bold text-amber-700 dark:text-amber-300">
        Проверка временно недоступна
      </div>
    );
  }

  const warningByType = new Map(data.warnings.map((warning) => [warning.type, warning]));
  const languageStatus = statusFromScore(destination.score_breakdown.language_match);
  const validationDailyCost =
    typeof data.info.avg_daily_cost === 'number' ? data.info.avg_daily_cost : undefined;
  const validationCurrency =
    typeof data.info.display_currency === 'string' ? data.info.display_currency : undefined;
  const dailyCost =
    validationDailyCost ??
    destination.avg_daily_budget ??
    destination.avg_daily_cost ??
    destination.avg_daily_cost_usd;
  const dailyCostCurrency =
    validationCurrency ??
    destination.avg_daily_budget_currency ??
    destination.avg_daily_cost_currency ??
    'USD';
  const rows = [
    {
      key: 'visa',
      label: 'Виза',
      status: statusFromWarning(warningByType.get('visa')),
      warning: warningByType.get('visa'),
      value: formatVisa(data.info.visa_type),
    },
    {
      key: 'season',
      label: 'Сезон',
      status: statusFromWarning(warningByType.get('season')),
      warning: warningByType.get('season'),
      value: formatPercent(data.info.season_score),
    },
    {
      key: 'budget',
      label: 'Бюджет',
      status: statusFromWarning(warningByType.get('budget')),
      warning: warningByType.get('budget'),
      value:
        typeof dailyCost === 'number'
          ? `${formatDailyCost(dailyCost, dailyCostCurrency)}/день`
          : 'нет данных',
    },
    {
      key: 'safety',
      label: 'Риск',
      status: statusFromWarning(warningByType.get('safety')),
      warning: warningByType.get('safety'),
      value: formatPercent(data.info.safety_score),
    },
    {
      key: 'language',
      label: 'Язык',
      status: languageStatus,
      warning: undefined,
      value: formatPercent(destination.score_breakdown.language_match),
    },
  ];
  const overallMeta = STATUS_META[getOverallStatus(rows.map((row) => row.status))];
  const OverallIcon = overallMeta.icon;

  return (
    <div className="overflow-hidden rounded-[24px] border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface))]">
      <div className="flex items-center justify-between gap-3 border-b border-[hsl(var(--surface-border))] px-4 py-3.5">
        <div className="min-w-0">
          <p className="text-[11px] font-extrabold uppercase tracking-[0.08em] text-muted-foreground">
            Проверка направления
          </p>
        </div>
        <span
          className={cn(
            'inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-extrabold',
            overallMeta.className
          )}
        >
          <OverallIcon className="h-3.5 w-3.5" />
          {overallMeta.label}
        </span>
      </div>

      <div className="divide-y divide-[hsl(var(--surface-border))] px-4">
        {rows.map((row) => {
          const meta = STATUS_META[row.status];
          const StatusIcon = meta.icon;
          return (
            <button
              key={row.key}
              type="button"
              onClick={() => {
                if (!row.warning) return;
                sendEvent(
                  'validation_warning_expanded',
                  {
                    destination_id: destination.destination_id,
                    warning_type: row.warning.type,
                    severity: row.warning.severity,
                    source: 'destination_detail',
                  },
                  'destination',
                  destination.destination_id
                );
              }}
              className="flex w-full items-center justify-between gap-3 py-3 text-left"
            >
              <div className="min-w-0">
                <p className="text-[10px] font-extrabold uppercase tracking-[0.06em] text-muted-foreground">
                  {row.label}
                </p>
                <p className="mt-0.5 break-words text-[13px] font-extrabold leading-snug text-foreground">
                  {row.value}
                </p>
              </div>
              <span
                className={cn(
                  'inline-flex h-8 shrink-0 items-center gap-1.5 rounded-full border px-2.5 text-[0px]',
                  meta.className
                )}
              >
                <StatusIcon className="h-3.5 w-3.5" />
                <span className="text-[11px] font-extrabold">{meta.label}</span>
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};

const DestinationDetailSkeleton = () => (
  <div className="flex flex-col gap-4">
    <section className="flex items-start gap-4">
      <div className="flex h-16 w-16 shrink-0 animate-pulse items-center justify-center rounded-3xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-muted))]">
        <div className="h-7 w-9 rounded-xl bg-background/70" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="mb-2 h-7 w-[70%] animate-pulse rounded-xl bg-[hsl(var(--surface-muted))]" />
        <div className="h-4 w-28 animate-pulse rounded-lg bg-[hsl(var(--surface-muted))]" />
      </div>
    </section>

    <section className="rounded-2xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface))] p-4">
      <div className="mb-3 h-3 w-28 animate-pulse rounded-lg bg-[hsl(var(--surface-muted))]" />
      <div className="flex flex-col gap-2.5">
        {[0, 1, 2, 3].map((item) => (
          <div key={item} className="flex items-center gap-3">
            <div className="h-4 w-28 shrink-0 animate-pulse rounded-lg bg-[hsl(var(--surface-muted))]" />
            <div className="h-2 flex-1 animate-pulse rounded-full bg-[hsl(var(--surface-muted))]" />
            <div className="h-4 w-16 animate-pulse rounded-lg bg-primary/15" />
          </div>
        ))}
      </div>
    </section>

    <section className="rounded-2xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface))] p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 animate-pulse items-center justify-center rounded-2xl bg-primary/10">
            <CheckCircle2 className="h-4 w-4 text-primary/30" />
          </div>
          <div>
            <div className="mb-2 h-3 w-32 animate-pulse rounded-lg bg-[hsl(var(--surface-muted))]" />
            <div className="h-4 w-40 animate-pulse rounded-lg bg-[hsl(var(--surface-muted))]" />
          </div>
        </div>
        <div className="h-8 w-24 animate-pulse rounded-full bg-primary/10" />
      </div>
      <div className="flex flex-col gap-2">
        {[0, 1, 2].map((item) => (
          <div
            key={item}
            className="flex items-center justify-between gap-3 rounded-2xl border border-[hsl(var(--surface-border))] bg-background/55 px-3 py-3"
          >
            <div className="min-w-0 flex-1">
              <div className="mb-2 h-3 w-20 animate-pulse rounded-lg bg-[hsl(var(--surface-muted))]" />
              <div className="h-4 w-[78%] animate-pulse rounded-lg bg-[hsl(var(--surface-muted))]" />
            </div>
            <div className="h-7 w-20 shrink-0 animate-pulse rounded-full bg-[hsl(var(--surface-muted))]" />
          </div>
        ))}
      </div>
    </section>
  </div>
);

export const DestinationDetailSheet = ({
  destination,
  month,
  recommendationId,
  modelVersion,
  open,
  isLoading = false,
  onClose,
}: DestinationDetailSheetProps) => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const trackedBudgetKeys = useRef<Set<string>>(new Set());
  const trackedValidationKeys = useRef<Set<string>>(new Set());
  const profileCached = queryClient.getQueryData<UserProfileV2>(['profile']);
  const defaultDuration =
    profileCached?.typical_duration_days ??
    TYPICAL_DURATION_MAP[profileCached?.typical_duration ?? 'standard'] ??
    7;
  const defaultTier: 'budget' | 'mid' | 'luxury' = (() => {
    const budgetMaxUsd = profileCached?.budget_max_usd;
    if (budgetMaxUsd !== null && budgetMaxUsd !== undefined) {
      if (budgetMaxUsd < 900) return 'budget';
      if (budgetMaxUsd < 3000 && profileCached?.rest_level === 'luxury') return 'mid';
    }
    if (profileCached?.rest_level === 'economy') return 'budget';
    if (profileCached?.rest_level === 'luxury') return 'luxury';
    return 'mid';
  })();
  const tripParams: TripParams = {
    duration_days: defaultDuration,
    people_count: 2,
    accommodation_tier: defaultTier,
  };

  const currency = profileCached?.preferred_currency ?? 'RUB';
  const budgetPredictionParams = destination
    ? {
        destination_id: destination.destination_id,
        duration_days: tripParams.duration_days,
        people_count: tripParams.people_count,
        travel_month: month,
        accommodation_tier: tripParams.accommodation_tier,
        currency,
        budget_limit_usd: profileCached?.budget_max_usd,
        origin_city_name: profileCached?.origin_city_name,
        origin_lat: profileCached?.origin_lat,
        origin_lng: profileCached?.origin_lng,
      }
    : null;
  const { data: budgetPrediction } = useBudgetPrediction(budgetPredictionParams);
  const budgetPerDayUsd = profileCached?.budget_max_usd
    ? profileCached.budget_max_usd / Math.max(tripParams.duration_days, 1)
    : null;
  const destinationValidationParams = destination
    ? {
        destination_id: destination.destination_id,
        citizenship_code: 'RU',
        travel_month: month,
        budget_per_day_usd: budgetPerDayUsd,
        display_currency: currency,
        duration_days: tripParams.duration_days,
        risk_tolerance: profileCached?.risk_tolerance,
        preferred_language:
          profileCached?.language_comfort?.find((language) => language !== 'any') ?? null,
      }
    : null;
  const {
    data: destinationValidation,
    isLoading: isValidationLoading,
    isError: isValidationError,
  } = useDestinationValidation(destinationValidationParams);

  useEffect(() => {
    if (!open || !destination || !budgetPrediction) return;
    const key = `${destination.destination_id}:${budgetPrediction.duration_days}:${budgetPrediction.people_count}:${budgetPrediction.currency}:${month}`;
    if (trackedBudgetKeys.current.has(key)) return;
    trackedBudgetKeys.current.add(key);
    sendEvent(
      'budget_prediction_viewed',
      {
        recommendation_id: recommendationId,
        model_version: modelVersion,
        destination_id: destination.destination_id,
        duration_days: budgetPrediction.duration_days,
        people_count: budgetPrediction.people_count,
        currency: budgetPrediction.currency,
        travel_month: month,
        total_mid: budgetPrediction.total_mid,
        origin_city_name: budgetPrediction.assumptions?.origin_city_name,
        travel_cost_source: budgetPrediction.assumptions?.travel_cost_source,
      },
      'destination',
      destination.destination_id
    );
  }, [budgetPrediction, destination, modelVersion, month, open, recommendationId]);

  useEffect(() => {
    if (!open || !destination || !destinationValidation) return;
    const key = `${destination.destination_id}:${month}:${budgetPerDayUsd ?? 'none'}`;
    if (trackedValidationKeys.current.has(key)) return;
    trackedValidationKeys.current.add(key);
    sendEvent(
      'validation_viewed',
      {
        recommendation_id: recommendationId,
        model_version: modelVersion,
        destination_id: destination.destination_id,
        travel_month: month,
        warnings_count: destinationValidation.warnings.length,
        warning_types: destinationValidation.warnings.map((warning) => warning.type),
        budget_per_day_usd: budgetPerDayUsd,
      },
      'destination',
      destination.destination_id
    );
  }, [
    budgetPerDayUsd,
    destination,
    destinationValidation,
    modelVersion,
    month,
    open,
    recommendationId,
  ]);

  if (!destination && !isLoading) return null;

  const title = destination
    ? (destination.display_name ?? destination.name_ru ?? localizeDestinationName(destination.name))
    : 'Направление';
  const flag = getCountryFlag(destination?.country_code);
  const topReasons = destination ? getTopReasons(destination) : [];

  const handleCreateTrip = () => {
    if (!destination) return;
    const dates = getSuggestedTripDates(month, tripParams.duration_days);
    const params = new URLSearchParams({
      destination:
        destination.display_name ??
        destination.name_ru ??
        localizeDestinationName(destination.name),
      destination_id: destination.destination_id,
      people_count: String(tripParams.people_count),
      accommodation_tier: tripParams.accommodation_tier,
      currency,
      start_date: dates.startDate,
      end_date: dates.endDate,
    });
    if (profileCached?.origin_city_name)
      params.set('departure_city', profileCached.origin_city_name);
    if (recommendationId) params.set('recommendation_id', recommendationId);
    if (modelVersion) params.set('model_version', modelVersion);
    if (budgetPrediction?.total_mid)
      params.set('budget', String(Math.round(budgetPrediction.total_mid)));
    onClose();
    navigate(`/trips/new?${params.toString()}`);
  };

  return (
    <AdaptiveSheet
      open={open}
      onOpenChange={(nextOpen) => !nextOpen && onClose()}
      title={title}
      description="Совпадение с предпочтениями и проверка направления"
      showHeader={false}
      bodyClassName="px-5 pb-5"
      footer={
        <Button
          className="h-[52px] w-full rounded-2xl text-[15px] font-extrabold"
          disabled={isLoading || !destination}
          onClick={handleCreateTrip}
        >
          <Plane className="h-4 w-4" />
          Создать поездку
        </Button>
      }
    >
      {isLoading ? (
        <DestinationDetailSkeleton />
      ) : destination ? (
        <div className="flex flex-col gap-4">
          <section className="flex items-start gap-4">
            <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-3xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-muted))] text-[34px]">
              {flag}
            </div>
            <div className="min-w-0 flex-1">
              <h2 className="line-clamp-2 text-[24px] font-extrabold leading-tight tracking-tight text-foreground">
                {destination.display_name ??
                  destination.name_ru ??
                  localizeDestinationName(destination.name)}
              </h2>
              <p className="mt-1 text-[13px] font-semibold text-muted-foreground">
                {destination.region}
              </p>
            </div>
          </section>

          <section className="rounded-2xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface))] p-4">
            <p className="mb-3 text-[11px] font-extrabold uppercase tracking-[0.08em] text-muted-foreground">
              Почему подходит
            </p>
            <div className="flex flex-col gap-2.5">
              {topReasons.map((reason) => (
                <div key={reason.key} className="flex items-center gap-3">
                  <span className="w-28 shrink-0 text-[12px] font-bold leading-tight text-foreground">
                    {reason.label}
                  </span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-[hsl(var(--surface-muted))]">
                    <div
                      className="h-full rounded-full bg-primary"
                      style={{ width: `${clampPercent(reason.value)}%` }}
                    />
                  </div>
                  <span className="w-16 text-right text-[12px] font-extrabold text-primary">
                    {reason.note ?? `${clampPercent(reason.value)}%`}
                  </span>
                </div>
              ))}
            </div>
          </section>

          <section>
            <ValidationBlock
              data={destinationValidation}
              destination={destination}
              isLoading={isValidationLoading}
              isError={isValidationError}
            />
          </section>
        </div>
      ) : null}
    </AdaptiveSheet>
  );
};
