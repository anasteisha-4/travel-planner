import { apiClient } from '@/shared/api';
import type {
  BudgetPredictRequest,
  BudgetPredictResponse,
  RecommendRequest,
  RecommendationsResponse,
} from '../model/types';

export const recommendationsApi = {
  getRecommendations: async (params: RecommendRequest): Promise<RecommendationsResponse> => {
    const { data } = await apiClient.post<RecommendationsResponse>('/api/v1/recommend', params);
    return data;
  },

  getBudgetPrediction: async (params: BudgetPredictRequest): Promise<BudgetPredictResponse> => {
    const { data } = await apiClient.post<BudgetPredictResponse>('/api/v1/budget/predict', params);
    return data;
  },
};
