import { apiClient } from '@/shared/api';
import type { Trip, TripCreate, TripStatus, TripUpdate } from '../model/types';
import { TripSchema } from '../model/types';

export const tripApi = {
  getTrips: async (status?: TripStatus): Promise<Trip[]> => {
    const params = status ? { status } : {};
    const response = await apiClient.get('/api/trips/', { params });
    return response.data.map((item: unknown) => TripSchema.parse(item));
  },

  getTrip: async (id: string): Promise<Trip> => {
    const response = await apiClient.get(`/api/trips/${id}`);
    return TripSchema.parse(response.data);
  },

  createTrip: async (data: TripCreate): Promise<Trip> => {
    const response = await apiClient.post('/api/trips/', data);
    return TripSchema.parse(response.data);
  },

  updateTrip: async (id: string, data: TripUpdate): Promise<Trip> => {
    const response = await apiClient.put(`/api/trips/${id}`, data);
    return TripSchema.parse(response.data);
  },

  deleteTrip: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/trips/${id}`);
  },
};
