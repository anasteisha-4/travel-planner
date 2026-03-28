import type { ConvertedExpenseSummary, ExpenseCategory } from '@/entities/expense';
import { AlertTriangle, Car, Coffee, Home, MoreHorizontal, Music, ShoppingBag } from 'lucide-react';

type ExpenseSummaryProps = {
  summary: ConvertedExpenseSummary;
  budget: number | null;
};

const CATEGORY_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  food: {
    bg: 'bg-amber-100 dark:bg-amber-900/30',
    text: 'text-amber-600 dark:text-amber-400',
    border: 'border-amber-600 dark:border-amber-400',
  },
  transport: {
    bg: 'bg-blue-100 dark:bg-blue-900/30',
    text: 'text-blue-600 dark:text-blue-400',
    border: 'border-blue-600 dark:border-blue-400',
  },
  housing: {
    bg: 'bg-sky-100 dark:bg-sky-900/30',
    text: 'text-sky-600 dark:text-sky-400',
    border: 'border-sky-600 dark:border-sky-400',
  },
  entertainment: {
    bg: 'bg-violet-100 dark:bg-violet-900/30',
    text: 'text-violet-600 dark:text-violet-400',
    border: 'border-violet-600 dark:border-violet-400',
  },
  shopping: {
    bg: 'bg-emerald-100 dark:bg-emerald-900/30',
    text: 'text-emerald-600 dark:text-emerald-400',
    border: 'border-emerald-600 dark:border-emerald-400',
  },
  other: {
    bg: 'bg-stone-100 dark:bg-stone-800',
    text: 'text-stone-500 dark:text-stone-400',
    border: 'border-stone-500 dark:border-stone-400',
  },
};

const CATEGORY_ICONS = {
  food: Coffee,
  transport: Car,
  housing: Home,
  entertainment: Music,
  shopping: ShoppingBag,
  other: MoreHorizontal,
};

const RING_R = 54;
const RING_SIZE = 128;
const CIRCUMFERENCE = 2 * Math.PI * RING_R;

const getRingColor = (pct: number, isOver: boolean): string => {
  if (isOver) return '#EF4444';
  if (pct >= 0.9) return '#F97316';
  if (pct >= 0.5) return '#F59E0B';
  return '#22C55E';
};

const fmtBudgetShort = (v: number): string => {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 10_000) return `${Math.round(v / 1_000)}K`;
  return v.toLocaleString('ru-RU');
};

