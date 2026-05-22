import { apiClient } from './client';

export type PushSubscriptionPayload = {
  endpoint: string;
  keys: {
    p256dh: string;
    auth: string;
  };
  user_agent?: string;
};

export const pushApi = {
  getVapidPublicKey: async (): Promise<string> => {
    const { data } = await apiClient.get<{ public_key: string }>('/api/push/vapid-public-key');
    return data.public_key;
  },

  saveSubscription: async (payload: PushSubscriptionPayload): Promise<void> => {
    await apiClient.post('/api/push/subscriptions', payload);
  },
};
