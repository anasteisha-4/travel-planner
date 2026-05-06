import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ChevronLeft, Loader2 } from 'lucide-react';
import { useState } from 'react';

import { BUDGET_LIMITS } from '@/shared/config';
import { expenseApi } from '@/entities/expense';
import {
  Button,
  Drawer,
  DrawerContent,
  DrawerTitle,
  StepIndicator,
} from '@/shared/ui';
import type { UserProfileV2 } from '@/entities/user';

import type { ClimatePref, DurationOption, LanguageOption, LikedDest, VacationPreference, VisaTolerance } from '@/features/onboarding-v2';
import { StepVacationPrefs, StepBudgetDuration, StepOriginCity, StepLikedDests, StepRiskVisaLang, StepClimateNotes } from '@/features/onboarding-v2';
import { profileApi } from '@/features/profile';

const STEP_META = [
  { title: 'Виды отдыха', subtitle: 'Расскажите о себе' },
  { title: 'Бюджет', subtitle: 'Финансовые предпочтения' },
  { title: 'Откуда летаете', subtitle: 'Город и длительность' },
  { title: 'Любимые места', subtitle: 'Ваши фавориты' },
  { title: 'Безопасность и визы', subtitle: 'Ограничения и комфорт' },
  { title: 'Климат и атмосфера', subtitle: 'Финальные штрихи' },
];

type EditState = {
  vacationPreferencesRanked: VacationPreference[];
  preferredCurrency: string;
  budgetMin: number | null;
  budgetMax: number | null;
  typicalDuration: DurationOption | null;
  originCityId: number | null;
  originCityName: string;
  originLat: number | null;
  originLng: number | null;
  likedDests: LikedDest[];
  riskTolerance: number | null;
  visaTolerance: VisaTolerance | null;
  languageComfort: LanguageOption[];
  crowdPreference: number | null;
  climatePreferences: ClimatePref[];
  freeTextNotes: string;
};

const profileToEditState = (p: Partial<UserProfileV2>): EditState => ({
  vacationPreferencesRanked: (p.vacation_preferences_ranked as VacationPreference[]) ?? [],
  preferredCurrency: p.preferred_currency ?? 'RUB',
  budgetMin: p.budget_min ?? null,
  budgetMax: p.budget_max ?? null,
  typicalDuration: (p.typical_duration as DurationOption) ?? null,
  originCityId: p.origin_city_id ?? null,
  originCityName: p.origin_city_name ?? '',
  originLat: p.origin_lat ?? null,
  originLng: p.origin_lng ?? null,
  likedDests: (p.liked_destination_ids ?? []).map((id, i) => ({
    id,
    name: p.liked_destination_names?.[i] ?? id,
    country_code: '',
  })),
  riskTolerance: p.risk_tolerance ?? null,
  visaTolerance: (p.visa_tolerance as VisaTolerance) ?? null,
  languageComfort: (p.language_comfort as LanguageOption[]) ?? [],
  crowdPreference: p.crowd_preference ?? null,
  climatePreferences: (p.climate_preferences as ClimatePref[]) ?? [],
  freeTextNotes: p.free_text_notes ?? '',
});

type Props = {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  initialData: Partial<UserProfileV2>;
  onSaved: () => void;
};

