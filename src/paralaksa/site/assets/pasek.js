/* Wspólny pasek i stopka wersji 2.0 (plx site zapisuje go jako v2/pasek.js, z logo w środku).
   Strona dnia ma tylko <div id="pasek" data-dzien="RRRR-MM-DD" [data-wstecz]> i ten skrypt zaraz za nim, więc zmiana
   paska to zmiana jednego pliku, bez przebudowy stron. Po lewej logo, pod nim na całą szerokość wybór dnia (duże ‹ › i data,
   lista z v2/dni.json) albo, na stronach tematów i spraw, powrót do strony dnia. W stopce link do starej wersji.
   Na serwerze (window.plxJa, wstawiane przez hosting/server.py) dochodzi menu osoby: imię, powiadomienia o nowym wydaniu,
   instalacja aplikacji, wylogowanie; oraz service worker /sw.js (bez niego Chrome nie proponuje instalacji). */
// Kółko nad poziomo przewijanym rzędem (filtry osi czasu, przyciski krajów) przesuwa go w bok; na końcu rzędu albo gdy
// się mieści, przewija stronę normalnie. Wywołanie: plxKolko(element).
window.plxKolko = el => el.addEventListener("wheel", ev => {
  if (ev.ctrlKey || Math.abs(ev.deltaX) >= Math.abs(ev.deltaY)) return;
  const m = el.scrollWidth - el.clientWidth;
  if (m <= 1 || (ev.deltaY < 0 && el.scrollLeft <= 0) || (ev.deltaY > 0 && el.scrollLeft >= m - 1)) return;
  ev.preventDefault(); el.scrollLeft += ev.deltaY;
}, { passive: false });

