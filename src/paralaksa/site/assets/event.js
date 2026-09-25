// Karta zdarzenia: wątki, oś czasu, kraje, opis; kontrasty podświetlają relacje we wszystkich widokach.
const EV = DATA;
const PALETTE = ["#2f6fb0", "#c0392b", "#d9822b", "#2d7a3e", "#7b4fa0", "#0f8b8d", "#a0522d", "#b03a7a", "#556b2f"];
const threadOf = {};
EV.watki.forEach((w, i) => { w.kolor = PALETTE[i % PALETTE.length]; threadOf[w.id] = w; });
const state = {
  tab: EV.watki.length ? "watki" : (EV.forma === "os_czasu" ? "os" : "kraje"),
  lang: "pl", zone: "local", contrast: null, picked: null,
};
const RODZAJ = { dobor_slow: "dobór słów", czyj_glos: "czyj głos", pominiecie: "pominięcie", kolejnosc: "kolejność",
  kolejnosc_informacji: "kolejność informacji", rozne_interesy: "różne interesy",
  liczby: "liczby", ilustracja: "ilustracja", ton: "ton" };
const FORMA = { dwie_opowiesci: "dwie opowieści", kilka_perspektyw: "kilka perspektyw", os_czasu: "oś czasu" };

function byTime(a, b) { return (a.t ?? Infinity) - (b.t ?? Infinity); }
function countriesInOrder() {
  const seen = [];
  [...EV.relacje].sort(byTime).forEach(r => { if (!seen.includes(r.kraj)) seen.push(r.kraj); });
  return seen;
}

function relCard(r) {
  const main = state.lang === "pl" ? (r.tlumaczenie || r.naglowek) : (r.naglowek || r.tlumaczenie);
  const alt = state.lang === "pl" ? r.naglowek : r.tlumaczenie;
  const w = r.watek && threadOf[r.watek];
  const pills = [
    cc(r.kraj), `<span class="kto">${esc(r.kto)}</span>`,
    r.typ ? `<span class="pill typ">${esc(r.typ)}</span>` : "",
    r.gatunek && r.gatunek !== "wiadomosc" ? `<span class="pill">${esc(r.gatunek.replace(/_/g, " "))}</span>` : "",
    r.rola && r.rola !== "redakcja" ? `<span class="pill">${esc(r.rola.replace(/_/g, " "))}</span>` : "",
    r.czlowiek ? `<span class="pill human" title="${esc(r.sprawdzil)}">sprawdzone przez człowieka</span>` : "",
    `<span class="rid">${esc(r.id)}</span>`,
  ].join(" ");
  const times = [];
  if (r.t != null) times.push("opubl. " + fmtTime(r.t, state.zone));
  else if (r.publikacja) times.push("opubl. " + esc(r.publikacja));
  else times.push("<span title='godzina publikacji nieustalona'>bez godziny</span>");
  if (r.tu != null) times.push("akt. " + fmtTime(r.tu, state.zone));
  const links = [
    times.join(" · "),
    link(r.link, "źródło"),
    r.archiwum ? link(r.archiwum, "kopia" + (r.archiwum_czas ? " " + r.archiwum_czas.slice(0, 16).replace("T", " ") : "")) : "<span>brak kopii</span>",
  ];
  if (r.baza && EV.dni_bazy.includes(r.baza.day))
    links.push(`<a href="${ROOT}dziennik/${r.baza.day}.html#a${r.baza.id}">w naszej bazie (#${r.baza.id})</a>`);
  else if (r.baza) links.push(`<span>w naszej bazie (#${r.baza.id})</span>`);
  if (r.sprawdzil && !r.czlowiek) links.push(`<span title="${esc(r.wersja || "")}">sprawdził: ${esc(r.sprawdzil)}</span>`);
  return `<div class="rel" data-rid="${esc(r.id)}" ${w ? `style="border-left:4px solid ${w.kolor}"` : ""}>
    <div class="head">${pills}</div>
    <div class="hl">${esc(main)}</div>
    ${alt && alt !== main ? `<div class="alt">${esc(alt)}</div>` : ""}
    ${r.zostawia_z ? `<div class="leave"><span class="muted">Zostawia z:</span> ${esc(r.zostawia_z)}</div>` : ""}
    <div class="links">${links.join("")}</div></div>`;
}

