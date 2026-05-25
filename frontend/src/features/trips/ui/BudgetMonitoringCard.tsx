import { useHapticFeedback } from '@/shared/lib/useHapticFeedback';
import cn from 'classnames';
import {
  AlertTriangle,
  BedDouble,
  Bus,
  CheckCircle2,
  ChevronDown,
  Gauge,
  Loader2,
  MoreHorizontal,
  RotateCcw,
  ShoppingBag,
  Sigma,
  Ticket,
  TrendingUp,
  Utensils,
  WalletCards,
} from 'lucide-react';
import { useState } from 'react';
import type { BudgetMonitoringStatus } from '../model/useTripAnalytics';

type BudgetMonitorCardData = {
  risk_status: string;
  budget_usage_projected_pct: number | null;
  projected_final_min: number;
  projected_final_mid: number;
  projected_final_max: number;
  budget_gap_mid: number | null;
  current_spent: number;
  planning_spent: number;
  recurring_spent: number;
  remaining_mid: number;
  locked_fixed_costs: number;
  used_ml_model: boolean;
  assumptions?: Record<string, unknown>;
  category_contributions: Array<{
    category: string;
    spent: number;
    remaining_mid: number;
    kind?: string;
  }>;
};

type BudgetMonitoringCardProps = {
  budget: number | null;
  budgetMonitoringStatus: BudgetMonitoringStatus | null;
  burnRatePerDay: number;
  currency: string;
  daysUntilStart?: number;
  elapsedDays: number;
  hasError?: boolean;
  hasForecastInput?: boolean;
  isUpdating?: boolean;
  onRetry?: () => void;
  monitor?: BudgetMonitorCardData;
  peopleCount: number;
  plannedDailyBudget: number | null;
  projectedBudgetDiff: number | null;
  projectedBudgetPct: number | null;
  projectedFinalSpend: number;
  remainingDays: number;
  totalSpent: number;
};

const fmt = (value: number): string =>
  value.toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 0 });

const formatMoney = (value: number, currency: string): string => `${fmt(value)} ${currency}`;

const CATEGORY_META: Record<
  string,
  {
    label: string;
    icon: typeof Utensils;
    accent: string;
  }
> = {
  food: {
    label: 'Еда',
    icon: Utensils,
    accent: 'bg-amber-500',
  },
  meals: {
    label: 'Еда',
    icon: Utensils,
    accent: 'bg-amber-500',
  },
  transport: {
    label: 'Транспорт',
    icon: Bus,
    accent: 'bg-sky-500',
  },
  housing: {
    label: 'Жильё',
    icon: BedDouble,
    accent: 'bg-indigo-500',
  },
  accommodation: {
    label: 'Жильё',
    icon: BedDouble,
    accent: 'bg-indigo-500',
  },
  entertainment: {
    label: 'Развлечения',
    icon: Ticket,
    accent: 'bg-rose-500',
  },
  activities: {
    label: 'Развлечения',
    icon: Ticket,
    accent: 'bg-rose-500',
  },
  shopping: {
    label: 'Покупки',
    icon: ShoppingBag,
    accent: 'bg-emerald-500',
  },
  other: {
    label: 'Другое',
    icon: MoreHorizontal,
    accent: 'bg-stone-400',
  },
};

const getCategoryMeta = (category: string) =>
  CATEGORY_META[category] ?? {
    label: category,
    icon: MoreHorizontal,
    accent: 'bg-stone-400',
  };

const formatDays = (count: number): string => {
  const lastDigit = Math.abs(count) % 10;
  const lastTwoDigits = Math.abs(count) % 100;

  if (lastTwoDigits >= 11 && lastTwoDigits <= 14) {
    return 'дней';
  }

  if (lastDigit === 1) {
    return 'день';
  }

  if (lastDigit >= 2 && lastDigit <= 4) {
    return 'дня';
  }

  return 'дней';
};

const STATUS_META: Record<
  BudgetMonitoringStatus,
  {
    badge: string;
    description: string;
    icon: typeof CheckCircle2;
    tone: string;
    bar: string;
  }
