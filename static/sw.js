const CACHE_NAME = "pharos-static-v1";
const IMAGE_CACHE_NAME = "pharos-images-v1";

const STATIC_ASSETS = [
  "/",
  "/static/index.html",
  "/static/styles.css",
  "/static/app.js",
  "/static/three_bg.js",
  "/static/lighthouse_spinner.js",
  "/static/stacks_3d.js",
  "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Playfair+Display:ital,wght@0,600;1,600&display=swap",
  "https://unpkg.com/@phosphor-icons/web",
  "https://cdnjs.cloudflare.com/ajax/libs/dompurify/3.0.6/purify.min.js"
];

// Install Event - Pre-cache static shell
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log("[Service Worker] Pre-caching offline shell...");
      return cache.addAll(STATIC_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

// Activate Event - Clean up old caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cache) => {
          if (cache !== CACHE_NAME && cache !== IMAGE_CACHE_NAME) {
            console.log("[Service Worker] Clearing old cache:", cache);
            return caches.delete(cache);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Helper to check if a request is for an image
function isImageRequest(request) {
  const url = request.url;
  // Check destination or common image extensions/headers
  if (request.destination === "image") return true;
  if (url.match(/\.(jpg|jpeg|gif|png|webp|svg)/i)) return true;
  return false;
}

// Fetch Event - Caching strategy
self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);

  // Ignore non-GET requests and browser extensions (e.g., chrome-extension://)
  if (request.method !== "GET" || !url.protocol.startsWith("http")) {
    return;
  }

  // 1. Handle API calls: Network only (let app.js handle database caching via IndexedDB)
  if (url.pathname.startsWith("/api/")) {
    return;
  }

  // 2. Handle Image requests: Cache-First strategy
  if (isImageRequest(request)) {
    event.respondWith(
      caches.open(IMAGE_CACHE_NAME).then((cache) => {
        return cache.match(request).then((cachedResponse) => {
          if (cachedResponse) {
            return cachedResponse;
          }
          // Fetch from network, cache, and return
          return fetch(request)
            .then((networkResponse) => {
              if (networkResponse.ok) {
                cache.put(request, networkResponse.clone());
              }
              return networkResponse;
            })
            .catch(() => {
              // Return a fallback SVG/Image if offline and image not cached
              return new Response(
                `<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" viewBox="0 0 24 24" fill="none" stroke="#2a2c3a" stroke-width="2"><rect width="20" height="20" x="2" y="2" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/></svg>`,
                { headers: { "Content-Type": "image/svg+xml" } }
              );
            });
        });
      })
    );
    return;
  }

  // 3. Handle Static Assets (HTML/CSS/JS): Stale-While-Revalidate
  event.respondWith(
    caches.match(request).then((cachedResponse) => {
      const fetchPromise = fetch(request)
        .then((networkResponse) => {
          if (networkResponse.ok) {
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(request, networkResponse.clone());
            });
          }
          return networkResponse;
        })
        .catch(() => {
          // If network fails, we just don't update cache.
        });

      return cachedResponse || fetchPromise;
    })
  );
});
