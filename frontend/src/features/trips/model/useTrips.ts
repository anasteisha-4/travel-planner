import type { Trip, TripStatus } from '@/entities/trip';
import { tripApi } from '@/entities/trip';
import { useToast } from '@/shared/ui';
import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

export const useTrips = (initialStatus?: TripStatus) => {
  const [statusFilter, setStatusFilter] = useState<TripStatus | undefined>(initialStatus);
  const { toast } = useToast();

  const query = useQuery<Trip[]>({
    queryKey: ['trips', statusFilter],
    queryFn: () => tripApi.getTrips(statusFilter),
  });

  useEffect(() => {
    if (query.isError) {
      toast({ variant: 'destructive', title: 'Ошибка', description: 'Не удалось загрузить поездки' });
    }
  }, [query.isError, toast]);

  const trips = query.data ?? [];
  const activeTrips = trips.filter((t) => t.status === 'planned' || t.status === 'active');
  const completedTrips = trips.filter((t) => t.status === 'completed' || t.status === 'cancelled');

  return {
    trips,
    activeTrips,
    completedTrips,
    loading: query.isLoading,
    statusFilter,
    setStatusFilter,
    refetch: query.refetch,
  };
};
