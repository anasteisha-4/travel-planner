import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { itineraryApi } from '../api/itinerary.api';
import type {
  Itinerary,
  ItineraryGenerateRequest,
  ItineraryItem,
  ItineraryItemMoveRequest,
  ItineraryItemSwapRequest,
  ItineraryItemUpdate,
  ItineraryManualItemCreate,
  ItineraryRegenerateRequest,
  ItineraryState,
} from './types';

export const itineraryQueryKey = (tripId: string) => ['trip-itinerary', tripId] as const;

const replaceApprovedItinerary = (state: ItineraryState | undefined, itinerary: Itinerary): ItineraryState | undefined => {
  if (!state) return state;
  return {
    approved: state.approved?.id === itinerary.id ? itinerary : state.approved,
    drafts: state.drafts.map((draft) => (draft.id === itinerary.id ? itinerary : draft)),
  };
};

const patchItemInState = (
  state: ItineraryState | undefined,
  item: ItineraryItem,
): ItineraryState | undefined => {
  if (!state) return state;
  const patchItinerary = (itinerary: Itinerary | null) =>
    itinerary
      ? {
          ...itinerary,
          days: itinerary.days.map((day) => ({
            ...day,
            items: day.items.map((current) => (current.id === item.id ? item : current)),
          })),
        }
      : null;

  return {
    approved: patchItinerary(state.approved),
    drafts: state.drafts.map((draft) => patchItinerary(draft) ?? draft),
  };
};

export const useItineraryState = (tripId: string) =>
  useQuery({
    queryKey: itineraryQueryKey(tripId),
    queryFn: () => itineraryApi.getState(tripId),
    staleTime: 30 * 1000,
  });

export const useGenerateItinerary = (tripId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: ItineraryGenerateRequest) => itineraryApi.generate(tripId, params),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: itineraryQueryKey(tripId) });
    },
  });
};

export const useRegenerateItinerary = (tripId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: ItineraryRegenerateRequest) => itineraryApi.regenerate(tripId, params),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: itineraryQueryKey(tripId) });
    },
  });
};

export const useApproveItinerary = (tripId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (itineraryId: string) => itineraryApi.approve(tripId, itineraryId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: itineraryQueryKey(tripId) });
    },
  });
};

export const useUpdateItineraryItem = (tripId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ itemId, params }: { itemId: string; params: ItineraryItemUpdate }) =>
      itineraryApi.updateItem(tripId, itemId, params),
    onSuccess: (item) => {
      queryClient.setQueryData<ItineraryState>(itineraryQueryKey(tripId), (state) =>
        patchItemInState(state, item)
      );
    },
  });
};

export const useSwapItineraryItems = (tripId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ itemId, params }: { itemId: string; params: ItineraryItemSwapRequest }) =>
      itineraryApi.swapItems(tripId, itemId, params),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: itineraryQueryKey(tripId) });
    },
  });
};

export const useMoveItineraryItem = (tripId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ itemId, params }: { itemId: string; params: ItineraryItemMoveRequest }) =>
      itineraryApi.moveItem(tripId, itemId, params),
    onSuccess: (itinerary) => {
      queryClient.setQueryData<ItineraryState>(itineraryQueryKey(tripId), (state) =>
        replaceApprovedItinerary(state, itinerary)
      );
    },
  });
};

export const useAddItineraryItem = (tripId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: ItineraryManualItemCreate) => itineraryApi.addItem(tripId, params),
    onSuccess: (item) => {
      queryClient.setQueryData<ItineraryState>(itineraryQueryKey(tripId), (state) => {
        if (!state) return state;
        const addItem = (itinerary: Itinerary | null) =>
          itinerary
            ? {
                ...itinerary,
                days: itinerary.days.map((day) =>
                  day.id === item.day_id ? { ...day, items: [...day.items, item] } : day
                ),
              }
            : null;
        return {
          approved: addItem(state.approved),
          drafts: state.drafts.map((draft) => addItem(draft) ?? draft),
        };
      });
    },
  });
};

export const useRemoveItineraryItem = (tripId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (itemId: string) => itineraryApi.removeItem(tripId, itemId),
    onSuccess: (_data, itemId) => {
      queryClient.setQueryData<ItineraryState>(itineraryQueryKey(tripId), (state) => {
        if (!state) return state;
        const removeItem = (itinerary: Itinerary | null) =>
          itinerary
            ? {
                ...itinerary,
                days: itinerary.days.map((day) => ({
                  ...day,
                  items: day.items.map((item) =>
                    item.id === itemId ? { ...item, is_removed: true, is_pinned: false } : item
                  ),
                })),
              }
            : null;
        return {
          approved: removeItem(state.approved),
          drafts: state.drafts.map((draft) => removeItem(draft) ?? draft),
        };
      });
    },
  });
};

export const useVisitItineraryItem = (tripId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (itemId: string) => itineraryApi.visitItem(tripId, itemId),
    onSuccess: (item) => {
      queryClient.setQueryData<ItineraryState>(itineraryQueryKey(tripId), (state) =>
        patchItemInState(state, item)
      );
      void queryClient.invalidateQueries({ queryKey: ['places', tripId] });
    },
  });
};

export const useUnvisitItineraryItem = (tripId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (itemId: string) => itineraryApi.unvisitItem(tripId, itemId),
    onSuccess: (item) => {
      queryClient.setQueryData<ItineraryState>(itineraryQueryKey(tripId), (state) =>
        patchItemInState(state, item)
      );
      void queryClient.invalidateQueries({ queryKey: ['places', tripId] });
    },
  });
};
