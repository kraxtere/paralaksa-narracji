// Dziennik: raport dnia, mapa kraje × tematy, porównanie krajów w temacie, lista artykułów z sygnałami.
const D = DATA;
const ART = new Map(D.artykuly.map(a => [a.id, a]));
const SRC = D.zrodla;
const state = { tab: "najwazniejsze", theme: null, f: { kraj: "", src: "", th: "", st: "", q: "" } };
const themeName = id => D.tematy[id] || id;
const fixedTheme = t => !t.startsWith("emergent:");   // tematy spoza taksonomii (nazwane przez model) chowamy

const countryCounts = {};
D.artykuly.forEach(a => { countryCounts[a.kraj] = (countryCounts[a.kraj] || 0) + 1; });
const COUNTRIES = Object.keys(countryCounts).sort((a, b) => countryCounts[b] - countryCounts[a]);

function artLine(a, withSignals = true) {
  const s = SRC[a.src] || {};
  const sig = withSignals ? a.s.filter(x => fixedTheme(x.th)).map(x => `<div class="sig">${stanceDot(x.st)}<span class="pill">${esc(themeName(x.th))}</span>
      <span>${esc(x.frame || "")}</span>${x.actor ? `<span class="muted">· aktor: ${esc(x.actor)}</span>` : ""}</div>`).join("") : "";
  return `<div class="art" id="a${a.id}"><div class="src">${cc(a.kraj)} <span>${esc(s.name || a.src)}</span> ${mediaTag(s.typ)}
      <span>· ${a.pub ? esc(a.pub.slice(0, 16).replace("T", " ")) + " UTC" : "bez daty"}</span>${a.lead ? `<span class="pill" title="ekstrakcja tylko z tytułu i leadu">tylko lead</span>` : ""}</div>
    <div><a class="t" href="#" data-art="${a.id}">${esc(a.tytul)}</a> ${link(a.url, "↗")}</div>${sig}</div>`;
}

function openDrawer(html) {
  let d = document.getElementById("drawer");
  if (!d) {
    document.body.appendChild(h(`<div class="drawer-bg" id="drawer-bg" data-close></div>`));
    d = h(`<div class="drawer" id="drawer" role="dialog"></div>`);
    document.body.appendChild(d);
  }
  d.innerHTML = `<button class="close" data-close aria-label="zamknij">×</button>${html}`;
  d.classList.add("open");
  document.getElementById("drawer-bg").classList.add("open");
  d.scrollTop = 0;
}
function closeDrawer() {
  const d = document.getElementById("drawer");
  if (d) { d.classList.remove("open"); document.getElementById("drawer-bg").classList.remove("open"); }
}
function showArticle(id) {
  const a = ART.get(+id);
  if (!a) { openDrawer(`<p>Artykuł #${esc(id)} nie należy do próbki tego dnia (poza oknem publikacji).</p>`); return; }
  const s = SRC[a.src] || {};
  openDrawer(`<div class="meta">${cc(a.kraj)} <span>${esc(s.name || a.src)}</span>${mediaTag(s.typ)}<span>#${a.id}</span></div>
    <h2 style="margin-top:6px">${esc(a.tytul)}</h2>
    <div class="small muted">${a.pub ? esc(a.pub.replace("T", " ").slice(0, 16)) + " UTC" : "bez daty publikacji"}${a.lead ? " · ekstrakcja tylko z tytułu i leadu" : ""} · ${link(a.url, "otwórz artykuł")}</div>
    <h3>Sygnały (${a.s.length})</h3>
    ${a.s.map(x => `<div class="claim">${stanceDot(x.st)} <strong>${esc(themeName(x.th))}</strong> <span class="muted small">${esc(x.st)} · ${esc((x.typ || "").replace(/_/g, " "))} · intensywność ${esc(x.int)}</span>
      <div><span class="muted">Rama:</span> ${esc(x.frame || "")}</div>${x.actor ? `<div class="small"><span class="muted">Aktor:</span> ${esc(x.actor)}</div>` : ""}
      <div class="small" style="margin-top:4px">${esc(x.sum || "")}</div></div>`).join("") || "<p class='muted'>Brak sygnałów.</p>"}
    <p class="small muted">Streszczenia i ramy są wynikiem ekstrakcji modelem językowym, nie cytatami.</p>`);
}
function showArticles(title, list) {
  openDrawer(`<h2 style="margin-top:0">${title}</h2><p class="muted small">${list.length} artykułów</p>${list.map(a => artLine(a)).join("")}`);
}

