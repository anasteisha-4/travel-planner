import { ChevronLeft, Loader2 } from 'lucide-react';

import {
  AppPageHeader,
  Button,
  PageContent,
  PageLayout,
  StepIndicator,
} from '@/shared/ui';
import { sendEvent } from '@/shared/api';
import { HAPTIC_SINGLE_TAP, useHapticFeedback } from '@/shared/lib/useHapticFeedback';

import { useOnboardingV2 } from '../model/useOnboardingV2';
import type { ClimatePref, DurationOption, LanguageOption, RestLevel, VisaTolerance } from '../model/types';
import { StepBudgetDuration } from './StepBudgetDuration';
import { StepClimateNotes } from './StepClimateNotes';
import { StepLikedDests } from './StepLikedDests';
import { StepOriginCity } from './StepOriginCity';
import { StepRiskVisaLang } from './StepRiskVisaLang';
import { StepVacationPrefs } from './StepVacationPrefs';

const STEP_META = [
  { title: 'Виды отдыха', subtitle: 'Расскажите о себе' },
  { title: 'Бюджет', subtitle: 'Финансовые предпочтения' },
  { title: 'Откуда летаете', subtitle: 'Город и длительность' },
  { title: 'Любимые места', subtitle: 'Ваши фавориты' },
  { title: 'Безопасность и визы', subtitle: 'Ограничения и комфорт' },
  { title: 'Климат и атмосфера', subtitle: 'Финальные штрихи' },
];


type Props = {
  onComplete: () => void;
};

export const OnboardingV2Wizard = ({ onComplete }: Props) => {
  const { play } = useHapticFeedback();
  const {
    currentStep,
    vacationPreferencesRanked,
    preferredCurrency,
    budgetMin,
    budgetMax,
    restLevel,
    typicalDuration,
    originCityName,
    likedDests,
    riskTolerance,
    visaTolerance,
    languageComfort,
    crowdPreference,
    climatePreferences,
    freeTextNotes,
    isLoading,
    isSaving,
    errors,
    update,
    handleCurrencyChange,
    goNext,
    goBack,
    handleComplete,
    handleSaveAndExit,
  } = useOnboardingV2({ onComplete });

  const meta = STEP_META[currentStep - 1];
  const isLastStep = currentStep === 6;

  if (isLoading) {
    return (
      <PageLayout fullScreen>
        <div className="flex flex-1 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-stone-300" />
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout fullScreen>
      <AppPageHeader pb="pb-4">
        <div className="mb-4 flex items-center gap-3">
          {currentStep > 1 ? (
            <button
              type="button"
              onClick={() => {
                play(HAPTIC_SINGLE_TAP);
                goBack();
              }}
              className="flex h-[38px] w-[38px] items-center justify-center rounded-full border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-muted))] transition-colors active:bg-[hsl(var(--surface-field))]"
            >
              <ChevronLeft className="h-5 w-5 text-foreground" />
            </button>
          ) : (
            <div className="h-[38px] w-[38px]" />
          )}
          <StepIndicator steps={6} current={currentStep} barClassName="w-7" className="flex-1 justify-center" />
          <div className="h-[38px] w-[38px]" />
        </div>
        <div>
          <p className="mb-0.5 text-[11px] font-bold uppercase tracking-[0.07em] text-muted-foreground">
            Шаг {currentStep} из 6
          </p>
          <h1 className="text-[22px] font-extrabold tracking-tight text-foreground">
            {meta.title}
          </h1>
          <p className="text-[14px] text-muted-foreground">{meta.subtitle}</p>
        </div>
      </AppPageHeader>

      <PageContent pb="pb-36" scrollHaptic>
        <div
          key={currentStep}
          className="animate-in fade-in slide-in-from-right-4 duration-200"
        >
          {currentStep === 1 && (
            <StepVacationPrefs
              selected={vacationPreferencesRanked}
              onChange={(v) => update({ vacationPreferencesRanked: v })}
              error={errors.vacation_preferences_ranked}
            />
          )}
          {currentStep === 2 && (
            <StepBudgetDuration
              currency={preferredCurrency}
              budgetMin={budgetMin}
              budgetMax={budgetMax}
              restLevel={restLevel}
              onCurrencyChange={handleCurrencyChange}
              onBudgetChange={(min, max) => update({ budgetMin: min, budgetMax: max })}
              onRestLevelChange={(v) => {
                if (restLevel !== v) {
                  sendEvent('rest_level_changed', {
                    rest_level: v,
                    previous_rest_level: restLevel,
                    source: 'onboarding',
                  });
                }
                update({ restLevel: v as RestLevel });
              }}
            />
          )}
          {currentStep === 3 && (
            <StepOriginCity
              cityName={originCityName}
              duration={typicalDuration}
              onSelect={({ name, lat, lng }) =>
                update({
                  originCityId: null,
                  originCityName: name,
                  originLat: lat,
                  originLng: lng,
                })
              }
              onDurationChange={(v) => update({ typicalDuration: v as DurationOption | null })}
              cityError={errors.origin_city_name}
              durationError={errors.typical_duration}
            />
          )}
          {currentStep === 4 && (
            <StepLikedDests
              dests={likedDests}
              onChange={(dests) => update({ likedDests: dests })}
            />
          )}
          {currentStep === 5 && (
            <StepRiskVisaLang
              riskTolerance={riskTolerance}
              visaTolerance={visaTolerance}
              languageComfort={languageComfort}
              onRiskChange={(v) => update({ riskTolerance: v })}
              onVisaChange={(v) => update({ visaTolerance: v as VisaTolerance })}
              onLanguageChange={(v) => update({ languageComfort: v as LanguageOption[] })}
            />
          )}
          {currentStep === 6 && (
            <StepClimateNotes
              crowdPreference={crowdPreference}
              climatePreferences={climatePreferences}
              freeTextNotes={freeTextNotes}
              onCrowdChange={(v) => update({ crowdPreference: v })}
              onClimateChange={(v) => update({ climatePreferences: v as ClimatePref[] })}
              onNotesChange={(v) => update({ freeTextNotes: v })}
            />
          )}
        </div>
      </PageContent>

      <div
        className="fixed bottom-0 left-0 right-0 z-50 border-t border-[hsl(var(--surface-border))] bg-[hsl(var(--app-bg))] px-5 py-3"
        style={{ paddingBottom: 'max(env(safe-area-inset-bottom, 0px), 20px)' }}
      >
        <Button
          haptic={isLastStep ? false : HAPTIC_SINGLE_TAP}
          onClick={isLastStep ? handleComplete : goNext}
          disabled={isSaving}
          className="mb-2 h-[52px] w-full rounded-2xl shadow-[0_4px_16px_rgba(37,99,235,0.28)]"
        >
          {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {isLastStep ? 'Завершить' : 'Далее'}
        </Button>
        <Button
          variant="ghost"
          haptic={false}
          onClick={handleSaveAndExit}
          disabled={isSaving}
          className="h-[44px] w-full text-[14px] text-muted-foreground"
        >
          Заполнить позже
        </Button>
      </div>
    </PageLayout>
  );
};
