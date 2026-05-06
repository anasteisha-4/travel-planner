import { apiClient } from '@/shared/api';
import type { ItineraryGenerateRequest, ItineraryGenerateResponse } from '../model/types';

export const itineraryApi = {
  generate: async (params: ItineraryGenerateRequest): Promise<ItineraryGenerateResponse> => {
    const { data } = await apiClient.post<ItineraryGenerateResponse>('/api/v1/itinerary', params);
    return data;
  },
};
