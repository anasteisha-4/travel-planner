import type { GeocoderResult, LngLat } from '@/shared/lib';
import { searchAddress } from '@/shared/lib';
import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

export const useMapSearch = (biasCenter?: LngLat | null) => {
  const [inputValue, setInputValue] = useState('');
  const [debouncedValue, setDebouncedValue] = useState('');

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(inputValue), 300);
    return () => clearTimeout(timer);
  }, [inputValue]);

  const isEnabled = debouncedValue.trim().length >= 2;

  const query = useQuery<GeocoderResult[]>({
    queryKey: ['geocode-search', debouncedValue, biasCenter],
    queryFn: () => searchAddress(debouncedValue, 5, biasCenter ?? undefined),
    enabled: isEnabled,
    staleTime: 1000 * 60,
  });

  return {
    searchQuery: inputValue,
    setSearchQuery: setInputValue,
    suggestions: isEnabled ? (query.data ?? []) : [],
    isSearching: query.isFetching,
    showSuggestions: isEnabled && (query.data?.length ?? 0) > 0,
    clearSearch: () => setInputValue(''),
  };
};
