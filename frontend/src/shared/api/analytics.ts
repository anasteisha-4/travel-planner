import { apiClient } from './client';
import { getCachedExperimentContext } from './experiments';
import { getCachedFeatureFlag } from './feature-flags';

type EventType =
  | 'app_opened'
  | 'page_viewed'
  | 'session_started'
  | 'session_ended'
  | 'login_started'
  | 'login_succeeded'
  | 'login_failed'
  | 'recommendation_shown'
  | 'recommendation_impression'
  | 'recommendation_clicked'
  | 'destination_detail_opened'
  | 'recommendation_filter_changed'
  | 'recommendation_search_started'
  | 'recommendation_search_result_opened'
  | 'recommendation_empty_state_shown'
  | 'budget_predicted'
  | 'budget_prediction_viewed'
  | 'budget_prediction_changed'
  | 'budget_monitor_viewed'
  | 'budget_risk_shown'
  | 'validation_viewed'
  | 'validation_warning_expanded'
  | 'trip_created'
  | 'trip_opened'
  | 'trip_status_changed'
  | 'itinerary_generated'
  | 'itinerary_viewed'
  | 'itinerary_edited'
  | 'itinerary_variant_generated'
  | 'itinerary_approved'
  | 'itinerary_regenerated'
  | 'itinerary_poi_removed'
  | 'itinerary_poi_added'
  | 'itinerary_poi_pinned'
  | 'itinerary_poi_reordered'
  | 'itinerary_poi_moved'
  | 'itinerary_poi_visited'
  | 'itinerary_day_regenerated'
  | 'place_visit_marked_visited'
  | 'expense_added'
  | 'expense_updated'
  | 'expense_deleted'
  | 'post_trip_feedback_submitted'
  | 'post_trip_feedback_updated'
  | 'profile_viewed'
  | 'profile_updated'
  | 'profile_origin_changed'
  | 'profile_budget_changed'
  | 'profile_preferences_changed'
  | 'currency_changed'
  | 'rest_level_changed'
  | 'failed_api_request'
  | 'slow_api_request'
  | 'frontend_error'
  | 'frontend_unhandled_rejection'
  | 'service_worker_error'
  | 'network_status_changed'
  | 'external_api_call_completed'
  | 'onboarding_step_completed'
  | 'onboarding_completed'
  | 'onboarding_abandoned';

type EntityType = 'destination' | 'trip' | 'itinerary' | 'model' | 'profile' | 'user' | 'experiment';

type QueuedEvent = {
  event_id: string;
  event_type: EventType;
  event_version: number;
  entity_type?: EntityType;
  entity_id?: string;
  context?: Record<string, unknown>;
  occurred_at: string;
  client_meta: {
    platform: 'web';
    app_version: string;
    path: string;
    referrer: string;
  };
};

type EventPayload = QueuedEvent & { session_id: string };

type BatchPayload = {
  events: EventPayload[];
};

const SESSION_KEY = 'analytics_session_id';
const QUEUE_KEY = 'analytics_event_queue_v1';
const COLLECTION_KEY = 'analytics_collection_enabled';
const EVENT_VERSION = 1;
const FLUSH_INTERVAL_MS = 5000;
const MAX_QUEUE_SIZE = 250;
const MAX_BATCH_SIZE = 25;
const FORBIDDEN_KEY_PARTS = ['password', 'token', 'secret', 'email', 'oauth', 'description', 'note', 'free_text'];

let appOpenedSent = false;
let sessionStartedSent = false;
let sessionEndedSent = false;
let lastPageViewPath: string | null = null;
let flushTimer: ReturnType<typeof setTimeout> | null = null;
let frontendObservabilityInitialized = false;

const getSessionId = (): string => {
  let id = sessionStorage.getItem(SESSION_KEY);
  if (!id) {
    id = crypto.randomUUID();
    sessionStorage.setItem(SESSION_KEY, id);
  }
  return id;
};

const isRecord = (value: unknown): value is Record<string, unknown> => {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
};

const isForbiddenKey = (key: string): boolean => {
  const normalized = key.toLowerCase();
  return FORBIDDEN_KEY_PARTS.some((part) => normalized.includes(part));
};

const sanitizeValue = (value: unknown): unknown => {
  if (Array.isArray(value)) return value.map(sanitizeValue);

  if (isRecord(value)) {
    return Object.fromEntries(
      Object.entries(value)
        .filter(([key]) => !isForbiddenKey(key))
        .map(([key, nestedValue]) => [key, sanitizeValue(nestedValue)])
    );
  }

  return value;
};

const sanitizeContext = (context?: Record<string, unknown>): Record<string, unknown> | undefined => {
  if (!context) return undefined;
  const sanitized = sanitizeValue(context);
  return isRecord(sanitized) ? sanitized : undefined;
};

const isAnalyticsEnabled = (): boolean => {
  if (!getCachedFeatureFlag('analytics_collection_enabled', true)) return false;
  return localStorage.getItem(COLLECTION_KEY) !== 'false';
};

const readQueue = (): QueuedEvent[] => {
  try {
    const raw = localStorage.getItem(QUEUE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as QueuedEvent[]) : [];
  } catch {
    return [];
  }
};

const writeQueue = (nextQueue: QueuedEvent[]) => {
  localStorage.setItem(QUEUE_KEY, JSON.stringify(nextQueue.slice(-MAX_QUEUE_SIZE)));
};

const queue: QueuedEvent[] = readQueue();

