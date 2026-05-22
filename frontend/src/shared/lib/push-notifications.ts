import { pushApi, type PushSubscriptionPayload } from '@/shared/api/push';

const urlBase64ToUint8Array = (base64String: string) => {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = `${base64String}${padding}`.replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  return Uint8Array.from([...rawData].map((char) => char.charCodeAt(0)));
};

const subscriptionToPayload = (subscription: PushSubscription): PushSubscriptionPayload | null => {
  const json = subscription.toJSON();
  if (!json.endpoint || !json.keys?.p256dh || !json.keys.auth) return null;
  return {
    endpoint: json.endpoint,
    keys: {
      p256dh: json.keys.p256dh,
      auth: json.keys.auth,
    },
    user_agent: navigator.userAgent,
  };
};

export const ensurePushNotifications = async () => {
  if (!('Notification' in window)) {
    return false;
  }

  const permission =
    Notification.permission === 'default'
      ? await Notification.requestPermission()
      : Notification.permission;
  if (permission !== 'granted') return false;

  if (!window.isSecureContext || !('serviceWorker' in navigator) || !('PushManager' in window)) {
    return false;
  }

  const publicKey = await pushApi.getVapidPublicKey();
  if (!publicKey) return false;

  const registration = await navigator.serviceWorker.ready;
  const existing = await registration.pushManager.getSubscription();
  const subscription =
    existing ??
    (await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(publicKey),
    }));
  const payload = subscriptionToPayload(subscription);
  if (!payload) return false;
  await pushApi.saveSubscription(payload);
  return true;
};
