/* Service worker Paralaksy (plx site zapisuje go jako /sw.js, serwer wydaje go bez logowania).
   Dwie rzeczy: przeglądarka proponuje instalację aplikacji tylko ze stroną, która go ma, i przez niego przychodzą
   powiadomienia o nowym wydaniu (serwer wysyła je po wdrożeniu, hosting/powiadomienia.py). Niczego nie zapisuje
   w pamięci podręcznej: strony zawsze idą z sieci, bez sieci tylko krótka informacja. */
const OFFLINE = '<!doctype html><html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">' +
  '<title>Paralaksa</title></head><body style="margin:0;background:#f4f0e8;color:#1d1b18;font:16px Segoe UI,sans-serif">' +
  '<p style="max-width:520px;margin:20vh auto;padding:0 20px">Brak połączenia z siecią. Paralaksa wróci, gdy wróci internet.</p>' +
  '</body></html>';

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));

self.addEventListener("fetch", e => {
  if (e.request.mode !== "navigate" || e.request.method !== "GET") return;
  e.respondWith(fetch(e.request).catch(() => new Response(OFFLINE, { headers: { "Content-Type": "text/html; charset=utf-8" } })));
});

self.addEventListener("push", e => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch (err) { d = { body: e.data ? e.data.text() : "" }; }
  e.waitUntil(self.registration.showNotification(d.title || "Paralaksa", {
    body: d.body || "Nowe wydanie", icon: "/icon-192.png", tag: d.tag || "wydanie", data: { url: d.url || "/" },
  }));
});

self.addEventListener("notificationclick", e => {
  e.notification.close();
  const url = new URL((e.notification.data && e.notification.data.url) || "/", self.location.origin).href;
  e.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then(wins => {
    for (const w of wins) {
      if ("focus" in w && "navigate" in w) return w.navigate(url).then(x => (x || w).focus());
    }
    return self.clients.openWindow(url);
  }));
});
