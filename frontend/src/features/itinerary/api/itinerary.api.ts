import { apiClient } from '@/shared/api';
import type {
  Itinerary,
  ItineraryGenerationJob,
  ItineraryGenerateRequest,
  ItineraryItem,
  ItineraryItemMoveRequest,
  ItineraryItemSwapRequest,
  ItineraryItemUpdate,
  ItineraryManualItemCreate,
  ItineraryRegenerateRequest,
  ItineraryState,
} from '../model/types';

export const itineraryApi = {
  getState: async (tripId: string): Promise<ItineraryState> => {
    const { data } = await apiClient.get<ItineraryState>(`/api/trips/${tripId}/itinerary`);
    return data;
  },

  generate: async (tripId: string, params: ItineraryGenerateRequest): Promise<ItineraryGenerationJob> => {
    const { data } = await apiClient.post<ItineraryGenerationJob>(`/api/trips/${tripId}/itinerary/generate`, params);
    return data;
  },

  regenerate: async (tripId: string, params: ItineraryRegenerateRequest): Promise<ItineraryGenerationJob> => {
    const { data } = await apiClient.post<ItineraryGenerationJob>(`/api/trips/${tripId}/itinerary/regenerate`, params);
    return data;
  },

  approve: async (tripId: string, itineraryId: string): Promise<Itinerary> => {
    const { data } = await apiClient.post<Itinerary>(`/api/trips/${tripId}/itinerary/${itineraryId}/approve`);
    return data;
  },

  addItem: async (tripId: string, params: ItineraryManualItemCreate): Promise<ItineraryItem> => {
    const { data } = await apiClient.post<ItineraryItem>(`/api/trips/${tripId}/itinerary/items`, params);
    return data;
  },

  updateItem: async (tripId: string, itemId: string, params: ItineraryItemUpdate): Promise<ItineraryItem> => {
    const { data } = await apiClient.patch<ItineraryItem>(`/api/trips/${tripId}/itinerary/items/${itemId}`, params);
    return data;
  },

  swapItems: async (tripId: string, itemId: string, params: ItineraryItemSwapRequest): Promise<Itinerary> => {
    const { data } = await apiClient.post<Itinerary>(`/api/trips/${tripId}/itinerary/items/${itemId}/swap`, params);
    return data;
  },

  moveItem: async (tripId: string, itemId: string, params: ItineraryItemMoveRequest): Promise<Itinerary> => {
    const { data } = await apiClient.post<Itinerary>(`/api/trips/${tripId}/itinerary/items/${itemId}/move`, params);
    return data;
  },

  removeItem: async (tripId: string, itemId: string): Promise<void> => {
    await apiClient.delete(`/api/trips/${tripId}/itinerary/items/${itemId}`);
  },

  visitItem: async (tripId: string, itemId: string): Promise<ItineraryItem> => {
    const { data } = await apiClient.post<ItineraryItem>(`/api/trips/${tripId}/itinerary/items/${itemId}/visit`);
    return data;
  },

  unvisitItem: async (tripId: string, itemId: string): Promise<ItineraryItem> => {
    const { data } = await apiClient.delete<ItineraryItem>(`/api/trips/${tripId}/itinerary/items/${itemId}/visit`);
    return data;
  },
};
