import { useQuery } from '@tanstack/react-query';
import { Check, Loader2, Search } from 'lucide-react';
import { useRef, useState } from 'react';

import { destinationApi, type CitizenshipOption } from '@/entities/destination';
import { getCountryFlag, useDebouncedValue } from '@/shared/lib';
import { HAPTIC_SINGLE_CONFIRM, useHapticFeedback } from '@/shared/lib/useHapticFeedback';
import { useScrollHaptics } from '@/shared/lib/useScrollHaptics';
import { AppInput, FieldLabel } from '@/shared/ui';

const regionNames = new Intl.DisplayNames(['ru'], { type: 'region' });

const normalizeSearch = (value: string) =>
  value
    .trim()
    .toLowerCase()
    .replace(/ё/g, 'е')
    .normalize('NFKD')
    .replace(/\p{Diacritic}/gu, '')
    .replace(/[^\p{Letter}\p{Number}]+/gu, ' ')
    .trim();

const localizeCitizenship = (option?: CitizenshipOption | null, code?: string | null) => {
  const normalizedCode = (option?.code ?? code ?? '').trim().toUpperCase();
  if (!normalizedCode) return '';
  return regionNames.of(normalizedCode) ?? option?.name ?? normalizedCode;
};

type SearchableCitizenship = {
  option: CitizenshipOption;
  label: string;
  variants: string[];
};

const tokens = (value: string) => value.split(' ').filter(Boolean);

const scoreVariant = (query: string, candidate: string) => {
  if (!query || !candidate) return 0;
  if (candidate === query) return 1000;
  if (candidate.startsWith(query)) return 930 - Math.min(candidate.length - query.length, 80) * 0.4;

  const queryTokens = tokens(query);
  const candidateTokens = tokens(candidate);
  if (queryTokens.length > 0 && candidateTokens.length > 0) {
    if (queryTokens.every((queryToken) => candidateTokens.includes(queryToken))) {
      return 920 - Math.max(0, candidateTokens.length - queryTokens.length) * 3;
    }
    if (
      queryTokens.every((queryToken) =>
        candidateTokens.some((candidateToken) => candidateToken.startsWith(queryToken))
      )
    ) {
      return 880 - Math.max(0, candidateTokens.length - queryTokens.length) * 2;
    }
    if (candidateTokens.some((candidateToken) => candidateToken.startsWith(query))) return 850;
  }

  if (query.length >= 3 && candidate.includes(query)) {
    return 760 - Math.min(candidate.indexOf(query), 80) * 0.8;
  }
  return 0;
};

const buildSearchableCitizenship = (option: CitizenshipOption): SearchableCitizenship => {
  const label = localizeCitizenship(option);
  const variants = [option.code, option.name, label]
    .map(normalizeSearch)
    .filter((variant, index, array) => variant && array.indexOf(variant) === index);
  return { option, label, variants };
};

const rankCitizenships = (query: string, citizenships: SearchableCitizenship[]) => {
  const normalizedQuery = normalizeSearch(query);
  if (normalizedQuery.length < 2) return [];

  return citizenships
    .map((citizenship) => ({
      citizenship,
      score: Math.max(
        ...citizenship.variants.map((variant) => scoreVariant(normalizedQuery, variant))
      ),
    }))
    .filter(({ score }) => score > 0)
    .sort((left, right) => {
      if (right.score !== left.score) return right.score - left.score;
      return left.citizenship.label.localeCompare(right.citizenship.label, 'ru');
    })
    .slice(0, 8)
    .map(({ citizenship }) => citizenship);
};

type Props = {
  citizenshipCode: string | null;
  onSelect: (code: string) => void;
};

export const CitizenshipSearch = ({ citizenshipCode, onSelect }: Props) => {
  const { play } = useHapticFeedback();
  const dropdownScrollHaptics = useScrollHaptics();
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const debouncedQuery = useDebouncedValue(query, 200);
  const inputRef = useRef<HTMLInputElement>(null);

  const shouldSearch = normalizeSearch(debouncedQuery).length >= 2;
  const { data: citizenships = [], isFetching } = useQuery({
    queryKey: ['citizenships'],
    queryFn: destinationApi.getCitizenships,
    enabled: open && shouldSearch,
    select: (items) => items.map(buildSearchableCitizenship),
    staleTime: 24 * 60 * 60 * 1000,
  });

  const selectedCode = citizenshipCode?.toUpperCase() ?? null;
  const selectedOption = selectedCode
    ? citizenships.find((item) => item.option.code === selectedCode)
    : undefined;
  const selectedLabel = selectedCode
    ? (selectedOption?.label ?? localizeCitizenship(null, selectedCode))
    : null;

  const filteredCitizenships = shouldSearch ? rankCitizenships(debouncedQuery, citizenships) : [];

  const showDropdown =
    open && normalizeSearch(query).length >= 2 && (filteredCitizenships.length > 0 || isFetching);

  const handleSelect = (option: CitizenshipOption) => {
    play(HAPTIC_SINGLE_CONFIRM);
    onSelect(option.code);
    setQuery('');
    setOpen(false);
    inputRef.current?.blur();
  };

  return (
    <div className="relative">
      <FieldLabel>Гражданство</FieldLabel>
      <p className="mb-3 text-[13px] text-muted-foreground">
        Используем для визовой проверки направлений
      </p>
      {selectedCode && selectedLabel && (
        <div className="mb-3 flex items-center gap-3 rounded-2xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-muted))] px-4 py-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[hsl(var(--surface-field))] text-[20px] leading-none">
            {getCountryFlag(selectedCode)}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[15px] font-extrabold text-foreground">{selectedLabel}</p>
            <p className="text-[12px] font-semibold text-muted-foreground">{selectedCode}</p>
          </div>
          <Check className="h-4 w-4 shrink-0 text-green-500" />
        </div>
      )}

      <div className="relative">
        <div className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2">
          {isFetching ? (
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          ) : (
            <Search className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
        <AppInput
          ref={inputRef}
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          placeholder="Россия, Германия, Соединенные Штаты..."
          className="pl-10"
        />
      </div>

      {showDropdown && (
        <div
          className="absolute mt-1.5 max-h-[min(320px,42dvh)] w-full overflow-y-auto overscroll-contain rounded-2xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface))] shadow-[0_8px_24px_rgba(0,0,0,0.1)]"
          {...dropdownScrollHaptics}
        >
          {isFetching && filteredCitizenships.length === 0 ? (
            <div className="flex items-center gap-2 px-4 py-3 text-[14px] text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Поиск...
            </div>
          ) : (
            filteredCitizenships.map(({ option, label }) => (
              <button
                key={option.code}
                type="button"
                onMouseDown={() => handleSelect(option)}
                className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-[hsl(var(--surface-muted))] active:bg-[hsl(var(--surface-field))] [&:not(:last-child)]:border-b [&:not(:last-child)]:border-[hsl(var(--surface-border))]"
              >
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-[hsl(var(--surface-field))] text-[18px] leading-none">
                  {getCountryFlag(option.code)}
                </div>
                <div className="min-w-0">
                  <p className="truncate text-[14px] font-semibold text-foreground">{label}</p>
                  <p className="text-[12px] text-muted-foreground">{option.code}</p>
                </div>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
};
