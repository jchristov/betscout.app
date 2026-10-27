const CACHE_NAME = 'betscout-pwa-v0.5.0';
const DATA_CACHE_NAME = 'betscout-data-v0.5.0';
const SHELL_ASSETS = [
  '/',
  '/app',
  '/manifest.webmanifest',
  '/betscout-logo.svg',
  '/favicon.svg',
];

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_ASSETS)).catch(() => {})
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== CACHE_NAME && k !== DATA_CACHE_NAME && k.startsWith('betscout-'))
          .map((k) => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  // Skip SSE stream
  if (url.pathname === '/api/stream') return;

  // Network-first with offline cache fallback for /api/snapshot and /api/data
  if (url.pathname === '/api/snapshot' || url.pathname === '/api/data') {
    event.respondWith(
      fetch(req)
        .then((resp) => {
          if (resp && resp.ok) {
            const clone = resp.clone();
            caches.open(DATA_CACHE_NAME).then((c) => c.put(req, clone)).catch(() => {});
          }
          return resp;
        })
        .catch(() => caches.match(req))
    );
    return;
  }

  // Skip other /api/ endpoints from static cache
  if (url.pathname.startsWith('/api/')) return;

  // Navigation requests (/, /app) -> Network first, fallback to cached index/shell
  if (req.mode === 'navigate' || url.pathname === '/' || url.pathname === '/app') {
    event.respondWith(
      fetch(req)
        .then((resp) => {
          const clone = resp.clone();
          caches.open(CACHE_NAME).then((c) => c.put(req, clone)).catch(() => {});
          return resp;
        })
        .catch(() => caches.match(req).then((r) => r || caches.match('/')))
    );
    return;
  }

  // Static assets (/assets/*, SVGs, fonts) -> Stale-While-Revalidate
  event.respondWith(
    caches.match(req).then((cached) => {
      const netFetch = fetch(req)
        .then((resp) => {
          if (resp && resp.ok) {
            const clone = resp.clone();
            caches.open(CACHE_NAME).then((c) => c.put(req, clone)).catch(() => {});
          }
          return resp;
        })
        .catch(() => cached);
      return cached || netFetch;
    })
  );
});
