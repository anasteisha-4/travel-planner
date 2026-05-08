import { apiClient } from '@/shared/api';
import type {
  BudgetPredictRequest,
  BudgetPredictResponse,
  BudgetMonitorRequest,
  BudgetMonitorResponse,
  DestinationValidationRequest,
  DestinationValidationResponse,
  RecommendDestinationRequest,
  RecommendRequest,
  RecommendationsResponse,
  ScoredDestination,
} from '../model/types';

export const recommendationsApi = {
  getRecommendations: async (params: RecommendRequest): Promise<RecommendationsResponse> => {
    const { data } = await apiClient.post<RecommendationsResponse>('/api/v1/recommend', params);
    return data;
  },

  getDestinationScore: async (params: RecommendDestinationRequest): Promise<ScoredDestination> => {
    const { data } = await apiClient.post<ScoredDestination>('/api/v1/recommend/destination', params);
    return data;
  },

  getBudgetPrediction: async (params: BudgetPredictRequest): Promise<BudgetPredictResponse> => {
    const { data } = await apiClient.post<BudgetPredictResponse>('/api/v1/budget/predict', params);
    return data;
  },

  getBudgetMonitor: async (params: BudgetMonitorRequest): Promise<BudgetMonitorResponse> => {
    const { data } = await apiClient.post<BudgetMonitorResponse>('/api/v1/budget/monitor', params);
    return data;
  },

  validateDestination: async (params: DestinationValidationRequest): Promise<DestinationValidationResponse> => {
    const { data } = await apiClient.post<DestinationValidationResponse>('/api/v1/validate', params);
    return data;
  },
};
