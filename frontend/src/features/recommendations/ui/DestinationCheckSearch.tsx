import { destinationApi, type DestinationSearchResult } from '@/entities/destination';
import { getCountryFlag, localizeDestinationName, useDebouncedValue } from '@/shared/lib';
import { AppInput } from '@/shared/ui';
import { useQuery } from '@tanstack/react-query';
import { CheckCircle2, Loader2, Search } from 'lucide-react';
import { useRef, useState } from 'react';

type DestinationCheckSearchProps = {
  onSelect: (destination: DestinationSearchResult) => void;
};

const getDestinationName = (destination: DestinationSearchResult) =>
  destination.display_name ??
  destination.name_ru ??
  destination.name_original ??
  localizeDestinationName(destination.name);

export const DestinationCheckSearch = ({ onSelect }: DestinationCheckSearchProps) => {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const debouncedQuery = useDebouncedValue(query, 400);

  const { data: results = [], isFetching } = useQuery({
    queryKey: ['destination-search', debouncedQuery],
    queryFn: () => destinationApi.searchDestinations(debouncedQuery, 8),
    enabled: open && debouncedQuery.trim().length >= 2,
    staleTime: 1000 * 60 * 10,
  });

  const handleSelect = (destination: DestinationSearchResult) => {
    setQuery(getDestinationName(destination));
    setOpen(false);
    onSelect(destination);
    inputRef.current?.blur();
  };

  const showDropdown =
    open &&
    query.trim().length >= 2 &&
    debouncedQuery.trim().length >= 2 &&
    (results.length > 0 || isFetching);

  return (
    <section className="relative z-30 rounded-[24px] border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface))] p-4 shadow-[0_14px_34px_rgba(15,23,42,0.08)] dark:shadow-none">
      <div className="mb-3 flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
          <CheckCircle2 className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <p className="text-[15px] font-extrabold leading-tight text-foreground">
            Проверить направление
          </p>
          <p className="mt-1 text-[13px] font-semibold leading-snug text-muted-foreground">
            Найдите город или страну из общего каталога
          </p>
        </div>
      </div>

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
          placeholder="Например, Стамбул или Япония"
          className="h-12 pl-10 pr-4 text-[15px] font-bold"
        />
      </div>

      {showDropdown && (
        <div className="absolute left-0 right-0 top-[calc(100%+8px)] z-50 max-h-[min(320px,42dvh)] overflow-y-auto overscroll-contain rounded-2xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-elevated))] shadow-[0_16px_42px_rgba(0,0,0,0.18)]">
          {isFetching && results.length === 0 ? (
            <div className="flex items-center gap-2 px-4 py-3 text-[14px] font-semibold text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Поиск...
            </div>
          ) : (
            results.map((destination) => (
              <button
                key={destination.id}
                type="button"
                onMouseDown={(event) => {
                  event.preventDefault();
                  handleSelect(destination);
                }}
                className="flex min-h-12 w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-[hsl(var(--surface-muted))] active:bg-[hsl(var(--surface-muted))] [&:not(:last-child)]:border-b [&:not(:last-child)]:border-[hsl(var(--surface-border))]"
              >
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-[hsl(var(--surface-muted))] text-[18px] leading-none">
                  {getCountryFlag(destination.country_code)}
                </div>
                <div className="min-w-0">
                  <p className="truncate text-[14px] font-extrabold text-foreground">
                    {getDestinationName(destination)}
                  </p>
                  <p className="text-[12px] font-semibold text-muted-foreground">
                    {destination.country_code}
                  </p>
                </div>
              </button>
            ))
          )}
        </div>
      )}
    </section>
  );
};
