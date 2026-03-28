import type { Expense, ExpenseCategory } from '@/entities/expense';
import { CATEGORY_META } from '@/entities/expense';
import { CURRENCIES } from '@/shared/config';
import { Button, Drawer, DrawerContent, DrawerTitle, Label } from '@/shared/ui';
import { Car, Coffee, Home, Loader2, MoreHorizontal, Music, ShoppingBag } from 'lucide-react';
import { useExpenseForm } from '../model/useExpenseForm';

const CATEGORY_ICONS: Record<string, React.ElementType> = {
  food: Coffee,
  transport: Car,
  housing: Home,
  entertainment: Music,
  shopping: ShoppingBag,
  other: MoreHorizontal,
};

const CATEGORY_COLORS: Record<
  string,
  { bg: string; icon: string; selectedBg: string; selectedIcon: string; ring: string }
> = {
  food: {
    bg: 'bg-amber-50 dark:bg-amber-900/20',
    icon: 'text-amber-500',
    selectedBg: 'bg-amber-100 dark:bg-amber-900/40',
    selectedIcon: 'text-amber-600',
    ring: 'border-amber-300/60',
  },
  transport: {
    bg: 'bg-blue-50 dark:bg-blue-900/20',
    icon: 'text-blue-500',
    selectedBg: 'bg-blue-100 dark:bg-blue-900/40',
    selectedIcon: 'text-blue-600',
    ring: 'border-blue-300/60',
  },
  housing: {
    bg: 'bg-sky-50 dark:bg-sky-900/20',
    icon: 'text-sky-500',
    selectedBg: 'bg-sky-100 dark:bg-sky-900/40',
    selectedIcon: 'text-sky-600',
    ring: 'border-sky-300/60',
  },
  entertainment: {
    bg: 'bg-violet-50 dark:bg-violet-900/20',
    icon: 'text-violet-500',
    selectedBg: 'bg-violet-100 dark:bg-violet-900/40',
    selectedIcon: 'text-violet-600',
    ring: 'border-violet-300/60',
  },
  shopping: {
    bg: 'bg-emerald-50 dark:bg-emerald-900/20',
    icon: 'text-emerald-500',
    selectedBg: 'bg-emerald-100 dark:bg-emerald-900/40',
    selectedIcon: 'text-emerald-600',
    ring: 'border-emerald-300/60',
  },
  other: {
    bg: 'bg-stone-100 dark:bg-stone-800',
    icon: 'text-stone-400',
    selectedBg: 'bg-stone-200 dark:bg-stone-700',
    selectedIcon: 'text-stone-600',
    ring: 'border-stone-300',
  },
};

const CATEGORIES: ExpenseCategory[] = [
  'food',
  'transport',
  'housing',
  'entertainment',
  'shopping',
  'other',
];

const inputBase =
  'h-[52px] w-full rounded-[14px] border border-stone-200 bg-stone-100 px-3.5 text-[15px] font-semibold text-stone-900 outline-none placeholder:font-normal placeholder:text-stone-400 focus:border-primary focus:border-[1.5px] dark:border-stone-700 dark:bg-stone-800 dark:text-white dark:placeholder:text-stone-500';

const labelClass =
  'mb-1.5 block text-[11px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500';

type ExpenseFormProps = {
  tripId: string;
  tripCurrency?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  existingExpense?: Expense;
  onSuccess: () => void;
  onDeleteRequest?: () => void;
};

