import axios, { type AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios';

import { getRuntimeEnv } from '../lib/runtime-env';

type ApiRequestMetadata = {
  startedAt: number;
  requestId: string;
};

type InstrumentedAxiosRequestConfig = InternalAxiosRequestConfig & {
  metadata?: ApiRequestMetadata;
  _retry?: boolean;
};

type InstrumentedAxiosError = AxiosError & {
  config?: InstrumentedAxiosRequestConfig;
};

const SLOW_API_REQUEST_MS = 1500;
const ANALYTICS_EVENTS_PATH = '/api/v1/events';

const getRequestPath = (url?: string): string => {
  if (!url) return '';
  try {
    return new URL(url, window.location.origin).pathname;
  } catch {
    return url;
  }
};

const shouldTrackApiRequest = (config?: InstrumentedAxiosRequestConfig): boolean => {
  return getRequestPath(config?.url) !== ANALYTICS_EVENTS_PATH;
};

const emitOperationalApiEvent = (
  eventType: 'failed_api_request' | 'slow_api_request',
  response: AxiosResponse | undefined,
  config: InstrumentedAxiosRequestConfig | undefined,
  errorCode?: string
) => {
  if (!shouldTrackApiRequest(config)) return;
  const startedAt = config?.metadata?.startedAt;
  const durationMs = startedAt ? Math.round(performance.now() - startedAt) : undefined;

  window.dispatchEvent(
    new CustomEvent('analytics:operational_event', {
      detail: {
        eventType,
        context: {
          method: config?.method?.toUpperCase(),
          path: getRequestPath(config?.url),
          status: response?.status,
          duration_ms: durationMs,
          request_id: config?.metadata?.requestId,
          backend_request_id: response?.headers?.['x-request-id'],
          error_code: errorCode,
        },
      },
    })
  );
};

export const apiClient = axios.create({
  baseURL: getRuntimeEnv('VITE_API_URL'),
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  const instrumentedConfig = config as InstrumentedAxiosRequestConfig;
  const requestId = crypto.randomUUID();
  instrumentedConfig.metadata = {
    startedAt: performance.now(),
    requestId,
  };
  instrumentedConfig.headers['X-Request-ID'] = requestId;

  const token = localStorage.getItem('access_token');
  if (token) {
    instrumentedConfig.headers.Authorization = `Bearer ${token}`;
  }
  return instrumentedConfig;
});

apiClient.interceptors.response.use(
  (response) => {
    const config = response.config as InstrumentedAxiosRequestConfig;
    const startedAt = config.metadata?.startedAt;
    const durationMs = startedAt ? performance.now() - startedAt : 0;
    if (durationMs >= SLOW_API_REQUEST_MS) {
      emitOperationalApiEvent('slow_api_request', response, config);
    }
    return response;
  },
  async (error) => {
    const instrumentedError = error as InstrumentedAxiosError;
    const originalRequest = instrumentedError.config;
    emitOperationalApiEvent(
      'failed_api_request',
      instrumentedError.response,
      originalRequest,
      instrumentedError.code ?? 'unknown'
    );
    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) {
          localStorage.removeItem('access_token');
          window.dispatchEvent(new CustomEvent('auth:logout'));
          return Promise.reject(error);
        }
        const res = await axios.post(`${apiClient.defaults.baseURL}/api/auth/refresh`, {
          refresh_token: refreshToken,
        });
        const { access_token, refresh_token: new_refresh_token } = res.data;
        localStorage.setItem('access_token', access_token);
        localStorage.setItem('refresh_token', new_refresh_token);

        apiClient.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.dispatchEvent(new CustomEvent('auth:logout'));
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  }
);
