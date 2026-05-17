import { Globe } from 'lucide-react';

import type { UserProfileV2 } from '@/entities/user';
import {
  BUDGET_LIMITS,
  CLIMATE_OPTIONS,
  CROWD_LABELS,
  DURATION_OPTIONS,
  LANGUAGE_OPTIONS,
  RISK_TOLERANCE_LABELS,
  REST_LEVEL_OPTIONS,
  TRAVEL_TYPES,
  TRIP_DURATIONS,
  VISA_OPTIONS,
} from '@/shared/config';

const getDurationLabel = (id: string) =>
  TRIP_DURATIONS.find((d) => d.id === id)?.label ??
  DURATION_OPTIONS.find((d) => d.id === id)?.label ??
  id;

const RISK_ICONS: Record<number, string> = { 1: '🛋️', 2: '🏖️', 3: '🗺️', 4: '🧗', 5: '🪂' };
const CROWD_ICONS: Record<number, string> = { 1: '🏕️', 2: '🌄', 3: '🏘️', 4: '🏙️', 5: '🎡' };

const VISA_ICONS: Record<string, string> = {
  visa_free_only: '🟢',
  evisa_ok: '🔵',
  any_visa: '🟡',
};

const SectionTitle = ({ children }: { children: React.ReactNode }) => (
  <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">{children}</p>
);

const Divider = () => <div className="my-3 h-px bg-[hsl(var(--surface-field))]" />;

const formatBudgetRange = (
  min: number | null | undefined,
  max: number | null | undefined,
  format: (value: number) => string
) => {
  const hasMin = min !== null && min !== undefined && min > 0;
  const hasMax = max !== null && max !== undefined;

  if (hasMin && hasMax) return `${format(min)} — ${format(max)}`;
  if (hasMin) return `от ${format(min)}`;
  if (hasMax) return `до ${format(max)}`;
  return 'Без лимита';
};

