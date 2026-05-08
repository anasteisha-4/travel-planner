import { AlertTriangle, CheckCircle2, Gauge, TrendingUp, WalletCards } from 'lucide-react';
import type { BudgetMonitoringStatus } from '../model/useTripAnalytics';

type BudgetMonitorCardData = {
  risk_status: string;
  budget_usage_projected_pct: number | null;
  projected_final_mid: number;
  budget_gap_mid: number | null;
  current_spent: number;
  remaining_mid: number;
  locked_fixed_costs: number;
  used_ml_model: boolean;
  category_contributions: Array<{
    category: string;
    remaining_mid: number;
  }>;
};

type BudgetMonitoringCardProps = {
  budget: number | null;
  budgetMonitoringStatus: BudgetMonitoringStatus | null;
  burnRatePerDay: number;
  currency: string;
  elapsedDays: number;
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
    description: 'Темп расходов ниже бюджета',
    icon: CheckCircle2,
    tone: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
    bar: 'bg-emerald-500',
  },
  on_track: {
    badge: 'По плану',
    description: 'Прогноз близок к лимиту',
    icon: Gauge,
    tone: 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300',
    bar: 'bg-amber-400',
  },
  risk: {
    badge: 'Риск перерасхода',
    description: 'Текущий темп ведет выше бюджета',
    icon: AlertTriangle,
    tone: 'border-orange-500/30 bg-orange-500/10 text-orange-700 dark:text-orange-300',
    bar: 'bg-orange-500',
  },
  over_budget: {
    badge: 'Бюджет превышен',
    description: 'Фактические расходы уже выше лимита',
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
  elapsedDays,
  monitor,
  plannedDailyBudget,
  projectedBudgetDiff,
  projectedBudgetPct,
  projectedFinalSpend,
  remainingDays,
  totalSpent,
}: BudgetMonitoringCardProps) => {
  if (
    !monitor &&
    (budget === null ||
      budget <= 0 ||
      budgetMonitoringStatus === null ||
      projectedBudgetPct === null)
  ) {
    return (
      <div className="trip-info-card">
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-[hsl(var(--surface-muted))] text-muted-foreground">
            <WalletCards className="h-5 w-5" />
          </div>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
              Контроль бюджета
            </p>
            <p className="mt-1 text-[15px] font-bold leading-snug text-stone-900 dark:text-white">
              Бюджет не задан
            </p>
            <p className="mt-1 text-[13px] leading-relaxed text-stone-500 dark:text-stone-400">
              Добавьте лимит поездки, чтобы видеть прогноз расходов во время путешествия
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
  const progressPct = Math.min(Math.max(effectiveProjectedPct ?? 0, 0), 1);

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
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
            Контроль бюджета
          </p>
          <p className="mt-1 text-[13px] font-medium text-stone-500 dark:text-stone-400">
            {isForecastOnly ? 'Прогноз без лимита поездки' : meta.description}
          </p>
        </div>
        <span
          className={`flex min-h-8 shrink-0 items-center gap-1.5 rounded-full border px-3 text-[11px] font-bold ${meta.tone}`}
        >
          <Icon className="h-3.5 w-3.5" />
          {isForecastOnly ? 'Прогноз' : meta.badge}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-2xl bg-[hsl(var(--surface-muted))] px-3 py-3">
          <p className="text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
            Потрачено
          </p>
          <p className="mt-1 text-[22px] font-extrabold leading-none tracking-tight text-stone-900 dark:text-white">
            {fmt(effectiveSpent)}
          </p>
          <p className="mt-1 text-[12px] font-semibold text-stone-400 dark:text-stone-500">
            {currency}
          </p>
        </div>
        <div className="rounded-2xl bg-[hsl(var(--surface-muted))] px-3 py-3">
          <p className="text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
            Прогноз
          </p>
          <p className="mt-1 text-[22px] font-extrabold leading-none tracking-tight text-stone-900 dark:text-white">
            {fmt(effectiveProjectedFinal)}
          </p>
          <p className="mt-1 text-[12px] font-semibold text-stone-400 dark:text-stone-500">
            {currency}
          </p>
        </div>
      </div>

      <div className="mt-4">
        <div className="mb-2 flex items-center justify-between text-[12px] font-semibold">
          <span className="text-stone-500 dark:text-stone-400">
            {effectiveProjectedPct != null ? `${Math.round(effectiveProjectedPct * 100)}% от бюджета` : 'Лимит не задан'}
          </span>
          {effectiveBudgetGap != null && (
            <span
              className={
                effectiveBudgetGap >= 0
                  ? 'text-emerald-600 dark:text-emerald-400'
                  : 'text-red-600 dark:text-red-400'
              }
            >
              {effectiveBudgetGap >= 0 ? 'Запас' : 'Перерасход'} {fmt(Math.abs(effectiveBudgetGap))}{' '}
              {currency}
            </span>
          )}
        </div>
        <div className="h-2.5 overflow-hidden rounded-full bg-[hsl(var(--surface-muted))]">
          <div
            className={`h-full rounded-full transition-all ${meta.bar}`}
            style={{ width: `${Math.round(progressPct * 100)}%` }}
          />
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 border-t border-[hsl(var(--surface-border))] pt-4">
        <div className="flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-blue-500 dark:text-blue-400" />
          <div>
            <p className="text-[11px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
              В день
            </p>
            <p className="text-[14px] font-bold text-stone-800 dark:text-stone-200">
              {fmt(burnRatePerDay)} {currency}
            </p>
          </div>
        </div>
        <div>
          <p className="text-[11px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
            Осталось
          </p>
          <p className="text-[14px] font-bold text-stone-800 dark:text-stone-200">
            {remainingDays} дн. · прошло {elapsedDays}
          </p>
        </div>
      </div>

      {plannedDailyBudget !== null && (
        <div className="mt-3 rounded-2xl bg-[hsl(var(--surface-muted))] px-3 py-3">
          <p className="text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
            План направления
          </p>
          <p className="mt-1 text-[15px] font-extrabold leading-snug text-stone-900 dark:text-white">
            {fmt(plannedDailyBudget)} {currency}/день
          </p>
          <p className="mt-1 text-[12px] leading-snug text-stone-500 dark:text-stone-400">
            Отель считается по комнатам, не линейно по людям
          </p>
        </div>
      )}

      {monitor && (
        <div className="mt-3 rounded-2xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-muted))] px-3 py-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
                ML-прогноз
              </p>
              <p className="mt-1 text-[14px] font-bold text-stone-900 dark:text-white">
                Осталось {fmt(monitor.remaining_mid)} {currency}
              </p>
            </div>
            <span className="shrink-0 rounded-full border border-[hsl(var(--surface-border))] px-2.5 py-1 text-[10px] font-bold text-stone-500 dark:text-stone-300">
              {monitor.used_ml_model ? 'модель' : 'fallback'}
            </span>
          </div>
          <p className="mt-2 text-[12px] leading-snug text-stone-500 dark:text-stone-400">
            Уже оплачено разово: {fmt(monitor.locked_fixed_costs)} {currency}. Прогноз не повторяет
            эти расходы и отдельно оценивает ежедневные траты.
          </p>
          <div className="mt-3 flex flex-col gap-1.5">
            {monitor.category_contributions.slice(0, 3).map((item) => (
              <div key={item.category} className="flex items-center justify-between gap-2 text-[12px]">
                <span className="font-semibold text-stone-500 dark:text-stone-400">
                  {item.category}
                </span>
                <span className="font-bold text-stone-800 dark:text-stone-200">
                  +{fmt(item.remaining_mid)} {currency}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
