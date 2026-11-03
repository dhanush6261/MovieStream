/**
 * sw-register.js
 * Registers the service worker so the offline fallback page works.
 * Fails silently on browsers without support instead of throwing.
 */
if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
        navigator.serviceWorker
            .register("/static/service-worker.js")
            .catch((err) => console.warn("Service worker registration failed:", err));
    });
}
