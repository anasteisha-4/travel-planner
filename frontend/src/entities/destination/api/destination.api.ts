import { apiClient } from '@/shared/api';

import type { DestinationDetail, DestinationSearchResult } from '../model/types';

export const destinationApi = {
  searchDestinations: async (query: string, limit = 10): Promise<DestinationSearchResult[]> => {
    const response = await apiClient.get('/api/destinations/search', {
      params: { q: query, limit },
    });
    return response.data;
  },

  fetchDestinationsByIds: async (ids: string[]): Promise<DestinationSearchResult[]> => {
    if (ids.length === 0) return [];
    const response = await apiClient.post('/api/destinations/by-ids', ids);
    return response.data;
  },

  getDestination: async (id: string): Promise<DestinationDetail> => {
    const response = await apiClient.get(`/api/destinations/${id}`);
    return response.data;
  },
};