export const PreferencesView = ({ preferences }: { preferences: Partial<UserProfileV2> }) => {
  const vacationPrefs = (preferences.vacation_preferences_ranked ?? []).filter(
    (id) => !!TRAVEL_TYPES.find((t) => t.id === id)
  );
  const climatePrefs = preferences.climate_preferences ?? [];
  const languageComfort = preferences.language_comfort ?? [];
  const likedNames = preferences.liked_destination_names ?? [];
  const likedIds = preferences.liked_destination_ids ?? [];
  const hasBudget =
    (preferences.budget_min !== null && preferences.budget_min !== undefined) ||
    (preferences.budget_max !== null && preferences.budget_max !== undefined);
  const currency = preferences.preferred_currency ?? 'RUB';
  const budgetConfig = BUDGET_LIMITS[currency] ?? BUDGET_LIMITS.RUB;
  const restLevel = REST_LEVEL_OPTIONS.find((option) => option.id === preferences.rest_level);

  const hasAnything =
    vacationPrefs.length > 0 ||
    climatePrefs.length > 0 ||
    hasBudget ||
    restLevel ||
    preferences.typical_duration ||
    preferences.origin_city_name ||
    preferences.risk_tolerance ||
    preferences.visa_tolerance ||
    languageComfort.length > 0 ||
    preferences.crowd_preference ||
    preferences.free_text_notes ||
    likedIds.length > 0;

  if (!hasAnything) return null;

  return (
    <div className="trip-info-card flex flex-col gap-0 pb-1">
      {/* Виды отдыха */}
      {vacationPrefs.length > 0 && (
        <div className="pb-1">
          <SectionTitle>Виды отдыха</SectionTitle>
          <div className="flex flex-wrap gap-1.5">
            {vacationPrefs.map((id, idx) => {
              const type = TRAVEL_TYPES.find((t) => t.id === id);
              if (!type) return null;
              const Icon = type.icon;
              return (
                <span
                  key={id}
                  className="flex items-center gap-1.5 rounded-xl border border-blue-100 bg-primary/10 py-1.5 pl-2 pr-3 text-[13px] font-semibold text-primary dark:border-[hsl(var(--surface-border))]"
                >
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary text-[10px] font-bold text-primary-foreground">
                    {idx + 1}
                  </span>
                  <Icon className="h-3.5 w-3.5 text-primary" />
                  {type.label}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {vacationPrefs.length > 0 &&
        (hasBudget || restLevel || preferences.typical_duration || preferences.origin_city_name) && <Divider />}

      {/* Бюджет и поездки */}
      {(hasBudget || restLevel || preferences.typical_duration || preferences.origin_city_name) && (
        <div className="flex flex-col gap-0">
          {preferences.origin_city_name && (
            <div className="flex items-center justify-between py-2">
              <span className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
                ✈️ Откуда
              </span>
              <span className="text-[14px] font-semibold text-foreground">
                {preferences.origin_city_name}
              </span>
            </div>
          )}
          {preferences.origin_city_name && (hasBudget || restLevel || preferences.typical_duration) && (
            <div className="h-px bg-[hsl(var(--surface-field))]" />
          )}

          {hasBudget && (
            <div className="flex items-center justify-between py-2">
              <span className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
                💰 Бюджет
              </span>
              <div className="text-right">
                <span className="text-[14px] font-bold text-foreground">
                  {formatBudgetRange(preferences.budget_min, preferences.budget_max, budgetConfig.format)}
                </span>
              </div>
            </div>
          )}
          {hasBudget && (restLevel || preferences.typical_duration) && <div className="h-px bg-[hsl(var(--surface-field))]" />}

          {restLevel && (
            <div className="flex items-center justify-between py-2">
              <span className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
                🧳 Уровень отдыха
              </span>
              <span className="text-[14px] font-semibold text-foreground">{restLevel.label}</span>
            </div>
          )}
          {restLevel && preferences.typical_duration && <div className="h-px bg-[hsl(var(--surface-field))]" />}

          {preferences.typical_duration && (
            <div className="flex items-center justify-between py-2">
              <span className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
                ⏱ Длительность
              </span>
              <span className="text-[14px] font-semibold text-foreground">
                {getDurationLabel(preferences.typical_duration)}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Любимые места */}
      {likedIds.length > 0 && (
        <>
          <Divider />
          <SectionTitle>Любимые места</SectionTitle>
          <div className="flex flex-wrap gap-1.5">
            {likedIds.map((id, i) => (
              <span
                key={id}
                className="flex items-center gap-1.5 rounded-xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-muted))] py-1.5 pl-2.5 pr-3 text-[13px] font-semibold text-foreground"
              >
                <Globe className="h-3.5 w-3.5 text-muted-foreground" />
                {likedNames[i] ?? id}
              </span>
            ))}
          </div>
        </>
      )}

      {/* Стиль и ограничения */}
      {(preferences.risk_tolerance || preferences.visa_tolerance || languageComfort.length > 0) && (
        <>
          <Divider />
          <SectionTitle>Стиль и ограничения</SectionTitle>
          <div className="flex flex-col gap-2">
            {preferences.risk_tolerance && (
              <div className="flex items-center justify-between rounded-xl bg-[hsl(var(--surface-muted))] px-3 py-2.5">
                <span className="text-[13px] font-semibold text-muted-foreground">Приключения</span>
                <div className="flex items-center gap-1.5">
                  <span className="text-[18px] leading-none">
                    {RISK_ICONS[preferences.risk_tolerance]}
                  </span>
                  <span className="text-[13px] font-semibold text-foreground">
                    {RISK_TOLERANCE_LABELS[preferences.risk_tolerance]}
                  </span>
                </div>
              </div>
            )}
            {preferences.visa_tolerance &&
              (() => {
                const visa = VISA_OPTIONS.find((v) => v.id === preferences.visa_tolerance);
                return visa ? (
                  <div className="flex items-center justify-between rounded-xl bg-[hsl(var(--surface-muted))] px-3 py-2.5">
                    <span className="text-[13px] font-semibold text-muted-foreground">Виза</span>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[16px] leading-none">
                        {VISA_ICONS[preferences.visa_tolerance!] ?? '🌐'}
                      </span>
                      <span className="text-[13px] font-semibold text-foreground">{visa.label}</span>
                    </div>
                  </div>
                ) : null;
              })()}
            {languageComfort.length > 0 && (
              <div className="flex items-center justify-between rounded-xl bg-[hsl(var(--surface-muted))] px-3 py-2.5">
                <span className="text-[13px] font-semibold text-muted-foreground">Языки</span>
                <div className="flex flex-wrap justify-end gap-1">
                  {languageComfort.map((id) => {
                    const opt = LANGUAGE_OPTIONS.find((l) => l.id === id);
                    return opt ? (
                      <span
                        key={id}
                        className="rounded-lg bg-[hsl(var(--surface-field))] px-2 py-0.5 text-[12px] font-semibold text-foreground"
                      >
                        {opt.label}
                      </span>
                    ) : null;
                  })}
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {/* Атмосфера */}
      {(preferences.crowd_preference || climatePrefs.length > 0) && (
        <>
          <Divider />
          <SectionTitle>Атмосфера</SectionTitle>
          <div className="flex flex-col gap-2">
            {preferences.crowd_preference && (
              <div className="flex items-center justify-between rounded-xl bg-[hsl(var(--surface-muted))] px-3 py-2.5">
                <span className="text-[13px] font-semibold text-muted-foreground">Людность</span>
                <div className="flex items-center gap-1.5">
                  <span className="text-[18px] leading-none">
                    {CROWD_ICONS[preferences.crowd_preference]}
                  </span>
                  <span className="text-[13px] font-semibold text-foreground">
                    {CROWD_LABELS[preferences.crowd_preference]}
                  </span>
                </div>
              </div>
            )}
            {climatePrefs.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {climatePrefs.map((id) => {
                  const opt = CLIMATE_OPTIONS.find((c) => c.id === id);
                  return opt ? (
                    <span
                      key={id}
                      className="flex items-center gap-1 rounded-xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-muted))] px-2.5 py-1.5 text-[13px] font-semibold text-foreground"
                    >
                      <span>{opt.emoji}</span>
                      {opt.label}
                    </span>
                  ) : null;
                })}
              </div>
            )}
          </div>
        </>
      )}

      {/* Заметки */}
      {preferences.free_text_notes && (
        <>
          <Divider />
          <div className="rounded-xl bg-[hsl(var(--surface-muted))] px-3 py-2.5">
            <p className="mb-1 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
              Заметки для маршрутов
            </p>
            <p className="mb-2 text-[12px] font-semibold leading-snug text-muted-foreground">
              Эти детали помогают точнее подбирать темп, активности и проверки поездки.
            </p>
            <p className="text-[13px] text-muted-foreground">{preferences.free_text_notes}</p>
          </div>
        </>
      )}
    </div>
  );
};
