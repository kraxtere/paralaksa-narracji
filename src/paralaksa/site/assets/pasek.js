/* Wspólny pasek i stopka wersji 2.0 (plx site zapisuje go jako v2/pasek.js, z logo w środku).
   Strona dnia ma tylko <div id="pasek" data-dzien="RRRR-MM-DD" [data-wstecz]> i ten skrypt zaraz za nim, więc zmiana
   paska to zmiana jednego pliku, bez przebudowy stron. Po lewej logo, po prawej wybór dnia (lista z v2/dni.json) albo,
   na stronach tematów i spraw, powrót do strony dnia. W stopce link do starej wersji. */
(() => {
  const LOGO = "__LOGO__";
  const box = document.getElementById("pasek");
  if (!box) return;
  const base = new URL(".", document.currentScript.src);          // .../v2/
  const day = box.dataset.dzien || "";
  const short = d => d.slice(8, 10) + "." + d.slice(5, 7);
  const full = d => short(d) + "." + d.slice(0, 4);
  const page = d => new URL(d + "/index.html", base).href;

  const style = document.createElement("style");
  style.textContent =
    ".bar2{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 16px;background:#1d1b18;" +
    "color:#f4f0e8;font:14px Segoe UI,sans-serif}.bar2 a{color:#f4f0e8;text-decoration:none}.bar2 .logo{line-height:0;flex:none}" +
    ".bar2 .logo svg{height:26px;width:auto}.bar2 .dni{display:flex;align-items:center;gap:6px;white-space:nowrap}" +
    ".bar2 .dni a{padding:4px 9px;border:1px solid #5a554c;border-radius:6px}.bar2 .dni a:hover{border-color:#bdb6a8}" +
    ".bar2 select{font:inherit;background:#2c2924;color:#f4f0e8;border:1px solid #5a554c;border-radius:6px;padding:4px 6px}" +
    ".bar2 .w{display:none}.stopka{max-width:720px;margin:28px auto 0;padding:14px 16px 72px;border-top:1px solid #ddd5c7;" +
    "display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px 16px;color:#7a746a;font:13px Segoe UI,sans-serif}" +
    ".stopka a{color:#8a3b2a}" +
    "@media(min-width:640px){.bar2{padding:14px max(20px,calc(50% - 360px))}.bar2 .logo svg{height:36px}.bar2 .w{display:inline}}";
  document.head.append(style);

  box.className = "bar2";
  box.innerHTML = `<a class="logo" href="${page(day)}" aria-label="Paralaksa, strona dnia">${LOGO}</a><span class="dni"></span>`;
  const right = box.querySelector(".dni");
  const link = (d, text, title) => {
    const a = document.createElement("a");
    a.href = page(d);
    a.innerHTML = text;
    a.title = title;
    return a;
  };

  if ("wstecz" in box.dataset) {
    right.append(link(day, `← <span class="w">strona dnia </span>${short(day)}`, "Wróć do strony dnia"));
  } else {
    right.textContent = full(day);
    fetch(new URL("dni.json", base), { cache: "no-store" }).then(r => r.json()).then(days => {
      const i = days.indexOf(day);
      const select = document.createElement("select");
      select.setAttribute("aria-label", "Dzień");
      for (const d of days) select.add(new Option(full(d), d, false, d === day));
      select.onchange = () => { location.href = page(select.value); };
      right.textContent = "";
      if (i >= 0 && i < days.length - 1) right.append(link(days[i + 1], `‹<span class="w"> ${short(days[i + 1])}</span>`, "Poprzedni dzień"));
      right.append(select);
      if (i > 0) right.append(link(days[i - 1], `<span class="w">${short(days[i - 1])} </span>›`, "Następny dzień"));
    }).catch(() => {});
  }

  // Kafelek „Dzień po dniu” (v2/os.json, gdy jest) zaraz pod okładką strony dnia, w stylu jej sekcji, niższy od nich:
  // oś ostatnich dni z okrągłymi kadrami na zakładkę; otwiera oś na tym dniu (#d=), a dzień spoza osi na jej końcu
  if (!("wstecz" in box.dataset)) {
    fetch(new URL("os.json", base), { cache: "no-store" }).then(r => r.ok ? r.json() : null).then(w => {
      if (!w || !w.dni || !w.dni.length) return;
      const dir = new URL("os/", base).href;
      const st = document.createElement("style");
      st.textContent =
        ".kafel-os{display:block;max-width:720px;margin:14px auto 0;box-sizing:border-box;background:#f4f0e8;border:2px solid #1d1b18;" +
        "border-radius:6px;overflow:hidden;text-decoration:none;color:#1d1b18;font:14px Segoe UI,sans-serif}" +
        ".kafel-os:hover{box-shadow:0 0 0 3px rgba(138,59,42,.25)}.kafel-os .gl{display:flex;align-items:center;justify-content:space-between}" +
        ".kafel-os .et{background:#8a3b2a;color:#fff;font:700 1.3em Georgia,serif;padding:4px 16px 4px 10px;" +
        "clip-path:polygon(0 0,100% 0,calc(100% - 10px) 100%,0 100%)}.kafel-os .gl i{font:700 1em Georgia,serif;font-style:normal;color:#8a3b2a;padding-right:10px}" +
        ".kafel-os .os{position:relative;display:flex;justify-content:space-between;padding:10px 10px 6px}" +
        ".kafel-os .os:before{content:'';position:absolute;left:10px;right:10px;height:3px;background:#1d1b18;top:58px}" +
        ".kafel-os .d{display:flex;flex-direction:column;align-items:center;flex:1}.kafel-os .d b{font:700 11px Georgia,serif;color:#5a554c;margin-top:4px}" +
        ".kafel-os .st{display:flex;height:42px}.kafel-os .st img{width:38px;height:38px;object-fit:cover;border:2px solid #f4f0e8;border-radius:50%;" +
        "margin-left:-22px;box-shadow:0 1px 3px rgba(0,0,0,.25)}.kafel-os .st img:first-child{margin-left:0}" +
        ".kafel-os .kr{width:9px;height:9px;border-radius:50%;background:#8a3b2a;border:2px solid #f4f0e8;margin-top:5px;z-index:1}" +
        "@media(min-width:640px){.kafel-os .st{height:62px}.kafel-os .st img{width:58px;height:58px;margin-left:-30px}.kafel-os .os:before{top:78px}" +
        ".kafel-os .d b{font-size:13px}}@media(max-width:740px){.kafel-os{margin:12px 6px 0}}";
      document.head.append(st);
      const a = document.createElement("a");
      a.className = "kafel-os";
      a.dataset.sekcja = "os";
      a.href = dir + "index.html" + (w.od <= day && day <= w.do ? "#d=" + day : "");
      const days = w.dni.map(x => `<span class="d"><span class="st">${x.obrazki.map(f => `<img src="${dir + f}" alt="" loading="lazy">`).join("")}` +
        `</span><span class="kr"></span><b>${short(x.d)}</b></span>`).join("");
      a.innerHTML = `<span class="gl"><span class="et">Dzień po dniu</span><i>Oś czasu ›</i></span><span class="os">${days}</span>`;
      const put = () => (document.querySelector('[data-sekcja="okladka"]') || box).after(a);
      document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", put) : put();
    }).catch(() => {});
  }

  document.addEventListener("DOMContentLoaded", () => {
    const foot = document.createElement("footer");
    foot.className = "stopka";
    foot.innerHTML = `<span>Paralaksa · wersja wewnętrzna · nowy dzień codziennie około 19:00</span>` +
      `<a href="${new URL("../index.html", base).href}">Stara wersja</a>`;
    document.body.append(foot);
  });
})();
