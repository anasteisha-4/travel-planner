import { cn } from '@/shared/lib/utils';

const MONTHS = [
  { num: 1, short: 'Янв', season: 'winter' },
  { num: 2, short: 'Фев', season: 'winter' },
  { num: 3, short: 'Мар', season: 'spring' },
  { num: 4, short: 'Апр', season: 'spring' },
  { num: 5, short: 'Май', season: 'spring' },
  { num: 6, short: 'Июн', season: 'summer' },
  { num: 7, short: 'Июл', season: 'summer' },
  { num: 8, short: 'Авг', season: 'summer' },
  { num: 9, short: 'Сен', season: 'autumn' },
  { num: 10, short: 'Окт', season: 'autumn' },
  { num: 11, short: 'Ноя', season: 'autumn' },
  { num: 12, short: 'Дек', season: 'winter' },
] as const;

const SEASON_CLASS: Record<string, string> = {
  winter:
    'data-[active=true]:border-blue-400 data-[active=true]:bg-blue-500/10 data-[active=true]:text-blue-600 dark:data-[active=true]:text-blue-300',
  spring:
    'data-[active=true]:border-emerald-400 data-[active=true]:bg-emerald-500/10 data-[active=true]:text-emerald-600 dark:data-[active=true]:text-emerald-300',
  summer:
    'data-[active=true]:border-amber-400 data-[active=true]:bg-amber-500/10 data-[active=true]:text-amber-600 dark:data-[active=true]:text-amber-300',
  autumn:
    'data-[active=true]:border-orange-400 data-[active=true]:bg-orange-500/10 data-[active=true]:text-orange-600 dark:data-[active=true]:text-orange-300',
};

const REGIONS = [
  { key: null, label: 'Все' },
  { key: 'Europe', label: 'Европа' },
  { key: 'Asia', label: 'Азия' },
  { key: 'Middle East', label: 'Ближний Восток' },
  { key: 'Africa', label: 'Африка' },
  { key: 'Americas', label: 'Америка' },
  { key: 'Oceania', label: 'Океания' },
] as const;

type RecommendationFiltersProps = {
  month: number;
  region: string | null;
  onMonthChange: (month: number) => void;
  onRegionChange: (region: string | null) => void;
};

export const RecommendationFilters = ({
  month,
  region,
  onMonthChange,
  onRegionChange,
}: RecommendationFiltersProps) => (
  <div className="flex flex-col gap-3">
    <div className="no-scrollbar flex gap-1.5 overflow-x-auto pb-1">
      {MONTHS.map((item) => {
        const isActive = item.num === month;
        return (
          <button
            key={item.num}
            type="button"
            data-active={isActive}
            onClick={() => onMonthChange(item.num)}
            className={cn(
              'flex min-h-8 min-w-12 shrink-0 flex-col items-center justify-center rounded-2xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface))] px-3 text-muted-foreground transition active:scale-[0.98]',
              SEASON_CLASS[item.season],
              isActive && 'font-extrabold'
            )}
          >
            <span className="text-[12px] leading-none">{item.short}</span>
          </button>
        );
      })}
    </div>

    <div className="no-scrollbar flex gap-1.5 overflow-x-auto pb-1">
      {REGIONS.map((item) => {
        const isActive = region === item.key;
        return (
          <button
            key={String(item.key)}
            type="button"
            onClick={() => onRegionChange(item.key)}
            className={cn(
              'min-h-8 shrink-0 rounded-full border px-4 text-[12px] font-bold transition active:scale-[0.98]',
              isActive
                ? 'border-primary/50 bg-primary/10 text-primary'
                : 'border-[hsl(var(--surface-border))] bg-[hsl(var(--surface))] text-muted-foreground'
            )}
          >
            {item.label}
          </button>
        );
      })}
    </div>
  </div>
);
