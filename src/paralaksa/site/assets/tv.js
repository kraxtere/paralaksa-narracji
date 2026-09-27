// Telewizja: widoki robocze z raportów GDELT „Today's Media Trends” (dane: gdelt/tv_views.py)
const TV = DATA;
const TV_CH = TV.channels, TV_ORDER = TV.blocs.flatMap(b => b.kanaly);
const TV_TABS = [["stories", "Historie dnia"], ["board", "Tablica dnia"], ["topic", "Jeden temat"], ["pair", "Dwie stacje"], ["diary", "Kanał w czasie"], ["search", "Szukaj frazy"]];
let tvLang = "pl";
try { tvLang = localStorage.getItem("plx-tv-lang") || "pl"; } catch (e) { /* file:// bez localStorage */ }
const tvS = { tab: "stories", more: false, day: TV.days[0], topic: 0, cell: null, a: "RUSSIA24", b: "ESPRESO", ch: "TVPINFO", q: "" };
{ const hash = location.hash.slice(1); if (TV_TABS.some(t => t[0] === hash)) tvS.tab = hash; }
const tvNorm = s => s.normalize("NFKD").replace(/[̀-ͯ]/g, "").replace(/ł/g, "l").replace(/Ł/g, "L").toLowerCase();
const TV_WORD = /[A-Za-zÀ-ɏ][A-Za-zÀ-ɏ0-9'’]*/g;
const tvKey = w => tvNorm(w.replace(/['’]s$/, ""));
const tvHas = (s, k) => (s.match(TV_WORD) || []).some(w => tvKey(w) === k);
const tvLab = c => `${esc(TV_CH[c].nazwa)} <span class="tv-small">${esc(TV_CH[c].kraj)}</span>`;
const tvDay = () => TV.data[tvS.day];
// po polsku (tłumaczenie maszynowe), gdy jest; inaczej angielski oryginał raportu
const tvPl = () => tvLang === "pl";
const tvText = (r, i) => (tvPl() && r.sentences_pl && r.sentences_pl[i]) || r.sentences[i];
const tvTitle = r => (tvPl() && r.title_pl) || r.title;
const tvGlance = r => (tvPl() && r.glance_pl) || r.glance;
function tvSnip(g, c) {
  const r = tvDay().reports[c], i = (g.snip_idx || {})[c];
  const pl = tvPl() && r && r.sentences_pl && i != null ? r.sentences_pl[i] : null;
  return pl ? (pl.length > 420 ? pl.slice(0, 420) + "…" : pl) : g.snippets[c];
}

function tvDaySel() {
  return `<select data-set="day">${TV.days.map(d => `<option value="${d}" ${d === tvS.day ? "selected" : ""}>${fmtDay(d)}</option>`).join("")}</select>`;
}
function tvChSel(prop) {
  return `<select data-set="${prop}">${TV_ORDER.map(c => `<option value="${c}" ${tvS[prop] === c ? "selected" : ""}>${esc(TV_CH[c].nazwa)} (${esc(TV_CH[c].kraj)})</option>`).join("")}</select>`;
}
function tvMark(s, q) {
  if (!q) return esc(s);
  const i = tvNorm(s).indexOf(tvNorm(q));
  return i < 0 ? esc(s) : esc(s.slice(0, i)) + "<mark>" + esc(s.slice(i, i + q.length)) + "</mark>" + esc(s.slice(i + q.length));
}
function tvSentence(c, k) {
  const r = tvDay().reports[c];
  if (!r) return "";
  const i = r.sentences.findIndex(s => tvHas(s, k));
  return i < 0 ? "" : tvText(r, i);
}
function tvChip(name, extra = "") { return `<button class="tv-chip" data-q="${esc(name)}">${esc(name)}${extra}</button>`; }

// zdanie stacji z podświetlonymi słowami różnicującymi (dosłowny fragment zdania, sprawdzony przy budowie)
function tvMarkExact(s, part) {
  const i = part ? s.indexOf(part) : -1;
  return i < 0 ? esc(s) : esc(s.slice(0, i)) + "<mark>" + esc(part) + "</mark>" + esc(s.slice(i + part.length));
}
// model w opisach bywa, że używa kodów GDELT (RUSSIA1, BBCNEWS): na stronie nazwy stacji
const TV_CODE = new RegExp("\\b(" + Object.keys(TV_CH).sort((a, b) => b.length - a.length).join("|") + ")\\b", "g");
const tvNames = s => (s || "").replace(TV_CODE, c => TV_CH[c].nazwa);
const TV_SILA = { 3: "wersje się wykluczają", 2: "wyraźna różnica", 1: "słaba różnica" };
function tvStory(h, n) {
  const d = tvDay(), ver = {};
  h.wersje.forEach((v, k) => v.stacje.forEach(r => ver[r.stacja] = k));
  const strip = TV.blocs.map(b => `<span class="tv-sb"><span class="tv-sbn">${esc(b.nazwa)}</span>` + b.kanaly.map(c => {
    const k = ver[c], cls = k != null ? `v${k}` : h.wspomina.includes(c) ? "m" : d.reports[c] ? "" : "x";
    const what = k != null ? h.wersje[k].etykieta : h.wspomina.includes(c) ? "wspomina, bez wyraźnej wersji" : d.reports[c] ? "nie znaleziono w streszczeniu" : "brak raportu";
    return `<i class="tv-sd ${cls}" title="${esc(TV_CH[c].nazwa)}: ${esc(what)}"></i>`;
  }).join("") + "</span>").join("");
  const cols = h.wersje.map((v, k) => `<div class="tv-ver"><div class="tv-vh"><i class="tv-sd v${k}"></i>${esc(v.etykieta)}</div>` + v.stacje.map(r => {
    const rep = d.reports[r.stacja];
    const pl = tvPl() && rep.sentences_pl && rep.sentences_pl[r.zdanie];
    const pdf = TV.pdf.replace("{day}", tvS.day.replaceAll("-", "")).replace("{code}", r.stacja);
    return `<div class="tv-vs"><b>${tvLab(r.stacja)}</b> <a class="tv-small" href="${esc(pdf)}" target="_blank" rel="noopener">raport</a><div>${pl ? tvMarkExact(pl, r.pl) : tvMarkExact(rep.sentences[r.zdanie], r.en)}</div></div>`;
  }).join("") + "</div>").join("");
  return `<article class="tv-story"><div class="tv-sh"><span class="tv-type">${esc(TV.types[h.typ] || h.typ)}</span><span class="tv-small">${n}. · ${TV_SILA[h.sila] || ""}</span></div>
<h2>${esc(h.tytul)}</h2><p class="tv-diff">${esc(tvNames(h.roznica))}</p><div class="tv-strip">${strip}</div>
<div class="tv-vers" style="--n:${h.wersje.length}">${cols}</div>
${h.uwaga ? `<p class="tv-note">Zastrzeżenie: ${esc(tvNames(h.uwaga))}</p>` : ""}</article>`;
}
function tvStories() {
  const st = tvDay().stories;
  let o = `<div class="tv-bar">${tvDaySel()}<span class="hint">Zdarzenia, w których streszczenia różnych stacji podają różne wersje: inną liczbę, status decyzji, przebieg, rolę aktora. Porównanie streszczeń GDELT (Gemini), nie słów z anteny: przed użyciem sprawdzić w wydaniu.</span></div>`;
  if (st == null) return o + "<p>Historii dla tego dnia jeszcze nie zbudowano (plx site albo plx gdelt tv-historie).</p>";
  if (!st.length) return o + "<p>Tego dnia model nie znalazł różnic, które przeszły sprawdzenie.</p>";
  o += `<div class="tv-legend"><i class="tv-sd v0"></i><i class="tv-sd v1"></i><i class="tv-sd v2"></i> wersje · <i class="tv-sd m"></i> wspomina bez wyraźnej wersji · <i class="tv-sd"></i> nie znaleziono w streszczeniu · <i class="tv-sd x"></i> brak raportu</div>`;
  const top = st.slice(0, TV.top), rest = st.slice(TV.top);
  o += top.map((h, i) => tvStory(h, i + 1)).join("");
  if (rest.length) o += tvS.more ? rest.map((h, i) => tvStory(h, TV.top + i + 1)).join("")
    : `<button class="tv-chip" data-more="1">Pokaż pozostałe (${rest.length}), słabsze</button>`;
  return o;
}

function tvBoard() {
  const g = tvDay().groups;
  let o = `<div class="tv-bar">${tvDaySel()}<span class="hint">Wiersz: nazwa nowa w co najmniej 3 stacjach (w nawiasie: w ilu była dzień wcześniej). Kropka: raport stacji o niej wspomina; kliknij, żeby zobaczyć zdanie.</span></div>`;
  if (!g.length) return o + "<p>Brak nowych nazw (albo brak dnia poprzedniego do porównania).</p>";
  o += `<div class="tv-scroll"><table class="tv-board"><tr><th></th>`;
  TV.blocs.forEach(b => o += `<th class="tv-bloc" colspan="${b.kanaly.length}">${esc(b.nazwa)}</th>`);
  o += `</tr><tr><th class="tv-topic">nazwa</th>` + TV_ORDER.map(c => `<th class="tv-ch" title="${esc(tvDay().reports[c] ? tvTitle(tvDay().reports[c]) : "brak raportu")}">${esc(TV_CH[c].nazwa)}</th>`).join("") + "</tr>";
  g.forEach((x, i) => {
    o += `<tr><td class="tv-topic"><a href="#topic" data-topic-i="${i}">${esc(x.label)}</a> <span class="tv-small">(${x.before})</span></td>`;
    TV_ORDER.forEach(c => {
      const sel = tvS.cell && tvS.cell[0] === i && tvS.cell[1] === c;
      o += x.channels.includes(c) ? `<td><button class="tv-dot ${sel ? "sel" : ""}" data-cell="${i}|${c}" title="${esc(TV_CH[c].nazwa)}">●</button></td>` : `<td class="tv-no">·</td>`;
    });
    o += "</tr>";
  });
  o += "</table></div>";
  if (tvS.cell) { const [i, c] = tvS.cell; o += `<div class="tv-panel"><b>${tvLab(c)}: ${esc(g[i].label)}</b><div>${esc(tvSnip(g[i], c))}</div></div>`; }
  return o;
}

function tvTopic() {
  const g = tvDay().groups;
  if (!g.length) return `<div class="tv-bar">${tvDaySel()}</div><p>Brak tematów.</p>`;
  const x = g[Math.min(tvS.topic, g.length - 1)];
  let o = `<div class="tv-bar">${tvDaySel()}<select data-set="topic">${g.map((t, i) => `<option value="${i}" ${i === tvS.topic ? "selected" : ""}>${esc(t.label)} (${t.channels.length})</option>`).join("")}</select></div>`;
  o += `<p class="hint">Jedno zdarzenie, wiele stacji: zdanie z raportu każdej stacji, według regionów. Na dole stacje, w których raporcie ta nazwa nie pada.</p>`;
  TV.blocs.forEach(b => {
    const on = b.kanaly.filter(c => x.channels.includes(c));
    if (on.length) o += `<div class="tv-bl">${esc(b.nazwa)}</div><div class="tv-cards">` + on.map(c => `<div class="tv-card"><b>${tvLab(c)}</b>${esc(tvSnip(x, c))}</div>`).join("") + "</div>";
  });
  const off = TV_ORDER.filter(c => tvDay().reports[c] && !x.channels.includes(c));
  return o + `<div class="tv-bl">Nie wspominają (według raportów)</div><div class="tv-small">${off.map(c => esc(TV_CH[c].nazwa)).join(", ") || "—"}</div>`;
}

function tvPair() {
  const d = tvDay(), A = tvS.a, B = tvS.b, ra = d.reports[A], rb = d.reports[B];
  let o = `<div class="tv-bar">${tvDaySel()} ${tvChSel("a")} <span>i</span> ${tvChSel("b")}</div>`;
  if (!ra || !rb) return o + "<p>Brak raportu jednej ze stacji.</p>";
  o += `<div class="tv-two">` + [[A, ra], [B, rb]].map(([c, r]) => `<div class="tv-card"><b>${tvLab(c)}</b><div class="tv-t">${esc(tvTitle(r))}</div><p>${esc(tvGlance(r))}</p></div>`).join("") + "</div>";
  const na = d.names[A] || {}, nb = d.names[B] || {}, n = Object.keys(d.reports).length;
  const rare = k => d.df[k] <= Math.ceil(n / 2);   // pomijamy nazwy obecne w większości stacji
  const shared = Object.keys(na).filter(k => nb[k] && rare(k))
    .sort((x, y) => d.df[x] - d.df[y] || Math.min(nb[y], na[y]) - Math.min(nb[x], na[x])).slice(0, 18);
  o += `<h3>Wspólne nazwy: to samo, dwa ujęcia</h3><p class="hint">Najpierw nazwy rzadkie tego dnia (w najmniejszej liczbie stacji); pomijamy obecne w ponad połowie stacji.</p>`;
  o += `<div class="tv-scroll"><table class="tv-pair"><tr><th></th><th>${esc(TV_CH[A].nazwa)}</th><th>${esc(TV_CH[B].nazwa)}</th></tr>` +
    shared.map(k => `<tr><td class="tv-k">${esc(d.display[k])}</td><td>${esc(tvSentence(A, k))}</td><td>${esc(tvSentence(B, k))}</td></tr>`).join("") + "</table></div>";
  const only = (x, y) => Object.keys(x).filter(k => !y[k] && rare(k)).sort((p, q) => x[q] - x[p]).slice(0, 14)
    .map(k => tvChip(d.display[k], ` <span class="tv-small">${x[k]}</span>`)).join("");
  return o + `<div class="tv-two"><div><h3>Tylko ${esc(TV_CH[A].nazwa)}</h3>${only(na, nb)}</div><div><h3>Tylko ${esc(TV_CH[B].nazwa)}</h3>${only(nb, na)}</div></div>`;
}

function tvDiary() {
  let o = `<div class="tv-bar">${tvChSel("ch")}<span class="hint">Dzień po dniu: tytuł raportu, początek streszczenia i nazwy nowe w tej stacji (co najmniej 2 razy, dzień wcześniej 0). Kliknij nazwę, żeby zobaczyć ją we wszystkich stacjach.</span></div>`;
  TV.days.forEach(d => {
    const r = TV.data[d].reports[tvS.ch];
    if (!r) return;
    const pdf = TV.pdf.replace("{day}", d.replaceAll("-", "")).replace("{code}", tvS.ch);
    o += `<div class="tv-day"><div class="tv-small">${fmtDay(d)} · wydań: ${r.shows} · <a href="${esc(pdf)}" target="_blank" rel="noopener">PDF</a></div><div class="tv-t">${esc(tvTitle(r))}</div><p>${esc(tvGlance(r))}</p><div>` +
      (TV.data[d].diary[tvS.ch] || []).map(n => tvChip(n)).join("") + "</div></div>";
  });
  return o;
}

function tvSearch() {
  return `<div class="tv-bar"><input id="tv-q" type="search" placeholder="fraza, np. Starlink, Bucha, Jarosław" value="${esc(tvS.q)}" size="34"><span class="hint">Szuka w wersji polskiej i angielskiej (np. Bucza albo Bucha); wielkość liter i znaki diakrytyczne bez znaczenia.</span></div><div id="tv-res"></div>`;
}
function tvResults() {
  const el = document.getElementById("tv-res"), q = tvS.q.trim();
  if (!el) return;
  if (q.length < 3) { el.innerHTML = ""; return; }
  const nq = tvNorm(q);
  let o = "", total = 0;
  TV.days.forEach(d => {
    let part = "";
    TV_ORDER.forEach(c => {
      const r = TV.data[d].reports[c];
      if (!r) return;
      const hits = r.sentences.map((s, i) => i).filter(i => tvNorm(r.sentences[i]).includes(nq)
        || (r.sentences_pl && r.sentences_pl[i] && tvNorm(r.sentences_pl[i]).includes(nq)));
      if (!hits.length) return;
      total += hits.length;
      part += `<div class="tv-hit"><b>${esc(TV_CH[c].nazwa)}</b> <span class="tv-small">${esc(TV_CH[c].kraj)}</span>: ${tvMark(tvText(r, hits[0]), q)}${hits.length > 1 ? ` <span class="tv-small">(+${hits.length - 1})</span>` : ""}</div>`;
    });
    if (part) o += `<div class="tv-day"><div class="tv-t">${fmtDay(d)}</div>${part}</div>`;
  });
  el.innerHTML = (total ? `<p class="hint">${total} zdań</p>` : "<p>Brak.</p>") + o;
}

function tvDraw() {
  if (!TV.days.length) {
    app.innerHTML = `<h1>Telewizja</h1><p class="lede">Brak raportów telewizyjnych w tej budowie strony (plx site bez --bez-tv pobiera ostatni tydzień).</p>`;
    return;
  }
  history.replaceState(null, "", "#" + tvS.tab);
  const view = { stories: tvStories, board: tvBoard, topic: tvTopic, pair: tvPair, diary: tvDiary, search: tvSearch }[tvS.tab]();
  app.innerHTML = `<h1>Telewizja</h1>
<p class="lede">Raporty GDELT „Today's Media Trends”: model (Gemini) streszcza po angielsku dzień wydań każdej z 17 stacji z archiwum TV News Archive. Na początek historie dnia, niżej widoki robocze.</p>
<p class="hint">Zdanie to słowa raportu, nie stacji: przed użyciem sprawdzić w transkrypcji wydania (Visual Explorer). Brak wzmianki w raporcie nie dowodzi, że stacja milczała. Wersja polska to tłumaczenie maszynowe; EN pokazuje oryginał raportu.</p>
<div class="tv-top"><nav class="tv-tabs">${TV_TABS.map(([k, n]) => `<button class="${tvS.tab === k ? "on" : ""}" data-tab="${k}">${n}</button>`).join("")}</nav>
<div class="tv-lang" role="group" aria-label="Język">${[["pl", "PL"], ["en", "EN"]].map(([k, n]) => `<button class="${tvLang === k ? "on" : ""}" data-lang="${k}" title="${k === "pl" ? "tłumaczenie na polski" : "oryginał raportu (angielski)"}">${n}</button>`).join("")}</div></div>
<div class="tv-view">${view}</div>`;
  if (tvS.tab === "search") {
    tvResults();
    const i = document.getElementById("tv-q");
    i.focus(); i.setSelectionRange(i.value.length, i.value.length);
  }
}

app.addEventListener("click", e => {
  const t = e.target.closest("[data-tab],[data-cell],[data-topic-i],[data-q],[data-lang],[data-more]");
  if (!t) return;
  e.preventDefault();
  if (t.dataset.lang) {
    tvLang = t.dataset.lang;
    try { localStorage.setItem("plx-tv-lang", tvLang); } catch (err) { /* file:// */ }
  } else if (t.dataset.tab) tvS.tab = t.dataset.tab;
  else if (t.dataset.cell) { const [i, c] = t.dataset.cell.split("|"); tvS.cell = [+i, c]; }
  else if (t.dataset.topicI) { tvS.tab = "topic"; tvS.topic = +t.dataset.topicI; }
  else if (t.dataset.q) { tvS.tab = "search"; tvS.q = t.dataset.q; }
  else if (t.dataset.more) tvS.more = true;
  tvDraw();
});
app.addEventListener("change", e => {
  const k = e.target.dataset.set;
  if (!k) return;
  tvS[k] = k === "topic" ? +e.target.value : e.target.value;
  if (k === "day") { tvS.topic = 0; tvS.cell = null; tvS.more = false; }
  tvDraw();
});
app.addEventListener("input", e => {
  if (e.target.id !== "tv-q") return;
  tvS.q = e.target.value;
  clearTimeout(tvS.timer);
  tvS.timer = setTimeout(tvResults, 250);
});
tvDraw();
