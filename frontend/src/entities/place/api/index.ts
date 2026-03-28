import { apiClient } from '@/shared/api';

import { PlaceVisitSchema } from '../model';
import type { PlaceVisit, PlaceVisitCreate, PlaceVisitUpdate } from '../model';

export const placeApi = {
  getPlaces: async (tripId: string): Promise<PlaceVisit[]> => {
    const response = await apiClient.get(`/api/trips/${tripId}/places`);
    return response.data.map((item: unknown) => PlaceVisitSchema.parse(item));
  },

  createPlace: async (tripId: string, data: PlaceVisitCreate): Promise<PlaceVisit> => {
    const response = await apiClient.post(`/api/trips/${tripId}/places`, data);
    return PlaceVisitSchema.parse(response.data);
  },

  updatePlace: async (placeId: string, data: PlaceVisitUpdate): Promise<PlaceVisit> => {
    const response = await apiClient.patch(`/api/places/${placeId}`, data);
    return PlaceVisitSchema.parse(response.data);
  },

  deletePlace: async (placeId: string): Promise<void> => {
    await apiClient.delete(`/api/places/${placeId}`);
  },

  reorderPlaces: async (tripId: string, date: string, placeIds: string[]): Promise<PlaceVisit[]> => {
    const response = await apiClient.patch(`/api/trips/${tripId}/places/reorder`, { date, place_ids: placeIds });
    return response.data.map((item: unknown) => PlaceVisitSchema.parse(item));
  },
};
