/* Archiwum 2.0: wyszukiwarka wszystkich artykułów (plx site → v2/archiwum/index.html, src/paralaksa/site/archive.py).
   Spis dni w stronie (#spis); paczka dnia D.json.gz (D.json, gdy przeglądarka nie ma DecompressionStream) pobierana tylko
   dla dni wybranego okresu i trzymana w pamięci. Wiersz paczki: [źródło, tytuł, nagłówek PL, link,
   [[temat, ton, aktor, rama, streszczenie], ...]]. Stan filtrów w adresie (#q=…), odświeżenie strony go nie gubi. */
(() => {
  const SPIS = JSON.parse(document.getElementById("spis").textContent);
  const app = document.getElementById("arch");
  const DAYS = SPIS.dni.map(x => x.d);                        // od najnowszego
  const LAST = DAYS[0] || "";
  const STANCES = ["alarm", "krytyka", "neutralny", "uspokojenie", "poparcie"];
  const PAGE = 40;                                            // wyników naraz; „pokaż więcej” dodaje tyle samo
  const ROWS = 6;                                             // krajów na wykresie, reszta po kliknięciu
  const GZ = "DecompressionStream" in window;
  const DEFAULT = { okres: "7", od: "", do: "", q: "", kraj: "", src: "", th: "", st: "", ak: "", widok: "lista" };

  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const short = d => d.slice(8, 10) + "." + d.slice(5, 7);
  const shift = (d, n) => new Date(Date.parse(d + "T00:00:00Z") + n * 864e5).toISOString().slice(0, 10);
  const norm = s => String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/ł/g, "l");
  const plural = n => n === 1 ? "artykuł" : n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 12 || n % 100 > 14) ? "artykuły" : "artykułów";
  const num = n => n.toLocaleString("pl-PL");
  let regions = null;
  try { regions = new Intl.DisplayNames(["pl"], { type: "region" }); } catch (e) { /* stara przeglądarka: same kody */ }
  const countryName = c => SPIS.kraje[c] || c;
  const actorName = a => {                                    // aktor to kod kraju albo nazwa organizacji/regionu
    if (SPIS.kraje[a]) return SPIS.kraje[a];
    if (regions && /^[A-Z]{2}$/.test(a)) { try { const n = regions.of(a); if (n && n !== a) return n; } catch (e) { /* kod spoza listy */ } }
    return a;
  };
  const srcName = s => (SPIS.zrodla[s] || [s])[0];

  const f = { ...DEFAULT };
  const hash = new URLSearchParams(location.hash.slice(1));
  for (const k in DEFAULT) if (hash.has(k)) f[k] = hash.get(k);
  if (!["1", "7", "30", "all", "zakres"].includes(f.okres)) f.okres = "7";
  const save = () => {
    const p = new URLSearchParams();
    for (const k in DEFAULT) if (f[k] !== DEFAULT[k] && (f.okres === "zakres" || (k !== "od" && k !== "do"))) p.set(k, f[k]);
    history.replaceState(null, "", location.pathname + location.search + (String(p) ? "#" + p : ""));
  };

  const style = document.createElement("style");
  style.textContent =
    ":root{--papier:#f4f0e8;--tusz:#1d1b18;--cegla:#8a3b2a;--szary:#7a746a;--karta:#fbf8f2;--linia:#ddd5c7;--zaznacz:#f1d9a8}" +
    "body{margin:0;background:var(--papier);color:var(--tusz);font-family:Segoe UI,sans-serif}" +
    ".arch{max-width:720px;margin:auto;padding:6px 14px 40px;box-sizing:border-box}" +
    ".arch h1{margin:12px 0 2px;color:var(--cegla);font:700 1.6em Georgia,serif}.arch .lead{margin:0 0 10px;color:var(--szary);font-size:.88em}" +
    ".q{width:100%;box-sizing:border-box;padding:11px 14px;border:2px solid var(--tusz);border-radius:10px;background:var(--karta);" +
    "color:var(--tusz);font:16px Segoe UI,sans-serif}.q:focus-visible{outline:3px solid var(--cegla);outline-offset:1px}" +
    ".chipy{display:flex;gap:6px;overflow-x:auto;margin:8px 0;padding-bottom:2px;scrollbar-width:thin}" +
    ".chipy button{flex:none;padding:7px 12px;border:2px solid var(--tusz);border-radius:999px;background:var(--karta);color:var(--tusz);" +
    "font:600 14px Segoe UI,sans-serif;cursor:pointer}.chipy button[aria-pressed=true]{background:var(--tusz);color:var(--papier)}" +
    ".chipy button:focus-visible,.arch select:focus-visible,.arch input[type=date]:focus-visible,.wiecej:focus-visible,.wk button:focus-visible," +
    ".kol h3 button:focus-visible{outline:3px solid var(--cegla);outline-offset:1px}" +
    ".zakres{display:flex;flex-wrap:wrap;gap:8px 12px;margin:0 0 8px;font-size:.88em;color:var(--szary)}.zakres[hidden]{display:none}" +
    ".zakres input{margin-left:4px;padding:6px 8px;border:2px solid var(--linia);border-radius:8px;background:var(--karta);color:var(--tusz);font:15px Segoe UI,sans-serif}" +
    ".filtry{margin:8px 0;border:2px solid var(--linia);border-radius:10px;background:var(--karta)}" +
    ".filtry summary{display:flex;align-items:center;gap:8px;padding:10px 12px;cursor:pointer;list-style:none;font-weight:700}" +
    ".filtry summary::-webkit-details-marker{display:none}.filtry summary:after{content:'▾';margin-left:auto}.filtry[open] summary:after{content:'▴'}" +
    ".filtry summary small{overflow:hidden;white-space:nowrap;text-overflow:ellipsis;color:var(--cegla);font-weight:600}" +
    ".pola{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:0 12px 12px}.pola .cala{grid-column:1/-1}" +
    ".pola label{display:flex;flex-direction:column;gap:3px;min-width:0;color:var(--szary);font-size:.8em}" +
    ".pola select{min-width:0;padding:7px 6px;border:2px solid var(--linia);border-radius:8px;background:var(--papier);color:var(--tusz);font:15px Segoe UI,sans-serif}" +
    ".czysc{align-self:end;padding:9px 12px;border:2px solid var(--tusz);border-radius:8px;background:var(--papier);color:var(--tusz);font:600 14px Segoe UI,sans-serif;cursor:pointer}" +
    ".wiersz{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:4px 10px;margin:10px 0 6px}" +
    ".info{margin:0 2px;color:var(--szary);font-size:.9em}.info b{color:var(--tusz)}" +
    // wykres: kraje × dni, jeden odcień (cegła) od jasnego do ciemnego; nad nim słupki „razem”, liczby w kratkach przy ≤ 10 dniach
    ".wykres{margin:4px 0 10px;padding:8px 10px 6px;border:1px solid var(--linia);border-radius:10px;background:var(--karta)}" +
    ".wykres[hidden]{display:none}.wk-t{margin:0 0 6px;color:var(--szary);font-size:.75em}" +
    ".wk{display:grid;gap:2px;align-items:center;font-size:11px}.wk .n{color:var(--szary);font-size:10px}" +
    ".wk .s{color:var(--szary);font-size:10px;text-align:right}.wk .bc{display:flex;align-items:flex-end;height:24px}" +
    ".wk .bc i{display:block;width:100%;min-height:1px;background:var(--tusz);border-radius:3px 3px 0 0}" +
    ".wk button{all:unset;cursor:pointer;font-weight:700;color:var(--tusz);padding:1px 0}.wk button[aria-pressed=true]{color:var(--cegla);text-decoration:underline}" +
    ".wk .c{position:relative;height:17px;border-radius:2px;background:var(--papier);color:var(--tusz);font-size:10px;line-height:17px;text-align:center;overflow:hidden}" +
    ".wk .c:before{content:'';position:absolute;inset:0;background:var(--cegla);opacity:var(--o,0)}.wk .c span{position:relative}.wk .c.dk{color:var(--papier)}" +
    ".wk .x{overflow:visible;white-space:nowrap;color:var(--szary);font-size:10px}.wk .rest{grid-column:1/-1;justify-self:start;font-weight:600;color:var(--cegla);font-size:12px;padding:4px 0}" +
    ".chipy.widoki{margin:0;gap:4px}.widoki button{padding:5px 10px;font-size:13px}" +
    ".wyniki ol{margin:0;padding:0;list-style:none}.wyniki li{padding:10px 2px;border-bottom:1px solid var(--linia)}" +
    ".wyniki li>a{color:var(--tusz);font-weight:600;line-height:1.35;text-decoration:none}.wyniki li>a:hover{text-decoration:underline}" +
    ".org{display:block;margin-top:2px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;color:var(--szary);font-size:.82em}" +
    ".meta{display:block;margin-top:3px;color:var(--szary);font-size:.8em}.meta b{color:var(--cegla)}" +
    ".snip{display:block;margin-top:4px;padding-left:8px;border-left:3px solid var(--linia);font-size:.84em;font-style:italic}" +
    "mark{background:var(--zaznacz);color:inherit;border-radius:2px}" +
    ".wiecej{display:block;width:100%;margin:12px 0;padding:11px;border:2px solid var(--tusz);border-radius:10px;background:var(--karta);" +
    "color:var(--tusz);font:700 15px Segoe UI,sans-serif;cursor:pointer}" +
    ".kols{display:grid;grid-template-columns:minmax(0,1fr);gap:10px}@media(min-width:640px){.kols{grid-template-columns:repeat(2,minmax(0,1fr))}}" +
    ".kol{padding:6px 12px;border:1px solid var(--linia);border-radius:12px;background:var(--karta)}" +
    ".kol h3{margin:4px 0 0;font:700 1.05em Georgia,serif}.kol h3 button{all:unset;cursor:pointer;color:var(--cegla)}" +
    ".kol h3 small{color:var(--szary);font:400 .75em Segoe UI,sans-serif}.kol li:last-child{border-bottom:0}.kol .wiecej{margin:4px 0 8px;padding:8px}" +
    ".pusto{margin:18px 2px;color:var(--szary)}";
  document.head.append(style);

  const lastToday = LAST === new Date().toLocaleDateString("sv");           // „sv” daje RRRR-MM-DD w czasie lokalnym
  const PERIODS = [["1", lastToday ? "dziś" : "ostatni dzień"], ["7", "7 dni"], ["30", "30 dni"], ["all", "wszystko"], ["zakres", "zakres…"]];
  const first = DAYS[DAYS.length - 1] || "";
  app.innerHTML = `<h1>Archiwum prasy</h1>
    <p class="lead">${DAYS.length ? `${num(DAYS.length)} dni (${short(first)}–${short(LAST)}): nagłówki polskie i oryginalne, ramy i streszczenia sygnałów, bez pełnych tekstów.` : "Archiwum jest puste."}</p>
    <input class="q" type="search" placeholder="Szukaj, np. Grenlandia" aria-label="Szukaj w nagłówkach, ramach i streszczeniach" autocomplete="off">
    <div class="chipy okresy" role="group" aria-label="Okres">${PERIODS.map(([v, l]) => `<button type="button" data-okres="${v}">${l}</button>`).join("")}</div>
    <div class="zakres" hidden><label>od<input type="date" data-z="od" min="${first}" max="${LAST}"></label><label>do<input type="date" data-z="do" min="${first}" max="${LAST}"></label></div>
    <details class="filtry"><summary>Filtry <small></small></summary><div class="pola">
      <label>Kraj<select data-f="kraj"></select></label><label>Źródło<select data-f="src"></select></label>
      <label>Temat<select data-f="th"></select></label><label>Ton<select data-f="st"></select></label>
      <label class="cala">Aktor (kraj, organizacja)<select data-f="ak"></select></label><button type="button" class="czysc cala">Wyczyść filtry i szukanie</button>
    </div></details>
    <div class="wiersz"><div class="info" aria-live="polite"></div><div class="chipy widoki" role="group" aria-label="Widok">` +
    `<button type="button" data-widok="lista">Lista</button><button type="button" data-widok="kraje">Po krajach</button></div></div><div class="wykres" hidden></div>
    <div class="wyniki"></div>`;
  const $ = sel => app.querySelector(sel);
  const q = $(".q"), info = $(".info"), chart = $(".wykres"), out = $(".wyniki");
  q.value = f.q;
  if (window.plxKolko) app.querySelectorAll(".chipy").forEach(window.plxKolko);

  // --- dane ---------------------------------------------------------------------------------------------------------
  const packs = {};
  const load = d => packs[d] || (packs[d] = fetch(`${d}.json${GZ ? ".gz" : ""}`).then(r => {
    if (!r.ok) throw new Error(`${d}: ${r.status}`);
    return GZ ? new Response(r.body.pipeThrough(new DecompressionStream("gzip"))).json() : r.json();
  }).then(rows => rows.map(([src, t, pl, u, s]) => ({ d, src, k: (SPIS.zrodla[src] || [])[1] || "", t, pl, u, s })))
    .catch(e => { delete packs[d]; throw e; }));

  const period = () => {
    if (f.okres === "all" || !LAST) return DAYS;
    let [from, to] = f.okres === "zakres" ? [f.od || shift(LAST, -6), f.do || LAST] : [shift(LAST, 1 - Number(f.okres)), LAST];
    if (from > to) [from, to] = [to, from];
    return DAYS.filter(d => d >= from && d <= to);
  };

  let arts = [], days = [], failed = [], token = 0, shown = PAGE, allRows = false;
  async function refresh() {
    const my = ++token;
    days = period();
    let done = 0;
    const todo = days.filter(d => !packs[d]).length;
    if (todo) info.textContent = `Wczytuję ${todo} ${todo === 1 ? "dzień" : "dni"}…`;
    const lists = await Promise.all(days.map(d => load(d).then(x => {
      if (my === token && todo) info.textContent = `Wczytuję dni: ${++done}/${days.length}…`;
      return x;
    }, () => null)));
    if (my !== token) return;
    failed = days.filter((d, i) => !lists[i]);
    arts = lists.filter(Boolean).flat();
    options();
    results();
  }

  // --- filtry -------------------------------------------------------------------------------------------------------
  // hasło od 5 liter bez 1–2 końcowych samogłosek łapie odmiany (grenlandia → grenland: Grenlandii, Grenlandią);
  // hasło do 3 liter tylko jako całe słowo (UE, PiS nie trafiają w „opis”)
  const terms = () => norm(f.q).split(/\s+/).filter(Boolean).map(w => w.length <= 3
    ? { w, re: new RegExp(`(^|[^\\p{L}\\p{N}])${w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(?![\\p{L}\\p{N}])`, "gu") }
    : { w: w.length >= 5 ? w.replace(/[aeiouy]{1,2}$/, "") : w });
  const hits = (s, t) => {                                   // początki trafień hasła w tekście po norm()
    const at = [];
    if (t.re) for (const m of s.matchAll(t.re)) at.push(m.index + m[1].length);
    else for (let i = s.indexOf(t.w); i >= 0; i = s.indexOf(t.w, i + t.w.length)) at.push(i);
    return at;
  };
  const has = (s, t) => t.re ? hits(s, t).length > 0 : s.includes(t.w);
  const text = a => a.x || (a.x = norm([a.t, a.pl, ...a.s.map(s => s[3] + "\n" + s[4])].join("\n")));
  const stanceOk = st => !f.st || (f.st === "nie-neutralny" ? st !== "neutralny" : st === f.st);
  const sigOk = s => (!f.th || s[0] === f.th) && stanceOk(s[1]) && (!f.ak || s[2] === f.ak);
  const filtered = () => {
    const ws = terms();
    return arts.filter(a => (!f.kraj || a.k === f.kraj) && (!f.src || a.src === f.src)
      && (!(f.th || f.st || f.ak) || a.s.some(sigOk)) && ws.every(t => has(text(a), t)));
  };

  function options() {
    const count = (key) => {
      const c = {};
      for (const a of arts) for (const v of new Set(key(a))) c[v] = (c[v] || 0) + 1;
      return c;
    };
    const fill = (name, first, items) => {
      const sel = $(`select[data-f="${name}"]`);
      if (f[name] && !items.some(([v]) => v === f[name])) items.push([f[name], `${f[name]} · brak w okresie`]);
      sel.innerHTML = `<option value="">${first}</option>` + items.map(([v, l]) => `<option value="${esc(v)}">${esc(l)}</option>`).join("");
      sel.value = f[name];
    };
    const byCount = c => Object.keys(c).sort((x, y) => c[y] - c[x] || x.localeCompare(y));
    const kraje = count(a => [a.k]);
    fill("kraj", "wszystkie kraje", byCount(kraje).map(k => [k, `${countryName(k)} · ${num(kraje[k])}`]));
    const zrodla = count(a => [a.src]);
    fill("src", f.kraj ? `wszystkie źródła (${countryName(f.kraj)})` : "wszystkie źródła",
         Object.keys(zrodla).filter(s => !f.kraj || (SPIS.zrodla[s] || [])[1] === f.kraj)
           .sort((x, y) => srcName(x).localeCompare(srcName(y), "pl")).map(s => [s, `${srcName(s)} (${(SPIS.zrodla[s] || [])[1] || "?"}) · ${num(zrodla[s])}`]));
    const tematy = count(a => a.s.map(s => s[0]));                        // tylko stałe tematy, emergent:* są rozdrobnione
    fill("th", "wszystkie tematy", byCount(tematy).filter(t => SPIS.tematy[t]).map(t => [t, `${SPIS.tematy[t]} · ${num(tematy[t])}`]));
    const tony = count(a => a.s.map(s => s[1]));
    const poza = arts.filter(a => a.s.some(s => s[1] !== "neutralny")).length;
    fill("st", "każdy ton", [["nie-neutralny", `poza neutralnym · ${num(poza)}`],
                             ...STANCES.filter(s => tony[s]).map(s => [s, `${s} · ${num(tony[s])}`])]);
    const aktorzy = count(a => a.s.map(s => s[2]));
    fill("ak", "wszyscy aktorzy", byCount(aktorzy).map(a => {
      const n = actorName(a);
      return [a, `${n}${n !== a ? ` (${a})` : ""} · ${num(aktorzy[a])}`];
    }));
  }

  function summary() {
    const tags = [];
    if (f.kraj) tags.push(countryName(f.kraj));
    if (f.src) tags.push(srcName(f.src));
    if (f.th) tags.push(SPIS.tematy[f.th] || f.th);
    if (f.st) tags.push(f.st === "nie-neutralny" ? "ton: poza neutralnym" : "ton: " + f.st);
    if (f.ak) tags.push("aktor: " + actorName(f.ak));
    $(".filtry small").textContent = tags.length ? "· " + tags.join(", ") : "";
    app.querySelectorAll("[data-okres]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.okres === f.okres)));
    app.querySelectorAll("[data-widok]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.widok === f.widok)));
    const z = $(".zakres");
    z.hidden = f.okres !== "zakres";
    if (!z.hidden) {
      const [lo, hi] = [days[days.length - 1] || "", days[0] || ""];
      $('[data-z="od"]').value = f.od || lo;
      $('[data-z="do"]').value = f.do || hi;
    }
  }

  // --- wyniki -------------------------------------------------------------------------------------------------------
  function mark(s, ws) {                                      // podświetlenie bez względu na wielkość liter i ogonki
    if (!ws.length || !s) return esc(s);
    const chars = [...s], pos = [];
    let flat = "";
    chars.forEach((ch, i) => { for (const x of norm(ch)) { flat += x; pos.push(i); } });
    const hit = chars.map(() => false);
    for (const t of ws) for (const i of hits(flat, t)) for (let j = i; j < i + t.w.length; j++) hit[pos[j]] = true;
    let html = "", open = false;
    chars.forEach((ch, i) => {
      if (hit[i] !== open) { html += hit[i] ? "<mark>" : "</mark>"; open = hit[i]; }
      html += esc(ch);
    });
    return html + (open ? "</mark>" : "");
  }

  function snippet(a, ws) {                                   // trafienie tylko w ramie albo streszczeniu: pokaż je
    const head = norm(a.t + " " + a.pl);
    const rest = ws.filter(t => !has(head, t));
    if (!rest.length) return "";
    for (const s of a.s) for (const part of [s[3], s[4]]) {
      const n = norm(part), i = hits(n, rest[0])[0] ?? -1;
      if (i < 0) continue;
      const words = part.split(/\s+/);
      if (words.length <= 15) return mark(part, ws);
      const at = n.slice(0, i).split(/\s+/).length - 1, lo = Math.max(0, at - 5), hi = Math.min(words.length, lo + 15);
      return (lo ? "… " : "") + mark(words.slice(lo, hi).join(" "), ws) + (hi < words.length ? " …" : "");
    }
    return "";
  }

  const item = (a, ws, withCountry = true) => {
    const url = /^https?:\/\//i.test(a.u) ? a.u : "#";
    const snip = snippet(a, ws);
    return `<li><a href="${esc(url)}" target="_blank" rel="noopener">${mark(a.pl || a.t, ws)}</a>` +
      (a.pl ? `<span class="org" dir="auto">${mark(a.t, ws)}</span>` : "") +
      `<span class="meta">${withCountry ? `<b title="${esc(countryName(a.k))}">${esc(a.k)}</b> · ` : ""}${esc(srcName(a.src))} · ${short(a.d)}</span>` +
      (snip ? `<span class="snip">${snip}</span>` : "") + "</li>";
  };

  function drawChart(list) {
    if (!list.length || !days.length) { chart.hidden = true; return; }
    const asc = [...days].reverse();
    const size = asc.length > 45 ? 7 : 1;                     // długi okres: kolumna = tydzień
    const cols = [];
    for (let i = asc.length; i > 0; i -= size) cols.unshift(asc.slice(Math.max(0, i - size), i));
    const col = {};
    cols.forEach((c, i) => c.forEach(d => { col[d] = i; }));
    const per = {}, tot = cols.map(() => 0), sum = {};
    for (const a of list) {
      const i = col[a.d];
      (per[a.k] || (per[a.k] = cols.map(() => 0)))[i]++;
      tot[i]++;
      sum[a.k] = (sum[a.k] || 0) + 1;
    }
    const order = Object.keys(per).sort((x, y) => sum[y] - sum[x]);
    const rows = allRows || order.length <= ROWS + 1 ? order : order.slice(0, ROWS);
    const max = Math.max(...rows.flatMap(k => per[k])), top = Math.max(...tot);
    const nums = cols.length <= 10;
    const label = c => size === 1 ? short(c[0]) : `${short(c[0])}–${short(c[c.length - 1])}`;
    const every = cols.length <= 7 ? 1 : Math.ceil(cols.length / 5);     // podpisy osi bez nachodzenia na telefonie
    let g = `<span class="n">razem</span>` + tot.map((v, i) =>
      `<span class="bc" title="${label(cols[i])}: ${num(v)}"><i style="height:${(v / top * 100).toFixed(1)}%"></i></span>`).join("") +
      `<span class="s">${num(list.length)}</span>`;
    for (const k of rows) {
      g += `<button type="button" data-kraj="${esc(k)}" aria-pressed="${f.kraj === k}" title="${esc(countryName(k))}: tylko ten kraj">${esc(k)}</button>` +
        per[k].map((v, i) => {
          const o = v ? 0.15 + 0.85 * Math.pow(v / max, 0.6) : 0;
          return `<span class="c${o > 0.55 ? " dk" : ""}" style="--o:${o.toFixed(2)}" title="${esc(countryName(k))} · ${label(cols[i])}: ${num(v)}">` +
            (nums && v ? `<span>${v}</span>` : "") + "</span>";
        }).join("") + `<span class="s">${num(sum[k])}</span>`;
    }
    if (rows.length < order.length) g += `<button type="button" class="rest" data-rest>+ ${order.length - rows.length} krajów ▾</button>`;
    else if (order.length > ROWS + 1) g += `<button type="button" class="rest" data-rest>mniej krajów ▴</button>`;
    g += `<span></span>` + cols.map((c, i) => `<span class="x">${i % every === 0 ? short(c[0]) : ""}</span>`).join("") + "<span></span>";
    chart.innerHTML = `<p class="wk-t">Trafienia ${size === 1 ? "dziennie" : "tygodniowo"} według krajów (ciemniej = więcej); kod kraju zawęża wynik</p>` +
      `<div class="wk" style="grid-template-columns:28px repeat(${cols.length},minmax(0,1fr)) 34px">${g}</div>`;
    chart.hidden = false;
  }

  function results() {
    summary();
    const ws = terms(), list = filtered();
    const range = days.length ? (days.length === 1 ? short(days[0]) : `${short(days[days.length - 1])}–${short(days[0])}`) : "";
    const narrowed = ws.length || f.kraj || f.src || f.th || f.st || f.ak;
    info.innerHTML = `<b>${num(list.length)}</b> ${narrowed ? `z ${num(arts.length)} ${plural(arts.length)}` : plural(list.length)} · ${range}` +
      (failed.length ? ` · <span style="color:var(--cegla)">nie wczytano: ${failed.map(short).join(", ")} (odśwież stronę)</span>` : "");
    drawChart(list);
    if (!list.length) {
      out.innerHTML = `<p class="pusto">${arts.length ? "Nic nie pasuje. Zmień okres albo filtry." : "Brak artykułów w tym okresie."}</p>`;
      return;
    }
    if (f.widok === "kraje") {
      const groups = {};
      for (const a of list) (groups[a.k] || (groups[a.k] = [])).push(a);
      out.innerHTML = '<div class="kols">' + Object.keys(groups).sort((x, y) => groups[y].length - groups[x].length).map(k =>
        `<section class="kol"><h3><button type="button" data-lista="${esc(k)}">${esc(countryName(k))} <small>${esc(k)} · ${num(groups[k].length)}</small></button></h3>` +
        `<ol>${groups[k].slice(0, 5).map(a => item(a, ws, false)).join("")}</ol>` +
        (groups[k].length > 5 ? `<button type="button" class="wiecej" data-lista="${esc(k)}">wszystkie ${num(groups[k].length)} ›</button>` : "") +
        "</section>").join("") + "</div>";
      return;
    }
    out.innerHTML = `<ol>${list.slice(0, shown).map(a => item(a, ws)).join("")}</ol>` +
      (list.length > shown ? `<button type="button" class="wiecej" data-wiecej>Pokaż więcej (${num(Math.min(PAGE, list.length - shown))} z ${num(list.length - shown)})</button>` : "");
  }

  // --- zdarzenia ----------------------------------------------------------------------------------------------------
  const changed = (reload = false) => { shown = PAGE; save(); reload ? refresh() : results(); };
  const fixSrc = () => { if (f.kraj && f.src && (SPIS.zrodla[f.src] || [])[1] !== f.kraj) f.src = ""; };   // źródło z innego kraju
  let typing;
  q.addEventListener("input", () => {
    clearTimeout(typing);
    typing = setTimeout(() => { f.q = q.value.trim(); changed(); }, 250);
  });
  app.addEventListener("change", ev => {
    const el = ev.target;
    if (el.dataset.f) {
      f[el.dataset.f] = el.value;
      if (el.dataset.f === "kraj") { fixSrc(); options(); }
      changed();
    } else if (el.dataset.z && el.value) {
      f[el.dataset.z] = el.value;
      changed(true);
    }
  });
  app.addEventListener("click", ev => {
    const b = ev.target.closest("button");
    if (!b) return;
    if (b.dataset.okres) {
      f.okres = b.dataset.okres;
      if (f.okres === "zakres" && !f.od) { f.od = shift(LAST, -6); f.do = LAST; }
      changed(true);
    } else if (b.dataset.widok) {
      f.widok = b.dataset.widok;
      changed();
    } else if ("wiecej" in b.dataset) {
      shown += PAGE;
      results();                                              // lista rośnie w dół, przewinięcie zostaje
      out.querySelectorAll("li")[shown - PAGE]?.querySelector("a")?.focus({ preventScroll: true });
    } else if (b.dataset.kraj !== undefined) {
      f.kraj = f.kraj === b.dataset.kraj ? "" : b.dataset.kraj;
      fixSrc();
      options();
      changed();
    } else if (b.dataset.lista) {
      f.kraj = b.dataset.lista;
      f.widok = "lista";
      options();
      changed();
      info.scrollIntoView({ behavior: "smooth", block: "start" });
    } else if ("rest" in b.dataset) {
      allRows = !allRows;
      results();
    } else if (b.classList.contains("czysc")) {
      Object.assign(f, { q: "", kraj: "", src: "", th: "", st: "", ak: "" });
      q.value = "";
      options();
      changed();
    }
  });
  refresh();
})();
