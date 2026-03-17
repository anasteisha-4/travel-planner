import { BUDGET_LIMITS, CURRENCIES, TRAVEL_TYPES, TRIP_DURATIONS } from '@/shared/config';
import { PillChip } from '@/shared/ui';
import { DollarSign, Globe, MessageSquare, PiggyBank, Plane, Timer } from 'lucide-react';

type PreferencesData = {
  travel_types: string[];
  favorite_destinations: string | null;
  currency: string;
  budget_min: number | null;
  budget_max: number | null;
  trip_duration: string | null;
  departure_city: string | null;
  additional_info: string | null;
};

const getCurrencyLabel = (code: string) => CURRENCIES.find((c) => c.value === code)?.label ?? code;

const getDurationLabel = (id: string) => TRIP_DURATIONS.find((d) => d.id === id)?.label ?? id;

const formatBudget = (min: number, max: number, currency: string) => {
  const config = BUDGET_LIMITS[currency] ?? BUDGET_LIMITS.RUB;
  return `${config.format(min)} — ${config.format(max)}`;
};

export const PreferencesView = ({ preferences }: { preferences: PreferencesData }) => {
  const rows: { icon: typeof Globe; label: string; value: React.ReactNode }[] = [];

  if (preferences.departure_city) {
    rows.push({
      icon: Plane,
      label: 'Откуда',
      value: (
        <span className="text-[15px] font-semibold text-stone-900 dark:text-white">
          {preferences.departure_city}
        </span>
      ),
    });
  }

  if (preferences.favorite_destinations) {
    rows.push({
      icon: Globe,
      label: 'Направления',
      value: (
        <span className="text-[15px] font-semibold text-stone-900 dark:text-white">
          {preferences.favorite_destinations}
        </span>
      ),
    });
  }

  if (preferences.currency) {
    rows.push({
      icon: DollarSign,
      label: 'Валюта',
      value: (
        <span className="text-[15px] font-bold text-stone-900 dark:text-white">
          {getCurrencyLabel(preferences.currency)}
        </span>
      ),
    });
  }

  if (preferences.budget_min !== null && preferences.budget_max !== null) {
    rows.push({
      icon: PiggyBank,
      label: 'Бюджет',
      value: (
        <span className="text-[15px] font-bold text-stone-900 dark:text-white">
          {formatBudget(preferences.budget_min, preferences.budget_max, preferences.currency)}
        </span>
      ),
    });
  }

  if (preferences.trip_duration) {
    rows.push({
      icon: Timer,
      label: 'Длительность',
      value: (
        <span className="text-[15px] font-bold text-stone-900 dark:text-white">
          {getDurationLabel(preferences.trip_duration)}
        </span>
      ),
    });
  }

  if (preferences.additional_info) {
    rows.push({
      icon: MessageSquare,
      label: 'Дополнительно',
      value: (
        <span className="text-[14px] text-stone-600 dark:text-stone-400">
          {preferences.additional_info}
        </span>
      ),
    });
  }

  return (
    <div className="trip-info-card flex flex-col gap-0">
      {preferences.travel_types.length > 0 && (
        <div className="pb-3">
          <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
            Виды отдыха
          </p>
          <div className="flex flex-wrap gap-1.5">
            {preferences.travel_types.map((id) => {
              const type = TRAVEL_TYPES.find((t) => t.id === id);
              if (!type) return null;
              return (
                <PillChip key={id} selected onClick={() => undefined} icon={type.icon}>
                  {type.label}
                </PillChip>
              );
            })}
          </div>
          {rows.length > 0 && <div className="mt-3 h-px bg-stone-100 dark:bg-stone-800" />}
        </div>
      )}

      {rows.map(({ icon: Icon, label, value }, i) => (
        <div key={label}>
          <div className="flex items-center justify-between py-2.5">
            <div className="flex items-center gap-2">
              <Icon className="h-4 w-4 shrink-0 text-stone-400 dark:text-stone-500" />
              <span className="text-[11px] font-semibold uppercase tracking-widest text-stone-400 dark:text-stone-500">
                {label}
              </span>
            </div>
            <div className="ml-4 text-right">{value}</div>
          </div>
          {i < rows.length - 1 && <div className="h-px bg-stone-100 dark:bg-stone-800" />}
        </div>
      ))}
    </div>
  );
};
