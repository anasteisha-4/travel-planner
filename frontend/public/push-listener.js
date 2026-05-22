self.addEventListener('push', (event) => {
  const fallback = {
    title: 'Triply',
    body: 'Маршрут поездки сгенерирован',
    url: '/',
    tag: 'triply-update',
  };
  let payload = fallback;
  try {
    payload = event.data ? event.data.json() : fallback;
  } catch (_error) {
    payload = fallback;
  }
  const title = payload.title || fallback.title;
  const options = {
    body: payload.body || fallback.body,
    icon: '/pwa-192x192.png',
    badge: '/pwa-192x192.png',
    tag: payload.tag || fallback.tag,
    data: {
      url: payload.url || fallback.url,
    },
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const targetUrl = new URL(event.notification.data?.url || '/', self.location.origin).href;

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if ('focus' in client) {
          client.navigate(targetUrl);
          return client.focus();
        }
      }
      return self.clients.openWindow(targetUrl);
    })
  );
});
