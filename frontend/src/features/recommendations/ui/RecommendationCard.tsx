import { localizeDestinationName } from '@/shared/lib';
import { cn } from '@/shared/lib/utils';
import type { ScoredDestination } from '../model/types';

const COUNTRY_FLAGS: Record<string, string> = {
  AF: '🇦🇫',
  AL: '🇦🇱',
  DZ: '🇩🇿',
  AD: '🇦🇩',
  AO: '🇦🇴',
  AG: '🇦🇬',
  AR: '🇦🇷',
  AM: '🇦🇲',
  AU: '🇦🇺',
  AT: '🇦🇹',
  AZ: '🇦🇿',
  BS: '🇧🇸',
  BH: '🇧🇭',
  BD: '🇧🇩',
  BB: '🇧🇧',
  BY: '🇧🇾',
  BE: '🇧🇪',
  BR: '🇧🇷',
  BG: '🇧🇬',
  CA: '🇨🇦',
  CH: '🇨🇭',
  CL: '🇨🇱',
  CN: '🇨🇳',
  CO: '🇨🇴',
  CY: '🇨🇾',
  CZ: '🇨🇿',
  DE: '🇩🇪',
  DK: '🇩🇰',
  EE: '🇪🇪',
  EG: '🇪🇬',
  ES: '🇪🇸',
  FI: '🇫🇮',
  FR: '🇫🇷',
  GB: '🇬🇧',
  GE: '🇬🇪',
  GR: '🇬🇷',
  HR: '🇭🇷',
  HU: '🇭🇺',
  ID: '🇮🇩',
  IE: '🇮🇪',
  IL: '🇮🇱',
  IN: '🇮🇳',
  IT: '🇮🇹',
  JP: '🇯🇵',
  KR: '🇰🇷',
  KZ: '🇰🇿',
  LT: '🇱🇹',
  LV: '🇱🇻',
  MA: '🇲🇦',
  MD: '🇲🇩',
  ME: '🇲🇪',
  MX: '🇲🇽',
  MY: '🇲🇾',
  NL: '🇳🇱',
  NO: '🇳🇴',
  NZ: '🇳🇿',
  PL: '🇵🇱',
  PT: '🇵🇹',
  RO: '🇷🇴',
  RS: '🇷🇸',
  RU: '🇷🇺',
  SE: '🇸🇪',
  SG: '🇸🇬',
  TH: '🇹🇭',
  TR: '🇹🇷',
  UA: '🇺🇦',
  US: '🇺🇸',
  UZ: '🇺🇿',
  VN: '🇻🇳',
  ZA: '🇿🇦',
};

const TAG_CONFIG: Record<string, { label: string; className: string }> = {
  beach: { label: 'Пляж', className: 'bg-sky-500/10 text-sky-700 dark:text-sky-300' },
  culture: {
    label: 'Культура',
    className: 'bg-violet-500/10 text-violet-700 dark:text-violet-300',
  },
  nature: {
    label: 'Природа',
    className: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
  },
  adventure: {
    label: 'Активный',
    className: 'bg-orange-500/10 text-orange-700 dark:text-orange-300',
  },
  food: { label: 'Гастро', className: 'bg-red-500/10 text-red-700 dark:text-red-300' },
  nightlife: {
    label: 'Ночная жизнь',
    className: 'bg-fuchsia-500/10 text-fuchsia-700 dark:text-fuchsia-300',
  },
  wellness: { label: 'Велнес', className: 'bg-cyan-500/10 text-cyan-700 dark:text-cyan-300' },
  shopping: { label: 'Шопинг', className: 'bg-amber-500/10 text-amber-700 dark:text-amber-300' },
  family: { label: 'Семейный', className: 'bg-blue-500/10 text-blue-700 dark:text-blue-300' },
  urban: { label: 'Городской', className: 'bg-slate-500/10 text-slate-700 dark:text-slate-300' },
  affordable: {
    label: 'Доступно',
    className: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
  },
  visa_free: {
    label: 'Без визы',
    className: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
  },
  easy_visa: {
    label: 'Простая виза',
    className: 'bg-teal-500/10 text-teal-700 dark:text-teal-300',
  },
  safe: {
    label: 'Безопасно',
    className: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
  },
  skiing: { label: 'Горные лыжи', className: 'bg-cyan-500/10 text-cyan-700 dark:text-cyan-300' },
  hot_springs: {
    label: 'Термальные источники',
    className: 'bg-rose-500/10 text-rose-700 dark:text-rose-300',
  },
  mountains: { label: 'Горы', className: 'bg-lime-500/10 text-lime-700 dark:text-lime-300' },
  premium: { label: 'Премиум', className: 'bg-zinc-500/10 text-zinc-700 dark:text-zinc-300' },
  popular: { label: 'Популярно', className: 'bg-blue-500/10 text-blue-700 dark:text-blue-300' },
  hot_season: {
    label: 'Лучший сезон',
    className: 'bg-amber-500/10 text-amber-700 dark:text-amber-300',
  },
  perfect_season: {
    label: 'Лучший сезон',
    className: 'bg-amber-500/10 text-amber-700 dark:text-amber-300',
  },
  good_season: {
    label: 'Хороший сезон',
    className: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
  },
  great_match: {
    label: 'Сильное совпадение',
    className: 'bg-primary/10 text-primary',
  },
};

