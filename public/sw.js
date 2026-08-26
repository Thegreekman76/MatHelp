// sw.js — service worker de MatHelp (F6, "instalable en el celu").
//
// Alcance deliberadamente chico: cachea los estáticos (íconos, sound.js, el
// manifest) para que la app instalada abra al toque, y deja pasar TODO lo
// demás a la red. Las páginas son dinámicas y con sesión (auth), y el juego
// necesita el server + WebSocket, así que no las cacheamos — el objetivo acá
// es la instalabilidad + arranque rápido, no jugar offline.
//
// Al cambiar los estáticos, subí la versión del cache (mathelp-vN) para que
// el SW viejo se limpie en el activate.
var CACHE = "mathelp-v2";
var ASSETS = ["/favicon.svg", "/sound.js", "/manifest.webmanifest"];

self.addEventListener("install", function (e) {
  e.waitUntil(
    caches.open(CACHE).then(function (c) {
      return c.addAll(ASSETS);
    }).then(function () {
      return self.skipWaiting();
    })
  );
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(
        keys.filter(function (k) { return k !== CACHE; })
            .map(function (k) { return caches.delete(k); })
      );
    }).then(function () {
      return self.clients.claim();
    })
  );
});

self.addEventListener("fetch", function (e) {
  var req = e.request;
  if (req.method !== "GET") return;
  var url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  // JS: network-first. El JS de la app (sound.js) cambia seguido; servirlo del
  // cache "para siempre" dejaba a los usuarios con una versión vieja (bug real).
  // Ahora va siempre a la red y rellena el cache; el cache es solo fallback offline.
  if (/\.js$/.test(url.pathname)) {
    e.respondWith(
      fetch(req).then(function (res) {
        var copy = res.clone();
        caches.open(CACHE).then(function (c) { c.put(req, copy); });
        return res;
      }).catch(function () { return caches.match(req); })
    );
    return;
  }
  // Otros estáticos (íconos, manifest, css): cache-first (rara vez cambian).
  if (/\.(svg|webmanifest|css|png|ico)$/.test(url.pathname)) {
    e.respondWith(
      caches.match(req).then(function (hit) {
        return hit || fetch(req).then(function (res) {
          var copy = res.clone();
          caches.open(CACHE).then(function (c) { c.put(req, copy); });
          return res;
        });
      })
    );
    return;
  }
  // Páginas y todo lo demás: red directa (sin fallback offline en este MVP).
});
