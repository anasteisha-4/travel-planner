import { destinationApi, type DestinationSearchResult } from '@/entities/destination';
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
import { useQuery } from '@tanstack/react-query';
import { Check, Loader2, MapPin, Minus, Plus, X } from 'lucide-react';
import type { ReactNode } from 'react';
import { useEffect, useRef, useState } from 'react';
import { type TripFormInitialValues, type TripFormSnapshot, useTripForm } from '../model/useTripForm';

type DestinationSearchInputProps = {
  label: string;
  value: string;
  placeholder: string;
  error?: string;
  onChange: (value: string) => void;
  onSelect: (dest: DestinationSearchResult) => void;
  onClearError: () => void;
};

const DestinationSearchInput = ({
  label,
  value,
  placeholder,
  error,
  onChange,
  onSelect,
  onClearError,
}: DestinationSearchInputProps) => {
  const [debouncedQuery, setDebouncedQuery] = useState(value);
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setDebouncedQuery(value);
    }, 400);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [value]);

  const { data: results = [], isFetching } = useQuery({
    queryKey: ['destination-search', debouncedQuery],
    queryFn: () => destinationApi.searchDestinations(debouncedQuery, 8),
    enabled: open && debouncedQuery.trim().length >= 2,
    staleTime: 1000 * 60 * 10,
  });

  const handleInput = (nextValue: string) => {
    onChange(nextValue);
    onClearError();
    setOpen(true);
  };

  const handleSelect = (dest: DestinationSearchResult) => {
    onSelect(dest);
    onClearError();
    setOpen(false);
    inputRef.current?.blur();
  };

  const showDropdown = open && debouncedQuery.trim().length >= 2 && (results.length > 0 || isFetching);

  return (
    <div>
      <FieldLabel>{label}</FieldLabel>
      <div className="relative">
        <div className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2">
          {isFetching ? (
            <Loader2 className="h-4 w-4 animate-spin text-stone-400 dark:text-stone-500" />
          ) : (
            <MapPin className="h-4 w-4 text-stone-400 dark:text-stone-500" />
          )}
        </div>
        <AppInput
          ref={inputRef}
          value={value}
          onChange={(e) => handleInput(e.target.value)}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          placeholder={placeholder}
          error={!!error}
          className="pl-10 pr-10"
        />
        {!isFetching && (value || error) && (
          <div className="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2">
            {error ? (
              <X className="h-4 w-4 text-red-500" />
            ) : value ? (
              <Check className="h-4 w-4 text-green-500" />
            ) : null}
          </div>
        )}
      </div>
      <FormError message={error} />

      {showDropdown && (
        <div className="mt-1.5 overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-[0_8px_24px_rgba(0,0,0,0.1)] dark:border-stone-700 dark:bg-stone-900">
          {isFetching && results.length === 0 ? (
            <div className="flex items-center gap-2 px-4 py-3 text-[14px] text-stone-400">
              <Loader2 className="h-4 w-4 animate-spin" />
              Поиск...
            </div>
          ) : (
            results.map((dest) => (
              <button
                key={dest.id}
                type="button"
                onMouseDown={(event) => {
                  event.preventDefault();
                  handleSelect(dest);
                }}
                className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-stone-50 active:bg-stone-100 dark:hover:bg-stone-800 dark:active:bg-stone-800 [&:not(:last-child)]:border-b [&:not(:last-child)]:border-stone-100 dark:[&:not(:last-child)]:border-stone-800"
              >
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-stone-100 dark:bg-stone-800">
                  <MapPin className="h-3.5 w-3.5 text-stone-500" />
                </div>
                <div>
                  <p className="text-[14px] font-semibold text-stone-900 dark:text-white">{dest.name}</p>
                  <p className="text-[12px] text-stone-400">{dest.country_code}</p>
                </div>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export const TripForm = ({
  existingTrip,
  initialValues,
  onSuccess,
  onCancel,
  asSheet,
  onSnapshotChange,
  validationSlot,
}: {
  existingTrip?: Trip;
  initialValues?: TripFormInitialValues;
  onSuccess: (trip: Trip) => void;
  onCancel?: () => void;
  asSheet?: boolean;
  onSnapshotChange?: (snapshot: TripFormSnapshot) => void;
  validationSlot?: ReactNode;
}) => {
  const {
    destination,
    handleDestinationInput,
    handleDestinationSelect,
    startDate,
    handleStartDateChange,
    endDate,
    setEndDate,
    departureCity,
    handleDepartureCityInput,
    handleDepartureCitySelect,
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
    isConverting,
    errors,
    clearError,
    todayStr,
    handleCreate,
    handleUpdate,
  } = useTripForm(existingTrip, initialValues, onSnapshotChange);

  const budgetConfig = BUDGET_LIMITS[currency] ?? BUDGET_LIMITS['USD'];

  const handleSubmit = async () => {
    const trip = existingTrip ? await handleUpdate(existingTrip.id) : await handleCreate();
    if (trip) onSuccess(trip);
  };

  const inputError = 'bg-red-50 border-stone-200 dark:bg-red-900/20 dark:border-stone-700';

  return (
    <div className="flex flex-col gap-2">
      {/* Destination + People */}
      <div className="grid grid-cols-[1fr,auto] items-start gap-3">
        <DestinationSearchInput
          label="Куда"
          value={destination}
          placeholder="Город или страна"
          error={errors.destination}
          onChange={handleDestinationInput}
          onSelect={handleDestinationSelect}
          onClearError={() => clearError('destination')}
        />

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
      <DestinationSearchInput
        label="Откуда"
        value={departureCity}
        placeholder="Пункт отправления"
        error={errors.departure_city}
        onChange={handleDepartureCityInput}
        onSelect={handleDepartureCitySelect}
        onClearError={() => clearError('departure_city')}
      />

      {/* Dates */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <FieldLabel>Начало</FieldLabel>
          <DateInput
            value={startDate}
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

      {validationSlot}

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
