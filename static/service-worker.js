/**
 * service-worker.js
 *
 * Minimal offline support: caches the core static assets on install,
 * and falls back to /static/offline.html for page navigations that
 * fail because the network is unreachable.
 *
 * This intentionally does NOT cache movie/poster files -- caching
 * large binary media in the service worker cache is a later
 * milestone (Streaming / adaptive quality), not part of the basic
 * offline-page requirement.
 */

// Bump this whenever a cached file changes: assets are served
// cache-first, so without a new name returning visitors keep the old
// JS/CSS indefinitely. (v2: api.js now sends the CSRF header.)
const CACHE_NAME = "moviestream-shell-v2";
const APP_SHELL = [
    "/static/css/variables.css",
    "/static/css/base.css",
    "/static/css/navbar.css",
    "/static/css/hero.css",
    "/static/css/movie-card.css",
    "/static/css/home.css",
    "/static/css/components.css",
    "/static/js/api.js",
    "/static/js/main.js",
    "/static/js/navbar.js",
    "/static/js/horizontal-scroll.js",
    "/static/js/movie-card.js",
    "/static/js/hero.js",
    "/static/js/search.js",
    "/static/offline.html",
];

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
    );
    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys
                    .filter((key) => key !== CACHE_NAME)
                    .map((key) => caches.delete(key))
            )
        )
    );
    self.clients.claim();
});

self.addEventListener("fetch", (event) => {
    // Only intercept page navigations; let every other request
    // (API calls, video streaming ranges) go straight to the network.
    if (event.request.mode === "navigate") {
        event.respondWith(
            fetch(event.request).catch(() => caches.match("/static/offline.html"))
        );
        return;
    }

    event.respondWith(
        caches.match(event.request).then((cached) => cached || fetch(event.request))
    );
});
