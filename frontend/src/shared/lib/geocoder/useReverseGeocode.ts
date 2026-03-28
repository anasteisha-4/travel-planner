import { useQuery } from '@tanstack/react-query';
import type { LngLat } from '../yandex-maps/types';
import { reverseGeocode } from './index';

export const useReverseGeocode = (coords: LngLat | null): string | null => {
  const query = useQuery<string | null>({
    queryKey: ['reverse-geocode', coords?.[0], coords?.[1]],
    queryFn: () => reverseGeocode(coords![1], coords![0]),
    enabled: coords !== null,
    staleTime: 30 * 24 * 60 * 60 * 1000,
  });

  return query.data ?? null;
};
