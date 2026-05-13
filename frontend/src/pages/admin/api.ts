import { apiClient } from '@/shared/api';

export type AdminEvent = {
  id: string;
  event_id: string | null;
  user_id: string | null;
  session_id: string;
  event_type: string;
  entity_type: string | null;
  entity_id: string | null;
  context: Record<string, unknown>;
  client_meta: Record<string, unknown>;
  created_at: string | null;
};

export type DashboardSummary = {
  product: {
    active_users: number;
    active_sessions: number;
    counts: Record<string, number>;
  };
  ml: {
    counts: Record<string, number>;
  };
  operational: {
    counts: Record<string, number>;
  };
  recent_events: AdminEvent[];
};

export type EventsFilters = {
  eventType?: string;
  userId?: string;
  sessionId?: string;
  entityId?: string;
};

export type EventsResponse = {
  events: AdminEvent[];
};

export type FeatureFlag = {
  key: string;
  description: string | null;
  enabled: boolean;
  rollout_percentage: number;
  environment: string;
  targeting_json: Record<string, unknown> | null;
  payload_json: Record<string, unknown> | null;
};

export type Experiment = {
  key: string;
  description: string | null;
  status: string;
  variants_json: string[];
  metrics_json: Record<string, unknown> | null;
  guardrails_json: Record<string, unknown> | null;
};

export type ExperimentReport = {
  experiment_key: string;
  variants: Record<string, Record<string, number>>;
};

export type MLDatasetReport = {
  builder_version: string;
  contract_version: string;
  readiness: Record<string, boolean>;
  ranker: Record<string, unknown>;
  budget: Record<string, unknown>;
  itinerary: Record<string, unknown>;
};

export type DatasetSnapshot = {
  id: string;
  dataset_type: string;
  row_count: number;
  positive_count: number;
  metadata: Record<string, unknown>;
  created_at: string | null;
};

export type ModelRegistryItem = {
  id: string;
  name: string;
  version: string;
  model_type: string;
  is_active: boolean;
  metrics: Record<string, unknown>;
  trained_at: string | null;
  created_at: string | null;
};

export type RecommendationDebug = {
  recommendation_log: Record<string, unknown> | null;
  events: AdminEvent[];
};

export type TimelineResponse = {
  sessions: Array<{
    session_id: string;
    events: AdminEvent[];
  }>;
};

export const getDashboardSummary = async (): Promise<DashboardSummary> => {
  const response = await apiClient.get<DashboardSummary>('/api/v1/admin/dashboards/summary');
  return response.data;
};

export const getAdminEvents = async (filters: EventsFilters): Promise<EventsResponse> => {
  const response = await apiClient.get<EventsResponse>('/api/v1/admin/dashboards/events', {
    params: {
      event_type: filters.eventType || undefined,
      user_id: filters.userId || undefined,
      session_id: filters.sessionId || undefined,
      entity_id: filters.entityId || undefined,
      limit: 100,
    },
  });
  return response.data;
};

export const getTimeline = async (filters: EventsFilters): Promise<TimelineResponse> => {
  const response = await apiClient.get<TimelineResponse>('/api/v1/admin/diagnostics/timeline', {
    params: {
      user_id: filters.userId || undefined,
      session_id: filters.sessionId || undefined,
      limit: 200,
    },
  });
  return response.data;
};

export const getFeatureFlags = async (): Promise<FeatureFlag[]> => {
  const response = await apiClient.get<FeatureFlag[]>('/api/v1/admin/feature-flags');
  return response.data;
};

export const updateFeatureFlag = async (flag: Pick<FeatureFlag, 'key' | 'enabled' | 'rollout_percentage'>) => {
  const response = await apiClient.patch<FeatureFlag>(`/api/v1/admin/feature-flags/${flag.key}`, {
    enabled: flag.enabled,
    rollout_percentage: flag.rollout_percentage,
  });
  return response.data;
};

export const getExperiments = async (): Promise<Experiment[]> => {
  const response = await apiClient.get<Experiment[]>('/api/v1/admin/experiments');
  return response.data;
};

export const getExperimentReport = async (experimentKey: string): Promise<ExperimentReport> => {
  const response = await apiClient.get<ExperimentReport>(`/api/v1/admin/experiments/${experimentKey}/report`);
  return response.data;
};

export const getMLDatasetReport = async (): Promise<MLDatasetReport> => {
  const response = await apiClient.get<MLDatasetReport>('/api/v1/admin/ml-datasets/report');
  return response.data;
};

export const createMLDatasetSnapshot = async (): Promise<DatasetSnapshot> => {
  const response = await apiClient.post<DatasetSnapshot>('/api/v1/admin/ml-datasets/snapshots', null, {
    params: { dataset_type: 'all' },
  });
  return response.data;
};

export const getModelRegistry = async (): Promise<{ models: ModelRegistryItem[] }> => {
  const response = await apiClient.get<{ models: ModelRegistryItem[] }>('/api/v1/admin/diagnostics/models');
  return response.data;
};

export const getRecommendationDebug = async (recommendationId: string): Promise<RecommendationDebug> => {
  const response = await apiClient.get<RecommendationDebug>(
    `/api/v1/admin/diagnostics/recommendations/${recommendationId}`
  );
  return response.data;
};

export const getBudgetDebug = async (tripId: string): Promise<{ events: AdminEvent[]; feedback: unknown[] }> => {
  const response = await apiClient.get<{ events: AdminEvent[]; feedback: unknown[] }>('/api/v1/admin/diagnostics/budget', {
    params: { trip_id: tripId || undefined },
  });
  return response.data;
};

export const getItineraryDebug = async (tripId: string): Promise<{ events: AdminEvent[] }> => {
  const response = await apiClient.get<{ events: AdminEvent[] }>('/api/v1/admin/diagnostics/itinerary', {
    params: { trip_id: tripId || undefined },
  });
  return response.data;
};