> = {
  under_budget: {
    badge: 'В рамках',
    description: 'Прогноз в рамках бюджета',
    icon: CheckCircle2,
    tone: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
    bar: 'bg-emerald-500',
  },
  on_track: {
    badge: 'В рамках',
    description: 'Прогноз в рамках бюджета',
    icon: Gauge,
    tone: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
    bar: 'bg-emerald-500',
  },
  risk: {
    badge: 'Почти лимит',
    description: 'Прогноз почти исчерпывает бюджет',
    icon: AlertTriangle,
    tone: 'border-orange-500/30 bg-orange-500/10 text-orange-700 dark:text-orange-300',
    bar: 'bg-orange-500',
  },
  over_budget: {
    badge: 'Превышен',
    description: 'Траты выше бюджета',
    icon: AlertTriangle,
    tone: 'border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-300',
    bar: 'bg-red-500',
  },
};

export const BudgetMonitoringCard = ({
  budget,
  budgetMonitoringStatus,
  burnRatePerDay,
  currency,
  daysUntilStart = 0,
  elapsedDays,
  hasError = false,
  hasForecastInput = true,
  isUpdating = false,
  monitor,
  onRetry,
  plannedDailyBudget,
  projectedBudgetDiff,
  projectedBudgetPct,
  projectedFinalSpend,
  remainingDays,
  totalSpent,
}: BudgetMonitoringCardProps) => {
  const { play } = useHapticFeedback();
  const [isBreakdownOpen, setIsBreakdownOpen] = useState(false);

  if (hasError) {
    return (
      <div className="trip-info-card border-red-200 dark:border-red-900/50">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-red-500/10 text-red-600 dark:text-red-300">
            {isUpdating ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <AlertTriangle className="h-5 w-5" />
            )}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
              Контроль бюджета
            </p>
            <p className="mt-1 text-[15px] font-bold leading-snug text-stone-900 dark:text-white">
              Не удалось обновить прогноз
            </p>
            <p className="mt-1 text-[12px] leading-snug text-stone-500 dark:text-stone-400">
              Попробуйте запросить расчет еще раз
            </p>
            <button
              type="button"
              onClick={() => {
                play('nudge');
                onRetry?.();
              }}
              disabled={isUpdating}
              className="mt-3 inline-flex min-h-10 items-center gap-2 rounded-2xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-muted))] px-3 text-[13px] font-bold text-stone-800 transition-colors hover:bg-background disabled:cursor-not-allowed disabled:opacity-60 dark:text-stone-100 dark:hover:bg-white/5"
            >
              {isUpdating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RotateCcw className="h-4 w-4" />
              )}
              {isUpdating ? 'Запрашиваю' : 'Перезапросить прогноз'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (isUpdating) {
    return (
      <div className="trip-info-card">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-blue-500/10 text-blue-600 dark:text-blue-300">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
              Контроль бюджета
            </p>
            <p className="mt-1 text-[15px] font-bold leading-snug text-stone-900 dark:text-white">
              Обновляю ИИ-прогноз...
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (
    !hasForecastInput ||
    (!monitor &&
      (budget === null ||
        budget <= 0 ||
        budgetMonitoringStatus === null ||
        projectedBudgetPct === null))
  ) {
    return (
      <div className="trip-info-card">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-[hsl(var(--surface-muted))] text-muted-foreground">
            <WalletCards className="h-5 w-5" />
          </div>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
              Контроль бюджета
            </p>
            <p className="mt-1 text-[15px] font-bold leading-snug text-stone-900 dark:text-white">
              {hasForecastInput ? 'Бюджет не задан' : 'Недостаточно данных'}
            </p>
            <p className="mt-1 text-[13px] leading-relaxed text-stone-500 dark:text-stone-400">
              {hasForecastInput
                ? 'Добавьте лимит поездки, чтобы видеть прогноз расходов'
                : 'Для прогноза нужны расходы или направление из каталога'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  const monitorStatus =
    monitor?.risk_status === 'under_budget' ||
    monitor?.risk_status === 'on_track' ||
    monitor?.risk_status === 'risk' ||
    monitor?.risk_status === 'over_budget'
      ? monitor.risk_status
      : budgetMonitoringStatus;
  const statusForMeta = monitorStatus ?? 'under_budget';
  const meta = STATUS_META[statusForMeta];
  const Icon = meta.icon;
  const isForecastOnly = monitor?.risk_status === 'forecast_only';
  const effectiveProjectedPct = monitor?.budget_usage_projected_pct ?? projectedBudgetPct;
  const effectiveProjectedFinal = monitor?.projected_final_mid ?? projectedFinalSpend;
  const effectiveBudgetGap = monitor?.budget_gap_mid ?? projectedBudgetDiff;
  const effectiveSpent = monitor?.current_spent ?? totalSpent;
  const effectiveBurnRate = monitor
    ? monitor.recurring_spent / Math.max(elapsedDays, 1)
    : burnRatePerDay;
  const isActuallyOverBudget = budget !== null && budget > 0 && effectiveSpent > budget;
  const progressPct = Math.min(Math.max(effectiveProjectedPct ?? 0, 0), 1);

  const preparationSpent = monitor
    ? monitor.planning_spent + monitor.locked_fixed_costs
    : totalSpent;
  const categoryBreakdown = monitor
    ? monitor.category_contributions
        .filter((item) => item.spent > 0 || item.remaining_mid > 0)
        .slice(0, 5)
    : [];
  const categoryRemainingTotal = categoryBreakdown.reduce(
    (sum, item) => sum + Math.max(0, item.remaining_mid),
    0
  );
  const dailyLabel =
    effectiveBurnRate > 0
      ? `${formatMoney(effectiveBurnRate, currency)}/день`
      : 'трат в поездке нет';

  return (
    <div
      className={`trip-info-card ${
        statusForMeta === 'risk'
          ? 'border-orange-200 dark:border-orange-900/50'
          : statusForMeta === 'over_budget'
            ? 'border-red-200 dark:border-red-900/50'
            : ''
      }`}
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
            Контроль бюджета
          </p>
          {isForecastOnly ? null : (
            <div className="mt-1 flex flex-wrap items-center gap-1.5">
              <span className="text-[13px] font-semibold text-stone-600 dark:text-stone-300">
                {isForecastOnly ? 'Прогноз без лимита' : meta.description}
              </span>
            </div>
          )}
        </div>
        <span
          className={`flex min-h-8 shrink-0 items-center gap-1.5 rounded-full border px-2.5 text-[11px] font-bold ${meta.tone}`}
        >
          <Icon className="h-3.5 w-3.5" />
          {isForecastOnly ? 'Прогноз без лимита' : meta.badge}
        </span>
      </div>

      <div className="rounded-2xl bg-[hsl(var(--surface-muted))] px-3.5 py-3">
        <div className="flex items-end justify-between gap-3">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
              Прогноз
            </p>
            <p className="mt-1 text-[26px] font-extrabold leading-none tracking-tight text-stone-900 dark:text-white">
              {fmt(effectiveProjectedFinal)}
            </p>
          </div>
          <div className="pb-0.5 text-right">
            <p className="text-[11px] font-bold text-stone-400 dark:text-stone-500">{currency}</p>
            <p className="mt-1 text-[12px] font-semibold text-stone-500 dark:text-stone-400">
              потрачено {formatMoney(effectiveSpent, currency)}
            </p>
          </div>
        </div>

        <div className="mt-3">
          <div className="mb-2 flex items-center justify-between gap-3 text-[12px] font-semibold">
            <span className="text-stone-500 dark:text-stone-400">
              {effectiveProjectedPct != null
                ? `${Math.round(effectiveProjectedPct * 100)}% от бюджета`
                : 'Лимит не задан'}
            </span>
            {effectiveBudgetGap != null && (
              <span
                className={
                  effectiveBudgetGap >= 0
                    ? 'text-emerald-600 dark:text-emerald-400'
                    : 'text-red-600 dark:text-red-400'
                }
              >
                {effectiveBudgetGap >= 0
                  ? 'Запас'
                  : isActuallyOverBudget
                    ? 'Перерасход'
                    : 'Выше плана'}{' '}
                {formatMoney(Math.abs(effectiveBudgetGap), currency)}
              </span>
            )}
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-background/70 dark:bg-black/20">
            <div
              className={`h-full rounded-full transition-all ${meta.bar}`}
              style={{ width: `${Math.round(progressPct * 100)}%` }}
            />
          </div>
        </div>
      </div>

      {monitor && (
        <div className="mt-3 overflow-hidden rounded-2xl border border-[hsl(var(--surface-border))] bg-background/60 dark:bg-white/[0.03]">
          <button
            type="button"
            onClick={() => {
              play('light');
              setIsBreakdownOpen((value) => !value);
            }}
            className="flex min-h-12 w-full items-center justify-between gap-3 px-3 py-3 text-left active:bg-[hsl(var(--surface-muted))]/70"
            aria-expanded={isBreakdownOpen}
          >
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-300">
                <Sigma className="h-4 w-4" />
              </div>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
                  Ожидаемые дополнительные расходы до конца поездки
                </p>
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              {monitor.used_ml_model && (
                <span className="rounded-full bg-blue-500/10 px-2 py-1 text-[10px] font-bold text-blue-700 dark:text-blue-300">
                  ML
                </span>
              )}
              <ChevronDown
                className={cn(
                  'h-5 w-5 text-stone-400 transition-transform duration-300 dark:text-stone-500',
                  isBreakdownOpen && 'rotate-180'
                )}
              />
            </div>
          </button>

          <div
            className={cn(
              'grid transition-[grid-template-rows,opacity] duration-300 ease-out',
              isBreakdownOpen ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'
            )}
          >
            <div className="min-h-0 overflow-hidden">
              <div className="px-3 pb-3">
                {categoryBreakdown.length > 0 && (
                  <div className="mt-3 rounded-2xl border border-[hsl(var(--surface-border))] px-3 py-3">
                    <div className="mb-2.5 flex items-center justify-between">
                      <p className="text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
                        Примерный бюджет по категориям
                      </p>
                    </div>

                    <div className="flex flex-col gap-2.5">
                      {categoryBreakdown.map((item) => {
                        const itemMeta = getCategoryMeta(item.category);
                        const CategoryIcon = itemMeta.icon;
                        const widthPct =
                          categoryRemainingTotal > 0
                            ? Math.max(
                                8,
                                Math.round(
                                  (Math.max(0, item.remaining_mid) / categoryRemainingTotal) * 100
                                )
                              )
                            : 0;

                        return (
                          <div key={item.category} className="min-w-0">
                            <div className="mb-1.5 flex items-center justify-between gap-2">
                              <div className="flex min-w-0 items-center gap-2">
                                <CategoryIcon className="h-3.5 w-3.5 shrink-0 text-stone-400 dark:text-stone-500" />
                                <span className="truncate text-[12px] font-bold text-stone-700 dark:text-stone-200">
                                  {itemMeta.label}
                                </span>
                              </div>
                              <span className="shrink-0 text-[12px] font-extrabold text-stone-900 dark:text-white">
                                {formatMoney(item.remaining_mid, currency)}
                              </span>
                            </div>
                            <div className="h-1.5 overflow-hidden rounded-full bg-[hsl(var(--surface-muted))]">
                              <div
                                className={`h-full rounded-full ${itemMeta.accent}`}
                                style={{ width: `${widthPct}%` }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="mt-3 grid grid-cols-2 gap-2">
        <div className="rounded-2xl border border-[hsl(var(--surface-border))] px-3 py-2.5">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-blue-500 dark:text-blue-400" />
            <p className="text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
              Ваш темп
            </p>
          </div>
          <p className="mt-1 text-[13px] font-bold text-stone-800 dark:text-stone-200">
            {dailyLabel}
          </p>
        </div>
        <div className="rounded-2xl border border-[hsl(var(--surface-border))] px-3 py-2.5">
          <p className="text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
            Период
          </p>
          <p className="mt-1 text-[13px] font-bold text-stone-800 dark:text-stone-200">
            {daysUntilStart > 0 ? (
              <>
                до поездки {daysUntilStart} {formatDays(daysUntilStart)}
              </>
            ) : (
              <>
                {elapsedDays} {formatDays(elapsedDays)}{' '}
                {elapsedDays % 100 !== 11 && elapsedDays % 10 === 1 ? 'прошел' : 'прошло'} <br />{' '}
                {remainingDays} осталось
              </>
            )}
          </p>
        </div>
      </div>
      <div
        className={cn('mt-3 grid gap-2', {
          'grid-cols-2': plannedDailyBudget !== null && !Number.isNaN(plannedDailyBudget),
          'grid-cols-1': plannedDailyBudget === null || Number.isNaN(plannedDailyBudget),
        })}
      >
        {plannedDailyBudget !== null && !Number.isNaN(plannedDailyBudget) && (
          <div className="h-[79px] rounded-2xl border border-[hsl(var(--surface-border))] px-3 py-2.5">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-blue-500 dark:text-blue-400" />
              <p className="text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
                Прогноз/день
              </p>
            </div>
            <p className="mt-1 text-[13px] font-bold text-stone-800 dark:text-stone-200">
              {formatMoney(plannedDailyBudget, currency)}/день
            </p>
          </div>
        )}
        <div className="h-[79px] rounded-2xl border border-[hsl(var(--surface-border))] px-3 py-2.5">
          <p className="text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
            Разовые траты
          </p>
          <p className="mt-1 text-[13px] font-bold text-stone-800 dark:text-stone-200">
            {formatMoney(preparationSpent, currency)}
          </p>
        </div>
      </div>
    </div>
  );
};
