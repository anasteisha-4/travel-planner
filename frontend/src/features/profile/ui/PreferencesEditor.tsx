import { CURRENCIES, TRAVEL_TYPES, TRIP_DURATIONS } from '@/shared/config';
import {
  AppInput,
  Button,
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
  FieldLabel,
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
import { ChevronLeft, Loader2 } from 'lucide-react';
import { useEffect } from 'react';
import { usePreferencesEditor } from '../model/usePreferencesEditor';

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

export const PreferencesEditor = ({
  open,
  onOpenChange,
  initialData,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialData: PreferencesData;
  onSaved: () => void;
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
    handleSave,
    budgetConfig,
    reset,
  } = usePreferencesEditor(initialData);

  useEffect(() => {
    if (open) {
      reset(initialData);
    }
  }, [open, initialData, reset]);

  const onSubmit = async () => {
    const success = await handleSave();
    if (success) {
      onSaved();
      onOpenChange(false);
    }
  };

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent className="h-[90dvh] overflow-y-auto px-5">
        <DrawerHeader className="px-0 pb-2">
          <DrawerTitle className="text-[22px] font-extrabold tracking-tight text-stone-900 dark:text-white">
            {step === 1 ? 'Предпочтения' : 'Бюджет и детали'}
          </DrawerTitle>
          <StepIndicator steps={2} current={step} barClassName="flex-1" className="pt-2" />
        </DrawerHeader>

        <div className="flex flex-col gap-5 pt-4">
          {step === 1 ? (
            <>
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
            </>
          ) : (
            <>
              <div>
                <FieldLabel>Средний бюджет поездки</FieldLabel>
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
            </>
          )}

          <div className="flex gap-3 pb-4 pt-2">
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
              onClick={step === 1 ? () => setStep(2) : onSubmit}
              disabled={isLoading}
              className="h-[52px] flex-1 rounded-2xl shadow-[0_4px_16px_rgba(37,99,235,0.28)]"
            >
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {step === 1 ? 'Далее' : 'Сохранить'}
            </Button>
          </div>
        </div>
      </DrawerContent>
    </Drawer>
  );
};