// --- raport -------------------------------------------------------------------------------------------------------

function ref(id) {
  const a = ART.get(id);
  if (!a) return `<span class="ref" role="button" tabindex="0" data-art="${id}">#${id}</span>`;
  const s = SRC[a.src] || {};
  return `<span class="ref" role="button" tabindex="0" data-art="${id}" title="${esc(a.tytul)}"><b>${esc(a.kraj)}</b> ${esc(s.name || a.src)}</span>`;
}
const CONF = { niski: "warn", "średni": "", wysoki: "ok" };

function claimHtml(it) {
  return `<div class="claim">
      <div class="meta">${it.temat ? `<span class="pill">${esc(themeName(it.temat))}</span>` : ""}${it.kraj ? cc(it.kraj) : ""}
        ${it.kierunek ? `<span>kierunek: ${esc(it.kierunek)}</span>` : ""}${it.pewnosc ? `<span class="pill ${CONF[it.pewnosc] ?? ""}">pewność: ${esc(it.pewnosc)}</span>` : ""}</div>
      <div class="txt">${esc(it.tekst || "")}</div>
      ${it.kraje.length ? `<ul class="small">${it.kraje.map(c => `<li>${cc(c.kraj)} ${esc(c.rama || "")} <span class="muted">(${esc(c.stance || "")}, źródeł: ${esc(c.n)})</span></li>`).join("")}</ul>` : ""}
      ${it.dodatki.map(([k, v]) => `<div class="small"><span class="muted">${esc(k)}:</span> ${esc(v)}</div>`).join("")}
      ${it.uzasadnienie ? `<div class="conf">Dlaczego taka pewność: ${esc(it.uzasadnienie)}</div>` : ""}
      <div class="refs">${it.artykuly.map(ref).join("")}</div>
    </div>`;
}

function viewReport() {
  if (!D.raport.length) return `<div class="notice">Brak raportu z syntezy dla tego dnia.</div>`;
  const warn = D.ostrzezenia.length ? `<details class="notice"><summary>Ostrzeżenia przebiegu (${D.ostrzezenia.length})</summary><ul class="small">${D.ostrzezenia.map(w => `<li>${esc(w)}</li>`).join("")}</ul></details>` : "";
  const full = D.raport.filter(sec => sec.pozycje.length), empty = D.raport.filter(sec => !sec.pozycje.length);
  return warn + `<p class="hint">Tekst syntezy modelu z walidacją. Pod każdą tezą artykuły źródłowe; kliknij, żeby zobaczyć nagłówek i sygnały.
      Audyt semantyczny: ${esc(D.audyt || "brak")}.</p>` +
    full.map(sec => `<section class="section"><h2>${esc(sec.nazwa)} · ${sec.pozycje.length}</h2>${sec.pozycje.map(claimHtml).join("")}</section>`).join("") +
    (empty.length ? `<p class="empty-sections">Bez pozycji w tym dniu: ${empty.map(sec => esc(sec.nazwa)).join(", ")}.</p>` : "");
}

// --- najważniejsze ------------------------------------------------------------------------------------------------

function storyArticles(h) { return [...h.kraje.map(k => k.article_id), ...h.pozostale].map(id => ART.get(id)).filter(Boolean); }

