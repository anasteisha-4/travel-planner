import { Globe } from 'lucide-react';

import type { UserProfileV2 } from '@/entities/user';
import {
  BUDGET_LIMITS,
  CLIMATE_OPTIONS,
  CROWD_LABELS,
  DURATION_OPTIONS,
  LANGUAGE_OPTIONS,
  RISK_TOLERANCE_LABELS,
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
  <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-stone-400">{children}</p>
);

const Divider = () => <div className="my-3 h-px bg-stone-100" />;

export const PreferencesView = ({ preferences }: { preferences: Partial<UserProfileV2> }) => {
  const vacationPrefs = (preferences.vacation_preferences_ranked ?? []).filter(
    (id) => !!TRAVEL_TYPES.find((t) => t.id === id)
  );
  const climatePrefs = preferences.climate_preferences ?? [];
  const languageComfort = preferences.language_comfort ?? [];
  const likedNames = preferences.liked_destination_names ?? [];
  const likedIds = preferences.liked_destination_ids ?? [];
  const hasBudget =
    preferences.budget_min !== null &&
    preferences.budget_max !== null &&
    preferences.budget_min !== undefined &&
    preferences.budget_max !== undefined;
  const currency = preferences.preferred_currency ?? 'RUB';
  const budgetConfig = BUDGET_LIMITS[currency] ?? BUDGET_LIMITS.RUB;

  const hasAnything =
    vacationPrefs.length > 0 ||
    climatePrefs.length > 0 ||
    hasBudget ||
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
                  className="flex items-center gap-1.5 rounded-xl border border-blue-100 bg-blue-50 py-1.5 pl-2 pr-3 text-[13px] font-semibold text-blue-800"
                >
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-600 text-[10px] font-bold text-white">
                    {idx + 1}
                  </span>
                  <Icon className="h-3.5 w-3.5 text-blue-500" />
                  {type.label}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {vacationPrefs.length > 0 &&
        (hasBudget || preferences.typical_duration || preferences.origin_city_name) && <Divider />}

      {/* Бюджет и поездки */}
      {(hasBudget || preferences.typical_duration || preferences.origin_city_name) && (
        <div className="flex flex-col gap-0">
          {preferences.origin_city_name && (
            <div className="flex items-center justify-between py-2">
              <span className="text-[11px] font-semibold uppercase tracking-widest text-stone-400">
                ✈️ Откуда
              </span>
              <span className="text-[14px] font-semibold text-stone-900">
                {preferences.origin_city_name}
              </span>
            </div>
          )}
          {preferences.origin_city_name && (hasBudget || preferences.typical_duration) && (
            <div className="h-px bg-stone-100" />
          )}

          {hasBudget && (
            <div className="flex items-center justify-between py-2">
              <span className="text-[11px] font-semibold uppercase tracking-widest text-stone-400">
                💰 Бюджет
              </span>
              <div className="text-right">
                <span className="text-[14px] font-bold text-stone-900">
                  {budgetConfig.format(preferences.budget_min!)} —{' '}
                  {budgetConfig.format(preferences.budget_max!)}
                </span>
              </div>
            </div>
          )}
          {hasBudget && preferences.typical_duration && <div className="h-px bg-stone-100" />}

          {preferences.typical_duration && (
            <div className="flex items-center justify-between py-2">
              <span className="text-[11px] font-semibold uppercase tracking-widest text-stone-400">
                ⏱ Длительность
              </span>
              <span className="text-[14px] font-semibold text-stone-900">
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
                className="flex items-center gap-1.5 rounded-xl border border-stone-200 bg-stone-50 py-1.5 pl-2.5 pr-3 text-[13px] font-semibold text-stone-700"
              >
                <Globe className="h-3.5 w-3.5 text-stone-400" />
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
              <div className="flex items-center justify-between rounded-xl bg-stone-50 px-3 py-2.5">
                <span className="text-[13px] font-semibold text-stone-600">Приключения</span>
                <div className="flex items-center gap-1.5">
                  <span className="text-[18px] leading-none">
                    {RISK_ICONS[preferences.risk_tolerance]}
                  </span>
                  <span className="text-[13px] font-semibold text-stone-900">
                    {RISK_TOLERANCE_LABELS[preferences.risk_tolerance]}
                  </span>
                </div>
              </div>
            )}
            {preferences.visa_tolerance &&
              (() => {
                const visa = VISA_OPTIONS.find((v) => v.id === preferences.visa_tolerance);
                return visa ? (
                  <div className="flex items-center justify-between rounded-xl bg-stone-50 px-3 py-2.5">
                    <span className="text-[13px] font-semibold text-stone-600">Виза</span>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[16px] leading-none">
                        {VISA_ICONS[preferences.visa_tolerance!] ?? '🌐'}
                      </span>
                      <span className="text-[13px] font-semibold text-stone-900">{visa.label}</span>
                    </div>
                  </div>
                ) : null;
              })()}
            {languageComfort.length > 0 && (
              <div className="flex items-center justify-between rounded-xl bg-stone-50 px-3 py-2.5">
                <span className="text-[13px] font-semibold text-stone-600">Языки</span>
                <div className="flex flex-wrap justify-end gap-1">
                  {languageComfort.map((id) => {
                    const opt = LANGUAGE_OPTIONS.find((l) => l.id === id);
                    return opt ? (
                      <span
                        key={id}
                        className="rounded-lg bg-stone-200 px-2 py-0.5 text-[12px] font-semibold text-stone-700"
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
              <div className="flex items-center justify-between rounded-xl bg-stone-50 px-3 py-2.5">
                <span className="text-[13px] font-semibold text-stone-600">Людность</span>
                <div className="flex items-center gap-1.5">
                  <span className="text-[18px] leading-none">
                    {CROWD_ICONS[preferences.crowd_preference]}
                  </span>
                  <span className="text-[13px] font-semibold text-stone-900">
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
                      className="flex items-center gap-1 rounded-xl border border-stone-200 bg-stone-50 px-2.5 py-1.5 text-[13px] font-semibold text-stone-700"
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
          <div className="rounded-xl bg-stone-50 px-3 py-2.5">
            <p className="mb-1 text-[10px] font-bold uppercase tracking-widest text-stone-400">
              💬 Заметки
            </p>
            <p className="text-[13px] text-stone-600">{preferences.free_text_notes}</p>
          </div>
        </>
      )}
    </div>
  );
};
