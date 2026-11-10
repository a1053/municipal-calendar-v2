/* Service worker mínimo: primero la red (siempre datos frescos) y, si no hay internet,
 * lo último que se vio. Solo toca archivos del propio sitio. */
<<<<<<< HEAD
const CACHE = "municipal-v5";
=======
const CACHE = "municipal-v6";
>>>>>>> origin/main
const SHELL = ["./", "styles.css", "app.js", "stats.js", "liguilla.js", "forecast.js", "live.js", "pitch.js", "topics.js", "share.js", "config.json",
  "manifest.webmanifest", "icons/icon-192.png", "icons/icon-512.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL).catch(() => {})).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== self.location.origin) return;
  e.respondWith(
    fetch(req).then((res) => {
      if (res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); }
      return res;
    }).catch(() => caches.match(req, { ignoreSearch: true }).then((hit) => hit || caches.match("./")))
  );
});