export const ExpenseSummary = ({ summary, budget }: ExpenseSummaryProps) => {
  const total = Number(summary.total);
  const currency = summary.target_currency;
  const remaining = budget ? budget - total : null;
  const pct = budget && budget > 0 ? total / budget : 0;
  const isOverBudget = pct > 1;
  const hasExpenses = total > 0;

  const ringColor = getRingColor(pct, isOverBudget);
  const clampedPct = Math.min(pct, 1);
  const dashOffset = CIRCUMFERENCE * (1 - (hasExpenses ? clampedPct : 0));
  const percentDisplay = budget && budget > 0 ? Math.round(pct * 100) : 0;

  const categoryEntries = Object.entries(summary.by_category)
    .map(([cat, val]) => ({ category: cat, amount: Number(val) }))
    .filter(({ amount }) => amount > 0)
    .sort((a, b) => b.amount - a.amount);

  const fmt = (v: number) =>
    v.toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 0 });

  const cx = RING_SIZE / 2;
  const cy = RING_SIZE / 2;

  return (
    <div
      className={`trip-info-card ${
        isOverBudget
          ? 'border-red-200 shadow-[0_1px_3px_rgba(239,68,68,0.1),0_4px_16px_rgba(239,68,68,0.08)] dark:border-red-900/50'
          : ''
      }`}
    >
      {/* Header */}
      <div className="mb-3 flex items-center gap-2">
        <span className="text-[11px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
          Бюджет
        </span>
        {isOverBudget && (
          <span className="rounded-full border border-red-200 bg-red-50 px-2.5 py-0.5 text-[11px] font-semibold text-red-600 dark:border-red-900/60 dark:bg-red-900/20 dark:text-red-400">
            Превышен
          </span>
        )}
      </div>

      {/* Ring + stats */}
      <div className="flex items-center gap-4">
        <div className="shrink-0">
          <svg width={RING_SIZE} height={RING_SIZE} viewBox={`0 0 ${RING_SIZE} ${RING_SIZE}`}>
            <circle
              cx={cx}
              cy={cy}
              r={RING_R}
              fill="none"
              stroke="rgba(28,25,23,0.07)"
              strokeWidth="10"
            />
            {budget && budget > 0 && (
              <circle
                cx={cx}
                cy={cy}
                r={RING_R}
                fill="none"
                stroke={ringColor}
                strokeWidth="10"
                strokeLinecap="round"
                strokeDasharray={CIRCUMFERENCE}
                strokeDashoffset={dashOffset}
                transform={`rotate(-90 ${cx} ${cy})`}
                style={{ transition: 'stroke-dashoffset 0.5s ease, stroke 0.3s ease' }}
              />
            )}
            {budget && budget > 0 ? (
              <>
                <text
                  x={cx}
                  y={cy - 8}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize="18"
                  fontWeight="800"
                  fontFamily="Manrope, sans-serif"
                  fill={hasExpenses ? (isOverBudget ? '#EF4444' : '#1C1917') : '#A8A29E'}
                >
                  {percentDisplay}%
                </text>
                <text
                  x={cx}
                  y={cy + 11}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize="10"
                  fontWeight="500"
                  fontFamily="Manrope, sans-serif"
                  fill="#A8A29E"
                >
                  {`из ${fmtBudgetShort(budget)}`}
                </text>
              </>
            ) : (
              <text
                x={cx}
                y={cy}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize="20"
                fontWeight="800"
                fontFamily="Manrope, sans-serif"
                fill="#A8A29E"
              >
                0
              </text>
            )}
          </svg>
        </div>

        <div className="flex flex-1 flex-col gap-3">
          <div>
            <p className="mb-0.5 text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
              Потрачено
            </p>
            <p
              className={`text-[26px] font-bold leading-none ${
                hasExpenses
                  ? 'text-stone-900 dark:text-white'
                  : 'text-stone-400 dark:text-stone-600'
              }`}
            >
              {fmt(total)}
            </p>
            <p className="text-[12px] font-medium text-stone-400 dark:text-stone-500">{currency}</p>
          </div>

          {budget !== null && remaining !== null && (
            <>
              <div className="h-px bg-stone-100 dark:bg-stone-700/50" />
              <div>
                <p className="mb-0.5 text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
                  {isOverBudget ? 'Перерасход' : 'Доступно'}
                </p>
                <p
                  className={`text-[22px] font-bold leading-none ${
                    isOverBudget
                      ? 'text-red-500 dark:text-red-400'
                      : 'text-emerald-600 dark:text-emerald-400'
                  }`}
                >
                  {fmt(Math.abs(remaining))}
                </p>
                <p className="text-[12px] font-medium text-stone-400 dark:text-stone-500">
                  {currency}
                </p>
              </div>
            </>
          )}
        </div>
      </div>

      {summary.has_conversion_errors && (
        <div className="mt-3 flex items-center gap-1.5 rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-600 dark:bg-amber-900/20 dark:text-amber-400">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
          Некоторые валюты не удалось сконвертировать
        </div>
      )}

      {categoryEntries.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {categoryEntries.map(({ category, amount }) => {
            const colors = CATEGORY_COLORS[category] ?? CATEGORY_COLORS['other'];
            const Icon = CATEGORY_ICONS[category as ExpenseCategory] ?? MoreHorizontal;
            return (
              <div
                key={category}
                className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[11px] font-semibold ${colors.bg} ${colors.text} border ${colors.border}`}
              >
                <Icon className="h-3 w-3" strokeWidth={2} />
                <span>
                  {fmt(amount)} {currency}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
