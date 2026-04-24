import { useQuery } from '@tanstack/react-query';
import { Globe, Loader2, X } from 'lucide-react';
import { useState } from 'react';

import { AppInput, FieldLabel } from '@/shared/ui';

import { onboardingV2Api } from '../api/onboarding-v2.api';
import type { DestinationSearchResult } from '../api/onboarding-v2.api';

export type LikedDest = { id: string; name: string; country_code: string };

type Props = {
  dests: LikedDest[];
  onChange: (dests: LikedDest[]) => void;
};

export const StepLikedDests = ({ dests, onChange }: Props) => {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);

  const { data: results = [], isFetching } = useQuery({
    queryKey: ['destination-search', query],
    queryFn: () => onboardingV2Api.searchDestinations(query, 8),
    enabled: query.trim().length >= 2,
    staleTime: 1000 * 60 * 10,
  });

  const selectedIds = dests.map((d) => d.id);

  const handleSelect = (dest: DestinationSearchResult) => {
    if (selectedIds.includes(dest.id) || dests.length >= 10) return;
    onChange([...dests, { id: dest.id, name: dest.name, country_code: dest.country_code }]);
    setQuery('');
    setOpen(false);
  };

  const handleRemove = (id: string) => {
    onChange(dests.filter((d) => d.id !== id));
  };

  const showDropdown = open && query.trim().length >= 2 && (results.length > 0 || isFetching);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <FieldLabel>Любимые направления</FieldLabel>
        <p className="mb-3 text-[13px] text-stone-400">
          До 10 мест — поможет находить похожие направления (необязательно)
        </p>

        {dests.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-2">
            {dests.map((dest) => (
              <span
                key={dest.id}
                className="flex items-center gap-1.5 rounded-xl border border-blue-100 bg-blue-50 py-1.5 pl-3 pr-2 text-[13px] font-semibold text-blue-800"
              >
                {dest.name}
                {dest.country_code && (
                  <span className="text-[11px] font-normal text-blue-400">{dest.country_code}</span>
                )}
                <button
                  type="button"
                  onClick={() => handleRemove(dest.id)}
                  className="flex h-4 w-4 items-center justify-center rounded-full bg-blue-200 text-blue-600 transition-colors hover:bg-blue-300"
                >
                  <X className="h-2.5 w-2.5" />
                </button>
              </span>
            ))}
          </div>
        )}

        {dests.length < 10 && (
          <div className="relative">
            <div className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2">
              {isFetching ? (
                <Loader2 className="h-4 w-4 animate-spin text-stone-400" />
              ) : (
                <Globe className="h-4 w-4 text-stone-400" />
              )}
            </div>
            <AppInput
              value={query}
              onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
              onFocus={() => setOpen(true)}
              onBlur={() => setTimeout(() => setOpen(false), 150)}
              placeholder="Стамбул, Барселона, Токио..."
              className="pl-10"
            />
          </div>
        )}

        {showDropdown && (
          <div className="mt-1.5 overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-[0_8px_24px_rgba(0,0,0,0.1)]">
            {isFetching && results.length === 0 ? (
              <div className="flex items-center gap-2 px-4 py-3 text-[14px] text-stone-400">
                <Loader2 className="h-4 w-4 animate-spin" />
                Поиск...
              </div>
            ) : (
              results
                .filter((d) => !selectedIds.includes(d.id))
                .map((dest) => (
                  <button
                    key={dest.id}
                    type="button"
                    onMouseDown={() => handleSelect(dest)}
                    className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-stone-50 [&:not(:last-child)]:border-b [&:not(:last-child)]:border-stone-100"
                  >
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-stone-100">
                      <Globe className="h-3.5 w-3.5 text-stone-500" />
                    </div>
                    <div>
                      <p className="text-[14px] font-semibold text-stone-900">{dest.name}</p>
                      <p className="text-[12px] text-stone-400">{dest.country_code}</p>
                    </div>
                  </button>
                ))
            )}
          </div>
        )}
      </div>

      {dests.length === 0 && (
        <div className="rounded-2xl border border-stone-100 bg-stone-50 px-4 py-4 text-center">
          <Globe className="mx-auto mb-2 h-8 w-8 text-stone-300" />
          <p className="text-[13px] text-stone-400">Пропустите или добавьте любимые места</p>
        </div>
      )}
    </div>
  );
};