const getSeasonMeta = (score: number) => {
  if (score >= 0.8)
    return {
      label: 'Лучший сезон',
      className: 'text-emerald-600 dark:text-emerald-300',
      dot: 'bg-emerald-500',
    };
  if (score >= 0.6)
    return {
      label: 'Хороший сезон',
      className: 'text-amber-600 dark:text-amber-300',
      dot: 'bg-amber-500',
    };
  return { label: 'Не сезон', className: 'text-muted-foreground', dot: 'bg-muted-foreground' };
};

const getMatchTone = (score: number) => {
  if (score >= 0.8)
    return 'border-emerald-500/40 bg-emerald-500/10 text-emerald-600 dark:text-emerald-300';
  if (score >= 0.6) return 'border-primary/40 bg-primary/10 text-primary';
  return 'border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-300';
};

const formatDailyCost = (amount: number, currency: string) => {
  try {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency,
      maximumFractionDigits: 0,
    }).format(Math.round(amount));
  } catch {
    return `${Math.round(amount).toLocaleString('ru-RU')} ${currency}`;
  }
};

type RecommendationCardProps = {
  destination: ScoredDestination;
  onClick?: () => void;
  className?: string;
};

export const RecommendationCard = ({
  destination,
  onClick,
  className,
}: RecommendationCardProps) => {
  const flag = COUNTRY_FLAGS[destination.country_code] ?? '🌍';
  const season = getSeasonMeta(destination.season_score ?? 0);
  const topTags = destination.explanation_tags.slice(0, 3);
  const score = Math.round(destination.score * 100);
  const dailyCost =
    destination.avg_daily_budget ?? destination.avg_daily_cost ?? destination.avg_daily_cost_usd;
  const dailyCostCurrency =
    destination.avg_daily_budget_currency ?? destination.avg_daily_cost_currency ?? 'USD';

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'trip-info-card w-full text-left transition active:scale-[0.99]',
        'hover:border-primary/30',
        className
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-muted))] text-[25px]">
            {flag}
          </div>
          <div className="min-w-0">
            <p className="line-clamp-2 text-[17px] font-extrabold leading-tight text-foreground">
              {destination.display_name ??
                destination.name_ru ??
                localizeDestinationName(destination.name)}
            </p>
            <p className="mt-1 text-[13px] font-semibold text-muted-foreground">
              {destination.region}
            </p>
          </div>
        </div>
        <div
          className={cn(
            'flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border font-extrabold leading-none',
            getMatchTone(destination.score)
          )}
        >
          <span className="text-[15px]">{score}</span>
          <span className="text-[13px]">%</span>
        </div>
      </div>

      <div className="my-3 h-px bg-[hsl(var(--surface-border))]" />

      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <span className={cn('h-2 w-2 shrink-0 rounded-full', season.dot)} />
          <span className={cn('text-[12px] font-bold', season.className)}>{season.label}</span>
        </div>
        {typeof dailyCost === 'number' && (
          <span className="rounded-full bg-[hsl(var(--surface-muted))] px-2.5 py-1 text-[11px] font-bold text-muted-foreground">
            {formatDailyCost(dailyCost, dailyCostCurrency)}/день
          </span>
        )}
      </div>

      {topTags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {topTags.map((tag) => {
            const cfg = TAG_CONFIG[tag];
            if (!cfg) return null;
            return (
              <span
                key={tag}
                className={cn('rounded-lg px-2.5 py-1 text-[11px] font-extrabold', cfg.className)}
              >
                {cfg.label}
              </span>
            );
          })}
        </div>
      )}
    </button>
  );
};
