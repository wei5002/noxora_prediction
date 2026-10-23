const CACHE_NAME = "noxora-static-v2";
const APP_SHELL = [
  "/",
  "/manifest.json",
  "/icons/icon-192.png",
  "/icons/icon-519.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE_NAME);

      await Promise.all(
        APP_SHELL.map(async (url) => {
          try {
            const response = await fetch(url);

            if (response.ok) {
              await cache.put(url, response);
            }
          } catch (error) {
            console.warn("Gagal menyimpan cache:", url, error);
          }
        }),
      );

      await self.skipWaiting();
    })(),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();

      await Promise.all(
        keys
          .filter(
            (key) => key.startsWith("noxora-static-") && key !== CACHE_NAME,
          )
          .map((key) => caches.delete(key)),
      );

      await self.clients.claim();
    })(),
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);

  if (request.method !== "GET" || url.origin !== self.location.origin) {
    return;
  }

  // Cache-first untuk file aplikasi Next.js dan aset statis.
  const isStaticAsset =
    url.pathname.startsWith("/_next/static/") ||
    url.pathname === "/manifest.json" ||
    url.pathname.startsWith("/icons/");

  if (isStaticAsset) {
    event.respondWith(
      (async () => {
        const cache = await caches.open(CACHE_NAME);
        const cachedResponse = await cache.match(request);

        if (cachedResponse) {
          return cachedResponse;
        }

        try {
          const response = await fetch(request);

          if (response.ok) {
            await cache.put(request, response.clone());
          }

          return response;
        } catch (error) {
          return new Response("Aset belum tersedia secara offline.", {
            status: 503,
            headers: {
              "Content-Type": "text/plain; charset=utf-8",
            },
          });
        }
      })(),
    );

    return;
  }

  // Network-first untuk halaman, dengan fallback ke cache.
  if (request.mode === "navigate") {
    event.respondWith(
      (async () => {
        try {
          const response = await fetch(request);

          if (response.ok) {
            const cache = await caches.open(CACHE_NAME);
            await cache.put("/", response.clone());
          }

          return response;
        } catch (error) {
          const cachedPage = await caches.match("/");

          if (cachedPage) {
            return cachedPage;
          }

          return new Response(
            "Noxora sedang offline. Hubungkan kembali perangkat ke internet.",
            {
              status: 503,
              headers: {
                "Content-Type": "text/plain; charset=utf-8",
              },
            },
          );
        }
      })(),
    );
  }
});
