// Dziennik: raport dnia, mapa kraje × tematy, porównanie krajów w temacie, lista artykułów z sygnałami.
const D = DATA;
const ART = new Map(D.artykuly.map(a => [a.id, a]));
const SRC = D.zrodla;
const state = { tab: "raport", theme: null, f: { kraj: "", src: "", th: "", st: "", q: "" } };
const TYP = { private: "prywatne", public: "publiczne", government: "państwowe", agency: "agencja", state: "państwowe" };
const themeName = id => D.tematy[id] || id;

const countryCounts = {};
D.artykuly.forEach(a => { countryCounts[a.kraj] = (countryCounts[a.kraj] || 0) + 1; });
const COUNTRIES = Object.keys(countryCounts).sort((a, b) => countryCounts[b] - countryCounts[a]);

function artLine(a, withSignals = true) {
  const s = SRC[a.src] || {};
  const sig = withSignals ? a.s.map(x => `<div class="sig">${stanceDot(x.st)}<span class="pill">${esc(themeName(x.th))}</span>
      <span>${esc(x.frame || "")}</span>${x.actor ? `<span class="muted">· aktor: ${esc(x.actor)}</span>` : ""}</div>`).join("") : "";
  return `<div class="art" id="a${a.id}">${cc(a.kraj)} <span class="muted small">${esc(s.name || a.src)} · ${a.pub ? esc(a.pub.slice(0, 16).replace("T", " ")) + " UTC" : "bez daty"}${a.lead ? " · tylko lead" : ""} · #${a.id}</span>
    <div><a class="t" href="#" data-art="${a.id}">${esc(a.tytul)}</a> ${link(a.url, "↗")}</div>${sig}</div>`;
}

