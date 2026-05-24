import { sendEvent } from '@/shared/api';
import { useHapticFeedback } from '@/shared/lib/useHapticFeedback';
import { AlertTriangle, CheckCircle2, Loader2, RotateCcw, ShieldAlert } from 'lucide-react';
import { useEffect, useRef } from 'react';
import type { DestinationValidationStatus, DestinationValidationWarning } from '../model/types';
import { useDestinationValidation } from '../model/useDestinationValidation';

type Props = {
  destinationId: string | null;
  travelMonth: number;
  budgetPerDayUsd?: number | null;
  budgetUnlimited?: boolean;
  citizenshipCode?: string | null;
  durationDays?: number | null;
  riskTolerance?: number | null;
  preferredLanguage?: string | null;
  className?: string;
};

const STATUS_META: Record<
  DestinationValidationStatus,
  { label: string; classes: string; icon: typeof CheckCircle2 }
> = {
  suitable: {
    label: 'Подходит',
    classes: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
    icon: CheckCircle2,
  },
  caution: {
    label: 'Есть ограничения',
    classes: 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300',
    icon: AlertTriangle,
  },
  not_recommended: {
    label: 'Не рекомендуется',
    classes: 'border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-300',
    icon: ShieldAlert,
  },
};

const statusFromWarning = (warning?: DestinationValidationWarning): DestinationValidationStatus => {
  if (!warning) return 'suitable';
  if (warning.severity === 'high') return 'not_recommended';
  return 'caution';
};

const getOverallStatus = (
  warnings: DestinationValidationWarning[]
): DestinationValidationStatus => {
  if (warnings.some((warning) => warning.severity === 'high')) return 'not_recommended';
  if (warnings.length > 0) return 'caution';
  return 'suitable';
};

const FACTORS = [
  { key: 'visa', label: 'Виза' },
  { key: 'season', label: 'Сезон' },
  { key: 'budget', label: 'Бюджет' },
  { key: 'safety', label: 'Риск' },
];

