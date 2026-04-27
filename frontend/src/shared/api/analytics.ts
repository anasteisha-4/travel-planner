import { apiClient } from './client';

type EventType =
  | 'recommendation_shown'
  | 'recommendation_clicked'
  | 'destination_detail_opened'
  | 'budget_predicted'
  | 'trip_created'
  | 'onboarding_step_completed'
  | 'onboarding_completed';

type QueuedEvent = {
  event_type: EventType;
  entity_type?: string;
  entity_id?: string;
  context?: Record<string, unknown>;
};

type EventPayload = QueuedEvent & { session_id: string };

type BatchPayload = {
  events: EventPayload[];
};

const SESSION_KEY = 'analytics_session_id';

const getSessionId = (): string => {
  let id = sessionStorage.getItem(SESSION_KEY);
  if (!id) {
    id = crypto.randomUUID();
    sessionStorage.setItem(SESSION_KEY, id);
  }
  return id;
};

const queue: QueuedEvent[] = [];
let flushTimer: ReturnType<typeof setTimeout> | null = null;

const flush = () => {
  if (queue.length === 0) return;

  const sessionId = getSessionId();
  const payload: BatchPayload = {
    events: queue.map((e) => ({ ...e, session_id: sessionId })),
  };
  queue.splice(0, queue.length);

  apiClient.post('/api/v1/events', payload).catch(() => {
    // fire-and-forget — silently ignore failures
  });
};

const scheduleFlush = () => {
  if (flushTimer !== null) return;
  flushTimer = setTimeout(() => {
    flushTimer = null;
    flush();
  }, 5000);
};

if (typeof window !== 'undefined') {
  window.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') flush();
  });
  window.addEventListener('pagehide', flush);
}

export const sendEvent = (
  eventType: EventType,
  context?: Record<string, unknown>,
  entityType?: string,
  entityId?: string
) => {
  queue.push({
    event_type: eventType,
    entity_type: entityType,
    entity_id: entityId,
    context,
  });
  scheduleFlush();
};