// --- widoki -------------------------------------------------------------------------------------------------------

function viewThreads() {
  if (!EV.watki.length)
    return `<div class="notice">Karta nie ma jeszcze wątków (pole <code>watki</code> i <code>watek</code> przy relacjach). Poniżej układ według krajów.</div>` + viewCountries();
  const cols = EV.watki.map(w => ({ w, rels: EV.relacje.filter(r => r.watek === w.id).sort(byTime) }));
  const loose = EV.relacje.filter(r => !r.watek || !threadOf[r.watek]).sort(byTime);
  if (loose.length) cols.push({ w: { id: "", nazwa: "Bez wątku", opis: "Relacje, których nie przypisano do żadnej opowieści.", kolor: "#999" }, rels: loose });
  const countries = countriesInOrder();
  const matrix = `<div style="overflow-x:auto"><table class="heat matrix"><thead><tr><th class="theme">wątek / kraj</th>${countries.map(c => `<th title="${esc(countryName(c))}">${esc(c)}</th>`).join("")}</tr></thead>
    <tbody>${cols.map(({ w, rels }) => `<tr><th class="theme"><span class="st" style="background:${w.kolor}"></span>${esc(w.nazwa)}</th>${countries.map(c => {
      const here = rels.filter(r => r.kraj === c);
      return here.length ? `<td style="background:${w.kolor}22">${here.map(r => `<span class="ref" data-jump="${esc(r.id)}" title="${esc(r.kto)}: ${esc(r.tlumaczenie || r.naglowek)}">${esc(r.id)}</span>`).join(" ")}</td>` : `<td class="empty">·</td>`;
    }).join("")}</tr>`).join("")}</tbody></table></div>`;
  return `<p class="muted small">Zestawienie: która opowieść w którym kraju. Kliknij numer relacji, żeby przejść do niej niżej.</p>${matrix}
    <p class="muted small" style="margin-top:16px">Kolumna to opowieść, czyli to, od czego zaczyna nagłówek. W kolumnie relacje według godziny publikacji.</p>
    <div class="threads">${cols.map(({ w, rels }) => {
      const ccs = [...new Set(rels.map(r => r.kraj))].map(c => cc(c)).join("");
      return `<div class="thread"><h3 style="color:${w.kolor}">${esc(w.nazwa)} <span class="muted small">(${rels.length})</span></h3>
        <div class="desc">${esc(w.opis || "")}</div><div class="countries">${ccs}</div>${rels.map(relCard).join("")}</div>`;
    }).join("")}</div>`;
}

function viewCountries() {
  return `<div class="grid-countries">${countriesInOrder().map(c => {
    const rels = EV.relacje.filter(r => r.kraj === c).sort(byTime);
    return `<div><h3>${cc(c)} ${esc(countryName(c))} <span class="muted small">(${rels.length})</span></h3>${rels.map(relCard).join("")}</div>`;
  }).join("")}</div>`;
}

