'use strict';

// Verziju pri objavi zamjenjuje GitHub Actions (kratki SHA commita), da se predmemorija
// osvježi kad se stranica promijeni. Lokalno ostaje "dev".
const VERSION = 'dev';
const CACHE = `akcije-${VERSION}`;
const SHELL = ['./', 'index.html', 'style.css', 'app.js', 'manifest.webmanifest',
  'icon-192.png', 'icon-512.png', 'icon-maskable-512.png', 'apple-touch-icon.png'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((imena) => Promise.all(imena.filter((n) => n !== CACHE).map((n) => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.origin !== self.location.origin) return;

  // Cjenik: uvijek prvo mreža (podaci se mijenjaju svaki dan), spremljena kopija je
  // rezerva kad nema signala. Ostalo: prvo predmemorija, pa tiho osvježavanje.
  if (url.pathname.endsWith('/data.json')) {
    e.respondWith(
      fetch(e.request)
        .then((r) => {
          const kopija = r.clone();
          caches.open(CACHE).then((c) => c.put(e.request, kopija));
          return r;
        })
        .catch(() => caches.match(e.request))
    );
    return;
  }

  e.respondWith(
    caches.match(e.request).then((spremljeno) => {
      const sMreze = fetch(e.request).then((r) => {
        if (r.ok) {
          const kopija = r.clone();
          caches.open(CACHE).then((c) => c.put(e.request, kopija));
        }
        return r;
      }).catch(() => spremljeno);
      return spremljeno || sMreze;
    })
  );
});
