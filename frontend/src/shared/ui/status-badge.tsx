import { cn } from '@/shared/lib/utils';

type TripStatus = 'planned' | 'active' | 'completed' | 'cancelled';

const STATUS_CONFIG: Record<TripStatus, { label: string; className: string }> = {
  planned: {
    label: 'Запланирована',
    className:
      'border-green-200/60 bg-green-50/80 text-green-700 dark:border-green-800/60 dark:bg-green-900/30 dark:text-green-400',
  },
  active: {
    label: 'В пути',
    className:
      'border-amber-300/50 bg-amber-50/80 text-amber-700 dark:border-amber-700/50 dark:bg-amber-900/30 dark:text-amber-400',
  },
  completed: {
    label: 'Завершена',
    className:
      'border-stone-200 bg-stone-100 text-stone-500 dark:border-stone-700 dark:bg-stone-800 dark:text-stone-400',
  },
  cancelled: {
    label: 'Отменена',
    className:
      'border-red-200/60 bg-red-50/80 text-red-600 dark:border-red-800/60 dark:bg-red-900/30 dark:text-red-400',
  },
};

export const StatusBadge = ({ status }: { status: TripStatus }) => {
  const { label, className } = STATUS_CONFIG[status];
  return (
    <span className={cn('rounded-full border px-2.5 py-1 text-[12px] font-semibold', className)}>
      {label}
    </span>
  );
};
