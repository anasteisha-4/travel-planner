import { authAPI } from '@/api/auth';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import { ArrowLeft, SkipForward } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const TRAVEL_TYPES = [
  { id: 'beach', label: '🏖️ Пляжный' },
  { id: 'family', label: '👨‍👩‍👧 Семейный' },
  { id: 'culture', label: '🏛️ Культура и история' },
  { id: 'active', label: '🚴 Активный' },
  { id: 'extreme', label: '🧗 Экстремальный' },
  { id: 'shopping', label: '🛍️ Шопинг' },
  { id: 'gastro', label: '🍽️ Гастрономический' },
  { id: 'nature', label: '🌲 Природа и эко' },
  { id: 'romantic', label: '💕 Романтический' },
  { id: 'business', label: '💼 Деловой' },
];

const TRIP_DURATIONS = [
  { id: 'weekend', label: 'Выходные' },
  { id: 'week', label: 'Неделя' },
  { id: 'two_weeks', label: '2 недели' },
  { id: 'month', label: 'Месяц+' },
];

const CURRENCIES = [
  { value: 'RUB', label: '₽ Рубль' },
  { value: 'USD', label: '$ Доллар' },
  { value: 'EUR', label: '€ Евро' },
  { value: 'GBP', label: '£ Фунт' },
  { value: 'TRY', label: '₺ Лира' },
  { value: 'CNY', label: '¥ Юань' },
];

const BUDGET_LIMITS: Record<string, { min: number; max: number; step: number; format: (v: number) => string }> = {
  RUB: { min: 0, max: 1000000, step: 10000, format: (v) => `${(v / 1000).toFixed(0)}тыс ₽` },
  USD: { min: 0, max: 10000, step: 100, format: (v) => `$${v}` },
  EUR: { min: 0, max: 10000, step: 100, format: (v) => `€${v}` },
  GBP: { min: 0, max: 8000, step: 100, format: (v) => `£${v}` },
  TRY: { min: 0, max: 350000, step: 5000, format: (v) => `${(v / 1000).toFixed(0)}тыс ₺` },
  CNY: { min: 0, max: 75000, step: 1000, format: (v) => `¥${v}` },
};

export const Onboarding = () => {
  const [step, setStep] = useState(1);
  const [travelTypes, setTravelTypes] = useState<string[]>([]);
  const [destinations, setDestinations] = useState('');
  const [currency, setCurrency] = useState('RUB');
  const [budgetRange, setBudgetRange] = useState<[number, number]>([0, 100000]);
  const [tripDuration, setTripDuration] = useState<string | null>(null);
  const [additionalInfo, setAdditionalInfo] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const navigate = useNavigate();
  const { toast } = useToast();

  const toggleTravelType = (id: string) => {
    setTravelTypes(prev =>
      prev.includes(id) ? prev.filter(t => t !== id) : [...prev, id]
    );
  };

  const handleSkip = async () => {
    setIsLoading(true);
    try {
      await authAPI.updatePreferences({
        travel_types: [],
        favorite_destinations: null,
        currency: 'RUB',
        budget_min: null,
        budget_max: null,
        trip_duration: null,
        additional_info: null,
      });
      navigate('/dashboard', { replace: true });
    } catch {
      navigate('/dashboard', { replace: true });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    setIsLoading(true);
    try {
      await authAPI.updatePreferences({
        travel_types: travelTypes,
        favorite_destinations: destinations || null,
        currency,
        budget_min: budgetRange[0] || null,
        budget_max: budgetRange[1] || null,
        trip_duration: tripDuration,
        additional_info: additionalInfo || null,
      });
      navigate('/dashboard', { replace: true });
    } catch {
      toast({ variant: 'destructive', title: 'Ошибка', description: 'Не удалось сохранить предпочтения' });
    } finally {
      setIsLoading(false);
    }
  };

  const budgetConfig = BUDGET_LIMITS[currency] || BUDGET_LIMITS.RUB;

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
                <Select value={currency} onValueChange={(v) => {
                  setCurrency(v);
                  const config = BUDGET_LIMITS[v] || BUDGET_LIMITS.RUB;
                  setBudgetRange([config.min, Math.round(config.max * 0.4)]);
                }}>
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