function viewTimeline() {
  const dated = EV.relacje.filter(r => r.t != null);
  const knowledge = EV.os_czasu.map((o, i) => ({ ...o, n: i + 1 })).filter(o => o.t != null);
  const times = dated.flatMap(r => [r.t, r.tu].filter(x => x != null)).concat(knowledge.map(o => o.t));
  if (EV.fakt.t != null) times.push(EV.fakt.t);
  if (!times.length) return `<div class="notice">Żadna relacja nie ma godziny publikacji.</div>`;
  // oś z przerwami: skupiska publikacji oddzielone dłuższą ciszą (> 12 h) dostają własny odcinek
  const GAP = 12 * 3600e3, PAD = 1800e3, BREAK = 70, LABEL_W = 150, RIGHT = 160;
  const segs = [];
  [...new Set(times)].sort((a, b) => a - b).forEach(t => {
    const last = segs[segs.length - 1];
    if (last && t - last.end <= GAP) last.end = t; else segs.push({ start: t, end: t });
  });
  segs.forEach(g => { g.start -= PAD; g.end += PAD; });
  const avail = window.innerWidth < 1000 ? window.innerWidth - 48 : Math.min(window.innerWidth, 1480) - 48 - 364;
  const dur = segs.reduce((a, g) => a + g.end - g.start, 0);
  const plot = Math.max(avail - LABEL_W - RIGHT - BREAK * (segs.length - 1), dur / 3600e3 * 14);
  const pxPerMs = plot / dur;
  let cursor = LABEL_W;
  segs.forEach(g => { g.x0 = cursor; g.x1 = cursor + (g.end - g.start) * pxPerMs; cursor = g.x1 + BREAK; });
  const W = cursor - BREAK + RIGHT;
  const x = t => { const g = segs.find(g => t >= g.start && t <= g.end) || segs[0]; return g.x0 + (t - g.start) * pxPerMs; };
  const ROW = 22;
  const lanes = [];
  if (knowledge.length || EV.fakt.t != null) {
    const items = knowledge.map(o => ({ kind: "k", t: o.t, label: "stan wiedzy " + o.n, o }));
    if (EV.fakt.t != null) items.unshift({ kind: "f", t: EV.fakt.t, label: "zdarzenie" });
    lanes.push({ name: "Fakt / stan wiedzy", items });
  }
  countriesInOrder().forEach(c => {
    const items = dated.filter(r => r.kraj === c).map(r => ({ kind: "r", t: r.t, r, label: r.kto.length > 22 ? r.kto.slice(0, 21) + "…" : r.kto }));
    if (items.length) lanes.push({ name: c + " · " + countryName(c), items });
  });
  // pakowanie etykiet w podwiersze pasa
  let y = 40;
  lanes.forEach(l => {
    const ends = [];
    l.items.sort((a, b) => a.t - b.t).forEach(it => {
      const x0 = x(it.t), w = 16 + it.label.length * 6.6;
      let row = ends.findIndex(e => e < x0 - 6);
      if (row < 0) { row = ends.length; ends.push(0); }
      ends[row] = x0 + w; it.row = row; it.x = x0;
    });
    l.y = y; l.rows = Math.max(1, ends.length); y += l.rows * ROW + 16;
  });
  const H = y + 4;
  const steps = [1, 2, 3, 6, 12, 24, 48, 72, 168].map(s => s * 3600e3);
  const step = steps.find(st => st * pxPerMs >= 95) || steps[steps.length - 1];
  const ticks = [];
  segs.forEach(g => { for (let t = Math.ceil(g.start / step) * step; t <= g.end; t += step) ticks.push(t); });
  if (!ticks.length) ticks.push(segs[0].start + PAD);
  const breaks = segs.slice(1).map((g, i) => {
    const prev = segs[i], days = (g.start - prev.end) / 86400e3;
    const label = days >= 1.5 ? `${Math.round(days)} dni` : `${Math.round(days * 24)} h`;
    const bx = (prev.x1 + g.x0) / 2;
    return `<rect x="${prev.x1 + 6}" y="30" width="${BREAK - 12}" height="${H - 30}" fill="url(#brk)"/><text x="${bx}" y="20" text-anchor="middle" class="brk">… ${label} …</text>`;
  }).join("");
  const grid = ticks.map(t => `<line x1="${x(t)}" x2="${x(t)}" y1="30" y2="${H}"/>`).join("");
  const axis = ticks.map(t => `<text x="${x(t)}" y="20" text-anchor="middle">${esc(fmtTime(t, state.zone))}</text>`).join("");
  const body = lanes.map((l, li) => {
    const bg = li % 2 ? "" : `<rect x="0" y="${l.y - 8}" width="${W}" height="${l.rows * ROW + 16}" fill="#faf9f6"/>`;
    const dots = l.items.map(it => {
      const cy = l.y + 6 + it.row * ROW;
      if (it.kind === "r") {
        const r = it.r, w = r.watek && threadOf[r.watek], col = w ? w.kolor : "#555";
        const upd = r.tu != null && r.tu !== r.t ? `<line class="upd" x1="${x(r.t)}" x2="${x(r.tu)}" y1="${cy}" y2="${cy}"/><circle cx="${x(r.tu)}" cy="${cy}" r="3.5" fill="#fff" stroke="${col}"/>` : "";
        return `<g class="dot" data-rid="${esc(r.id)}">${upd}<circle cx="${it.x}" cy="${cy}" r="6.5" fill="${col}"/>
          <text x="${it.x + 10}" y="${cy + 4}">${esc(it.label)}</text><title>${esc(r.id)} · ${esc(r.kto)}: ${esc(r.tlumaczenie || r.naglowek)}</title></g>`;
      }
      const col = it.kind === "f" ? "#1d1d1b" : "#888";
      const tip = it.kind === "f" ? (EV.fakt.opis || "") : (it.o.co_wiadomo || "");
      return `<g class="dot fact-dot"><rect x="${it.x - 5}" y="${cy - 5}" width="10" height="10" fill="${col}" transform="rotate(45 ${it.x} ${cy})"/>
        <text x="${it.x + 10}" y="${cy + 4}">${esc(it.label)}</text><title>${esc(tip)}</title></g>`;
    }).join("");
    return `${bg}<text class="lane-label" x="8" y="${l.y + 10}">${esc(l.name.length > 22 ? l.name.slice(0, 21) + "…" : l.name)}</text>${dots}`;
  }).join("");
  const legend = EV.watki.length ? `<div class="toggles" style="margin-bottom:6px">${EV.watki.map(w => `<span><span class="st" style="background:${w.kolor}"></span>${esc(w.nazwa)}</span>`).join("")}</div>` : "";
  const undated = EV.relacje.filter(r => r.t == null);
  const kn = EV.os_czasu.length ? `<h3>Stan wiedzy w czasie</h3><ol class="small">${EV.os_czasu.map(o => `<li><strong>${o.t != null ? fmtTime(o.t, state.zone) : esc(o.czas || "")}</strong> ${esc(o.co_wiadomo)} <span class="muted">(${/^r\d+$/.test(o.zrodlo || "") ? esc(o.zrodlo) : link(o.zrodlo, "źródło")})</span></li>`).join("")}</ol>` : "";
  return `<p class="muted small">Kropka to publikacja, puste kółko na końcu przerywanej linii to aktualizacja. Kolor to wątek. Kliknij kropkę, żeby zobaczyć relację.</p>${legend}
    <div class="tl-wrap"><svg class="tl" width="${W}" height="${H}"><defs><pattern id="brk" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="3" height="8" fill="#ecebe6"/></pattern></defs><g class="grid">${grid}</g><g class="axis">${axis}${breaks}</g>${body}</svg></div>
    ${undated.length ? `<div class="tl-undated"><span class="muted">Bez godziny publikacji:</span> ${undated.map(r => `<a href="#" data-pick="${esc(r.id)}">${esc(r.id)} ${esc(r.kto)}</a>`).join(", ")}</div>` : ""}
    <div class="tl-detail" id="tl-detail">${state.picked ? relCard(EV.relacje.find(r => r.id === state.picked)) : ""}</div>${kn}`;
}

