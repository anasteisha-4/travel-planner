import { useQuery } from '@tanstack/react-query';
import type { LngLat } from '../yandex-maps/types';
import { reverseGeocode } from './index';

const COORD_PRECISION = 5;
const normalizeCoord = (value: number): number => Number(value.toFixed(COORD_PRECISION));

export const useReverseGeocode = (coords: LngLat | null): string | null => {
  const lon = coords ? normalizeCoord(coords[0]) : null;
  const lat = coords ? normalizeCoord(coords[1]) : null;
  const query = useQuery<string | null>({
    queryKey: ['reverse-geocode', lon, lat],
    queryFn: () => reverseGeocode(lat!, lon!),
    enabled: lon !== null && lat !== null,
    staleTime: 30 * 24 * 60 * 60 * 1000,
  });

  return query.data ?? null;
};
