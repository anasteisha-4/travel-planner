import { useMutation, useQueryClient } from '@tanstack/react-query';
import { itineraryApi } from '../api/itinerary.api';
import type { ItineraryGenerateRequest, ItineraryGenerateResponse } from './types';

type GenerateVariables = {
  tripId: string;
  params: ItineraryGenerateRequest;
};

export const itineraryQueryKey = (
  tripId: string,
  destinationId: string,
  startDate: string,
  durationDays: number
) => ['itinerary', tripId, destinationId, startDate, durationDays] as const;

export const useGenerateItinerary = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ params }: GenerateVariables) => itineraryApi.generate(params),
    onSuccess: (data: ItineraryGenerateResponse, variables) => {
      queryClient.setQueryData(
        itineraryQueryKey(
          variables.tripId,
          variables.params.destination_id,
          variables.params.start_date,
          variables.params.duration_days
        ),
        data
      );
    },
  });
};
