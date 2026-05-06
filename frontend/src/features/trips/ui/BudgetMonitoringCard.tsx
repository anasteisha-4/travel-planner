import type { BudgetMonitoringStatus } from '../model/useTripAnalytics';
import { AlertTriangle, CheckCircle2, Gauge, TrendingUp, WalletCards } from 'lucide-react';

type BudgetMonitoringCardProps = {
  budget: number | null;
  budgetMonitoringStatus: BudgetMonitoringStatus | null;
  burnRatePerDay: number;
  currency: string;
  elapsedDays: number;
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
  projectedBudgetDiff,
  projectedBudgetPct,
  projectedFinalSpend,
  remainingDays,
  totalSpent,
}: BudgetMonitoringCardProps) => {
  if (budget === null || budget <= 0 || budgetMonitoringStatus === null || projectedBudgetPct === null) {
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

  const meta = STATUS_META[budgetMonitoringStatus];
  const Icon = meta.icon;
  const progressPct = Math.min(Math.max(projectedBudgetPct, 0), 1);
  const remainingProjected = projectedBudgetDiff ?? 0;

  return (
    <div
      className={`trip-info-card ${
        budgetMonitoringStatus === 'risk'
          ? 'border-orange-200 dark:border-orange-900/50'
          : budgetMonitoringStatus === 'over_budget'
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
            {meta.description}
          </p>
        </div>
        <span className={`flex min-h-8 shrink-0 items-center gap-1.5 rounded-full border px-3 text-[11px] font-bold ${meta.tone}`}>
          <Icon className="h-3.5 w-3.5" />
          {meta.badge}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-2xl bg-[hsl(var(--surface-muted))] px-3 py-3">
          <p className="text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
            Потрачено
          </p>
          <p className="mt-1 text-[22px] font-extrabold leading-none tracking-tight text-stone-900 dark:text-white">
            {fmt(totalSpent)}
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
            {fmt(projectedFinalSpend)}
          </p>
          <p className="mt-1 text-[12px] font-semibold text-stone-400 dark:text-stone-500">
            {currency}
          </p>
        </div>
      </div>

      <div className="mt-4">
        <div className="mb-2 flex items-center justify-between text-[12px] font-semibold">
          <span className="text-stone-500 dark:text-stone-400">
            {Math.round(projectedBudgetPct * 100)}% от бюджета
          </span>
          <span
            className={
              remainingProjected >= 0
                ? 'text-emerald-600 dark:text-emerald-400'
                : 'text-red-600 dark:text-red-400'
            }
          >
            {remainingProjected >= 0 ? 'Запас' : 'Перерасход'} {fmt(Math.abs(remainingProjected))} {currency}
          </span>
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
    </div>
  );
};
