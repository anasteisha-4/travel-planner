import { apiClient } from './client';
import { createClientUuid } from '../lib/uuid';

type EvaluatedFlag = {
  key: string;
  enabled: boolean;
  payload: Record<string, unknown>;
};

type EvaluatedFlagsResponse = {
  flags: Record<string, EvaluatedFlag>;
};

const FLAGS_CACHE_KEY = 'feature_flags_cache_v1';
const ANONYMOUS_ID_KEY = 'feature_flags_anonymous_id';

let cachedFlags: Record<string, EvaluatedFlag> = {};

const getAnonymousId = (): string => {
  let id = localStorage.getItem(ANONYMOUS_ID_KEY);
  if (!id) {
    id = createClientUuid();
    localStorage.setItem(ANONYMOUS_ID_KEY, id);
  }
  return id;
};

const readCachedFlags = (): Record<string, EvaluatedFlag> => {
  try {
    const raw = localStorage.getItem(FLAGS_CACHE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return typeof parsed === 'object' && parsed !== null ? (parsed as Record<string, EvaluatedFlag>) : {};
  } catch {
    return {};
  }
};

const writeCachedFlags = (flags: Record<string, EvaluatedFlag>) => {
  cachedFlags = flags;
  localStorage.setItem(FLAGS_CACHE_KEY, JSON.stringify(flags));
};

cachedFlags = readCachedFlags();

export const refreshFeatureFlags = async () => {
  const response = await apiClient.get<EvaluatedFlagsResponse>('/api/v1/flags', {
    headers: {
      'X-Anonymous-ID': getAnonymousId(),
      'X-Platform': 'web',
    },
  });
  writeCachedFlags(response.data.flags);
  return response.data.flags;
};

export const getCachedFeatureFlag = (key: string, fallback = false): boolean => {
  return cachedFlags[key]?.enabled ?? fallback;
};

export const getCachedFeatureFlagPayload = (key: string): Record<string, unknown> => {
  return cachedFlags[key]?.payload ?? {};
};
