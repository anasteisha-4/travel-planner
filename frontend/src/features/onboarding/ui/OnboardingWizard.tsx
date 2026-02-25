import { Badge } from '@/shared/ui';
import { Button } from '@/shared/ui';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui';
import { Label } from '@/shared/ui';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui';
import { Slider } from '@/shared/ui';
import { Textarea } from '@/shared/ui';
import { ArrowLeft, Loader2, SkipForward } from 'lucide-react';
import { CURRENCIES, TRAVEL_TYPES, TRIP_DURATIONS } from '../config/constants';
import { useOnboarding } from '../model/useOnboarding';

export const OnboardingWizard = ({ 
  onComplete,
  onSkip
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
    additionalInfo,
    setAdditionalInfo,
    isLoading,
    handleSkip,
    handleSave,
    budgetConfig,
  } = useOnboarding({ onComplete, onSkip });

  return (
    <div className="flex flex-1 items-center justify-center p-4">
      <Card className="w-full max-w-lg mx-auto glass-card">
        <CardHeader className="text-center space-y-2">
          <CardTitle className="text-2xl font-bold tracking-tight">
            {step === 1 ? 'Расскажите о себе' : 'Ещё пара вопросов'}
          </CardTitle>
          <CardDescription>
            Шаг {step} из 2
          </CardDescription>
          <div className="flex gap-2 justify-center pt-2">
            <div className={`h-1.5 w-16 rounded-full transition-colors ${step >= 1 ? 'bg-primary' : 'bg-muted'}`} />
            <div className={`h-1.5 w-16 rounded-full transition-colors ${step >= 2 ? 'bg-primary' : 'bg-muted'}`} />
          </div>
        </CardHeader>

        <CardContent className="space-y-6">
          {step === 1 ? (
            <>
              <div className="space-y-3">
                <Label className="text-base font-semibold">Любимые виды отдыха</Label>
                <div className="flex flex-wrap gap-2">
                  {TRAVEL_TYPES.map(type => (
                    <Badge
                      key={type.id}
                      variant={travelTypes.includes(type.id) ? 'default' : 'outline'}
                      className="cursor-pointer text-sm py-2 px-3 transition-all active:scale-95 select-none"
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
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CURRENCIES.map(c => (
                      <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
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
                <div className="flex justify-between text-sm text-muted-foreground font-medium">
                  <span>{budgetConfig.format(budgetRange[0])}</span>
                  <span>{budgetConfig.format(budgetRange[1])}</span>
                </div>
              </div>

              <div className="space-y-3">
                <Label className="text-base font-semibold">Обычная длительность поездок</Label>
                <div className="flex flex-wrap gap-2">
                  {TRIP_DURATIONS.map(d => (
                    <Badge
                      key={d.id}
                      variant={tripDuration === d.id ? 'default' : 'outline'}
                      className="cursor-pointer text-sm py-2 px-4 transition-all active:scale-95 select-none"
                      onClick={() => setTripDuration(tripDuration === d.id ? null : d.id)}
                    >
                      {d.label}
                    </Badge>
                  ))}
                </div>
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

          <div className="flex flex-col gap-3 pt-2">
            <div className="flex gap-3">
              {step === 2 && (
               <Button
                  variant="outline"
                  onClick={() => setStep(1)}
                  disabled={isLoading}
                  className="flex-1"
                >
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Назад
                </Button>
              )}
              <Button
                onClick={step === 1 ? () => setStep(2) : handleSave}
                disabled={isLoading}
                className="flex-1"
              >
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {step === 1 ? 'Далее' : 'Сохранить'}
              </Button>
            </div>
            <Button
              variant="ghost"
              onClick={handleSkip}
              disabled={isLoading}
              className="text-muted-foreground"
            >
              <SkipForward className="mr-2 h-4 w-4" />
              Заполнить позже
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
