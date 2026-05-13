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

export type EventsResponse = {
  events: AdminEvent[];
};

export const getDashboardSummary = async (): Promise<DashboardSummary> => {
  const response = await apiClient.get<DashboardSummary>('/api/v1/admin/dashboards/summary');
  return response.data;
};

export const getAdminEvents = async (eventType?: string): Promise<EventsResponse> => {
  const response = await apiClient.get<EventsResponse>('/api/v1/admin/dashboards/events', {
    params: {
      event_type: eventType || undefined,
      limit: 100,
    },
  });
  return response.data;
};
