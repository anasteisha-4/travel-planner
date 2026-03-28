import type { Trip, TripStatus } from '@/entities/trip';
import { tripApi } from '@/entities/trip';
import { useToast } from '@/shared/ui';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export const useTripDetail = (id: string | undefined) => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();

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

  const statusMutation = useMutation({
    mutationFn: (newStatus: TripStatus) => tripApi.updateTrip(id!, { status: newStatus }),
    onSuccess: (updated) => {
      queryClient.setQueryData(['trip', id], updated);
      queryClient.invalidateQueries({ queryKey: ['trips'] });
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