const flush = () => {
  if (queue.length === 0) return;

  const sessionId = getSessionId();
  const batch = queue.splice(0, MAX_BATCH_SIZE);
  writeQueue(queue);
  const payload: BatchPayload = {
    events: batch.map((event) => ({ ...event, session_id: sessionId })),
  };

  apiClient.post('/api/v1/events', payload).catch(() => {
    queue.unshift(...batch);
    writeQueue(queue);
  });
};

const scheduleFlush = () => {
  if (flushTimer !== null) return;
  flushTimer = setTimeout(() => {
    flushTimer = null;
    flush();
  }, FLUSH_INTERVAL_MS);
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
  entityType?: EntityType,
  entityId?: string
) => {
  if (!isAnalyticsEnabled()) return;

  queue.push({
    event_id: crypto.randomUUID(),
    event_type: eventType,
    event_version: EVENT_VERSION,
    entity_type: entityType,
    entity_id: entityId,
    context: sanitizeContext(context),
    occurred_at: new Date().toISOString(),
    client_meta: {
      platform: 'web',
      app_version: import.meta.env.VITE_APP_VERSION ?? 'dev',
      path: window.location.pathname,
      referrer: document.referrer,
    },
  });
  const last = queue[queue.length - 1];
  last.context = sanitizeContext({
    ...(last.context ?? {}),
    ...getCachedExperimentContext(),
  });
  writeQueue(queue);
  scheduleFlush();
};

export const setAnalyticsCollectionEnabled = (enabled: boolean) => {
  localStorage.setItem(COLLECTION_KEY, enabled ? 'true' : 'false');
};

export const sendAppOpened = () => {
  if (appOpenedSent) return;
  appOpenedSent = true;
  sendEvent('app_opened', { path: window.location.pathname });
};

export const sendSessionStarted = () => {
  if (sessionStartedSent) return;
  sessionStartedSent = true;
  sendEvent('session_started', { path: window.location.pathname });
};

export const sendSessionEnded = () => {
  if (sessionEndedSent) return;
  sessionEndedSent = true;
  sendEvent('session_ended', { path: window.location.pathname });
  flush();
};

export const sendPageViewed = (path: string) => {
  if (lastPageViewPath === path) return;
  lastPageViewPath = path;
  sendEvent('page_viewed', { path });
};

export const initFrontendObservability = () => {
  if (frontendObservabilityInitialized) return;
  frontendObservabilityInitialized = true;

  window.addEventListener('analytics:operational_event', (event) => {
    const detail = (event as CustomEvent<{ eventType?: EventType; context?: Record<string, unknown> }>).detail;
    if (!detail?.eventType) return;
    sendEvent(detail.eventType, detail.context);
  });

  window.addEventListener('error', (event) => {
    sendEvent('frontend_error', {
      message: event.message,
      source: event.filename,
      line: event.lineno,
      column: event.colno,
    });
  });

  window.addEventListener('unhandledrejection', (event) => {
    sendEvent('frontend_unhandled_rejection', {
      reason_type: typeof event.reason,
      reason_name: event.reason instanceof Error ? event.reason.name : undefined,
      reason_message: event.reason instanceof Error ? event.reason.message : undefined,
    });
  });

  window.addEventListener('online', () => {
    sendEvent('network_status_changed', { status: 'online' });
  });

  window.addEventListener('offline', () => {
    sendEvent('network_status_changed', { status: 'offline' });
  });

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      sendEvent('service_worker_error', { reason_code: 'controller_changed' });
    });
  }
};

export const sendRecommendationEvent = (
  eventType: Extract<
    EventType,
    | 'recommendation_shown'
    | 'recommendation_impression'
    | 'recommendation_clicked'
    | 'destination_detail_opened'
    | 'recommendation_filter_changed'
  >,
  context: Record<string, unknown>,
  destinationId?: string
) => {
  sendEvent(eventType, context, destinationId ? 'destination' : undefined, destinationId);
};

export const sendTripEvent = (
  eventType: Extract<EventType, 'trip_created' | 'trip_opened' | 'trip_status_changed'>,
  context: Record<string, unknown>,
  tripId?: string
) => {
  sendEvent(eventType, context, tripId ? 'trip' : undefined, tripId);
};

export const sendBudgetEvent = (
  eventType: Extract<
    EventType,
    | 'budget_predicted'
    | 'budget_prediction_viewed'
    | 'budget_prediction_changed'
    | 'budget_monitor_viewed'
    | 'budget_risk_shown'
  >,
  context: Record<string, unknown>,
  entityId?: string,
  entityType?: Extract<EntityType, 'destination' | 'trip'>
) => {
  sendEvent(eventType, context, entityType, entityId);
};

export const sendItineraryEvent = (
  eventType: Extract<
    EventType,
    | 'itinerary_generated'
    | 'itinerary_viewed'
    | 'itinerary_edited'
    | 'itinerary_approved'
    | 'itinerary_regenerated'
    | 'itinerary_poi_removed'
    | 'itinerary_poi_added'
    | 'itinerary_poi_reordered'
    | 'itinerary_poi_moved'
    | 'itinerary_poi_visited'
  >,
  context: Record<string, unknown>,
  tripId?: string
) => {
  sendEvent(eventType, context, tripId ? 'trip' : undefined, tripId);
};

export const sendFeedbackEvent = (
  eventType: Extract<EventType, 'post_trip_feedback_submitted' | 'post_trip_feedback_updated'>,
  context: Record<string, unknown>,
  tripId?: string
) => {
  sendEvent(eventType, context, tripId ? 'trip' : undefined, tripId);
};
