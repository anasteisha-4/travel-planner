import { placeApi } from '@/entities/place';
import type { PlaceVisit } from '@/entities/place';
import { useToast } from '@/shared/ui/use-toast';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';

export const usePlaceDiary = (tripId: string) => {
  const [selectedPlace, setSelectedPlace] = useState<PlaceVisit | null>(null);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const query = useQuery<PlaceVisit[]>({
    queryKey: ['places', tripId],
    queryFn: () => placeApi.getPlaces(tripId),
  });

  useEffect(() => {
    if (query.isError) {
      toast({ title: 'Не удалось загрузить места', variant: 'destructive' });
    }
  }, [query.isError, toast]);

  const deleteMutation = useMutation({
    mutationFn: (placeId: string) => placeApi.deletePlace(placeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['places', tripId] });
      setSelectedPlace(null);
    },
    onError: () => {
      toast({ title: 'Не удалось удалить место', variant: 'destructive' });
    },
  });

  const reorderMutation = useMutation({
    mutationFn: ({ date, placeIds }: { date: string; placeIds: string[] }) =>
      placeApi.reorderPlaces(tripId, date, placeIds),
    onMutate: async ({ date, placeIds }) => {
      await queryClient.cancelQueries({ queryKey: ['places', tripId] });
      const prev = queryClient.getQueryData<PlaceVisit[]>(['places', tripId]);
      const orderMap = Object.fromEntries(placeIds.map((id, i) => [id, i]));
      queryClient.setQueryData<PlaceVisit[]>(['places', tripId], (old = []) =>
        old.map((p) =>
          p.visited_at === date && orderMap[p.id] !== undefined
            ? { ...p, order: orderMap[p.id] }
            : p,
        ),
      );
      return { prev };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) queryClient.setQueryData(['places', tripId], ctx.prev);
      toast({ title: 'Не удалось сохранить порядок', variant: 'destructive' });
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['places', tripId] });
    },
  });

  const places = useMemo(() => {
    const list = query.data ?? [];
    return [...list].sort(
      (a, b) =>
        a.visited_at.localeCompare(b.visited_at) ||
        (a.order ?? Infinity) - (b.order ?? Infinity) ||
        a.created_at.localeCompare(b.created_at),
    );
  }, [query.data]);

  const handleAddPlace = (_place: PlaceVisit) => {
    queryClient.invalidateQueries({ queryKey: ['places', tripId] });
  };

  const handleUpdatePlace = (updated: PlaceVisit) => {
    queryClient.invalidateQueries({ queryKey: ['places', tripId] });
    setSelectedPlace(updated);
  };

  const handleDeletePlace = (placeId: string) => deleteMutation.mutateAsync(placeId).catch(() => {});

  const handleReorderPlaces = (date: string, placeIds: string[]) => {
    reorderMutation.mutate({ date, placeIds });
  };

  return {
    places,
    loading: query.isLoading,
    selectedPlace,
    setSelectedPlace,
    handleAddPlace,
    handleUpdatePlace,
    handleDeletePlace,
    handleReorderPlaces,
  };
};