export const DestinationValidationCompact = ({
  destinationId,
  travelMonth,
  budgetPerDayUsd,
  budgetUnlimited = false,
  citizenshipCode = 'RU',
  durationDays,
  riskTolerance,
  preferredLanguage,
  className = '',
}: Props) => {
  const { play } = useHapticFeedback();
  const trackedKeys = useRef<Set<string>>(new Set());
  const { data, isFetching, isLoading, isError, refetch } = useDestinationValidation(
    destinationId
      ? {
          destination_id: destinationId,
          citizenship_code: citizenshipCode ?? 'RU',
          travel_month: travelMonth,
          budget_per_day_usd: budgetPerDayUsd ?? null,
          duration_days: durationDays ?? null,
          risk_tolerance: riskTolerance ?? null,
          preferred_language: preferredLanguage === 'any' ? null : (preferredLanguage ?? null),
        }
      : null
  );

  useEffect(() => {
    if (!destinationId || !data) return;
    const key = [
      destinationId,
      travelMonth,
      budgetUnlimited ? 'unlimited' : (budgetPerDayUsd ?? 'none'),
      citizenshipCode ?? 'RU',
      durationDays ?? 'duration-none',
      riskTolerance ?? 'risk-none',
      preferredLanguage ?? 'lang-none',
    ].join(':');
    if (trackedKeys.current.has(key)) return;
    trackedKeys.current.add(key);
    sendEvent(
      'validation_viewed',
      {
        destination_id: destinationId,
        travel_month: travelMonth,
        budget_per_day_usd: budgetPerDayUsd ?? null,
        budget_unlimited: budgetUnlimited,
        citizenship_code: citizenshipCode ?? 'RU',
        duration_days: durationDays ?? null,
        risk_tolerance: riskTolerance ?? null,
        preferred_language: preferredLanguage ?? null,
        warnings_count: data.warnings.length,
        warning_types: data.warnings.map((warning) => warning.type),
        source: 'trip_form',
      },
      'destination',
      destinationId
    );
  }, [
    budgetPerDayUsd,
    budgetUnlimited,
    data,
    destinationId,
    citizenshipCode,
    durationDays,
    preferredLanguage,
    riskTolerance,
    travelMonth,
  ]);

  if (!destinationId) {
    return (
      <div
        className={`h-[112px] rounded-2xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface))] p-3 transition-[opacity,transform,background-color,border-color] duration-300 ease-out ${className}`}
      >
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-[12px] font-extrabold uppercase tracking-[0.06em] text-stone-400">
              Проверка направления
            </p>
            <p className="mt-0.5 text-[13px] font-bold text-stone-900 dark:text-white">
              Для проверки выберите направление из каталога
            </p>
          </div>
        </div>

        <div className="mt-3 grid grid-cols-4 gap-1.5">
          {FACTORS.map((factor) => (
            <div
              key={factor.key}
              className="truncate rounded-xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-muted))] px-2 py-1.5 text-center text-[11px] font-bold text-muted-foreground"
            >
              {factor.label}
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (isLoading || (isFetching && !data)) {
    return (
      <div
        className={`h-[112px] rounded-2xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface))] p-3 transition-[opacity,transform,background-color,border-color] duration-300 ease-out ${className}`}
      >
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-[12px] font-extrabold uppercase tracking-[0.06em] text-stone-400">
              Проверка направления
            </p>
          </div>
          <span className="inline-flex h-8 shrink-0 items-center gap-1.5 rounded-full border border-primary/25 bg-primary/10 px-2.5 text-[11px] font-extrabold text-primary">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Проверка
          </span>
        </div>
        <div className="mt-3 grid grid-cols-4 gap-1.5">
          {[0, 1, 2, 3].map((item) => (
            <div
              key={item}
              className="h-[30.5px] truncate rounded-xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-muted))] px-2 py-1.5 text-center text-[11px] font-bold text-muted-foreground"
            />
          ))}
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div
        className={`h-[112px] rounded-2xl border border-red-500/25 bg-red-500/10 p-3 transition-[opacity,transform,background-color,border-color] duration-300 ease-out ${className}`}
      >
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-[12px] font-extrabold uppercase tracking-[0.06em] text-red-700 dark:text-red-300">
              Проверка направления
            </p>
            <p className="mt-0.5 text-[13px] font-bold text-red-700 dark:text-red-200">
              Проверка временно недоступна
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              play('nudge');
              void refetch();
            }}
            className="inline-flex h-8 shrink-0 items-center gap-1.5 rounded-full border border-red-500/25 bg-background/70 px-2.5 text-[11px] font-extrabold text-red-600 dark:text-red-300"
            aria-label="Повторить проверку"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Повторить
          </button>
        </div>

        <div className="mt-3 grid grid-cols-4 gap-1.5">
          {FACTORS.map((factor) => (
            <div
              key={factor.key}
              className="truncate rounded-xl border border-red-500/20 bg-red-500/10 px-2 py-1.5 text-center text-[11px] font-bold text-red-700 dark:text-red-200"
            >
              {factor.label}
            </div>
          ))}
        </div>
      </div>
    );
  }

  const warningsByType = new Map(data.warnings.map((warning) => [warning.type, warning]));
  const missingBudget =
    !budgetUnlimited && (budgetPerDayUsd === null || budgetPerDayUsd === undefined);
  const overallStatus =
    missingBudget && data.warnings.length === 0 ? 'caution' : getOverallStatus(data.warnings);
  const overallMeta = STATUS_META[overallStatus];
  const OverallIcon = overallMeta.icon;

  return (
    <div
      className={`h-[112px] rounded-2xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface))] p-3 transition-[opacity,transform,background-color,border-color] duration-300 ease-out ${className}`}
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-[12px] font-extrabold uppercase tracking-[0.06em] text-stone-400">
            Обновляем проверку
          </p>
        </div>
        <span
          className={`inline-flex h-8 shrink-0 items-center gap-1.5 rounded-full border px-2.5 text-[11px] font-extrabold ${overallMeta.classes}`}
        >
          <OverallIcon className="h-3.5 w-3.5" />
          {overallMeta.label}
        </span>
      </div>

      <div className="mt-3 grid grid-cols-4 gap-1.5">
        {FACTORS.map((factor) => {
          const warning = warningsByType.get(factor.key);
          const status =
            factor.key === 'budget' && missingBudget ? 'caution' : statusFromWarning(warning);
          const meta = STATUS_META[status];
          const title =
            factor.key === 'budget' && budgetUnlimited
              ? 'Бюджет без лимита'
              : factor.key === 'budget' && missingBudget
                ? 'Бюджет не проверен: нужен лимит поездки'
                : (warningsByType.get(factor.key)?.message ?? meta.label);
          return (
            <button
              key={factor.key}
              type="button"
              onClick={() => {
                if (!warning || !destinationId) return;
                sendEvent(
                  'validation_warning_expanded',
                  {
                    destination_id: destinationId,
                    warning_type: warning.type,
                    severity: warning.severity,
                    source: 'trip_form',
                  },
                  'destination',
                  destinationId
                );
              }}
              className={`truncate rounded-xl border px-2 py-1.5 text-center text-[11px] font-bold ${meta.classes}`}
              title={title}
            >
              {factor.label}
            </button>
          );
        })}
      </div>
    </div>
  );
};
