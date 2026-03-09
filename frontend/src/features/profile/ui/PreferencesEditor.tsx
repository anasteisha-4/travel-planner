import { CURRENCIES, TRAVEL_TYPES, TRIP_DURATIONS } from '@/shared/config';
import { useIsOnline } from '@/shared/lib';
import {
  Badge,
  Button,
  Input,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  Slider,
  Textarea,
} from '@/shared/ui';
import { ArrowLeft, Loader2 } from 'lucide-react';
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
  const isOnline = useIsOnline();

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
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="bottom" className="h-[90dvh] overflow-y-auto rounded-t-2xl">
        <SheetHeader className="pb-2">
          <SheetTitle className="text-xl font-bold tracking-tight">
            {step === 1 ? 'Предпочтения' : 'Бюджет и детали'}
          </SheetTitle>
          <div className="flex gap-2 pt-2">
            <div
              className={`h-1.5 flex-1 rounded-full transition-colors ${step >= 1 ? 'bg-primary' : 'bg-muted'}`}
            />
            <div
              className={`h-1.5 flex-1 rounded-full transition-colors ${step >= 2 ? 'bg-primary' : 'bg-muted'}`}
            />
          </div>
        </SheetHeader>

        <div className="space-y-6 pt-4">
          {step === 1 ? (
            <>
              <div className="space-y-3">
                <Label className="text-base font-semibold">Любимые виды отдыха</Label>
                <div className="flex flex-wrap gap-2">
                  {TRAVEL_TYPES.map((type) => (
                    <Badge
                      key={type.id}
                      variant={travelTypes.includes(type.id) ? 'default' : 'outline'}
                      className="cursor-pointer select-none px-3 py-2 text-sm transition-all active:scale-95"
                      onClick={() => toggleTravelType(type.id)}
                    >
                      {type.label}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="space-y-3">
                <Label className="text-base font-semibold">Любимые направления</Label>
                <Textarea
                  placeholder="Например: Италия, Япония, Грузия..."
                  value={destinations}
                  onChange={(e) => setDestinations(e.target.value)}
                  className="min-h-[80px] resize-none"
                />
              </div>

              <div className="space-y-3">
                <Label className="text-base font-semibold">Валюта</Label>
                <Select value={currency} onValueChange={handleCurrencyChange}>
                  <SelectTrigger className="h-12 w-full">
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
              <div className="space-y-4">
                <Label className="text-base font-semibold">Средний бюджет поездки</Label>
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
                <div className="flex justify-between text-sm font-medium text-muted-foreground">
                  <span>{budgetConfig.format(budgetRange[0])}</span>
                  <span>{budgetConfig.format(budgetRange[1])}</span>
                </div>
              </div>

              <div className="space-y-3">
                <Label className="text-base font-semibold">Обычная длительность поездок</Label>
                <div className="flex flex-wrap gap-2">
                  {TRIP_DURATIONS.map((d) => (
                    <Badge
                      key={d.id}
                      variant={tripDuration === d.id ? 'default' : 'outline'}
                      className="cursor-pointer select-none px-4 py-2 text-sm transition-all active:scale-95"
                      onClick={() => setTripDuration(tripDuration === d.id ? null : d.id)}
                    >
                      {d.label}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="space-y-3">
                <Label className="text-base font-semibold">Город отправления</Label>
                <Input
                  placeholder="Например: Россия, Москва"
                  value={departureCity}
                  onChange={(e) => setDepartureCity(e.target.value)}
                  className="h-12"
                />
              </div>

              <div className="space-y-3">
                <Label className="text-base font-semibold">Дополнительная информация</Label>
                <Textarea
                  placeholder="Аллергии, ограничения, пожелания"
                  value={additionalInfo}
                  onChange={(e) => setAdditionalInfo(e.target.value)}
                  className="min-h-[80px] resize-none"
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
                className="h-12 flex-1"
              >
                <ArrowLeft className="mr-2 h-4 w-4" />
                Назад
              </Button>
            )}
            <Button
              onClick={step === 1 ? () => setStep(2) : onSubmit}
              disabled={isLoading || (!isOnline && step === 2)}
              className="h-12 flex-1"
            >
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {step === 1 ? 'Далее' : 'Сохранить'}
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
};
