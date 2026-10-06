const CACHE_NAME = 'climber-v1';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/favicon.svg'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );

  self.skipWaiting(); // Activate immediately
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  const cacheWhitelist = [CACHE_NAME];

  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (!cacheWhitelist.includes(cacheName)) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );

  self.clients.claim(); // Take control of all clients
});

// Fetch event - network first, fallback to cache
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip chrome-extension and other non-http requests
  if (!url.protocol.startsWith('http')) {
    return;
  }

  event.respondWith(
    fetch(request)
      .then((response) => {
        // Cache successful responses
        if (response.status === 200) {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, responseClone);
          });
        }
        return response;
      })
      .catch(() => {
        return caches.match(request).then((cached) => {
          if (!cached) {
            // For navigation requests without a cached copy, fall back to the
            // shell so the app can still start; for everything else, let the
            // fetch reject so callers see a real network failure.
            if (request.mode === 'navigate') {
              return caches.match('/index.html');
            }
            return undefined;
          }
          // Serving a stale cached response for a list/detail payload. Tell the
          // page so it can surface an offline hint instead of pretending the
          // data is current (R12-H63).
          self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
            clients.forEach((client) => client.postMessage({ type: 'STALE_RESPONSE', url: request.url }));
          });
          return cached;
        });
      })
  );
});

// Background sync for offline actions
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-messages') {
    event.waitUntil(syncMessages());
  }
});

async function syncMessages() {
  // Implementation for syncing pending messages
  const clients = await self.clients.matchAll();
  clients.forEach((client) => {
    client.postMessage({ type: 'SYNC_COMPLETE' });
  });
}

// Push notifications
self.addEventListener('push', (event) => {
  const data = event.data?.json();
  const title = data?.title || 'Climber Notification';
  const options = data?.options || {
    body: 'You have a new notification',
    icon: '/icon-192x192.png',
    badge: '/icon-96x96.png'
  };

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

// Notification click handler
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  event.waitUntil(
    self.clients.openWindow('/')
  );
});
