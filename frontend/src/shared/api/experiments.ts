import { apiClient } from './client';

type ExperimentAssignment = {
  experiment_key: string;
  variant: string;
};

type ExperimentAssignmentsResponse = {
  assignments: Record<string, ExperimentAssignment>;
};

const EXPERIMENTS_CACHE_KEY = 'experiment_assignments_cache_v1';
const ANONYMOUS_ID_KEY = 'feature_flags_anonymous_id';

let cachedAssignments: Record<string, ExperimentAssignment> = {};

const getAnonymousId = (): string => {
  let id = localStorage.getItem(ANONYMOUS_ID_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(ANONYMOUS_ID_KEY, id);
  }
  return id;
};

const readCachedAssignments = (): Record<string, ExperimentAssignment> => {
  try {
    const raw = localStorage.getItem(EXPERIMENTS_CACHE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return typeof parsed === 'object' && parsed !== null ? (parsed as Record<string, ExperimentAssignment>) : {};
  } catch {
    return {};
  }
};

cachedAssignments = readCachedAssignments();

export const refreshExperimentAssignments = async () => {
  const response = await apiClient.get<ExperimentAssignmentsResponse>('/api/v1/experiments/assignments', {
    headers: {
      'X-Anonymous-ID': getAnonymousId(),
    },
  });
  cachedAssignments = response.data.assignments;
  localStorage.setItem(EXPERIMENTS_CACHE_KEY, JSON.stringify(cachedAssignments));
  return cachedAssignments;
};

export const getCachedExperimentContext = (): Record<string, string> => {
  return Object.fromEntries(
    Object.entries(cachedAssignments).map(([key, assignment]) => [`experiment.${key}`, assignment.variant])
  );
};
