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
  const KRAJE = "__KRAJE__";                                      // plx site: liczba krajów z aktywnych źródeł (config/sources.yaml) albo null
  const krajow = KRAJE ? KRAJE + " krajów" : "wielu krajów";
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
    // przycisk Udostępnij (ikona obok logo, od 17.10) i komunikat „Skopiowano”; powitanie (modal przy pierwszym wejściu)
    ".bar2 .udo{flex:none;width:34px;height:34px;border-radius:50%;border:1px solid #5a554c;background:#2c2924;color:#f4f0e8;display:flex;" +
    "align-items:center;justify-content:center;cursor:pointer;padding:0}.bar2 .udo:hover,.bar2 .udo:focus-visible{border-color:#f4f0e8;outline:2px solid #8a3b2a}" +
    "@media(pointer:coarse){.bar2 .udo{width:40px;height:40px}}" +
    ".udo-info{position:fixed;top:60px;right:16px;z-index:60;background:#1d1b18;color:#f4f0e8;padding:8px 14px;border-radius:8px;" +
    "font:14px Segoe UI,sans-serif;box-shadow:0 4px 14px rgba(0,0,0,.3)}" +
    ".pow-tlo{position:fixed;inset:0;z-index:100;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;padding:16px}" +
    ".pow{background:#f4f0e8;color:#1d1b18;max-width:440px;width:100%;max-height:calc(100vh - 32px);overflow:auto;border:2px solid #1d1b18;" +
    "border-radius:14px;padding:20px;font:15px/1.45 Segoe UI,sans-serif;box-sizing:border-box}" +
    ".pow h2{margin:0 0 10px;font:700 21px Georgia,serif}.pow p{margin:0 0 10px}.pow ul{margin:0 0 12px;padding-left:20px}.pow li{margin-bottom:4px}" +
    ".pow label{display:flex;align-items:center;gap:8px;margin:12px 0;font-size:14px;color:#3d3a34;cursor:pointer}" +
    ".pow input{width:18px;height:18px;flex:none}.pow .ok{display:block;width:100%;min-height:46px;border:0;border-radius:10px;background:#1d1b18;" +
    "color:#f4f0e8;font:700 16px Segoe UI,sans-serif;cursor:pointer}.pow .ok:focus-visible,.pow input:focus-visible{outline:2px solid #8a3b2a;outline-offset:2px}" +
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
  // Udostępnij: na stronie dnia cała Paralaksa (adres główny, który otwiera najnowszy dzień), na podstronach ta strona. Telefon i tablet (dotyk): systemowe okno
  // udostępniania (w aplikacji z ekranu głównego to samo co w innych aplikacjach: WhatsApp, SMS…); komputer albo brak
  // navigator.share: kopiowanie linku do schowka z komunikatem „Skopiowano” (bez schowka: okno z linkiem do skopiowania ręcznie).
  const rootUrl = new URL("../", base).href;
  const opis = `Paralaksa narracji: jak prasa z ${krajow} opisuje to samo wydarzenie. Codzienny przegląd w obrazkach.`;
  const udo = document.createElement("button");
  udo.type = "button";
  udo.className = "udo";
  udo.title = "Udostępnij Paralaksę";
  udo.setAttribute("aria-label", "Udostępnij Paralaksę");
  udo.innerHTML = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="currentColor"><path d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92s2.92-1.31 2.92-2.92-1.31-2.92-2.92-2.92z"/></svg>';
  right.append(udo);
  let infoTimer = 0;
  const info = text => {
    let el = document.querySelector(".udo-info");
    if (!el) { el = document.createElement("div"); el.className = "udo-info"; el.setAttribute("role", "status"); document.body.append(el); }
    el.textContent = text;
    clearTimeout(infoTimer);
    infoTimer = setTimeout(() => el.remove(), 2200);
  };
  const udostepnij = async (url, title, text) => {
    if (navigator.share && matchMedia("(pointer:coarse)").matches) {
      try { await navigator.share({ title, text, url }); return; }
      catch (e) { if (e && e.name === "AbortError") return; }          // anulowane przez osobę: bez kopiowania
    }
    try { await navigator.clipboard.writeText(url); info("Skopiowano"); }
    catch (e) { window.prompt("Skopiuj link:", url); }
  };
  // Pasek: strona dnia = cała Paralaksa (adres główny); podstrona (temat, sprawa, kraj, oś) = ta strona, z hashem (wybrany kraj,
  // dzień i wątek osi). Przy artykule (przycisk w karcie, niżej) link prowadzi do tego miejsca u nas, nigdy do oryginału.
  const podstrona = "wstecz" in box.dataset;
  const tuUrl = () => { const u = new URL(location.href); u.searchParams.delete("a"); u.searchParams.delete("t"); return u.href; };
  if (podstrona) { udo.title = "Udostępnij tę stronę"; udo.setAttribute("aria-label", "Udostępnij tę stronę"); }
  udo.onclick = () => podstrona
    ? udostepnij(tuUrl(), document.title, `${document.title} · Paralaksa narracji`)
    : udostepnij(rootUrl, "Paralaksa narracji", opis);

  // Powitanie i przewodnik (od 17.10). Modal „Czym jest Paralaksa” pokazuje się raz (flaga plx-przewodnik-v1 w localStorage:
  // pokazane / ukonczony / pominiety; dawna flaga plx-powitanie też wyłącza zaproszenie) i proponuje przewodnik po stronie dnia:
  // kilka kroków ze światłem na elemencie i panelem z objaśnieniem. Stały link „O Paralaksie” (stopka, menu osoby) otwiera
  // ten sam modal. Kroki z brakującym elementem są pomijane; nazwy sekcji jak na stronie. Teksty: docs/PRZEWODNIK_BURZA_MOZGOW.md.
  const memo = (st, k, v) => { try { return v === undefined ? window[st].getItem(k) : window[st].setItem(k, v); } catch (e) { return null; } };
  const PKEY = "plx-przewodnik-v1";
  const pst = document.createElement("style");
  pst.textContent =
    ".pow .dr{display:block;width:100%;min-height:44px;margin-top:8px;border:2px solid #1d1b18;border-radius:10px;background:#f4f0e8;color:#1d1b18;" +
    "font:600 15px Segoe UI,sans-serif;cursor:pointer}.pow .dr:focus-visible{outline:2px solid #8a3b2a;outline-offset:2px}" +
    ".pow .mala{margin:0 0 10px;color:#5a554c;font-size:13px}" +
    ".pz-tlo{position:fixed;inset:0;z-index:90}.pz-sp{position:absolute;z-index:91;border-radius:10px;pointer-events:none;" +
    "box-shadow:0 0 0 9999px rgba(20,18,15,.62);outline:3px solid #f4f0e8;transition:top .25s,left .25s,width .25s,height .25s}" +
    ".pz-pan{position:fixed;z-index:95;left:50%;transform:translateX(-50%);bottom:calc(86px + env(safe-area-inset-bottom));" +
    "width:min(440px,calc(100vw - 24px));box-sizing:border-box;background:#f4f0e8;color:#1d1b18;border:2px solid #1d1b18;" +
    "border-radius:14px;padding:14px 16px;font:15px/1.45 Segoe UI,sans-serif;box-shadow:0 6px 24px rgba(0,0,0,.35)}" +
    ".pz-pan .nr{margin:0 0 2px;color:#8a3b2a;font:700 12px Segoe UI,sans-serif;letter-spacing:.06em;text-transform:uppercase}" +
    ".pz-pan h3{margin:0 0 6px;font:700 19px Georgia,serif}.pz-pan p{margin:0 0 12px}" +
    ".pz-pan .rz{display:flex;gap:8px;align-items:center}.pz-pan button{min-height:44px;padding:0 14px;border-radius:10px;" +
    "border:2px solid #1d1b18;background:#f4f0e8;color:#1d1b18;font:600 15px Segoe UI,sans-serif;cursor:pointer}" +
    ".pz-pan .dalej{flex:1;background:#1d1b18;color:#f4f0e8;font-weight:700}.pz-pan .pomin{margin-left:auto;border-color:transparent;text-decoration:underline}" +
    ".pz-pan button:focus-visible{outline:2px solid #8a3b2a;outline-offset:2px}" +
    "@media(min-width:640px){.pz-pan{bottom:24px}}" +
    "@media(prefers-reduced-motion:reduce){.pz-sp{transition:none}}";
  document.head.append(pst);

  const przewodnik = (() => {
    const sek = name => {
      const h = [...document.querySelectorAll("h2.pp-sek")].find(x => x.textContent.trim() === name);
      return h && h.nextElementSibling ? [h, h.nextElementSibling] : [];
    };
    const STEPS = [
      { t: "Sprawy mają ciąg dalszy", x: "Oś łączy najważniejsze sprawy z kolejnych dni i pozwala wrócić do wcześniejszych opisów. Data to dzień przeglądu prasy, niekoniecznie dzień zdarzenia.",
        el: () => [document.querySelector(".kafel-os")] },
      { t: "O czym pisano najwięcej", x: "Tu zaczynasz: sprawy, które tego dnia opisały redakcje z wielu krajów. Otwórz kartę, żeby zobaczyć, jak każda z nich ją przedstawia.",
        el: () => sek("Tego dnia") },
      { t: "Inne akcenty", x: "Dwa opisy tego samego tematu obok siebie. Zwróć uwagę, co redakcje podkreślają i jak przedstawiają sprawę. Różnica nie musi oznaczać sprzeczności.",
        el: () => sek("Tonacje") },
      { t: "O sobie i z zewnątrz", x: "Jak wybrane redakcje opisują własny kraj, a jak przedstawiają go redakcje zagraniczne. To obraz medialny, nie poglądy wszystkich mieszkańców.",
        el: () => sek("Autoportret") },
      { t: "Co zajmuje prasę kraju", x: "Tematy prasy jednego kraju, które nie weszły do wielokrajowych spraw dnia. To nie dowód, że inne media o nich milczą.",
        el: () => sek("Czym żyją kraje") },
      { t: "Szukaj samodzielnie", x: "Artykuły ze wszystkich zebranych dni. Zawężaj wyniki według kraju, źródła, tematu i tonu.",
        el: () => sek("Archiwum") },
    ];
    const rectOf = els => {
      let t = 1e9, l = 1e9, b = 0, r = 0;
      els.forEach(e => { const q = e.getBoundingClientRect(); t = Math.min(t, q.top); l = Math.min(l, q.left); b = Math.max(b, q.bottom); r = Math.max(r, q.right); });
      return { t: t + scrollY, l: l + scrollX, w: r - l, h: b - t };
    };
    const calm = matchMedia("(prefers-reduced-motion:reduce)").matches;
    let live = false;
    const start = () => {
      if (live) return;
      const steps = STEPS.map(s => ({ ...s, els: s.el().filter(e => e && e.offsetParent !== null) })).filter(s => s.els.length);
      if (!steps.length) return;
      live = true;
      const before = document.activeElement;
      const catcher = document.createElement("div"); catcher.className = "pz-tlo";
      const spot = document.createElement("div"); spot.className = "pz-sp";
      const pan = document.createElement("div");
      pan.className = "pz-pan"; pan.setAttribute("role", "dialog"); pan.setAttribute("aria-labelledby", "pz-h"); pan.setAttribute("aria-live", "polite");
      document.body.append(catcher, spot, pan);
      let i = 0, final = false;
      const fit = () => {
        const s = steps[i];
        if (final || !s) return;
        const r = rectOf(s.els), pad = 6;
        spot.style.cssText = `top:${r.t - pad}px;left:${Math.max(4, r.l - pad)}px;width:${r.w + 2 * pad}px;height:${r.h + 2 * pad}px`;
      };
      const finish = flag => {
        memo("localStorage", PKEY, flag);
        catcher.remove(); spot.remove(); pan.remove(); live = false;
        document.removeEventListener("keydown", keys, true); removeEventListener("resize", fit);
        if (before && before.focus) before.focus();
      };
      const render = () => {
        const s = steps[i];
        if (final) {
          spot.style.display = "none";
          const first = document.querySelector("h2.pp-sek + .pp-k a[href]");
          pan.innerHTML = `<h3 id="pz-h">Wybierz sprawę</h3><p>Zacznij od interesującej Cię karty. Do przewodnika wrócisz przez „O Paralaksie” na dole strony.</p>` +
            `<div class="rz">${first ? '<button type="button" class="dalej otw">Otwórz pierwszą sprawę</button>' : ""}<button type="button" class="zostan">Zostań na okładce</button></div>`;
          pan.querySelector(".zostan").onclick = () => finish("ukonczony");
          const o = pan.querySelector(".otw"); if (o) o.onclick = () => { finish("ukonczony"); location.href = first.href; };
          (o || pan.querySelector(".zostan")).focus();
          return;
        }
        spot.style.display = "";
        pan.innerHTML = `<p class="nr">${i + 1} z ${steps.length}</p><h3 id="pz-h">${s.t}</h3><p>${s.x}</p>` +
          `<div class="rz"><button type="button" class="wstecz"${i ? "" : " hidden"}>Wstecz</button>` +
          `<button type="button" class="dalej">${i === steps.length - 1 ? "Koniec" : "Dalej"}</button>` +
          `<button type="button" class="pomin">Pomiń</button></div>`;
        pan.querySelector(".wstecz").onclick = () => { i--; render(); };
        pan.querySelector(".dalej").onclick = () => { if (i === steps.length - 1) { final = true; } else { i++; } render(); };
        pan.querySelector(".pomin").onclick = () => finish("pominiety");
        pan.querySelector(".dalej").focus({ preventScroll: true });
        const r = rectOf(s.els), room = innerHeight - pan.offsetHeight - (innerWidth < 640 ? 100 : 40);
        const top = Math.max(12, Math.min(72, (room - r.h) / 2));
        scrollTo({ top: Math.max(0, r.t - top), behavior: calm ? "auto" : "smooth" });
        fit(); setTimeout(fit, 500);
      };
      const keys = e => {
        if (e.key === "Escape") { e.preventDefault(); finish("pominiety"); return; }
        if (e.key !== "Tab") return;
        const f = [...pan.querySelectorAll("button:not([hidden])")];
        const k = f.indexOf(document.activeElement);
        if (e.shiftKey && k <= 0) { e.preventDefault(); f[f.length - 1].focus(); }
        else if (!e.shiftKey && k === f.length - 1) { e.preventDefault(); f[0].focus(); }
      };
      document.addEventListener("keydown", keys, true);
      addEventListener("resize", fit);
      render();
    };
    return start;
  })();

  const powitanie = (() => {
    const SES = "plx-powitanie-sesja";
    const podstronaPow = "wstecz" in box.dataset;
    const open = () => {
      if (document.getElementById("plx-powitanie")) return;
      const back = document.createElement("div");
      back.id = "plx-powitanie";
      back.className = "pow-tlo";
      back.innerHTML = `<div class="pow" role="dialog" aria-modal="true" aria-labelledby="pow-h"><h2 id="pow-h">Czym jest Paralaksa narracji?</h2>` +
        `<p>Codziennie zestawiamy, jak wybrane redakcje z ${krajow} opisują te same sprawy. Pokazujemy podobieństwa i różnice w przekazie, ` +
        `jego ciąg dalszy oraz tematy prasy poszczególnych krajów.</p>` +
        `<p>Opisujemy <b>przekaz medialny, nie fakty</b>: nie rozstrzygamy, co jest prawdą. To przegląd wybranych redakcji, nie wszystkich mediów ani opinii mieszkańców krajów. ` +
        `Brak tematu w zestawieniu nie oznacza, że nikt o nim nie pisał.</p>` +
        `<p class="mala">Na stronie: Dzień po dniu · Tego dnia · Tonacje · Autoportret · Czym żyją kraje · Czym żyła prasa · Archiwum. ` +
        `Nazwa: paralaksa to zmiana widoku zależnie od miejsca, z którego patrzymy.</p>` +
        `<button type="button" class="ok">Pokaż mi stronę</button><button type="button" class="dr">Przeglądam samodzielnie</button></div>`;
      const before = document.activeElement;
      const keys = e => {
        if (e.key === "Escape") { e.preventDefault(); close(); return; }
        if (e.key !== "Tab") return;
        const f = [...back.querySelectorAll("button")];
        const i = f.indexOf(document.activeElement);
        if (e.shiftKey && i <= 0) { e.preventDefault(); f[f.length - 1].focus(); }
        else if (!e.shiftKey && i === f.length - 1) { e.preventDefault(); f[0].focus(); }
      };
      const close = () => {
        back.remove();
        document.removeEventListener("keydown", keys, true);
        if (before && before.focus) before.focus();
      };
      back.querySelector(".ok").onclick = () => {
        close();
        if (podstronaPow) location.href = page(day) + "?przewodnik=1";      // przewodnik jest na stronie dnia
        else przewodnik();
      };
      back.querySelector(".dr").onclick = close;
      back.addEventListener("click", e => { if (e.target === back) close(); });
      document.addEventListener("keydown", keys, true);
      document.body.append(back);
      back.querySelector(".ok").focus();
    };
    const auto = () => {
      if (window.top !== window) return;
      const q = new URLSearchParams(location.search);
      if (q.get("przewodnik") && !podstronaPow) {                          // wejście z „Pokaż mi stronę” na podstronie
        q.delete("przewodnik");
        history.replaceState(null, "", location.pathname + (q.toString() ? "?" + q : "") + location.hash);
        setTimeout(przewodnik, 900);
        return;
      }
      if (memo("localStorage", PKEY) || memo("localStorage", "plx-powitanie") || memo("sessionStorage", SES)) return;
      memo("sessionStorage", SES, "1");
      memo("localStorage", PKEY, "pokazane");
      open();
    };
    document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", auto) : auto();
    return open;
  })();
  const oParalaksie = el => el.addEventListener("click", e => { e.preventDefault(); powitanie(); });

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
  // Udostępnianie tematu (od 17.10): sama ikona (bez napisu), bez dokładania pustych rzędów. Karta tematu z oryginalnymi artykułami
  // (h3 przed listą .arts): ikona po prawej w rzędzie „Artykuły (N)”, nad artykułami; karta zdarzenia na osi czasu: po prawej, w linii
  // przycisku „Czytaj”; strona tematu, sprawy, autoportretu: po prawej na końcu opisu (akapit .s). Link = ta strona + ?t=<id pierwszego
  // artykułu karty> (+ hash widoku, np. kraj), nigdy oryginał. Wejście z ?t= przewija do karty i na chwilę ją zaznacza.
  document.addEventListener("DOMContentLoaded", () => {
    const holderOf = arts => {
      const ev = arts.closest("article.ev");
      if (ev) return { box: ev, head: ev.querySelector(".tresc h2") };
      let el = arts.previousElementSibling;
      while (el && !/^H[23]$/.test(el.tagName)) el = el.previousElementSibling;
      return el && el.tagName === "H3" ? { box: el, head: el } : null;
    };
    const ikona = '<svg viewBox="0 0 24 24" width="17" height="17" aria-hidden="true" fill="currentColor"><path d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92s2.92-1.31 2.92-2.92-1.31-2.92-2.92-2.92z"/></svg>';
    const przycisk = (aria, onclick) => {
      const b = document.createElement("button");
      b.type = "button"; b.className = "tem-udo"; b.title = "Udostępnij temat"; b.setAttribute("aria-label", aria);
      b.innerHTML = ikona;
      b.onclick = e => { e.preventDefault(); e.stopPropagation(); onclick(); };
      return b;
    };
    let kart = 0;
    document.querySelectorAll(".arts").forEach(arts => {
      const first = arts.querySelector("a[data-a]");
      const h = first && holderOf(arts);
      if (!h || !h.head || h.box.dataset.udo) return;
      h.box.dataset.udo = "1"; kart++;
      const tytul = () => [...h.head.childNodes].map(n => n.textContent).join("").trim();
      const w = przycisk("Udostępnij temat: " + tytul(), () => {
        const u = new URL(location.href);
        u.searchParams.delete("a");
        u.searchParams.set("t", first.dataset.a);
        udostepnij(u.href, tytul(), `Paralaksa narracji: ${tytul()}`);
      });
      if (h.box.tagName === "ARTICLE") h.head.after(w);
      else (arts.querySelector(".arts-l") || arts).append(w);
    });
    if (!kart && podstrona && document.querySelector(".arts")) {         // cała strona jest tematem: ikona na końcu opisu
      const w = przycisk("Udostępnij ten temat", () => udostepnij(tuUrl(), document.title, `${document.title} · Paralaksa narracji`));
      const note = document.querySelector("p.s");
      note ? note.prepend(w) : box.after(w);
    }
    const id = new URL(location.href).searchParams.get("t");
    const a = id && document.querySelector(`.arts a[data-a="${CSS.escape(id)}"]`);
    const h = a && holderOf(a.closest(".arts"));
    if (!h) return;
    const det = h.box.closest("details"); if (det) det.open = true;
    const sec = h.box.closest("section.zwin"); if (sec) sec.classList.remove("zwin");
    setTimeout(() => {
      if (!h.box.offsetParent) return;                                 // karta w ukrytym widoku (inny kraj): bez przewijania
      h.box.scrollIntoView({ block: "center", inline: "center" });
      h.box.classList.add("wsk");
      setTimeout(() => h.box.classList.remove("wsk"), 4500);
    }, 350);
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
    ".tem-udo{display:inline-flex;align-items:center;justify-content:center;flex:none;width:34px;height:34px;padding:0;" +
    "border:1px solid var(--art-linia);border-radius:50%;background:var(--art-tlo);color:var(--art-akcent);cursor:pointer}" +
    ".tem-udo:hover,.tem-udo:focus-visible{border-color:var(--art-akcent);background:var(--art-tlo-hover)}" +
    ".tem-udo:focus-visible{outline:2px solid var(--art-focus);outline-offset:1px}@media(pointer:coarse){.tem-udo{width:40px;height:40px}}" +
    ".arts-l{display:flex;align-items:center;justify-content:space-between}.arts-l .tem-udo{margin:-10px 0 -10px 8px}" +
    ".tresc .tem-udo{float:right;margin:2px 0 0 8px}p.s>.tem-udo{float:right;margin:-4px 0 0 10px}" +
    ".wsk{outline:3px solid var(--art-akcent);outline-offset:4px;border-radius:8px}" +
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
        (ja.wlasciciel ? `<a href="/osoby">Osoby</a>` : "<span></span>") + `<a href="/wyloguj">Wyloguj</a></div>` +
        `<p class="s"><a href="#o-paralaksie" class="o-par">O Paralaksie</a></p>`;
      oParalaksie(menu.querySelector(".o-par"));
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
        "<style>.arch-pas{min-height:96px;background:linear-gradient(120deg,var(--tusz) 55%,var(--cegla))}.arch-pas .okl-t{padding-top:30px}" +
        ".arch-pas .strz{float:right;font-size:1.3em;line-height:.8}</style>";
      document.body.append(a);
    }
    const foot = document.createElement("footer");
    foot.className = "stopka";
    foot.innerHTML = `<span>Paralaksa · wersja wewnętrzna · nowy dzień codziennie około 19:00</span>` +
      `<a href="#o-paralaksie" class="o-par">O Paralaksie</a><a href="${new URL("../index.html", base).href}">Stara wersja</a>`;
    oParalaksie(foot.querySelector(".o-par"));
    document.body.append(foot);
  });
})();
