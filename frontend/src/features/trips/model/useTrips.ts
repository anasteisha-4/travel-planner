import type { Trip, TripStatus } from '@/entities/trip';
import { tripApi } from '@/entities/trip';
import { useToast } from '@/shared/ui';
import { useCallback, useEffect, useState } from 'react';

export const useTrips = (initialStatus?: TripStatus) => {
  const [trips, setTrips] = useState<Trip[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<TripStatus | undefined>(initialStatus);
  const { toast } = useToast();

  const fetchTrips = useCallback(async () => {
    setLoading(true);
    try {
      const data = await tripApi.getTrips(statusFilter);
      setTrips(data);
    } catch {
      toast({
        variant: 'destructive',
        title: 'Ошибка',
        description: 'Не удалось загрузить поездки',
      });
    } finally {
      setLoading(false);
    }
  }, [statusFilter, toast]);

  useEffect(() => {
    fetchTrips();
  }, [fetchTrips]);

  const activeTrips = trips.filter((t) => t.status === 'planned' || t.status === 'active');
  const completedTrips = trips.filter((t) => t.status === 'completed' || t.status === 'cancelled');

  return {
    trips,
    activeTrips,
    completedTrips,
    loading,
    statusFilter,
    setStatusFilter,
    refetch: fetchTrips,
  };
};