function viewStories() {
  if (!D.historie.length)
    return `<div class="notice">Brak historii dnia: strona zbudowana bez modelu (<code>--bez-historii</code>) albo żadne wydarzenie nie trafiło do co najmniej 3 krajów.</div>`;
  return D.historie.map((h, i) => {
    const n = storyArticles(h).length;
    return `<section class="story">
      <div class="story-head"><h3>${esc(h.tytul)}</h3><span class="chips">${h.kraje.map(k => cc(k.kraj)).join("")}</span></div>
      ${h.opis ? `<p class="story-desc">${esc(h.opis)}</p>` : ""}
      <div class="story-grid">${h.kraje.map(k => {
        const a = ART.get(k.article_id) || {}, s = SRC[a.src] || {};
        return `<div class="sh"><div class="src">${cc(k.kraj)} <span>${esc(s.name || a.src || "")}</span> ${mediaTag(s.typ)}</div>
          <a class="h" href="#" data-art="${k.article_id}">${esc(k.naglowek_pl)}</a>
          ${a.tytul && a.tytul !== k.naglowek_pl ? `<div class="alt">${esc(a.tytul)}</div>` : ""}</div>`;
      }).join("")}</div>
      <div class="small" style="margin-top:10px"><a href="#" data-story="${i}">wszystkie artykuły o tym wydarzeniu (${n}) →</a></div></section>`;
  }).join("");
}

const pct = v => `${Math.round(v * 100)}%`;
function viewStandouts() {
  if (!D.wyroznia.length) return `<p class="muted small">Żaden kraj nie odstaje wyraźnie od pozostałych.</p>`;
  return `<div class="standouts">${D.wyroznia.map(w => {
    const more = w.kierunek === "wiecej";
    const caveat = w.zrodla < 2 ? "jedno źródło w kraju" : w.n_kraj < 20 ? "mała próbka" : "";
    return `<div class="standout" role="button" tabindex="0" data-cell="${esc(w.temat)}|${esc(w.kraj)}">
      <div>${cc(w.kraj)} <b>${esc(countryName(w.kraj))}</b> ${more ? "pisze znacznie więcej niż inni o temacie" : "prawie pomija temat"}
        <b>${esc(themeName(w.temat))}</b>${caveat ? ` <span class="pill warn">${caveat}</span>` : ""}
        <div class="small muted">${pct(w.udzial)} artykułów kraju (${w.n} z ${w.n_kraj}); pozostałe kraje średnio ${pct(w.srednia)}</div></div>
      <div class="bars"><div><span class="lbl">${esc(w.kraj)}</span><span class="b"><i style="width:${Math.min(100, w.udzial * 100 / .6)}%"></i></span></div>
        <div><span class="lbl">inni</span><span class="b other"><i style="width:${Math.min(100, w.srednia * 100 / .6)}%"></i></span></div></div></div>`;
  }).join("")}</div>`;
}

function viewEssence() {
  const brief = (D.raport.find(sec => sec.klucz === "w_skrocie") || { pozycje: [] }).pozycje;
  const meta = D.historie_meta;
  return `<h2 style="margin-top:4px">Historie dnia · ${D.historie.length}</h2>
    <p class="hint">Wydarzenia opisywane w co najmniej trzech krajach. Z każdego kraju jeden nagłówek przetłumaczony przez model, oryginał pod spodem.
      Grupowanie jest automatyczne (dwa kroki: wyszukanie i sprawdzenie każdego artykułu) i może się pomylić, dlatego zawsze widać oryginał.
      ${meta ? `<span class="muted">${esc(meta.model)}, ${esc(meta.created)}, ${meta.cost_usd.toFixed(3)} $.</span>` : ""}</p>
    ${viewStories()}
    <h2>Co się wyróżnia</h2>
    <p class="hint">Największe różnice między udziałem tematu w danym kraju a średnią pozostałych krajów (kraje z co najmniej 10 artykułami). Kliknij, żeby zobaczyć artykuły.</p>
    ${viewStandouts()}
    ${brief.length ? `<h2>W skrócie z raportu</h2>${brief.map(claimHtml).join("")}<p class="small"><a href="#" data-tab="raport">cały raport →</a></p>` : ""}`;
}

