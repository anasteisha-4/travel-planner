import { cn } from '@/shared/lib/utils';

type TabItem<T> = {
  id: T;
  label: string;
  count?: number;
};

type TabBarProps<T extends string> = {
  tabs: TabItem<T>[];
  active: T;
  onChange: (id: T) => void;
  className?: string;
};

export const TabBar = <T extends string,>({ tabs, active, onChange, className }: TabBarProps<T>) => (
  <div className={cn('flex border-b border-stone-100 dark:border-stone-800', className)}>
    {tabs.map(({ id, label, count }) => (
      <button
        key={id}
        type="button"
        onClick={() => onChange(id)}
        className={cn(
          'flex items-center gap-1.5 pb-2.5 pr-5 text-[15px] font-semibold transition-colors',
          active === id
            ? 'border-b-[2.5px] border-primary text-stone-900 dark:text-white'
            : 'text-stone-400 dark:text-stone-500'
        )}
      >
        {label}
        {count !== undefined && (
          <span
            className={cn(
              'rounded-full px-1.5 py-0.5 text-[11px] font-bold tabular-nums',
              active === id
                ? 'bg-primary/10 text-primary dark:bg-primary/20'
                : 'bg-stone-100 text-stone-400 dark:bg-stone-800 dark:text-stone-500'
            )}
          >
            {count}
          </span>
        )}
      </button>
    ))}
  </div>
);