function viewText() {
  const search = EV.jak_szukano.length ? `<h3>Jak szukano</h3><ul class="small">${EV.jak_szukano.map(s => `<li>${esc(s)}</li>`).join("")}</ul>` : "";
  return `<div class="prose">${EV.opis_html}${search}</div>`;
}

// --- kontrasty ----------------------------------------------------------------------------------------------------

function sideContrasts() {
  if (!EV.kontrasty.length) return `<h2 style="margin-top:0">Kontrasty</h2><p class="muted small">Brak.</p>`;
  return `<h2 style="margin-top:0">Kontrasty <span class="muted small">(${EV.kontrasty.length})</span></h2>
    <p class="muted small">Kliknij, żeby podświetlić porównywane relacje.</p>
    ${EV.kontrasty.map((k, i) => `<div class="contrast ${state.contrast === i ? "on" : ""}" data-contrast="${i}">
      <div class="ids">${esc(k.miedzy.join(" · "))} <span class="pill">${esc(RODZAJ[k.rodzaj] || k.rodzaj || "")}</span></div>
      <div>${esc(k.opis)}</div>${k.zastrzezenia ? `<div class="caveat">Zastrzeżenia: ${esc(k.zastrzezenia)}</div>` : ""}</div>`).join("")}`;
}

function applyHighlight() {
  const k = state.contrast != null ? EV.kontrasty[state.contrast] : null;
  const ids = new Set(k ? k.miedzy : []);
  document.querySelectorAll("#view [data-rid]").forEach(el => {
    el.classList.toggle("lit", !!k && ids.has(el.dataset.rid));
    el.classList.toggle("dim", !!k && !ids.has(el.dataset.rid));
  });
  if (k) {
    const first = document.querySelector("#view .rel.lit");
    if (first && state.tab !== "os") first.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
  }
}

