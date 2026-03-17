import { CURRENCIES, TRAVEL_TYPES, TRIP_DURATIONS } from '../config/constants';
import { useOnboarding } from '../model/useOnboarding';
import {
  AppInput,
  AppPageHeader,
  Button,
  FieldLabel,
  PageContent,
  PageLayout,
  PillChip,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Slider,
  StepIndicator,
  Textarea,
} from '@/shared/ui';
import { ChevronLeft, Loader2, SkipForward } from 'lucide-react';

export const OnboardingWizard = ({
  onComplete,
  onSkip,
}: {
  onComplete: () => void;
  onSkip: () => void;
}) => {
  const {
    step,
    setStep,
    travelTypes,
    toggleTravelType,
    destinations,
    setDestinations,
    currency,
    handleCurrencyChange,
    budgetRange,
    setBudgetRange,
    tripDuration,
    setTripDuration,
    departureCity,
    setDepartureCity,
    additionalInfo,
    setAdditionalInfo,
    isLoading,
    handleSkip,
    handleSave,
    budgetConfig,
  } = useOnboarding({ onComplete, onSkip });

  return (
    <PageLayout fullScreen>
      <AppPageHeader pb="pb-3">
        <div className="flex items-center justify-between">
          <h1 className="text-[22px] font-extrabold tracking-tight text-stone-900 dark:text-white">
            {step === 1 ? 'Расскажите о себе' : 'Еще пара вопросов'}
          </h1>
          <StepIndicator steps={2} current={step} />
        </div>
      </AppPageHeader>

      <PageContent pb="pb-28">
        {step === 1 ? (
          <div className="flex flex-col gap-5">
            <div>
              <FieldLabel>Любимые виды отдыха</FieldLabel>
              <div className="flex flex-wrap gap-2">
                {TRAVEL_TYPES.map((type) => (
                  <PillChip
                    key={type.id}
                    selected={travelTypes.includes(type.id)}
                    onClick={() => toggleTravelType(type.id)}
                    icon={type.icon}
                  >
                    {type.label}
                  </PillChip>
                ))}
              </div>
            </div>

            <div>
              <FieldLabel>Любимые направления</FieldLabel>
              <Textarea
                placeholder="Например: Италия, Япония, Грузия"
                value={destinations}
                onChange={(e) => setDestinations(e.target.value)}
                className="min-h-[92px] resize-none rounded-[14px] border-stone-200 bg-stone-100 px-3.5 py-3 text-[15px] placeholder:text-stone-400 dark:border-stone-700 dark:bg-stone-800 dark:text-white dark:placeholder:text-stone-500"
              />
            </div>

            <div>
              <FieldLabel>Валюта</FieldLabel>
              <Select value={currency} onValueChange={handleCurrencyChange}>
                <SelectTrigger className="h-[52px] w-full rounded-[14px] border-stone-200 bg-stone-100 text-[15px] font-semibold dark:border-stone-700 dark:bg-stone-800 dark:text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CURRENCIES.map((c) => (
                    <SelectItem key={c.value} value={c.value}>
                      {c.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-5">
            <div>
              <div className="mb-2 flex items-center justify-between">
                <FieldLabel className="mb-0">Средний бюджет поездки</FieldLabel>
              </div>
              <div className="mb-3 flex justify-between">
                <span className="text-[15px] font-bold text-stone-900 dark:text-white">
                  {budgetConfig.format(budgetRange[0])}
                </span>
                <span className="text-[15px] font-bold text-stone-900 dark:text-white">
                  {budgetConfig.format(budgetRange[1])}
                </span>
              </div>
              <div className="px-1">
                <Slider
                  value={budgetRange}
                  onValueChange={(v) => setBudgetRange(v as [number, number])}
                  min={budgetConfig.min}
                  max={budgetConfig.max}
                  step={budgetConfig.step}
                  className="w-full"
                />
              </div>
            </div>

            <div>
              <FieldLabel>Обычная длительность поездок</FieldLabel>
              <div className="flex flex-wrap gap-2">
                {TRIP_DURATIONS.map((d) => (
                  <PillChip
                    key={d.id}
                    selected={tripDuration === d.id}
                    onClick={() => setTripDuration(tripDuration === d.id ? null : d.id)}
                  >
                    {d.label}
                  </PillChip>
                ))}
              </div>
            </div>

            <div>
              <FieldLabel>Город отправления</FieldLabel>
              <AppInput
                value={departureCity}
                onChange={(e) => setDepartureCity(e.target.value)}
                placeholder="Например: Москва"
              />
            </div>

            <div>
              <FieldLabel>Дополнительная информация</FieldLabel>
              <Textarea
                placeholder="Аллергии, ограничения, пожелания"
                value={additionalInfo}
                onChange={(e) => setAdditionalInfo(e.target.value)}
                className="min-h-[92px] resize-none rounded-[14px] border-stone-200 bg-stone-100 px-3.5 py-3 text-[15px] placeholder:text-stone-400 dark:border-stone-700 dark:bg-stone-800 dark:text-white dark:placeholder:text-stone-500"
              />
            </div>
          </div>
        )}
      </PageContent>

      <div
        className="fixed bottom-0 left-0 right-0 z-50 border-t border-stone-100 bg-white px-5 py-3 dark:border-stone-800 dark:bg-stone-950"
        style={{ paddingBottom: 'max(env(safe-area-inset-bottom, 0px), 24px)' }}
      >
        <div className="flex gap-3">
          {step === 2 && (
            <Button
              variant="outline"
              onClick={() => setStep(1)}
              disabled={isLoading}
              className="h-[52px] flex-1 rounded-2xl border-stone-200 bg-stone-100 text-stone-700 dark:border-stone-700 dark:bg-stone-800 dark:text-stone-200"
            >
              <ChevronLeft className="h-5 w-5" />
              Назад
            </Button>
          )}
          <Button
            onClick={step === 1 ? () => setStep(2) : handleSave}
            disabled={isLoading}
            className="h-[52px] flex-1 rounded-2xl shadow-[0_4px_16px_rgba(37,99,235,0.28)]"
          >
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {step === 1 ? 'Далее' : 'Сохранить'}
          </Button>
        </div>
        <Button
          variant="ghost"
          onClick={handleSkip}
          disabled={isLoading}
          className="mt-1 h-[52px] w-full text-stone-400 dark:text-stone-500"
        >
          <SkipForward className="mr-1.5 h-3.5 w-3.5" />
          Заполнить позже
        </Button>
      </div>
    </PageLayout>
  );
};