// --- mapa ---------------------------------------------------------------------------------------------------------

function viewMap() {
  const M = {};
  D.metryki.forEach(m => { (M[m.theme_id] = M[m.theme_id] || {})[m.country] = m; });
  const themes = Object.keys(M).sort((a, b) => {
    const s = t => Object.values(M[t]).reduce((x, m) => x + m.n_articles, 0);
    return s(b) - s(a);
  });
  const cols = COUNTRIES.filter(c => D.metryki.some(m => m.country === c));
  const hist = (t, c) => ((D.historia[t] || {})[c] || []).map(([d, v]) => `${d.slice(5)}: ${(v * 100).toFixed(0)}%`).join(" → ");
  const shown = themes.filter(fixedTheme);
  const more = "";
  return `<p class="hint">Jaka część artykułów danego kraju z tego dnia dotyczy tematu. Kliknij komórkę, żeby zobaczyć artykuły, a temat, żeby porównać kraje.</p>
    <div style="overflow-x:auto"><table class="heat"><thead><tr><th class="theme"></th>${cols.map(c => `<th title="${esc(countryName(c))}">${cc(c)}<div class="muted">${countryCounts[c]} art.</div></th>`).join("")}</tr></thead>
    <tbody>${shown.map(t => `<tr><th class="theme"><a href="#" data-theme="${esc(t)}">${esc(themeName(t))}</a></th>${cols.map(c => {
      const m = M[t][c];
      if (!m) return `<td class="empty"></td>`;
      const a = Math.max(.06, Math.min(1, m.article_share * 2.2));
      return `<td class="cell ${m.n_sources < 2 ? "one" : ""}" data-cell="${esc(t)}|${esc(c)}" style="background-color:rgba(47,93,138,${a.toFixed(2)});color:${a > .55 ? "#fff" : "inherit"}"
        title="${esc(countryName(c))} · ${esc(themeName(t))}\n${m.n_articles} art., ${m.n_sources} źr.\nDominująca rama: ${esc(m.dominant_frame || "")}\nHistoria: ${esc(hist(t, c))}">${(m.article_share * 100).toFixed(0)}%</td>`;
    }).join("")}</tr>`).join("")}${more}</tbody></table></div>
    <div class="scale"><span>0%</span><span class="grad"></span><span>45% i więcej</span><span style="margin-left:18px" class="one"></span><span>tylko jedno źródło w kraju: słabszy sygnał</span></div>`;
}

// --- porównanie ---------------------------------------------------------------------------------------------------

function viewCompare() {
  const themes = Object.keys(D.tematy).filter(fixedTheme).filter(t => D.artykuly.some(a => a.s.some(s => s.th === t)));
  const count = t => D.artykuly.filter(a => a.s.some(s => s.th === t)).length;
  themes.sort((a, b) => count(b) - count(a));
  const t = state.theme || themes[0];
  const sel = `<div class="filters">Temat: <select id="cmp-theme">${themes.map(x => `<option value="${esc(x)}" ${x === t ? "selected" : ""}>${esc(themeName(x))} (${count(x)})</option>`).join("")}</select></div>`;
  const cols = COUNTRIES.map(c => {
    const arts = D.artykuly.filter(a => a.kraj === c && a.s.some(s => s.th === t));
    if (!arts.length) return null;
    const sigs = arts.flatMap(a => a.s.filter(s => s.th === t));
    const st = {}; sigs.forEach(s => { st[s.st] = (st[s.st] || 0) + 1; });
    const fr = {}; sigs.forEach(s => { if (s.frame) fr[s.frame] = (fr[s.frame] || 0) + 1; });
    const frames = Object.entries(fr).sort((a, b) => b[1] - a[1]).slice(0, 5);
    const srcs = new Set(arts.map(a => a.src));
    return `<div class="col"><h3 style="margin:0">${cc(c)} ${esc(countryName(c))}</h3>
      <div class="small muted">${arts.length} art. z ${countryCounts[c]} · źródła: ${[...srcs].map(s => esc((SRC[s] || {}).name || s)).join(", ")}${srcs.size < 2 ? " · <span style='color:var(--warn)'>jedno źródło</span>" : ""}</div>
      <div class="bar" title="${esc(STANCES.map(s => `${s}: ${st[s] || 0}`).join(", "))}">${STANCES.map(s => st[s] ? `<span class="st-${s}" style="width:${st[s] / sigs.length * 100}%"></span>` : "").join("")}</div>
      <div class="small muted">Najczęstsze ramy:</div><ul class="frames">${frames.map(([f, n]) => `<li>${esc(f)}${n > 1 ? ` <span class="muted">×${n}</span>` : ""}</li>`).join("")}</ul>
      <div class="small muted">Nagłówki:</div><div class="heads">${arts.slice(0, 6).map(a => `<a href="#" data-art="${a.id}">${esc(a.tytul)}</a>`).join("")}</div>
      ${arts.length > 6 ? `<div class="small" style="margin-top:8px"><a href="#" data-cell="${esc(t)}|${esc(c)}">wszystkie ${arts.length} →</a></div>` : ""}</div>`;
  }).filter(Boolean);
  return sel + `<p class="hint">Kraje obok siebie w jednym temacie: rozkład tonu (${STANCES.map(s => `${stanceDot(s)}${s}`).join(" ")}), najczęstsze ramy i nagłówki.</p><div class="cmp">${cols.join("")}</div>`;
}

