import type { Expense, ExpenseCategory } from '@/entities/expense';
import { CATEGORY_META } from '@/entities/expense';
import { useHapticFeedback } from '@/shared/lib/useHapticFeedback';
import { CalendarClock, Car, Coffee, Home, MoreHorizontal, Music, ShoppingBag } from 'lucide-react';

type ExpenseListProps = {
  expenses: Expense[];
  onEdit: (expense: Expense) => void;
  readonly?: boolean;
  tripStartDate?: string;
  tripEndDate?: string;
};

const formatDate = (dateStr: string) =>
  new Date(dateStr).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' });

const groupByDate = (expenses: Expense[]) => {
  const groups: Record<string, Expense[]> = {};
  for (const expense of expenses) {
    const key = expense.expense_date ?? 'no-date';
    if (!groups[key]) groups[key] = [];
    groups[key].push(expense);
  }
  return Object.entries(groups).sort(([a], [b]) => b.localeCompare(a));
};

const CATEGORY_STYLES: Record<string, { bg: string; icon: string }> = {
  food: { bg: 'bg-amber-50 dark:bg-amber-900/25', icon: 'text-amber-500 dark:text-amber-400' },
  transport: { bg: 'bg-blue-50 dark:bg-blue-900/25', icon: 'text-blue-500 dark:text-blue-400' },
  housing: { bg: 'bg-sky-50 dark:bg-sky-900/25', icon: 'text-sky-500 dark:text-sky-400' },
  entertainment: {
    bg: 'bg-violet-50 dark:bg-violet-900/25',
    icon: 'text-violet-500 dark:text-violet-400',
  },
  shopping: {
    bg: 'bg-emerald-50 dark:bg-emerald-900/25',
    icon: 'text-emerald-500 dark:text-emerald-400',
  },
  other: { bg: 'bg-stone-100 dark:bg-[hsl(var(--surface-muted))]', icon: 'text-stone-400 dark:text-stone-500' },
};

const CATEGORY_ICONS = {
  food: Coffee,
  transport: Car,
  housing: Home,
  entertainment: Music,
  shopping: ShoppingBag,
  other: MoreHorizontal,
};

const CategoryIcon = ({ category }: { category: ExpenseCategory }) => {
  const styles = CATEGORY_STYLES[category] ?? CATEGORY_STYLES['other'];
  const Icon = CATEGORY_ICONS[category] ?? MoreHorizontal;
  return (
    <div
      className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-[13px] ${styles.bg}`}
    >
      <Icon className={`h-5 w-5 ${styles.icon}`} strokeWidth={1.75} />
    </div>
  );
};

export const ExpenseList = ({ expenses, onEdit, readonly, tripStartDate, tripEndDate }: ExpenseListProps) => {
  const { play } = useHapticFeedback();
  const isPlanningExpense = (expense: Expense) =>
    !!expense.expense_date &&
    !!tripStartDate &&
    !!tripEndDate &&
    (expense.expense_date < tripStartDate || expense.expense_date > tripEndDate);
  if (expenses.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 py-10 text-center">
        <div className="flex h-[72px] w-[72px] items-center justify-center rounded-3xl bg-[hsl(var(--surface-muted))]">
          <svg
            width="28"
            height="28"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#A8A29E"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2" />
            <rect x="9" y="3" width="6" height="4" rx="1" />
            <line x1="9" y1="12" x2="15" y2="12" />
            <line x1="9" y1="16" x2="13" y2="16" />
          </svg>
        </div>
        <div>
          <p className="text-[17px] font-bold text-stone-900 dark:text-white">Расходов пока нет</p>
          <p className="mt-1 text-[13px] text-stone-400 dark:text-stone-500">
            Добавьте первый расход, чтобы отслеживать бюджет поездки
          </p>
        </div>
      </div>
    );
  }

  const groups = groupByDate(expenses);

  return (
    <div className="flex flex-col gap-5">
      {groups.map(([dateKey, items]) => (
        <div key={dateKey}>
          <div className="mb-2 flex items-center gap-3">
            <p className="text-[11px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
              {dateKey === 'no-date' ? 'Без даты' : formatDate(dateKey)}
            </p>
            <div className="h-px flex-1 bg-[hsl(var(--surface-border))]" />
          </div>
          <div className="flex flex-col gap-2">
            {items.map((expense) => {
              const meta = CATEGORY_META[expense.category];
              const planningExpense = isPlanningExpense(expense);
              return (
                <div
                  key={expense.id}
                  className={`flex items-center gap-3 rounded-2xl border px-3 py-3 shadow-[0_1px_4px_rgba(0,0,0,0.05)] transition-all active:scale-[0.99] dark:shadow-none ${
                    planningExpense
                      ? 'border-blue-200/80 bg-blue-50/45 dark:border-blue-900/60 dark:bg-blue-950/20'
                      : 'border-[hsl(var(--surface-border))] bg-[hsl(var(--surface))]'
                  }`}
                  onClick={() => {
                    if (!readonly) {
                      play('nudge');
                      onEdit(expense);
                    }
                  }}
                  role={readonly ? undefined : 'button'}
                  tabIndex={readonly ? undefined : 0}
                  onKeyDown={(e) => {
                    if (!readonly && e.key === 'Enter') {
                      play('nudge');
                      onEdit(expense);
                    }
                  }}
                >
                  <CategoryIcon category={expense.category} />
                  <div className="flex-1 overflow-hidden">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <p className="line-clamp-2 text-[15px] font-bold leading-snug text-stone-900 dark:text-white">
                        {expense.description || meta.label}
                      </p>
                      {planningExpense && (
                        <CalendarClock
                          className="h-3.5 w-3.5 shrink-0 text-blue-500 dark:text-blue-300"
                          aria-label="До поездки"
                        />
                      )}
                    </div>
                    {expense.description && (
                      <p className="text-[12px] font-medium text-stone-400 dark:text-stone-500">
                        {meta.label}
                      </p>
                    )}
                  </div>
                  <p className="shrink-0 text-right text-[16px] font-bold text-stone-900 dark:text-white">
                    {Number(expense.amount).toLocaleString('ru-RU', {
                      minimumFractionDigits: 0,
                      maximumFractionDigits: 2,
                    })}{' '}
                    <span className="text-[12px] font-medium text-stone-400 dark:text-stone-500">
                      {expense.currency}
                    </span>
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
};