(() => {
  const LOGO = "__LOGO__";
  const box = document.getElementById("pasek");
  if (!box) return;
  const base = new URL(".", document.currentScript.src);          // .../v2/
  const day = box.dataset.dzien || "";
  const short = d => d.slice(8, 10) + "." + d.slice(5, 7);
  const page = d => new URL(d + "/index.html", base).href;

  const style = document.createElement("style");
  style.textContent =
    ".bar2{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:10px 12px;padding:12px 16px;background:#1d1b18;" +
    "color:#f4f0e8;font:14px Segoe UI,sans-serif}.bar2 a{color:#f4f0e8;text-decoration:none}.bar2 .logo{line-height:0;flex:none}" +
    ".bar2 .logo svg{height:26px;width:auto}.bar2 .dni{display:flex;align-items:center;gap:6px;white-space:nowrap}" +
    // przełącznik dni (od 02.10, dla starszych osób): duże przyciski ‹ › po bokach, data na środku. Na telefonie przyklejony
    // jasny pasek na dole ekranu (górny pasek zostaje sam z logo), od 640 px w ciemnym pasku u góry, obok logo
    ".bar2 .nawi{position:fixed;left:0;right:0;bottom:0;z-index:40;display:grid;grid-template-columns:64px minmax(0,1fr) 64px;gap:8px;" +
    "padding:8px 10px calc(8px + env(safe-area-inset-bottom));background:#f4f0e8;border-top:2px solid #1d1b18;" +
    "box-shadow:0 -4px 14px rgba(0,0,0,.12)}body{padding-bottom:78px}" +
    ".bar2 .nawi a,.bar2 .nawi .pusty{display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:52px;" +
    "border:2px solid #1d1b18;border-radius:10px;background:#fbf8f2;color:#1d1b18;line-height:1.1}.bar2 .nawi .pusty{visibility:hidden}" +
    ".bar2 .nawi a b{font-size:40px;line-height:.75}.bar2 .nawi a small{font-size:13px;color:#5a554c}" +
    ".bar2 .nawi a:hover,.bar2 .nawi a:focus-visible,.bar2 .nawi select:focus-visible{border-color:#8a3b2a;outline:2px solid #8a3b2a}" +
    ".bar2 .nawi select,.bar2 .nawi .data{width:100%;min-height:52px;min-width:0;font:700 17px Segoe UI,sans-serif;text-align:center;text-align-last:center;appearance:none;" +
    "background:#1d1b18;color:#f4f0e8;border:2px solid #1d1b18;border-radius:10px;padding:6px 8px;cursor:pointer;box-sizing:border-box}" +
    ".bar2 .nawi .data{display:flex;align-items:center;justify-content:center}" +
    ".bar2 .nawi.wroc{grid-template-columns:1fr}.bar2 .nawi.wroc a{flex-direction:row;gap:10px;font:700 18px Segoe UI,sans-serif}" +
    ".baner-ja{bottom:86px!important}" +
    "@media(min-width:640px){.bar2 .nawi{position:static;flex:0 1 430px;margin-left:auto;padding:0;background:none;border:0;box-shadow:none}" +
    "body{padding-bottom:0}.baner-ja{bottom:8px!important}.bar2 .nawi a,.bar2 .nawi .pusty{background:#2c2924;color:#f4f0e8;border-color:#8a7f6e}" +
    ".bar2 .nawi a small{color:#d8d1c3}.bar2 .nawi select,.bar2 .nawi .data{background:#f4f0e8;color:#1d1b18;border-color:#f4f0e8}}" +
    ".stopka{max-width:720px;margin:28px auto 0;padding:14px 16px 72px;border-top:1px solid #ddd5c7;" +
    "display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px 16px;color:#7a746a;font:13px Segoe UI,sans-serif}" +
    ".stopka a{color:#8a3b2a}" +
    "@media(min-width:640px){.bar2{padding:14px max(20px,calc(50% - 360px))}.bar2 .logo svg{height:36px}}";
  document.head.append(style);

  box.className = "bar2";
  box.innerHTML = `<a class="logo" href="${page(day)}" aria-label="Paralaksa, strona dnia">${LOGO}</a>` +
    `<nav class="nawi" aria-label="Wybór dnia"></nav><span class="dni"></span>`;
  const right = box.querySelector(".dni");                     // miejsce na menu osoby (serwer)
  const nav = box.querySelector(".nawi");
  const wide = matchMedia("(min-width:480px)").matches;      // na telefonie skrót dnia tygodnia, żeby data się mieściła
  const long = d => new Date(d + "T12:00:00").toLocaleDateString("pl-PL", { weekday: wide ? "long" : "short", day: "numeric", month: "long" });
  const link = (d, text, title) => {
    const a = document.createElement("a");
    a.href = page(d);
    a.innerHTML = text;
    a.title = title;
    return a;
  };

  if ("wstecz" in box.dataset) {
    nav.classList.add("wroc");
    nav.append(link(day, `<b>‹</b> Wróć do dnia ${short(day)}`, "Wróć do strony dnia"));
  } else {
    nav.innerHTML = `<span class="pusty"></span><span class="data">${long(day)}</span><span class="pusty"></span>`;
    fetch(new URL("dni.json", base), { cache: "no-store" }).then(r => r.json()).then(days => {
      const i = days.indexOf(day);
      const select = document.createElement("select");
      select.setAttribute("aria-label", "Dzień");
      for (const d of days) select.add(new Option(long(d), d, false, d === day));
      select.onchange = () => { location.href = page(select.value); };
      const side = (d, arrow, title) => {
        if (!d) { const s = document.createElement("span"); s.className = "pusty"; return s; }
        const a = link(d, `<b>${arrow}</b><small>${short(d)}</small>`, title);
        a.setAttribute("aria-label", `${title}: ${long(d)}`);
        return a;
      };
      nav.textContent = "";
      nav.append(side(i >= 0 && i < days.length - 1 ? days[i + 1] : null, "‹", "Poprzedni dzień"), select,
                 side(i > 0 ? days[i - 1] : null, "›", "Następny dzień"));
    }).catch(() => {});
  }

  // Kafelek „Dzień po dniu” (v2/os.json, gdy jest) na stronie dnia jako druga pozycja: zaraz pod nagłówkiem „Co w prasie piszczy” (okładka HTML, od 02.10; bez niej pod paskiem), w stylu sekcji okładki:
  // oś ostatnich dni z kwadratowymi kadrami na zakładkę; otwiera oś na tym dniu (#d=), a dzień spoza osi na jej końcu
  if (!("wstecz" in box.dataset)) {
    fetch(new URL("os.json", base), { cache: "no-store" }).then(r => r.ok ? r.json() : null).then(w => {
      if (!w || !w.dni || !w.dni.length) return;
      const dir = new URL("os/", base).href;
      const st = document.createElement("style");
      st.textContent =
        ".kafel-os{display:block;max-width:720px;margin:10px auto;box-sizing:border-box;background:#f4f0e8;border:2px solid #1d1b18;" +
        "border-radius:6px;overflow:hidden;text-decoration:none;color:#1d1b18;font:14px Segoe UI,sans-serif}" +
        ".kafel-os:hover{box-shadow:0 0 0 3px rgba(138,59,42,.25)}.kafel-os .gl{display:flex;align-items:center;justify-content:space-between}" +
        ".kafel-os .et{background:#8a3b2a;color:#fff;font:700 1.3em Georgia,serif;padding:4px 16px 4px 10px;" +
        "clip-path:polygon(0 0,100% 0,calc(100% - 10px) 100%,0 100%)}.kafel-os .gl i{font:700 1em Georgia,serif;font-style:normal;color:#8a3b2a;padding-right:10px}" +
        ".kafel-os .os{position:relative;display:flex;justify-content:space-between;padding:10px 10px 6px}" +
        ".kafel-os .os:before{content:'';position:absolute;left:10px;right:10px;height:3px;background:#1d1b18;top:58px}" +
        ".kafel-os .d{display:flex;flex-direction:column;align-items:center;flex:1}.kafel-os .d b{font:700 11px Georgia,serif;color:#5a554c;margin-top:4px}" +
        ".kafel-os .st{display:flex;height:42px}.kafel-os .st img{width:38px;height:38px;object-fit:cover;border:2px solid #f4f0e8;border-radius:3px;" +
        "margin-left:-22px;box-shadow:0 1px 3px rgba(0,0,0,.25)}.kafel-os .st img:first-child{margin-left:0}" +
        ".kafel-os .kr{width:9px;height:9px;border-radius:50%;background:#8a3b2a;border:2px solid #f4f0e8;margin-top:5px;z-index:1}" +
        "@media(min-width:640px){.kafel-os .st{height:62px}.kafel-os .st img{width:58px;height:58px;margin-left:-30px}.kafel-os .os:before{top:78px}" +
        ".kafel-os .d b{font-size:13px}}@media(max-width:740px){.kafel-os{margin:8px 6px}}";
      document.head.append(st);
      const a = document.createElement("a");
      a.className = "kafel-os";
      a.dataset.sekcja = "os";
      a.href = dir + "index.html" + (w.od <= day && day <= w.do ? "#d=" + day : "");
      const days = w.dni.map(x => `<span class="d"><span class="st">${x.obrazki.map(f => `<img src="${dir + f}" alt="" loading="lazy">`).join("")}` +
        `</span><span class="kr"></span><b>${short(x.d)}</b></span>`).join("");
      a.innerHTML = `<span class="gl"><span class="et">Dzień po dniu</span><i>Oś czasu ›</i></span><span class="os">${days}</span>`;
      const put = () => (document.querySelector('[data-sekcja="okladka"] .okl-h') || box).after(a);
      document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", put) : put();
    }).catch(() => {});
  }

  // Czytanie na głos (od 02.10): Web Speech API przeglądarki, bez własnego modelu. Przyciski dodaje JS, tylko gdy jest
  // polski głos. Temat: blok [data-czytaj=temat] (podsumowanie) + sekcje [data-czytaj=kraj] w kolejności kraje-nav;
  // karta kraju i streszczenie artykułu mają własne głośniczki. Jedno czytanie naraz; tekst dzielony na zdania (Chrome
  // ucina długie wypowiedzi), kolejka zdań w JS.
  const mowa = (() => {
    const ss = window.speechSynthesis;
    if (!ss || typeof SpeechSynthesisUtterance === "undefined") return null;
    let voice = null, run = 0, active = null, keep = null;
    const pick = () => {
      const score = v => /Natural|Online/.test(v.name) ? 3 : /Google/.test(v.name) ? 2 : 1;
      const pl = ss.getVoices().filter(v => /^pl([-_]|$)/i.test(v.lang));
      voice = pl.sort((a, b) => score(b) - score(a))[0] || null;
      if (voice) document.dispatchEvent(new Event("plx-mowa"));
    };
    pick();
    if (!voice) ss.addEventListener("voiceschanged", () => { if (!voice) pick(); });
    const norm = s => (s || "").replace(/\s+/g, " ").trim();
    const chunks = text => norm(text).split(/(?<=[.!?…])\s+/).flatMap(z => {
      const out = [];
      while (z.length > 220) {                              // bardzo długie zdanie: tnij na przecinku/spacji
        let i = z.lastIndexOf(", ", 200); if (i < 60) i = z.lastIndexOf(" ", 200); if (i < 1) i = 200;
        out.push(z.slice(0, i + 1)); z = z.slice(i + 1).trim();
      }
      return z ? out.concat(z) : out;
    });
    const IKONA_GLOS = '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true"><path d="M3 9v6h4l5 4V5L7 9H3z"/><path d="M15.5 8.5a5 5 0 0 1 0 7M18 6a8.5 8.5 0 0 1 0 12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
    const IKONA_STOP = '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true"><rect x="5" y="5" width="14" height="14" rx="2"/></svg>';
    const look = (b, on) => {
      const big = b.classList.contains("duza");
      b.setAttribute("aria-pressed", String(on));
      b.setAttribute("aria-label", on ? "Zatrzymaj czytanie" : big ? "Czytaj temat na głos" : "Czytaj na głos");
      b.innerHTML = (on ? IKONA_STOP : IKONA_GLOS) + (on ? (big ? "Zatrzymaj" : "Stop") : (big ? "Czytaj temat" : "Czytaj"));
    };
    const stop = () => {
      run++; ss.cancel(); keep = null;
      if (active) { look(active.btn, false); active.mark && active.mark.classList.remove("czyta"); active = null; }
    };
    const start = (btn, items) => {                         // items: [{el, text, przed}]; el dostaje .czyta i jest przewijany
      stop();
      const id = run;
      active = { btn, mark: null };
      look(btn, true);
      let k = 0;
      const item = () => {
        if (id !== run) return;
        if (active.mark) active.mark.classList.remove("czyta");
        if (k >= items.length) return stop();
        const it = items[k++], parts = chunks(typeof it.text === "function" ? it.text() : it.text);
        if (it.przed) it.przed();
        if (it.el) { active.mark = it.el; it.el.classList.add("czyta"); it.el.scrollIntoView({ behavior: "smooth", block: "start" }); }
        let i = 0;
        const next = () => {
          if (id !== run) return;
          if (i >= parts.length) return item();
          const u = new SpeechSynthesisUtterance(parts[i++]);
          u.lang = "pl-PL"; u.rate = 1; if (voice) u.voice = voice;
          u.onend = next;
          u.onerror = e => { if (id === run && e.error !== "canceled" && e.error !== "interrupted") stop(); };
          keep = u;                                         // Chrome gubi wypowiedź bez referencji (brak onend)
          ss.speak(u);
        };
        next();
      };
      item();
    };
    const button = (cls, items, place) => {
      const b = document.createElement("button");
      b.type = "button"; b.className = "czytaj " + cls; look(b, false);
      b.onclick = e => { e.preventDefault(); e.stopPropagation(); active && active.btn === b ? stop() : start(b, items); };
      place(b); return b;
    };
    addEventListener("pagehide", stop);
    addEventListener("hashchange", stop);                   // zmiana kraju z zewnątrz (wstecz); nasza zmiana nie rusza hasha
    document.addEventListener("click", e => { if (e.isTrusted && e.target.closest && e.target.closest(".kraje-nav a")) stop(); });
    return { ok: () => !!voice, stop, button, norm, active: b => !!active && active.btn === b };
  })();
  const mowaStart = () => {
    if (!mowa) return;
    const init = () => {
      const nav = document.querySelector(".kraje-nav");
      const secs = [...document.querySelectorAll("section[id^=kraj-], section[id^=d-]")];
      const MIES = ["", "stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia", "września", "października", "listopada", "grudnia"];
      const sentence = t => { t = mowa.norm(t); return t && !/[.!?…:]$/.test(t) ? t + "." : t; };
      // treść karty: nagłówki h3 i akapity bez przypisów (.s), „ciągu dalszego” i listy artykułów
      const body = el => [...el.querySelectorAll(":scope > h3, :scope > p")].filter(x => !x.matches(".s, .ciag"))
        .map(x => sentence(x.textContent)).join(" ");
      const title = sec => {
        const h = sec.querySelector("h2");
        if (!h) return "";
        const c = h.cloneNode(true); c.querySelectorAll("a.osk, button, .s, .src").forEach(x => x.remove());
        const t = mowa.norm(c.textContent), m = t.match(/^(\d\d)\.(\d\d)$/);   // data osi kraju: „30.09” → „30 września”
        return sentence(m ? `${+m[1]} ${MIES[+m[2]] || m[2]}` : t);
      };
      const text = sec => title(sec) + " " + body(sec);
      // przy trybie „jeden kraj naraz” sekcja bywa ukryta: przełącz ją programowo (untrusted click nie zatrzymuje czytania)
      const show = sec => { if (sec.offsetParent === null && nav) { const b = nav.querySelector(`a[data-k="${sec.id.slice(5)}"]`); b && b.click(); } };
      secs.forEach(sec => {                                 // przycisk nad opisem karty kraju / dnia
        const first = sec.querySelector(":scope > h3, :scope > p");
        if (first && !sec.querySelector(":scope > .czytaj")) mowa.button("m", [{ text: () => text(sec) }], b => first.before(b));
      });
      document.querySelectorAll("article.ev .tresc").forEach(t => {   // oś czasu: tytuł i opis zdarzenia
        const h = t.querySelector("h2");
        if (h) mowa.button("m", [{ text: () => sentence(h.textContent) + " " + sentence((t.querySelector(".opis") || {}).textContent) }],
          b => h.after(b));
      });
      // cały temat: blok podsumowania (strona tematu) albo wstęp strony zestawienia + karty krajów po kolei
      const pods = document.querySelector(".pods"), lab = pods && pods.querySelector(".pods-l");
      const list = document.querySelector(".list:not(.jeden)"), h1 = list && list.querySelector(":scope > h1");
      const cards = secs.filter(x => x.id.startsWith("kraj-")).map(x => ({ el: x, przed: () => show(x), text: () => text(x) }));
      if (lab && !lab.querySelector(".czytaj")) {
        // podsumowanie tematu: wstęp i akapity zwinięte pod „Czytaj dalej” (.pods-wiecej), także gdy są zwinięte
        const podsText = () => body(pods) + [...pods.querySelectorAll(":scope > .pods-wiecej > p")]
          .map(x => " " + sentence(x.textContent)).join("");
        mowa.button("duza", [{ el: pods, text: podsText }]
          .concat(cards), b => lab.append(b));
      } else if (h1 && cards.length && !list.querySelector(":scope > .czytaj.duza")) {
        const lead = () => sentence(h1.textContent) + " " + [...list.querySelectorAll(":scope > p")].filter(x => !x.matches(".s"))
          .map(x => sentence(x.textContent)).join(" ");
        const at = list.querySelector(":scope > section");
        mowa.button("duza", [{ el: h1, text: lead }].concat(cards), b => { b.style.marginBottom = "10px"; at.before(b); });
      }
    };
    mowa.ok() ? init() : document.addEventListener("plx-mowa", init, { once: true });
  };
  document.addEventListener("DOMContentLoaded", mowaStart);
  const mst = document.createElement("style");
  mst.textContent =
    "button.czytaj{font:600 13px/1 Segoe UI,sans-serif;cursor:pointer;color:#fff;background:var(--art-akcent);" +
    "border:0;border-radius:999px;padding:7px 12px;vertical-align:middle;white-space:nowrap;" +
    "text-transform:none;letter-spacing:0;box-shadow:0 1px 3px rgba(0,0,0,.2)}" +
    "button.czytaj{display:inline-flex;align-items:center;gap:6px}button.czytaj.m{margin:0 0 8px}button.czytaj.duza{padding:8px 14px;font-size:14px}" +
    ".pods .pods-l{display:flex;flex-wrap:wrap;align-items:center;gap:8px 14px}" +
    ".streszcz button.czytaj{float:right;margin:0 0 4px 8px}" +
    "button.czytaj[aria-pressed=true]{background:var(--art-tusz);color:var(--art-tlo)}" +
    "button.czytaj:hover{filter:brightness(1.12)}" +
    "button.czytaj:focus-visible{outline:2px solid var(--art-focus);outline-offset:2px}" +
    ".czyta{outline:2px solid var(--art-akcent);outline-offset:6px;border-radius:12px}";
  document.head.append(mst);

  // Streszczenia (od 02.10): nagłówki z data-a to karty (art_card w scripts/v2/widok_obrazkowy.py); klik w kartę ze
  // streszczeniem (v2/streszczenia/<id/500>.json, scripts/v2/streszczenia.py) rozwija je w tej samej karcie z linkiem do
  // artykułu, drugi klik zwija. Pliki wczytane od razu po załadowaniu strony, żeby klik był synchroniczny (nowa karta po
  // fetch to dla przeglądarki wyskakujące okno). Karta bez streszczenia: ikona ↗, klik otwiera artykuł jak zwykle.
  const sums = {};
  document.addEventListener("DOMContentLoaded", () => {
    const ns = new Set([...document.querySelectorAll("a[data-a]")].map(a => Math.floor(Number(a.dataset.a) / 500)));
    Promise.all([...ns].map(n => fetch(new URL(`streszczenia/${n}.json`, base)).then(r => r.ok ? r.json() : {})
      .then(d => Object.assign(sums, d)).catch(() => {})))
      .then(() => document.querySelectorAll("a[data-a]").forEach(a => {   // strzałka tylko przy kartach ze streszczeniem
        if (!sums[a.dataset.a]) return;
        a.classList.add("ma-str");
        a.setAttribute("aria-expanded", "false");
        a.title = "Kliknij, aby rozwinąć streszczenie";
      }));
  });
  const sst = document.createElement("style");
  sst.textContent =
    ":root{--art-tlo:#fffdf8;--art-tlo-hover:#f6f0e4;--art-linia:#ddd5c7;--art-tusz:#1d1b18;--art-szary:#7a746a;" +
    "--art-akcent:#8a3b2a;--art-focus:#2f6db3}" +
    ":root[data-theme=dark]{--art-tlo:#24211d;--art-tlo-hover:#2e2a25;--art-linia:#3d3832;--art-tusz:#ece6dc;" +
    "--art-szary:#a49c90;--art-akcent:#d98a72;--art-focus:#7fb0ea}" +
    ".arts{margin:10px 0 4px}.arts-l{color:var(--art-szary);font:600 .72em/1.2 Segoe UI,sans-serif;letter-spacing:.06em;" +
    "text-transform:uppercase;margin:0 0 6px}ul.arts-u{list-style:none;margin:0;padding:0}" +
    "li.art{margin:0 0 8px;padding:0;background:var(--art-tlo);border:1px solid var(--art-linia);border-radius:12px;" +
    "overflow:hidden;line-height:1.4}" +
    "li.art>a[data-a]{display:flex;flex-direction:column;gap:4px;position:relative;padding:10px 52px 10px 12px;" +
    "color:var(--art-tusz);text-decoration:none;font-weight:500;cursor:pointer;border-radius:12px}" +
    "li.art>a[data-a]:hover{background:var(--art-tlo-hover)}" +
    "li.art>a[data-a]:focus-visible{outline:2px solid var(--art-focus);outline-offset:-2px}" +
    ".art-t{color:var(--art-tusz)}.art-m{color:var(--art-szary);font-size:.8em;font-weight:400}" +
    ".art-m .src{margin-left:0}" +
    "li.art>a[data-a]::after{content:\"↗\";position:absolute;right:12px;top:50%;width:28px;height:28px;margin-top:-14px;" +
    "border:1.5px solid var(--art-linia);border-radius:50%;display:flex;align-items:center;justify-content:center;" +
    "color:var(--art-akcent);font:600 15px/1 Segoe UI,sans-serif;transition:transform .25s}" +
    "li.art>a.ma-str::after{content:\"›\";font-size:24px;padding-bottom:3px;box-sizing:border-box}" +
    "li.art>a.ma-str.otw::after{transform:rotate(90deg)}li.art>a.otw{border-radius:12px 12px 0 0}" +
    ".streszcz{display:grid;grid-template-rows:0fr;transition:grid-template-rows .3s ease}" +
    ".streszcz.otw{grid-template-rows:1fr}.streszcz>div{overflow:hidden;min-height:0}" +
    ".streszcz>div>div{margin:0 12px 12px;padding:9px 0 0;border-top:1px solid var(--art-linia);" +
    "font:14px/1.5 Segoe UI,sans-serif;color:var(--art-tusz)}.streszcz p{margin:0 0 6px}" +
    ".streszcz .s{color:var(--art-szary);font-size:.82em}" +
    ".streszcz a.dalej{color:var(--art-akcent);font-weight:600;text-decoration:none}" +
    "@media(prefers-reduced-motion:reduce){.streszcz,li.art>a[data-a]::after{transition:none}}";
  document.head.append(sst);
  document.addEventListener("click", e => {
    const a = e.target.closest && e.target.closest("a[data-a]");
    if (!a || e.ctrlKey || e.metaKey || e.shiftKey || e.button) return;
    const s = sums[a.dataset.a];
    if (!s) return;
    e.preventDefault();
    let box = a.parentElement.querySelector(":scope > .streszcz");
    if (!box) {
      box = document.createElement("div");
      box.className = "streszcz";
      box.innerHTML = `<div><div><p></p><p class="s"></p><a class="dalej" target="_blank" rel="noopener">Przejdź do artykułu →</a></div></div>`;
      box.querySelector("p").textContent = s.t;
      box.querySelector(".s").textContent = s.lead
        ? "Streszczenie robocze (AI) tylko z tytułu i leadu: nie mamy pełnego tekstu (np. paywall)."
        : "Streszczenie robocze (AI) z treści artykułu.";
      box.querySelector("a").href = a.href;
      if (mowa && mowa.ok()) mowa.button("m", [{ text: () => (a.querySelector(".art-t")?.textContent || "") + ". " + s.t }],
        b => box.querySelector("p").before(b));
      a.after(box);
      box.offsetHeight;                                   // stan zwinięty przed animacją
    }
    const open = !box.classList.contains("otw");
    box.classList.toggle("otw", open);
    a.classList.toggle("otw", open);
    a.setAttribute("aria-expanded", String(open));
    const cb = box.querySelector(".czytaj");
    if (!open && mowa && cb && mowa.active(cb)) mowa.stop();
  });

  // --- menu osoby, instalacja i powiadomienia (tylko na serwerze: window.plxJa) ------------------------------------
  const ios = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  const standalone = matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  let installEvent = null;
  const later = (k, v) => { try { return v === undefined ? localStorage.getItem(k) : localStorage.setItem(k, v); } catch (e) { return null; } };
  addEventListener("beforeinstallprompt", e => { e.preventDefault(); installEvent = e; document.dispatchEvent(new Event("plx-instalacja")); });
  if ("serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "127.0.0.1" || location.hostname === "localhost")) navigator.serviceWorker.register("/sw.js").catch(() => {});

  const key = s => { const b = atob((s + "===".slice((s.length + 3) % 4)).replace(/-/g, "+").replace(/_/g, "/"));
    return Uint8Array.from(b, c => c.charCodeAt(0)); };
  const post = body => fetch("/_push", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body) }).then(r => { if (!r.ok) throw new Error(r.status); });
  const pushReady = () => "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
  const currentSub = () => navigator.serviceWorker.ready.then(r => r.pushManager.getSubscription());
  const pushOn = ja => Notification.requestPermission().then(p => {
    if (p !== "granted") throw new Error("odmowa");
    return navigator.serviceWorker.ready;
  }).then(r => r.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: key(ja.push) }))
    .then(sub => post({ sub: sub.toJSON() })).then(() => later("plx-push-sync", String(Date.now())));
  const pushOff = () => currentSub().then(sub => sub ? post({ usun: sub.endpoint }).catch(() => {}).then(() => sub.unsubscribe()) : null);

  const ui = document.createElement("style");
  ui.textContent =
    ".bar2 .ja{flex:none;width:30px;height:30px;border-radius:50%;border:1px solid #5a554c;background:#2c2924;color:#f4f0e8;" +
    "font:700 14px Segoe UI,sans-serif;cursor:pointer;margin-left:8px;padding:0}.bar2 .prawa{display:flex;align-items:center}" +
    ".menu-ja{position:absolute;right:max(8px,calc(50% - 352px));z-index:50;width:min(300px,calc(100vw - 16px));box-sizing:border-box;" +
    "background:#fbf8f2;color:#1d1b18;border:1px solid #ddd5c7;border-radius:10px;box-shadow:0 6px 24px rgba(0,0,0,.18);" +
    "padding:12px 14px;font:14px/1.45 Segoe UI,sans-serif}.menu-ja p{margin:0 0 10px}.menu-ja .s{color:#7a746a;font-size:.85em}" +
    ".menu-ja button,.baner-ja button{font:inherit;border:0;border-radius:6px;padding:6px 12px;background:#8a3b2a;color:#fff;cursor:pointer}" +
    ".menu-ja button.l{background:#5a554c}.menu-ja a{color:#8a3b2a}.menu-ja .r{display:flex;justify-content:space-between;gap:8px;margin-top:6px}" +
    ".baner-ja{position:fixed;left:8px;right:8px;bottom:8px;z-index:60;max-width:560px;margin:auto;display:flex;gap:10px;align-items:center;" +
    "background:#1d1b18;color:#f4f0e8;border-radius:10px;padding:10px 12px;font:14px/1.4 Segoe UI,sans-serif;box-shadow:0 6px 24px rgba(0,0,0,.25)}" +
    ".baner-ja span{flex:1}.baner-ja .x{background:none;color:#bdb6a8;padding:4px 6px}";

  const banner = (id, text, action) => {
    if (later(id) || document.querySelector(".baner-ja")) return;
    const b = document.createElement("div");
    b.className = "baner-ja";
    b.innerHTML = `<span></span>` + (action ? `<button class="tak"></button>` : "") + `<button class="x" aria-label="Zamknij">✕</button>`;
    b.querySelector("span").textContent = text;
    b.querySelector(".x").onclick = () => { later(id, "1"); b.remove(); };
    if (action) {
      b.querySelector(".tak").textContent = action[0];
      b.querySelector(".tak").onclick = () => { later(id, "1"); b.remove(); action[1](); };
    }
    document.body.append(b);
  };
  const install = () => {
    if (!installEvent) return;
    installEvent.prompt();
    installEvent.userChoice.finally(() => { installEvent = null; });
  };

  document.addEventListener("DOMContentLoaded", () => {
    const ja = window.plxJa;
    if (!ja) return;
    document.head.append(ui);
    const btn = document.createElement("button");
    btn.className = "ja";
    btn.title = ja.imie;
    btn.setAttribute("aria-label", "Menu: " + ja.imie);
    btn.textContent = (ja.imie || "?").trim().charAt(0).toUpperCase();
    const wrap = document.createElement("span");
    wrap.className = "prawa";
    right.replaceWith(wrap);
    wrap.append(right, btn);

    const menu = document.createElement("div");
    menu.className = "menu-ja";
    menu.hidden = true;
    document.body.append(menu);
    const render = () => {
      let push = "";
      if (ja.push && pushReady()) {
        push = `<p><b>Powiadomienia</b> o nowym wydaniu<br><span class="s" id="push-stan">sprawdzam…</span></p>`;
      } else if (ja.push && ios && !standalone) {
        push = `<p><b>Powiadomienia</b><br><span class="s">Na iPhonie działają w aplikacji: Udostępnij → „Do ekranu początkowego”, ` +
          `potem otwórz Paralaksę z ikony.</span></p>`;
      }
      let inst = "";
      if (!standalone && installEvent) inst = `<p><button class="inst">Zainstaluj aplikację</button></p>`;
      else if (!standalone && ios) inst = `<p class="s">Aplikacja na iPhonie: Udostępnij → „Do ekranu początkowego”.</p>`;
      menu.innerHTML = `<p>Zalogowano: <b class="kto"></b></p>${push}${inst}<div class="r">` +
        (ja.wlasciciel ? `<a href="/osoby">Osoby</a>` : "<span></span>") + `<a href="/wyloguj">Wyloguj</a></div>`;
      menu.querySelector(".kto").textContent = ja.imie;
      const ib = menu.querySelector(".inst");
      if (ib) ib.onclick = () => { menu.hidden = true; install(); };
      const st = menu.querySelector("#push-stan");
      if (!st) return;
      const show = sub => {
        if (Notification.permission === "denied") {
          st.textContent = "zablokowane w ustawieniach przeglądarki dla tej strony";
          return;
        }
        st.innerHTML = (sub ? "włączone na tym urządzeniu " : "wyłączone na tym urządzeniu ") +
          `<button class="${sub ? "l" : ""}">${sub ? "Wyłącz" : "Włącz"}</button>`;
        st.querySelector("button").onclick = () => {
          st.textContent = "chwila…";
          (sub ? pushOff() : pushOn(ja)).then(currentSub).then(show)
            .catch(() => { st.textContent = "nie udało się, spróbuj jeszcze raz"; setTimeout(() => currentSub().then(show), 2500); });
        };
      };
      currentSub().then(show).catch(() => { st.textContent = "niedostępne w tej przeglądarce"; });
    };
    btn.onclick = e => {
      e.stopPropagation();
      if (menu.hidden) { render(); menu.style.top = (btn.getBoundingClientRect().bottom + scrollY + 10) + "px"; }
      menu.hidden = !menu.hidden;
    };
    document.addEventListener("click", e => { if (!menu.hidden && !menu.contains(e.target)) menu.hidden = true; });
    document.addEventListener("plx-instalacja", () => { if (!menu.hidden) render(); });

    // subskrypcja raz na dobę jeszcze raz do serwera (gdyby ją zgubił), bez pytania o zgodę
    if (ja.push && pushReady() && Notification.permission === "granted" && Date.now() - Number(later("plx-push-sync") || 0) > 86400000) {
      currentSub().then(sub => sub && post({ sub: sub.toJSON() }).then(() => later("plx-push-sync", String(Date.now())))).catch(() => {});
    }
    // propozycje (raz, z zamknięciem na stałe): instalacja, a w zainstalowanej aplikacji powiadomienia
    const offerInstall = () => banner("plx-baner-instalacja", "Paralaksa jako aplikacja: ikona na ekranie, bez paska przeglądarki.",
      ["Zainstaluj", install]);
    if (installEvent) offerInstall(); else document.addEventListener("plx-instalacja", offerInstall, { once: true });
    if (!standalone && ios) banner("plx-baner-ios", "Paralaksa jako aplikacja: Udostępnij → „Do ekranu początkowego”.");
    if (standalone && ja.push && pushReady() && Notification.permission === "default") {
      banner("plx-baner-push", "Powiadomić Cię, gdy będzie nowe wydanie (raz dziennie)?", ["Tak", () => pushOn(ja).catch(() => {})]);
    }
  });

  // zwijany tekst: element z data-zwin przycięty w CSS strony (np. 4 linie); „więcej ›” tylko gdy coś jest ucięte
  document.addEventListener("DOMContentLoaded", () => document.querySelectorAll("[data-zwin]").forEach(el => {
    if (el.scrollHeight <= el.clientHeight + 1) return;
    const b = document.createElement("button");
    b.type = "button";
    b.className = "zwin-b";
    b.textContent = "więcej ›";
    b.setAttribute("aria-expanded", "false");
    b.addEventListener("click", () => {
      const open = el.classList.toggle("rozwin");
      b.textContent = open ? "mniej ‹" : "więcej ›";
      b.setAttribute("aria-expanded", String(open));
    });
    el.after(b);
  }));

  document.addEventListener("DOMContentLoaded", () => {
    // Kafel „Archiwum” (od 05.10) na dole strony dnia, przed stopką, w stylu sekcji okładki (belka i ciemny pas bez obrazka):
    // wyszukiwarka wszystkich artykułów (v2/archiwum/, src/paralaksa/site/archive.py); ?dzien= to powrót na ten dzień
    const archive = "__ARCHIWUM__";                                 // plx site: true, gdy zbudował v2/archiwum/
    if (archive && !("wstecz" in box.dataset)) {
      const a = document.createElement("div");
      a.className = "okl";
      a.innerHTML = "<h2 class=\"pp-sek\">Archiwum</h2>" +             // belka pierwsza: odstęp jak przed innymi sekcjami
        `<a class="okl-pas arch-pas" href="${new URL("archiwum/index.html?dzien=" + day, base).href}">` +
        "<span class=\"okl-t\"><b>Szukaj we wszystkich artykułach <span class=\"strz\">›</span></b>" +
        "<span class=\"okl-n\">Nagłówki, ramy i streszczenia ze wszystkich dni; kraj, źródło, temat, ton</span></span></a>" +
        "<style>.arch-pas{min-height:96px}.arch-pas .okl-t{padding-top:30px}" +
        ".arch-pas .strz{float:right;font-size:1.3em;line-height:.8}</style>";
      document.body.append(a);
    }
    const foot = document.createElement("footer");
    foot.className = "stopka";
    foot.innerHTML = `<span>Paralaksa · wersja wewnętrzna · nowy dzień codziennie około 19:00</span>` +
      `<a href="${new URL("../index.html", base).href}">Stara wersja</a>`;
    document.body.append(foot);
  });
})();
