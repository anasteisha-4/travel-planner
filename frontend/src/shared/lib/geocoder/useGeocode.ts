import { useQuery } from '@tanstack/react-query';
import { searchAddress } from './index';
import type { GeocoderResult } from './index';

export const useGeocode = (address: string): { result: GeocoderResult | null; isLoading: boolean } => {
  const query = useQuery<GeocoderResult[]>({
    queryKey: ['geocode', address],
    queryFn: () => searchAddress(address, 1),
    enabled: !!address,
    staleTime: 30 * 24 * 60 * 60 * 1000,
  });

  return {
    result: query.data?.[0] ?? null,
    isLoading: query.isLoading,
  };
};