// --- artykuły -----------------------------------------------------------------------------------------------------

function viewArticles() {
  const f = state.f;
  const opts = (vals, cur, label) => `<option value="">${label}</option>` + vals.map(([v, l]) => `<option value="${esc(v)}" ${v === cur ? "selected" : ""}>${esc(l)}</option>`).join("");
  const srcIds = [...new Set(D.artykuly.map(a => a.src))].sort();
  const list = D.artykuly.filter(a => (!f.kraj || a.kraj === f.kraj) && (!f.src || a.src === f.src)
    && (!f.th || a.s.some(s => s.th === f.th)) && (!f.st || a.s.some(s => s.st === f.st && (!f.th || s.th === f.th)))
    && (!f.q || (a.tytul + " " + a.s.map(s => s.frame + " " + s.sum).join(" ")).toLowerCase().includes(f.q.toLowerCase())));
  return `<div class="filters">
      <select data-f="kraj">${opts(COUNTRIES.map(c => [c, `${c} ${countryName(c)} (${countryCounts[c]})`]), f.kraj, "wszystkie kraje")}</select>
      <select data-f="src">${opts(srcIds.map(s => [s, (SRC[s] || {}).name || s]), f.src, "wszystkie źródła")}</select>
      <select data-f="th">${opts(Object.keys(D.tematy).filter(fixedTheme).map(t => [t, themeName(t)]), f.th, "wszystkie tematy")}</select>
      <select data-f="st">${opts(STANCES.map(s => [s, s]), f.st, "każdy ton")}</select>
      <input data-f="q" type="search" placeholder="szukaj w nagłówkach i ramach" value="${esc(f.q)}">
      <span class="muted">${list.length} z ${D.artykuly.length}</span></div>
    <div id="art-list">${list.slice(0, 300).map(a => artLine(a)).join("")}${list.length > 300 ? `<p class="muted">Pokazano 300; zawęź filtry.</p>` : ""}</div>`;
}

// --- całość -------------------------------------------------------------------------------------------------------

