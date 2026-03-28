import type { Trip } from '@/entities/trip';
import { BUDGET_LIMITS, CURRENCIES } from '@/shared/config';
import { cn } from '@/shared/lib/utils';
import {
  AppInput,
  Button,
  DateInput,
  FieldLabel,
  FormError,
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
    isConverting,
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

  const inputError = 'bg-red-50 border-stone-200 dark:bg-red-900/20 dark:border-stone-700';

  return (
    <div className="flex flex-col gap-2">
      {/* Destination + People */}
      <div className="grid grid-cols-[1fr,auto] items-start gap-3">
        <div>
          <FieldLabel>Куда</FieldLabel>
          <div className="relative">
            <MapPin className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400 dark:text-stone-500" />
            <AppInput
              value={destination}
              onChange={(e) => {
                setDestination(e.target.value);
                clearError('destination');
              }}
              placeholder="Город или страна"
              error={!!errors.destination}
              className="pl-10"
            />
          </div>
          <FormError message={errors.destination} />
        </div>

        <div>
          <FieldLabel>Люди</FieldLabel>
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
          <div className="min-h-[11px]" />
        </div>
      </div>

      {/* Departure city */}
      <div>
        <FieldLabel>Откуда</FieldLabel>
        <div className="relative">
          <MapPin className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400 dark:text-stone-500" />
          <AppInput
            value={departureCity}
            onChange={(e) => {
              setDepartureCity(e.target.value);
              clearError('departure_city');
            }}
            placeholder="Пункт отправления"
            error={!!errors.departure_city}
            className="pl-10"
          />
        </div>
        <FormError message={errors.departure_city} />
      </div>

      {/* Dates */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <FieldLabel>Начало</FieldLabel>
          <DateInput
            value={startDate}
            min={todayStr}
            placeholder="Дата"
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
              handleStartDateChange(e.target.value);
              clearError('start_date');
            }}
            className={cn(
              'h-[52px] rounded-[14px] border-stone-200 bg-stone-100 dark:border-stone-700 dark:bg-stone-800',
              errors.start_date && inputError
            )}
          />
          <FormError message={errors.start_date} />
        </div>
        <div>
          <FieldLabel>Конец</FieldLabel>
          <DateInput
            value={endDate}
            min={startDate || todayStr}
            placeholder="Дата"
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
              setEndDate(e.target.value);
              clearError('end_date');
            }}
            className={cn(
              'h-[52px] rounded-[14px] border-stone-200 bg-stone-100 dark:border-stone-700 dark:bg-stone-800',
              errors.end_date && inputError
            )}
          />
          <FormError message={errors.end_date} />
        </div>
      </div>

      {/* Budget slider */}
      <div>
        <div className="mb-2 flex items-center justify-between">
          <FieldLabel className="mb-0">Бюджет</FieldLabel>
          <span className="flex items-center gap-1.5 text-[15px] font-bold text-stone-900 dark:text-white">
            {isConverting && <Loader2 className="h-3.5 w-3.5 animate-spin text-stone-400" />}
            {budget > 0 ? `${budget.toLocaleString('ru-RU')} ${currencySymbol}` : 'Без лимита'}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <Select value={currency} onValueChange={handleCurrencyChange}>
            <SelectTrigger className="h-[52px] w-[120px] shrink-0 rounded-2xl border-stone-200 bg-stone-100 text-[13px] font-semibold dark:border-stone-700 dark:bg-stone-800 dark:text-white">
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
              disabled={isConverting}
            />
          </div>
        </div>
      </div>

      {/* Notes */}
      <div className="mt-[20px]">
        <FieldLabel>Заметки</FieldLabel>
        <Textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Аллергии, особые пожелания"
          className="mb-4 min-h-[92px] resize-none rounded-2xl border-stone-200 bg-stone-100 text-[15px] placeholder:text-stone-400 dark:border-stone-700 dark:bg-stone-800 dark:text-white dark:placeholder:text-stone-500"
        />
      </div>

      {/* Action buttons */}
      <div
        className={cn(
          'flex gap-3',
          !asSheet
            ? 'fixed bottom-0 left-0 right-0 z-50 border-t border-stone-100 bg-white px-5 py-3 dark:border-stone-800 dark:bg-stone-950'
            : 'pt-2'
        )}
        style={
          !asSheet ? { paddingBottom: 'max(env(safe-area-inset-bottom, 0px), 24px)' } : undefined
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
