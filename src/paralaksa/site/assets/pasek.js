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

  // Wejście na oś tygodnia (v2/tydzien.json, gdy jest): pasek z miniaturami pod paskiem strony dnia; tydzień,
  // który obejmuje ten dzień, a gdy żaden: najnowszy
  if (!("wstecz" in box.dataset)) {
    fetch(new URL("tydzien.json", base), { cache: "no-store" }).then(r => r.ok ? r.json() : []).then(weeks => {
      const w = weeks.find(x => x.od <= day && day <= x.koniec) || weeks[0];
      if (!w) return;
      const dir = new URL("tydzien/" + w.koniec + "/", base).href;
      const st = document.createElement("style");
      st.textContent =
        ".tydz{display:flex;align-items:center;gap:12px;max-width:720px;margin:10px auto 0;padding:8px 12px;box-sizing:border-box;" +
        "background:#fbf8f2;border:1px solid #ddd5c7;border-radius:12px;text-decoration:none;color:#1d1b18;font:14px Segoe UI,sans-serif}" +
        ".tydz .mini{display:flex;flex:none}.tydz .mini img{width:44px;height:44px;border-radius:8px;object-fit:cover;" +
        "border:2px solid #fbf8f2;margin-left:-14px;background:#ebe4d6}.tydz .mini img:first-child{margin-left:0}" +
        ".tydz b{display:block;color:#8a3b2a}.tydz span{color:#7a746a;font-size:.9em}.tydz i{margin-left:auto;font-style:normal;" +
        "color:#8a3b2a;font-size:1.3em}@media(max-width:740px){.tydz{margin:10px 10px 0}}";
      document.head.append(st);
      const a = document.createElement("a");
      a.className = "tydz";
      a.href = dir + "index.html";
      a.innerHTML = `<span class="mini">${w.obrazki.slice(0, 4).map(f => `<img src="${dir + f}" alt="">`).join("")}</span>` +
        `<span><b>Tydzień w prasie · ${short(w.od)}–${short(w.koniec)}</b><span>Najważniejsze sprawy po kolei</span></span><i>›</i>`;
      box.after(a);
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