function header() {
  const p = D.publikacja;
  const cost = Object.values(D.koszt).reduce((x, v) => x + v, 0);
  const costTitle = Object.entries(D.koszt).map(([k, v]) => `${k} ${v.toFixed(2)} $`).join(", ");
  const nSig = D.artykuly.reduce((x, a) => x + a.s.length, 0);
  const stat = (b, s, t = "") => `<div class="stat" ${t ? `title="${esc(t)}"` : ""}><b>${b}</b><span>${s}</span></div>`;
  return `<div class="meta"><span class="pill ${p.status === "inicjalny" ? "warn" : ""}">przebieg ${esc(p.status)}</span><span>dziennik automatyczny</span></div>
    <h1>${fmtDay(D.dzien)}</h1>
    <div class="small muted">Porównujemy artykuły opublikowane od ${esc(p.publication_window_start.slice(0, 10))} do ${esc(new Date(Date.parse(p.publication_window_end_exclusive) - 1).toISOString().slice(0, 10))} (UTC); starsze z RSS są pomijane.
      ${p.status === "inicjalny" ? "Pierwszy przebieg zawiera zaległość z RSS i nie wchodzi do linii bazowej." : ""}</div>
    <div class="stats">${stat(D.artykuly.length, `artykułów w oknie (z ${p.fetched_articles})`)}${stat(COUNTRIES.length, "krajów")}
      ${stat(new Set(D.artykuly.map(a => a.src)).size, "źródeł")}${stat(nSig, "sygnałów")}${cost ? stat(cost.toFixed(2) + " $", "koszt modeli", costTitle) : ""}</div>
    ${D.zdarzenia.length ? `<div class="notice" style="margin-top:12px">Karty zdarzeń z tych dni: ${D.zdarzenia.map(e => `<a href="${ROOT}zdarzenia/${esc(e.id)}.html">${esc(e.tytul)}</a>`).join(" · ")}</div>` : ""}`;
}

const TABS = [["najwazniejsze", "Najważniejsze"], ["raport", "Raport"], ["mapa", "Mapa tematów"], ["porownanie", "Porównanie krajów"], ["artykuly", "Wszystkie artykuły"]];
function render() {
  const views = { najwazniejsze: viewEssence, raport: viewReport, mapa: viewMap, porownanie: viewCompare, artykuly: viewArticles };
  app.innerHTML = `${header()}<div class="tabs">${TABS.map(([id, l]) => `<button data-tab="${id}" class="${state.tab === id ? "on" : ""}">${l}</button>`).join("")}</div>
    <div id="view">${views[state.tab]()}</div>`;
}

document.addEventListener("click", e => {
  const el = e.target.closest("[data-tab],[data-art],[data-cell],[data-theme],[data-close],[data-story]");
  if (!el) return;
  if (el.dataset.close !== undefined) { closeDrawer(); return; }
  e.preventDefault();
  if (el.dataset.story !== undefined) { const h = D.historie[+el.dataset.story]; showArticles(esc(h.tytul), storyArticles(h)); return; }
  if (el.dataset.tab) { state.tab = el.dataset.tab; history.replaceState(null, "", "#" + state.tab); render(); window.scrollTo(0, 0); }
  else if (el.dataset.art) showArticle(el.dataset.art);
  else if (el.dataset.theme) { state.theme = el.dataset.theme; state.tab = "porownanie"; render(); }
  else if (el.dataset.cell) {
    const [t, c] = el.dataset.cell.split("|");
    showArticles(`${cc(c)} ${esc(countryName(c))} · ${esc(themeName(t))}`, D.artykuly.filter(a => a.kraj === c && a.s.some(s => s.th === t)));
  }
});
document.addEventListener("keydown", e => { if (e.key === "Escape") closeDrawer(); });
document.addEventListener("change", e => {
  if (e.target.id === "cmp-theme") { state.theme = e.target.value; render(); }
  else if (e.target.dataset.f && e.target.dataset.f !== "q") { state.f[e.target.dataset.f] = e.target.value; render(); }
});
document.addEventListener("input", e => {
  if (e.target.dataset.f === "q") {
    state.f.q = e.target.value;
    const pos = e.target.selectionStart;
    render();
    const inp = document.querySelector('[data-f="q"]'); inp.focus(); inp.setSelectionRange(pos, pos);
  }
});

const hash = location.hash.slice(1);
if (TABS.some(([id]) => id === hash)) state.tab = hash;
render();
if (/^a\d+$/.test(hash)) showArticle(hash.slice(1));
