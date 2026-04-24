import { apiClient } from '@/shared/api';

export type PostTripFeedbackPayload = {
  trip_id: string;
  destination: string;
  overall_rating: number;
  destination_rating?: number | null;
  value_rating?: number | null;
  actual_total_cost?: number | null;
  actual_currency?: string | null;
  would_revisit?: boolean | null;
  free_text?: string | null;
};

export type PostTripFeedbackResponse = {
  id: string;
  user_id: string;
  trip_id: string;
  destination: string;
  overall_rating: number;
  destination_rating: number | null;
  value_rating: number | null;
  actual_total_cost: number | null;
  actual_currency: string | null;
  would_revisit: boolean | null;
  free_text: string | null;
  created_at: string;
};

export type PendingFeedbackItem = {
  trip_id: string;
  destination: string;
  completed_at: string | null;
};

export type PostTripFeedbackUpdate = Omit<PostTripFeedbackPayload, 'trip_id' | 'destination' | 'overall_rating'> & {
  overall_rating?: number;
};

export const feedbackApi = {
  submitPostTrip: async (payload: PostTripFeedbackPayload): Promise<PostTripFeedbackResponse> => {
    const { data } = await apiClient.post<PostTripFeedbackResponse>(
      '/api/v1/feedback/post-trip',
      payload
    );
    return data;
  },

  updatePostTrip: async (tripId: string, payload: PostTripFeedbackUpdate): Promise<PostTripFeedbackResponse> => {
    const { data } = await apiClient.put<PostTripFeedbackResponse>(
      `/api/v1/feedback/post-trip/${tripId}`,
      payload
    );
    return data;
  },

  getForTrip: async (tripId: string): Promise<PostTripFeedbackResponse | null> => {
    try {
      const { data } = await apiClient.get<PostTripFeedbackResponse>(
        `/api/v1/feedback/post-trip/${tripId}`
      );
      return data;
    } catch {
      return null;
    }
  },

  deletePostTrip: async (tripId: string): Promise<void> => {
    await apiClient.delete(`/api/v1/feedback/post-trip/${tripId}`);
  },

  getPending: async (
    trips: Array<{ trip_id: string; destination: string; completed_at?: string | null }>
  ): Promise<PendingFeedbackItem[]> => {
    if (trips.length === 0) return [];
    const params = new URLSearchParams();
    trips.forEach((t) => {
      params.append('trip_id', t.trip_id);
      params.append('destination', t.destination);
      if (t.completed_at) params.append('completed_at', t.completed_at);
    });
    const { data } = await apiClient.get<PendingFeedbackItem[]>(
      `/api/v1/feedback/pending?${params.toString()}`
    );
    return data;
  },
};
