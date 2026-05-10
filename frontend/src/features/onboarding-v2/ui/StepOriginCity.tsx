import { useQuery } from '@tanstack/react-query';
import { MapPin, Loader2, Check, X } from 'lucide-react';
import { useRef, useState } from 'react';

import { useDebouncedValue } from '@/shared/lib';
import { HAPTIC_SINGLE_CONFIRM, HAPTIC_SINGLE_TAP, useHapticFeedback } from '@/shared/lib/useHapticFeedback';
import { useScrollHaptics } from '@/shared/lib/useScrollHaptics';
import { cn } from '@/shared/lib/utils';
import { DURATION_OPTIONS } from '@/shared/config';
import { AppInput, FieldLabel } from '@/shared/ui';

import { onboardingV2Api } from '../api/onboarding-v2.api';
import type { DestinationSearchResult } from '../api/onboarding-v2.api';
import type { DurationOption } from '../model/types';

type Props = {
  cityName: string;
  duration: DurationOption | null;
  onSelect: (city: { name: string; lat: number | null; lng: number | null }) => void;
  onDurationChange: (v: DurationOption | null) => void;
  cityError?: string;
  durationError?: string;
};

export const StepOriginCity = ({ cityName, duration, onSelect, onDurationChange, cityError, durationError }: Props) => {
  const { play } = useHapticFeedback();
  const dropdownScrollHaptics = useScrollHaptics();
  const [inputValue, setInputValue] = useState(cityName);
  const debouncedQuery = useDebouncedValue(inputValue, 400);
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const { data: results = [], isFetching } = useQuery({
    queryKey: ['destination-search', debouncedQuery],
    queryFn: () => onboardingV2Api.searchDestinations(debouncedQuery, 8),
    enabled: debouncedQuery.trim().length >= 2,
    staleTime: 1000 * 60 * 10,
  });

  const handleInput = (value: string) => {
    setInputValue(value);
    setOpen(true);
    if (!value.trim()) {
      onSelect({ name: '', lat: null, lng: null });
    }
  };

  const handleSelect = (dest: DestinationSearchResult) => {
    play(HAPTIC_SINGLE_CONFIRM);
    setInputValue(dest.name);
    setOpen(false);
    onSelect({ name: dest.name, lat: dest.lat, lng: dest.lng });
    inputRef.current?.blur();
  };

  const showDropdown =
    open && inputValue.trim().length >= 2 && debouncedQuery.trim().length >= 2 && (results.length > 0 || isFetching);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <FieldLabel>Откуда обычно летаете?</FieldLabel>
        <p className="mb-3 text-[13px] text-muted-foreground">
          Поможет подобрать удобные направления с хорошей связностью
        </p>
        <div className="relative">
          <div className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2">
            {isFetching ? (
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            ) : (
              <MapPin className="h-4 w-4 text-muted-foreground" />
            )}
          </div>
          <AppInput
            ref={inputRef}
            value={inputValue}
            onChange={(e) => handleInput(e.target.value)}
            onFocus={() => setOpen(true)}
            onBlur={() => setTimeout(() => setOpen(false), 150)}
            placeholder="Москва, Санкт-Петербург..."
            error={!!cityError}
            className="pl-10 pr-10"
          />
          {!isFetching && (cityName || cityError) && (
            <div className="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2">
              {cityError ? (
                <X className="h-4 w-4 text-red-500" />
              ) : cityName ? (
                <Check className="h-4 w-4 text-green-500" />
              ) : null}
            </div>
          )}
        </div>
        {cityError && <p className="mt-2 text-[13px] text-red-500">{cityError}</p>}

        {showDropdown && (
          <div
            className="mt-1.5 max-h-[min(320px,42dvh)] overflow-y-auto overscroll-contain rounded-2xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface))] shadow-[0_8px_24px_rgba(0,0,0,0.1)]"
            {...dropdownScrollHaptics}
          >
            {isFetching && results.length === 0 ? (
              <div className="flex items-center gap-2 px-4 py-3 text-[14px] text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Поиск...
              </div>
            ) : (
              results.map((dest) => (
                <button
                  key={dest.id}
                  type="button"
                  onMouseDown={() => handleSelect(dest)}
                  className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-[hsl(var(--surface-muted))] active:bg-[hsl(var(--surface-field))] [&:not(:last-child)]:border-b [&:not(:last-child)]:border-[hsl(var(--surface-border))]"
                >
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-[hsl(var(--surface-field))]">
                    <MapPin className="h-3.5 w-3.5 text-muted-foreground" />
                  </div>
                  <div>
                    <p className="text-[14px] font-semibold text-foreground">{dest.name}</p>
                    <p className="text-[12px] text-muted-foreground">{dest.country_code}</p>
                  </div>
                </button>
              ))
            )}
          </div>
        )}
      </div>

      <div>
        <FieldLabel>Длительность поездок</FieldLabel>
        <div className="flex flex-col gap-2">
          {DURATION_OPTIONS.map((d) => (
            <button
              key={d.id}
              type="button"
              onClick={() => {
                play(duration === d.id ? HAPTIC_SINGLE_TAP : HAPTIC_SINGLE_CONFIRM);
                onDurationChange(duration === d.id ? null : d.id as DurationOption);
              }}
              className={cn(
                'flex items-center justify-between rounded-2xl border px-4 py-3.5 text-left transition-all active:scale-[0.98]',
                duration === d.id
                  ? 'border-primary/35 bg-primary/10 shadow-[0_2px_8px_rgba(37,99,235,0.1)]'
                  : 'border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-muted))]',
              )}
            >
              <span className={cn(
                'text-[15px] font-semibold',
                duration === d.id ? 'text-primary' : 'text-foreground',
              )}>
                {d.label}
              </span>
              <span className={cn(
                'text-[13px] font-medium',
                duration === d.id ? 'text-blue-500' : 'text-muted-foreground',
              )}>
                ~{d.days} дн.
              </span>
            </button>
          ))}
        </div>
        {durationError && <p className="mt-2 text-[13px] text-red-500">{durationError}</p>}
      </div>
    </div>
  );
};
