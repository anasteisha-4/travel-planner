import type { Trip } from '@/entities/trip';
import { BUDGET_LIMITS, CURRENCIES } from '@/shared/config';
import { cn } from '@/shared/lib/utils';
import {
  Button,
  DateInput,
  FormError,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Slider,
  Textarea,
} from '@/shared/ui';
import { Loader2, MapPin, Minus, Plus } from 'lucide-react';
import { useTripForm } from '../model/useTripForm';
import { TripFormSkeleton } from './TripFormSkeleton';

const inputBase =
  'h-[52px] w-full rounded-[14px] border border-stone-200 bg-stone-100 px-3.5 text-[15px] font-semibold text-stone-900 outline-none placeholder:font-normal placeholder:text-stone-400 focus:border-primary focus:border-[1.5px] dark:border-stone-700 dark:bg-stone-800 dark:text-white dark:placeholder:text-stone-500';

const inputError = 'bg-red-50 border-stone-200 dark:bg-red-900/20 dark:border-stone-700';

export const TripForm = ({
  existingTrip,
  onSuccess,
  onCancel,
  asSheet,
}: {
  existingTrip?: Trip;
  onSuccess: (trip: Trip) => void;
  onCancel?: () => void;
  asSheet?: boolean;
}) => {
  const {
    destination,
    setDestination,
    startDate,
    handleStartDateChange,
    endDate,
    setEndDate,
    departureCity,
    setDepartureCity,
    budget,
    setBudget,
    currency,
    currencySymbol,
    handleCurrencyChange,
    peopleCount,
    incrementPeople,
    decrementPeople,
    notes,
    setNotes,
    isLoading,
    isInitialLoading,
    errors,
    clearError,
    todayStr,
    handleCreate,
    handleUpdate,
  } = useTripForm(existingTrip);

  const budgetConfig = BUDGET_LIMITS[currency] ?? BUDGET_LIMITS['USD'];

  if (isInitialLoading) return <TripFormSkeleton />;

  const handleSubmit = async () => {
    const trip = existingTrip ? await handleUpdate(existingTrip.id) : await handleCreate();
    if (trip) onSuccess(trip);
  };

  return (
    <div className="flex flex-col gap-3">
      {/* Destination + People */}
      <div className="grid grid-cols-[1fr,auto] items-start gap-3">
        <div>
          <Label className="mb-1 block text-[11px] font-semibold uppercase tracking-widest text-stone-400 dark:text-stone-500">
            Куда
          </Label>
          <div className="relative">
            <MapPin className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400 dark:text-stone-500" />
            <input
              value={destination}
              onChange={(e) => {
                setDestination(e.target.value);
                clearError('destination');
              }}
              placeholder="Направление"
              className={cn(inputBase, 'pl-10', errors.destination && inputError)}
            />
          </div>
          <FormError message={errors.destination} className="mt-2" />
        </div>

        <div>
          <Label className="mb-1 block text-[11px] font-semibold uppercase tracking-widest text-stone-400 dark:text-stone-500">
            Люди
          </Label>
          <div className="flex h-[52px] items-center gap-2 rounded-2xl border border-stone-200 bg-stone-100 px-2.5 dark:border-stone-700 dark:bg-stone-800">
            <button
              type="button"
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-stone-200 bg-white text-stone-700 disabled:opacity-40 dark:border-stone-600 dark:bg-stone-700 dark:text-stone-200"
              onClick={decrementPeople}
              disabled={peopleCount <= 1}
            >
              <Minus className="h-3.5 w-3.5" />
            </button>
            <span className="w-6 text-center text-lg font-extrabold tabular-nums text-stone-900 dark:text-white">
              {peopleCount}
            </span>
            <button
              type="button"
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary text-white disabled:opacity-40"
              onClick={incrementPeople}
              disabled={peopleCount >= 20}
            >
              <Plus className="h-3.5 w-3.5" />
            </button>
          </div>
          <div className="min-h-[14px]" />
        </div>
      </div>

      {/* Departure city */}
      <div>
        <Label className="mb-1 block text-[11px] font-semibold uppercase tracking-widest text-stone-400 dark:text-stone-500">
          Откуда
        </Label>
        <input
          value={departureCity}
          onChange={(e) => {
            setDepartureCity(e.target.value);
            clearError('departure_city');
          }}
          placeholder="Москва, Россия"
          className={cn(inputBase, errors.departure_city && inputError)}
        />
        <FormError message={errors.departure_city} className="mt-2" />
      </div>

      {/* Dates */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label className="mb-1 block text-[11px] font-semibold uppercase tracking-widest text-stone-400 dark:text-stone-500">
            Начало
          </Label>
          <DateInput
            value={startDate}
            min={todayStr}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
              handleStartDateChange(e.target.value);
              clearError('start_date');
            }}
            className={cn(
              'h-[52px] rounded-[14px] border-stone-200 bg-stone-100 dark:border-stone-700 dark:bg-stone-800 dark:text-white',
              errors.start_date && inputError
            )}
          />
          <FormError message={errors.start_date} className="mt-2" />
        </div>
        <div>
          <Label className="mb-1 block text-[11px] font-semibold uppercase tracking-widest text-stone-400 dark:text-stone-500">
            Конец
          </Label>
          <DateInput
            value={endDate}
            min={startDate || todayStr}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
              setEndDate(e.target.value);
              clearError('end_date');
            }}
            className={cn(
              'h-[52px] rounded-[14px] border-stone-200 bg-stone-100 dark:border-stone-700 dark:bg-stone-800 dark:text-white',
              errors.end_date && inputError
            )}
          />
          <FormError message={errors.end_date} className="mt-2" />
        </div>
      </div>

      {/* Budget slider */}
      <div>
        <div className="mb-2 flex items-center justify-between">
          <Label className="text-[11px] font-semibold uppercase tracking-widest text-stone-400 dark:text-stone-500">
            Бюджет
          </Label>
          <span className="text-[15px] font-bold text-stone-900 dark:text-white">
            {budget > 0 ? `${budget.toLocaleString('ru-RU')} ${currencySymbol}` : 'Без лимита'}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <Select value={currency} onValueChange={handleCurrencyChange}>
            <SelectTrigger className="h-[44px] w-[105px] shrink-0 rounded-2xl border-stone-200 bg-stone-100 text-[13px] font-semibold dark:border-stone-700 dark:bg-stone-800 dark:text-white">
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
          <div className="flex-1">
            <Slider
              value={[budget]}
              min={budgetConfig.min}
              max={budgetConfig.max}
              step={budgetConfig.step}
              onValueChange={([val]) => setBudget(val)}
            />
          </div>
        </div>
      </div>

      {/* Notes */}
      <div className="space-y-2">
        <div className="flex min-h-[20px] items-center justify-between">
          <Label className="text-[11px] font-semibold uppercase tracking-widest text-stone-400 animate-in fade-in dark:text-stone-500">
            Заметки
          </Label>
        </div>
        <div
          className={cn('grid grid-rows-[1fr] opacity-100 transition-all duration-200 ease-in-out')}
        >
          <div className="overflow-hidden">
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Дополнительная информация о поездке"
              className="mt-1.5 min-h-[80px] resize-none rounded-2xl border-stone-200 bg-stone-100 text-[15px] placeholder:text-stone-400 dark:border-stone-700 dark:bg-stone-800 dark:text-white dark:placeholder:text-stone-500"
            />
          </div>
        </div>
      </div>

      {/* Spacer for fixed bottom bar in page mode */}
      {!asSheet && <div className="h-[80px]" />}

      {/* Action buttons */}
      <div
        className={cn(
          'flex gap-3',
          !asSheet
            ? 'fixed bottom-0 left-0 right-0 z-50 border-t border-stone-100 bg-white px-5 py-3 dark:border-stone-800 dark:bg-stone-950'
            : 'pt-2'
        )}
        style={
          !asSheet ? { paddingBottom: 'max(env(safe-area-inset-bottom, 0px), 12px)' } : undefined
        }
      >
        {onCancel && (
          <Button
            variant="outline"
            onClick={onCancel}
            disabled={isLoading}
            className="h-[52px] flex-1 rounded-2xl border-stone-200 bg-stone-100 text-stone-700 dark:border-stone-700 dark:bg-stone-800 dark:text-stone-200"
          >
            Отмена
          </Button>
        )}
        <Button
          onClick={handleSubmit}
          disabled={isLoading}
          className={cn(
            'h-[52px] rounded-2xl shadow-[0_4px_16px_rgba(37,99,235,0.28)]',
            asSheet ? 'flex-[2]' : 'flex-1'
          )}
        >
          {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {existingTrip ? 'Сохранить' : 'Создать поездку'}
        </Button>
      </div>
    </div>
  );
};
