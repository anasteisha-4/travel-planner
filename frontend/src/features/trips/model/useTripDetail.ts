import type { Trip, TripStatus } from '@/entities/trip';
import { tripApi } from '@/entities/trip';
import { sendEvent } from '@/shared/api';
import { useToast } from '@/shared/ui';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

export const useTripDetail = (id: string | undefined) => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const trackedTripOpenIds = useRef<Set<string>>(new Set());

  const query = useQuery<Trip>({
    queryKey: ['trip', id],
    queryFn: () => tripApi.getTrip(id!),
    enabled: !!id,
    retry: false,
  });

  useEffect(() => {
    if (!query.isError) return;
    toast({ variant: 'destructive', title: 'Ошибка', description: 'Поездка не найдена' });
    navigate('/trips', { replace: true });
  }, [query.isError, navigate, toast]);

  useEffect(() => {
    if (!query.data || trackedTripOpenIds.current.has(query.data.id)) return;
    trackedTripOpenIds.current.add(query.data.id);
    sendEvent(
      'trip_opened',
      {
        trip_id: query.data.id,
        destination_id: query.data.destination_id,
        destination: query.data.destination,
        status: query.data.status,
        currency: query.data.currency,
        has_budget: query.data.budget !== null,
      },
      'trip',
      query.data.id
    );
  }, [query.data]);

  const statusMutation = useMutation({
    mutationFn: (newStatus: TripStatus) => tripApi.updateTrip(id!, { status: newStatus }),
    onSuccess: (updated) => {
      queryClient.setQueryData(['trip', id], updated);
      queryClient.invalidateQueries({ queryKey: ['trips'] });
      sendEvent(
        'trip_status_changed',
        {
          trip_id: updated.id,
          destination_id: updated.destination_id,
          status: updated.status,
        },
        'trip',
        updated.id
      );
    },
    onError: () => {
      toast({ variant: 'destructive', title: 'Ошибка', description: 'Не удалось обновить статус' });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => tripApi.deleteTrip(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trips'] });
      navigate('/trips', { replace: true });
    },
    onError: () => {
      toast({ variant: 'destructive', title: 'Ошибка', description: 'Не удалось удалить поездку' });
    },
  });

  return {
    trip: query.data ?? null,
    loading: query.isLoading,
    handleStatusChange: (status: TripStatus): Promise<void> =>
      statusMutation.mutateAsync(status).then(() => {}).catch(() => {}),
    isStatusChanging: statusMutation.isPending,
    handleDelete: () => deleteMutation.mutateAsync().catch(() => {}),
    isDeleting: deleteMutation.isPending,
    invalidateTrip: () => queryClient.invalidateQueries({ queryKey: ['trip', id] }),
  };
};