// --- całość -------------------------------------------------------------------------------------------------------

function header() {
  const n = EV.relacje.length, nc = new Set(EV.relacje.map(r => r.kraj)).size;
  const human = EV.relacje.filter(r => r.czlowiek).length;
  const f = EV.fakt;
  return `<div class="meta"><span class="pill ${EV.status === "odrzucony" ? "warn" : ""}">${esc(EV.status)}</span>
      <span>${esc(FORMA[EV.forma] || EV.forma)}</span><span>${esc(EV.dziedzina.join(", ").replace(/_/g, " "))}</span>
      <span>${n} relacji z ${nc} krajów</span>
      <span>${human ? `sprawdzone przez człowieka: ${human} z ${n}` : "człowiek nie sprawdził jeszcze żadnej relacji"}</span></div>
    <h1>${esc(EV.tytul)}</h1>
    ${EV.status === "odrzucony" ? `<div class="notice">Odrzucone: ${esc(EV.powod_odrzucenia || "")}</div>` : ""}
    <div class="box-card fact"><strong>Fakt${f.t != null ? ", " + fmtTime(f.t, state.zone) : ""}.</strong> ${esc(f.opis || "")}
      ${f.zrodlo ? `<div class="small muted" style="margin-top:4px">Źródło pierwotne: ${/^https?:/.test(f.zrodlo) ? link(f.zrodlo, f.zrodlo) : esc(f.zrodlo)}</div>` : ""}</div>`;
}

const TABS = [["watki", "Wątki"], ["os", "Oś czasu"], ["kraje", "Kraje"], ["opis", "Opis karty"]];
function render() {
  const views = { watki: viewThreads, os: viewTimeline, kraje: viewCountries, opis: viewText };
  app.innerHTML = `${header()}
    <div class="tabs">${TABS.map(([id, label]) => `<button data-tab="${id}" class="${state.tab === id ? "on" : ""}">${label}</button>`).join("")}
      <span class="spacer"></span>
      <div class="toggles">
        <label><input type="radio" name="lang" value="pl" ${state.lang === "pl" ? "checked" : ""}> tłumaczenie</label>
        <label><input type="radio" name="lang" value="orig" ${state.lang === "orig" ? "checked" : ""}> oryginał</label>
        <label><input type="radio" name="zone" value="local" ${state.zone === "local" ? "checked" : ""}> czas polski</label>
        <label><input type="radio" name="zone" value="utc" ${state.zone === "utc" ? "checked" : ""}> UTC</label>
      </div></div>
    <div class="layout"><div id="view">${views[state.tab]()}</div><aside class="side">${sideContrasts()}</aside></div>`;
  applyHighlight();
}

app.addEventListener("click", e => {
  const tab = e.target.closest("[data-tab]");
  if (tab) { state.tab = tab.dataset.tab; history.replaceState(null, "", "#" + state.tab); render(); return; }
  const c = e.target.closest("[data-contrast]");
  if (c) { const i = +c.dataset.contrast; state.contrast = state.contrast === i ? null : i; render(); return; }
  const jump = e.target.closest("[data-jump]");
  if (jump) {
    const el = document.querySelector(`#view .rel[data-rid="${jump.dataset.jump}"]`);
    if (el) { el.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" }); el.classList.add("lit"); setTimeout(() => applyHighlight(), 1600); }
    return;
  }
  const pick = e.target.closest("[data-pick]") || (state.tab === "os" && e.target.closest("g.dot[data-rid]"));
  if (pick) {
    e.preventDefault();
    state.picked = pick.dataset.pick || pick.dataset.rid;
    document.getElementById("tl-detail").innerHTML = relCard(EV.relacje.find(r => r.id === state.picked));
    applyHighlight();
  }
});
app.addEventListener("change", e => {
  if (e.target.name === "lang") state.lang = e.target.value;
  if (e.target.name === "zone") state.zone = e.target.value;
  render();
});
const initial = location.hash.slice(1);
if (TABS.some(([id]) => id === initial)) state.tab = initial;
document.title = (EV.tytul || EV.id) + " · Paralaksa";
render();
