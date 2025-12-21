// Service Worker pour DEFITECH PWA
// Version 1.0.0

const CACHE_NAME = 'defitech-v1.0.0';
const STATIC_CACHE_NAME = 'defitech-static-v1.0.0';
const DYNAMIC_CACHE_NAME = 'defitech-dynamic-v1.0.0';

// Ressources à mettre en cache lors de l'installation
const STATIC_ASSETS = [
  '/',
  '/static/css/style.css',
  '/static/js/sw.js',
  '/static/assets/favicon.png',
  '/static/images/icons/icon-192x192.png',
  '/static/images/icons/icon-512x512.png',
  '/manifest.json',
  '/offline.html'
];

// Pages importantes à mettre en cache
const IMPORTANT_PAGES = [
  '/login',
  '/profile',
  '/community',
  '/etudiant/dashboard',
  '/enseignant/dashboard'
];

// Cache des ressources statiques
const STATIC_ASSETS_CACHE = [
  '/static/css/',
  '/static/js/',
  '/static/assets/',
  '/static/images/'
];

// Installation du Service Worker
self.addEventListener('install', event => {
  console.log('Service Worker: Installing...');

  event.waitUntil(
    caches.open(STATIC_CACHE_NAME)
      .then(cache => {
        console.log('Service Worker: Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => {
        console.log('Service Worker: Static assets cached successfully');
        return self.skipWaiting();
      })
      .catch(error => {
        console.error('Service Worker: Error caching static assets', error);
      })
  );
});

// Activation du Service Worker
self.addEventListener('activate', event => {
  console.log('Service Worker: Activating...');

  event.waitUntil(
    caches.keys()
      .then(cacheNames => {
        return Promise.all(
          cacheNames.map(cacheName => {
            if (cacheName !== STATIC_CACHE_NAME &&
              cacheName !== DYNAMIC_CACHE_NAME &&
              cacheName.startsWith('defitech-')) {
              console.log('Service Worker: Deleting old cache', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => {
        console.log('Service Worker: Activated successfully');
        return self.clients.claim();
      })
  );
});

// Interception des requêtes
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Stratégie pour les ressources statiques (CSS, JS, images)
  if (STATIC_ASSETS_CACHE.some(path => url.pathname.startsWith(path))) {
    event.respondWith(
      cacheFirst(request)
    );
  }
  // Stratégie pour les pages importantes
  else if (IMPORTANT_PAGES.some(page => url.pathname.startsWith(page)) ||
    url.pathname === '/' || url.pathname.startsWith('/community')) {
    event.respondWith(
      networkFirst(request)
    );
  }
  // Stratégie pour les autres requêtes (API, etc.)
  else if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      networkOnly(request)
    );
  }
  // Stratégie par défaut
  else {
    event.respondWith(
      staleWhileRevalidate(request)
    );
  }
});

// Stratégie Cache First - pour les ressources statiques
async function cacheFirst(request) {
  try {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(STATIC_CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }

    return networkResponse;
  } catch (error) {
    console.error('Cache First strategy failed:', error);
    // Retourner une page d'erreur pour les images
    if (request.destination === 'image') {
      return new Response('', { status: 404 });
    }
    return new Response('Offline', { status: 503 });
  }
}

// Stratégie Network First - pour les pages importantes
async function networkFirst(request) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(DYNAMIC_CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.log('Network First strategy: Network failed, trying cache');
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    // Si c'est une page HTML, retourner la page offline
    if (request.headers.get('accept')?.includes('text/html')) {
      const offlineResponse = await caches.match('/offline.html');
      if (offlineResponse) {
        return offlineResponse;
      }
    }

    return new Response('Offline', {
      status: 503,
      headers: { 'Content-Type': 'text/plain' }
    });
  }
}

// Stratégie Network Only - pour les requêtes API
async function networkOnly(request) {
  try {
    return await fetch(request);
  } catch (error) {
    return new Response(JSON.stringify({
      error: 'Offline',
      message: 'Cette fonctionnalité nécessite une connexion internet'
    }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

// Stratégie Stale While Revalidate - pour les autres ressources
async function staleWhileRevalidate(request) {
  const cache = await caches.open(DYNAMIC_CACHE_NAME);
  const cachedResponse = await cache.match(request);

  const networkFetch = fetch(request)
    .then(networkResponse => {
      if (networkResponse.ok) {
        cache.put(request, networkResponse.clone());
      }
      return networkResponse;
    })
    .catch(error => {
      console.log('Stale While Revalidate: Network failed');
      return cachedResponse;
    });

  return cachedResponse || networkFetch;
}

// Gestion des messages du client
self.addEventListener('message', event => {
  const { type, data } = event.data;

  switch (type) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;

    case 'GET_VERSION':
      event.ports[0].postMessage({
        type: 'VERSION',
        data: { version: CACHE_NAME }
      });
      break;

    case 'CLEAR_CACHE':
      clearAllCaches();
      break;
  }
});

// Fonction pour vider tous les caches
async function clearAllCaches() {
  const cacheNames = await caches.keys();
  await Promise.all(
    cacheNames.map(cacheName => caches.delete(cacheName))
  );
  console.log('Service Worker: All caches cleared');
}

// Gestion de la synchronisation en arrière-plan
self.addEventListener('sync', event => {
  if (event.tag === 'background-sync') {
    console.log('Service Worker: Background sync triggered');
    // Ici on peut ajouter la logique de sync des données offline
  }
});

// Gestion des notifications push (si nécessaire plus tard)
self.addEventListener('push', event => {
  if (event.data) {
    const data = event.data.json();
    const options = {
      body: data.body,
      icon: '/static/images/icons/icon-192x192.png',
      badge: '/static/images/icons/icon-72x72.png',
      tag: data.tag || 'defitech-notification',
      requireInteraction: false,
      actions: data.actions || []
    };

    event.waitUntil(
      self.registration.showNotification(data.title, options)
    );
  }
});

// Gestion des clics sur les notifications
self.addEventListener('notificationclick', event => {
  event.notification.close();

  if (event.action) {
    // Gérer les actions des notifications
    console.log('Notification action:', event.action);
  } else {
    // Ouvrir l'application
    event.waitUntil(
      clients.openWindow(event.notification.data?.url || '/')
    );
  }
});