function openDrawer(html) {
  let d = document.getElementById("drawer");
  if (!d) { d = h(`<div class="drawer" id="drawer"></div>`); document.body.appendChild(d); }
  d.innerHTML = `<button class="close" data-close>×</button>${html}`;
  d.classList.add("open");
  d.scrollTop = 0;
}
function showArticle(id) {
  const a = ART.get(+id);
  if (!a) { openDrawer(`<p>Artykuł #${esc(id)} nie należy do próbki tego dnia (poza oknem publikacji).</p>`); return; }
  const s = SRC[a.src] || {};
  openDrawer(`<div class="meta">${cc(a.kraj)} <span>${esc(s.name || a.src)}</span><span>${esc(TYP[s.typ] || s.typ || "")}</span><span>#${a.id}</span></div>
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

function viewReport() {
  if (!D.raport.length) return `<div class="notice">Brak raportu z syntezy dla tego dnia.</div>`;
  const warn = D.ostrzezenia.length ? `<details class="notice"><summary>Ostrzeżenia przebiegu (${D.ostrzezenia.length})</summary><ul class="small">${D.ostrzezenia.map(w => `<li>${esc(w)}</li>`).join("")}</ul></details>` : "";
  return warn + `<p class="muted small">Tekst syntezy modelu z walidacją. Numery to artykuły źródłowe; kliknij, żeby zobaczyć nagłówek i sygnały.
      Audyt semantyczny: ${esc(D.audyt || "brak")}.</p>` +
    D.raport.map(sec => `<h2>${esc(sec.nazwa)}</h2>${sec.pozycje.length ? sec.pozycje.map(it => `<div class="claim">
      <div class="meta">${it.temat ? `<span class="pill">${esc(themeName(it.temat))}</span>` : ""}${it.kraj ? cc(it.kraj) : ""}
        ${it.kierunek ? `<span>kierunek: ${esc(it.kierunek)}</span>` : ""}${it.pewnosc ? `<span class="pill ${it.pewnosc === "niski" ? "warn" : ""}">pewność: ${esc(it.pewnosc)}</span>` : ""}</div>
      <div>${esc(it.tekst || "")}</div>
      ${it.kraje.length ? `<ul class="small">${it.kraje.map(c => `<li>${cc(c.kraj)} ${esc(c.rama || "")} <span class="muted">(${esc(c.stance || "")}, źródeł: ${esc(c.n)})</span></li>`).join("")}</ul>` : ""}
      ${it.dodatki.map(([k, v]) => `<div class="small"><span class="muted">${esc(k)}:</span> ${esc(v)}</div>`).join("")}
      ${it.uzasadnienie ? `<div class="small muted">Pewność: ${esc(it.uzasadnienie)}</div>` : ""}
      <div class="refs">${it.artykuly.map(id => { const a = ART.get(id); return `<span class="ref" data-art="${id}" title="${esc(a ? a.tytul : "")}">${a ? esc(a.kraj) + " " : ""}#${id}</span>`; }).join("")}</div>
    </div>`).join("") : `<p class="muted small">Pusto.</p>`}`).join("");
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
  const fixed = themes.filter(t => !t.startsWith("emergent:"));
  const emergent = themes.filter(t => t.startsWith("emergent:"));
  const shown = state.emergent ? themes : fixed;
  const more = emergent.length ? `<tr><td colspan="${cols.length + 1}" style="text-align:left"><a href="#" data-emergent>${state.emergent ? "ukryj" : "pokaż"} nowe tematy spoza taksonomii (${emergent.length})</a>
      <span class="muted">: model nazywa je sam, często pojedyncze artykuły</span></td></tr>` : "";
  return `<p class="muted small">Udział: jaka część artykułów kraju z tego dnia dotyczy tematu. Kreskowanie: tylko jedno źródło w kraju (słabszy sygnał).
      Kliknij komórkę, żeby zobaczyć artykuły; kliknij temat, żeby porównać kraje.</p>
    <div style="overflow-x:auto"><table class="heat"><thead><tr><th class="theme">temat / kraj <span class="muted">(artykuły)</span></th>${cols.map(c => `<th title="${esc(countryName(c))}">${esc(c)}<div class="muted" style="font-weight:400">${countryCounts[c]}</div></th>`).join("")}</tr></thead>
    <tbody>${shown.map(t => `<tr><th class="theme"><a href="#" data-theme="${esc(t)}">${esc(themeName(t))}</a></th>${cols.map(c => {
      const m = M[t][c];
      if (!m) return `<td class="empty">·</td>`;
      const a = Math.min(1, m.article_share * 2.2);
      return `<td class="cell ${m.n_sources < 2 ? "one" : ""}" data-cell="${esc(t)}|${esc(c)}" style="background-color:rgba(47,93,138,${a.toFixed(2)});color:${a > .55 ? "#fff" : "inherit"}"
        title="${esc(countryName(c))} · ${esc(themeName(t))}\n${m.n_articles} art., ${m.n_sources} źr.\nDominująca rama: ${esc(m.dominant_frame || "")}\nHistoria: ${esc(hist(t, c))}">${(m.article_share * 100).toFixed(0)}%</td>`;
    }).join("")}</tr>`).join("")}${more}</tbody></table></div>`;
}

// --- porównanie ---------------------------------------------------------------------------------------------------

function viewCompare() {
  const themes = Object.keys(D.tematy).filter(t => D.artykuly.some(a => a.s.some(s => s.th === t)));
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
      <div class="small">${arts.slice(0, 6).map(a => `<div style="margin-top:4px"><a href="#" data-art="${a.id}">${esc(a.tytul)}</a></div>`).join("")}
      ${arts.length > 6 ? `<a href="#" data-cell="${esc(t)}|${esc(c)}">… wszystkie ${arts.length}</a>` : ""}</div></div>`;
  }).filter(Boolean);
  return sel + `<p class="muted small">Kraje obok siebie w jednym temacie: rozkład tonu (${STANCES.map(s => `${stanceDot(s)}${s}`).join(" ")}), najczęstsze ramy i nagłówki.</p><div class="cmp">${cols.join("")}</div>`;
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
      <select data-f="th">${opts(Object.keys(D.tematy).map(t => [t, themeName(t)]), f.th, "wszystkie tematy")}</select>
      <select data-f="st">${opts(STANCES.map(s => [s, s]), f.st, "każdy ton")}</select>
      <input data-f="q" type="search" placeholder="szukaj w nagłówkach i ramach" value="${esc(f.q)}">
      <span class="muted">${list.length} z ${D.artykuly.length}</span></div>
    <div id="art-list">${list.slice(0, 300).map(a => artLine(a)).join("")}${list.length > 300 ? `<p class="muted">Pokazano 300; zawęź filtry.</p>` : ""}</div>`;
}

// --- całość -------------------------------------------------------------------------------------------------------

function header() {
  const p = D.publikacja;
  const cost = Object.entries(D.koszt).map(([k, v]) => `${k} ${v.toFixed(2)} $`).join(", ");
  return `<div class="meta"><span class="pill ${p.status === "inicjalny" ? "warn" : ""}">przebieg ${esc(p.status)}</span>
      <span>${D.artykuly.length} artykułów w oknie publikacji (z ${p.fetched_articles} pobranych)</span>
      <span>${COUNTRIES.length} krajów, ${new Set(D.artykuly.map(a => a.src)).size} źródeł</span>
      <span>${D.artykuly.reduce((x, a) => x + a.s.length, 0)} sygnałów</span>${cost ? `<span>koszt: ${esc(cost)}</span>` : ""}</div>
    <h1>Dziennik ${esc(D.dzien)}</h1>
    <div class="small muted">Porównujemy artykuły opublikowane od ${esc(p.publication_window_start.slice(0, 10))} do ${esc(new Date(Date.parse(p.publication_window_end_exclusive) - 1).toISOString().slice(0, 10))} (UTC); starsze z RSS są pomijane.
      ${p.status === "inicjalny" ? "Pierwszy przebieg zawiera zaległość z RSS i nie wchodzi do linii bazowej." : ""}</div>
    ${D.zdarzenia.length ? `<div class="notice" style="margin-top:10px">Karty zdarzeń z tych dni: ${D.zdarzenia.map(e => `<a href="${ROOT}zdarzenia/${esc(e.id)}.html">${esc(e.tytul)}</a>`).join(" · ")}</div>` : ""}`;
}

const TABS = [["raport", "Raport"], ["mapa", "Mapa tematów"], ["porownanie", "Porównanie krajów"], ["artykuly", "Artykuły"]];
function render() {
  const views = { raport: viewReport, mapa: viewMap, porownanie: viewCompare, artykuly: viewArticles };
  app.innerHTML = `${header()}<div class="tabs">${TABS.map(([id, l]) => `<button data-tab="${id}" class="${state.tab === id ? "on" : ""}">${l}</button>`).join("")}</div>
    <div id="view">${views[state.tab]()}</div>`;
}

document.addEventListener("click", e => {
  const el = e.target.closest("[data-tab],[data-art],[data-cell],[data-theme],[data-close],[data-emergent]");
  if (!el) return;
  if (el.dataset.close !== undefined) { document.getElementById("drawer").classList.remove("open"); return; }
  e.preventDefault();
  if (el.dataset.emergent !== undefined) { state.emergent = !state.emergent; render(); return; }
  if (el.dataset.tab) { state.tab = el.dataset.tab; history.replaceState(null, "", "#" + state.tab); render(); }
  else if (el.dataset.art) showArticle(el.dataset.art);
  else if (el.dataset.theme) { state.theme = el.dataset.theme; state.tab = "porownanie"; render(); }
  else if (el.dataset.cell) {
    const [t, c] = el.dataset.cell.split("|");
    showArticles(`${cc(c)} ${esc(countryName(c))} · ${esc(themeName(t))}`, D.artykuly.filter(a => a.kraj === c && a.s.some(s => s.th === t)));
  }
});
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
