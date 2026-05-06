import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { sendEvent } from '@/shared/api';
import { feedbackApi, type PostTripFeedbackPayload } from '../api/feedback.api';

export const useFeedback = (tripId: string, destination: string) => {
  const queryClient = useQueryClient();

  const existingQuery = useQuery({
    queryKey: ['feedback', tripId],
    queryFn: () => feedbackApi.getForTrip(tripId),
    staleTime: 1000 * 60 * 5,
  });

  const existing = existingQuery.data ?? null;
  const alreadySubmitted = existingQuery.data !== undefined && existingQuery.data !== null;

  const submitMutation = useMutation({
    mutationFn: (payload: PostTripFeedbackPayload) => feedbackApi.submitPostTrip(payload),
    onSuccess: (data) => {
      queryClient.setQueryData(['feedback', tripId], data);
      sendEvent(
        'post_trip_feedback_submitted',
        {
          trip_id: tripId,
          destination: data.destination,
          overall_rating: data.overall_rating,
          destination_rating: data.destination_rating,
          would_revisit: data.would_revisit,
          value_rating: data.value_rating,
          actual_total_cost: data.actual_total_cost,
          actual_currency: data.actual_currency,
        },
        'trip',
        tripId
      );
    },
  });

  const updateMutation = useMutation({
    mutationFn: (payload: Partial<PostTripFeedbackPayload>) =>
      feedbackApi.updatePostTrip(tripId, payload),
    onSuccess: (data) => {
      queryClient.setQueryData(['feedback', tripId], data);
      sendEvent(
        'post_trip_feedback_updated',
        {
          trip_id: tripId,
          destination: data.destination,
          overall_rating: data.overall_rating,
          destination_rating: data.destination_rating,
          would_revisit: data.would_revisit,
          value_rating: data.value_rating,
          actual_total_cost: data.actual_total_cost,
          actual_currency: data.actual_currency,
        },
        'trip',
        tripId
      );
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => feedbackApi.deletePostTrip(tripId),
    onSuccess: () => {
      queryClient.setQueryData(['feedback', tripId], null);
    },
  });

  const submit = async (payload: PostTripFeedbackPayload) => {
    if (alreadySubmitted) {
      const { trip_id: _t, destination: _d, ...rest } = payload;
      return updateMutation.mutateAsync(rest);
    }
    return submitMutation.mutateAsync({ ...payload, destination });
  };

  return {
    existing,
    alreadySubmitted,
    submit,
    deleteFeedback: deleteMutation.mutateAsync,
    isPending: submitMutation.isPending || updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
    isLoading: existingQuery.isLoading,
  };
};