export const ProfileEditWizard = ({ open, onOpenChange, initialData, onSaved }: Props) => {
  const qc = useQueryClient();
  const [step, setStep] = useState(1);
  const [state, setState] = useState<EditState>(() => profileToEditState(initialData));

  const update = (patch: Partial<EditState>) => setState((prev) => ({ ...prev, ...patch }));

  const handleCurrencyChange = (newCurrency: string) => {
    const config = BUDGET_LIMITS[newCurrency] ?? BUDGET_LIMITS.RUB;
    const prevCurrency = state.preferredCurrency;
    const hasBudget = state.budgetMin !== null || state.budgetMax !== null;

    if (!hasBudget || prevCurrency === newCurrency) {
      setState((prev) => ({
        ...prev,
        preferredCurrency: newCurrency,
        budgetMin: config.min,
        budgetMax: Math.round(config.max * 0.3),
      }));
      return;
    }

    setState((prev) => ({ ...prev, preferredCurrency: newCurrency }));

    qc.fetchQuery({
      queryKey: ['exchange-rates', prevCurrency],
      queryFn: () => expenseApi.getExchangeRates(prevCurrency),
      staleTime: 60 * 60 * 1000,
    }).then((rates) => {
      const rate = rates.rates[newCurrency];
      if (!rate) return;
      setState((s) => ({
        ...s,
        budgetMin: s.budgetMin !== null ? Math.round(s.budgetMin * rate) : null,
        budgetMax: s.budgetMax !== null ? Math.min(Math.round(s.budgetMax * rate), config.max) : null,
      }));
    }).catch(() => {
      setState((s) => ({ ...s, budgetMin: config.min, budgetMax: Math.round(config.max * 0.3) }));
    });
  };

  const patchMutation = useMutation({
    mutationFn: (data: Partial<UserProfileV2>) => profileApi.patchProfile(data),
    onSuccess: (updated) => {
      qc.setQueryData(['profile'], updated);
      onSaved();
      onOpenChange(false);
    },
  });

  const handleSave = () => {
    patchMutation.mutate({
      vacation_preferences_ranked: state.vacationPreferencesRanked,
      preferred_currency: state.preferredCurrency,
      budget_min: state.budgetMin,
      budget_max: state.budgetMax,
      typical_duration: state.typicalDuration ?? undefined,
      origin_city_id: state.originCityId ?? undefined,
      origin_city_name: state.originCityName || undefined,
      origin_lat: state.originLat ?? undefined,
      origin_lng: state.originLng ?? undefined,
      liked_destination_ids: state.likedDests.map((d) => d.id),
      liked_destination_names: state.likedDests.map((d) => d.name),
      risk_tolerance: state.riskTolerance ?? undefined,
      visa_tolerance: state.visaTolerance ?? undefined,
      language_comfort: state.languageComfort,
      crowd_preference: state.crowdPreference ?? undefined,
      climate_preferences: state.climatePreferences,
      free_text_notes: state.freeTextNotes || undefined,
    });
  };

  const handleOpen = (v: boolean) => {
    if (!v) setStep(1);
    onOpenChange(v);
  };

  const isLastStep = step === 6;
  const meta = STEP_META[step - 1];

  return (
    <Drawer open={open} onOpenChange={handleOpen}>
      <DrawerContent className="flex h-[93dvh] flex-col overflow-hidden border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-elevated))] px-0">
        <DrawerTitle className="sr-only">Редактирование предпочтений</DrawerTitle>
        <div className="shrink-0 px-5 pb-3 pt-4">
          <div className="mb-3 flex items-center gap-3">
            {step > 1 ? (
              <button
                type="button"
                onClick={() => setStep((s) => s - 1)}
                className="flex h-[38px] w-[38px] items-center justify-center rounded-full border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-muted))] transition-colors active:bg-[hsl(var(--surface-field))]"
              >
                <ChevronLeft className="h-5 w-5 text-foreground" />
              </button>
            ) : (
              <div className="h-[38px] w-[38px]" />
            )}
            <StepIndicator steps={6} current={step} barClassName="w-7" className="flex-1 justify-center" />
            <div className="h-[38px] w-[38px]" />
          </div>
          <p className="mb-0.5 text-[11px] font-bold uppercase tracking-[0.07em] text-muted-foreground">
            Шаг {step} из 6
          </p>
          <h2 className="text-[20px] font-extrabold tracking-tight text-foreground">{meta.title}</h2>
          <p className="text-[13px] text-muted-foreground">{meta.subtitle}</p>
        </div>

        <div className="flex-1 overflow-y-auto px-5 pb-4">
          <div key={step} className="animate-in fade-in slide-in-from-right-4 duration-200">
            {step === 1 && (
              <StepVacationPrefs
                selected={state.vacationPreferencesRanked}
                onChange={(v) => update({ vacationPreferencesRanked: v })}
              />
            )}
            {step === 2 && (
              <StepBudgetDuration
                currency={state.preferredCurrency}
                budgetMin={state.budgetMin}
                budgetMax={state.budgetMax}
                onCurrencyChange={handleCurrencyChange}
                onBudgetChange={(min, max) => update({ budgetMin: min, budgetMax: max })}
              />
            )}
            {step === 3 && (
              <StepOriginCity
                cityName={state.originCityName}
                duration={state.typicalDuration}
                onSelect={({ name, lat, lng }) =>
                  update({ originCityId: null, originCityName: name, originLat: lat, originLng: lng })
                }
                onDurationChange={(v) => update({ typicalDuration: v as DurationOption | null })}
              />
            )}
            {step === 4 && (
              <StepLikedDests
                dests={state.likedDests}
                onChange={(dests) => update({ likedDests: dests })}
              />
            )}
            {step === 5 && (
              <StepRiskVisaLang
                riskTolerance={state.riskTolerance}
                visaTolerance={state.visaTolerance}
                languageComfort={state.languageComfort}
                onRiskChange={(v) => update({ riskTolerance: v })}
                onVisaChange={(v) => update({ visaTolerance: v as VisaTolerance })}
                onLanguageChange={(v) => update({ languageComfort: v as LanguageOption[] })}
              />
            )}
            {step === 6 && (
              <StepClimateNotes
                crowdPreference={state.crowdPreference}
                climatePreferences={state.climatePreferences}
                freeTextNotes={state.freeTextNotes}
                onCrowdChange={(v) => update({ crowdPreference: v })}
                onClimateChange={(v) => update({ climatePreferences: v as ClimatePref[] })}
                onNotesChange={(v) => update({ freeTextNotes: v })}
              />
            )}
          </div>
        </div>

        <div
          className="shrink-0 border-t border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-elevated))] px-5 py-3"
          style={{ paddingBottom: 'max(env(safe-area-inset-bottom, 0px), 16px)' }}
        >
          <Button
            onClick={isLastStep ? handleSave : () => setStep((s) => s + 1)}
            disabled={patchMutation.isPending}
            className="mb-2 h-[52px] w-full rounded-2xl shadow-[0_4px_16px_rgba(37,99,235,0.28)]"
          >
            {patchMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {isLastStep ? 'Сохранить' : 'Далее'}
          </Button>
          {!isLastStep && (
            <Button
              variant="ghost"
              onClick={handleSave}
              disabled={patchMutation.isPending}
              className="h-[44px] w-full text-[14px] text-stone-400"
            >
              Сохранить
            </Button>
          )}
        </div>
      </DrawerContent>
    </Drawer>
  );
};