export const ExpenseForm = ({
  tripId,
  tripCurrency,
  open,
  onOpenChange,
  existingExpense,
  onSuccess,
  onDeleteRequest,
}: ExpenseFormProps) => {
  const form = useExpenseForm(tripId, existingExpense, tripCurrency);
  const isEdit = !!existingExpense;

  const handleSubmit = async () => {
    const result = isEdit ? await form.handleUpdate(existingExpense.id) : await form.handleCreate();
    if (result) {
      form.reset();
      onOpenChange(false);
      onSuccess();
    }
  };

  const handleDelete = () => {
    onOpenChange(false);
    onDeleteRequest?.();
  };

  return (
    <Drawer
      open={open}
      onOpenChange={(newOpen) => {
        if (!newOpen) form.reset();
        onOpenChange(newOpen);
      }}
    >
      <DrawerContent className="max-h-[92dvh] overflow-y-auto bg-white px-5 pb-10 dark:bg-stone-950">
        {/* Header */}
        <div className="mb-5 flex items-center justify-between">
          <DrawerTitle className="text-[20px] font-extrabold text-stone-900 dark:text-white">
            {isEdit ? 'Редактировать расход' : 'Добавить расход'}
          </DrawerTitle>
        </div>

        <div className="flex flex-col gap-4">
          {/* Category */}
          <div>
            <Label className={labelClass}>Категория</Label>
            <div className="grid grid-cols-3 gap-2">
              {CATEGORIES.map((cat) => {
                const meta = CATEGORY_META[cat];
                const isSelected = form.category === cat;
                const Icon = CATEGORY_ICONS[cat] ?? MoreHorizontal;
                const colors = CATEGORY_COLORS[cat] ?? CATEGORY_COLORS['other'];
                return (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => form.setCategory(cat)}
                    className={`flex min-h-[62px] flex-col items-center justify-center gap-1.5 rounded-[14px] border-2 px-2 py-3 transition-all ${
                      isSelected
                        ? `${colors.ring} ${colors.selectedBg}`
                        : 'border-stone-100 bg-stone-50 dark:border-stone-800 dark:bg-stone-800/50'
                    }`}
                  >
                    <div
                      className={`flex h-8 w-8 items-center justify-center rounded-[10px] ${isSelected ? colors.selectedBg : colors.bg}`}
                    >
                      <Icon
                        className={`h-4 w-4 ${isSelected ? colors.selectedIcon : colors.icon}`}
                        strokeWidth={1.75}
                      />
                    </div>
                    <span
                      className={`text-[11px] font-semibold ${isSelected ? 'text-stone-900 dark:text-white' : 'text-stone-500 dark:text-stone-400'}`}
                    >
                      {meta.label}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Amount + Currency */}
          <div>
            <Label className={labelClass}>Сумма</Label>
            <div className="flex gap-2">
              <input
                type="number"
                inputMode="decimal"
                placeholder="0"
                value={form.amount}
                onChange={(e) => form.setAmount(e.target.value)}
                className={`${inputBase} flex-1`}
              />
              <select
                value={form.currency}
                onChange={(e) => form.setCurrency(e.target.value)}
                className="h-[52px] rounded-[14px] border border-stone-200 bg-stone-100 px-3 text-[14px] font-semibold text-stone-700 outline-none focus:border-primary dark:border-stone-700 dark:bg-stone-800 dark:text-white"
              >
                {CURRENCIES.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.value}
                  </option>
                ))}
              </select>
            </div>
            {form.errors.amount && (
              <p className="mt-1 text-[12px] text-red-500">{form.errors.amount}</p>
            )}
          </div>

          {/* Date */}
          <div>
            <Label className={labelClass}>Дата</Label>
            <input
              type="date"
              value={form.expenseDate}
              onChange={(e) => form.setExpenseDate(e.target.value)}
              className={inputBase}
            />
          </div>

          {/* Description */}
          <div>
            <Label className={labelClass}>Описание</Label>
            <input
              type="text"
              placeholder="Например: ужин в ресторане"
              value={form.description}
              onChange={(e) => form.setDescription(e.target.value)}
              className={inputBase}
            />
          </div>

          {isEdit && onDeleteRequest ? (
            <div className="flex gap-2.5">
              <Button
                variant="destructive"
                onClick={handleDelete}
                disabled={form.isLoading}
                className="h-[52px] flex-1 rounded-2xl text-base font-bold shadow-[0_4px_16px_rgba(239,68,68,0.28)]"
              >
                Удалить
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={form.isLoading}
                className="h-[52px] flex-1 rounded-2xl text-base font-bold shadow-[0_4px_16px_rgba(37,99,235,0.28)]"
              >
                {form.isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Сохранить
              </Button>
            </div>
          ) : (
            <Button
              onClick={handleSubmit}
              disabled={form.isLoading}
              className="h-[52px] w-full rounded-2xl text-base font-bold shadow-[0_4px_16px_rgba(37,99,235,0.28)]"
            >
              {form.isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Добавить расход
            </Button>
          )}
        </div>
      </DrawerContent>
    </Drawer>
  );
};
