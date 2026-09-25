// Karta zdarzenia: wątki, oś czasu, kraje, opis; kontrasty podświetlają relacje we wszystkich widokach.
const EV = DATA;
const PALETTE = ["#2f6fb0", "#c0392b", "#d9822b", "#2d7a3e", "#7b4fa0", "#0f8b8d", "#a0522d", "#b03a7a", "#556b2f"];
const threadOf = {};
EV.watki.forEach((w, i) => { w.kolor = PALETTE[i % PALETTE.length]; threadOf[w.id] = w; });
const state = {
  tab: EV.kontrasty.length ? "zestawienia" : EV.watki.length ? "watki" : (EV.forma === "os_czasu" ? "os" : "kraje"),
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

const REL = new Map(EV.relacje.map(r => [r.id, r]));
function headline(r) { return state.lang === "pl" ? (r.tlumaczenie || r.naglowek) : (r.naglowek || r.tlumaczenie); }
function altHeadline(r) { const a = state.lang === "pl" ? r.naglowek : r.tlumaczenie; return a && a !== headline(r) ? a : ""; }
function relRef(id) {
  const r = REL.get(id);
  if (!r) return `<span class="ref">${esc(id)}</span>`;
  return `<span class="ref" role="button" tabindex="0" data-jump="${esc(r.id)}" title="${esc(r.id)} · ${esc(r.tlumaczenie || r.naglowek)}"><b>${esc(r.kraj)}</b> ${esc(r.kto)}</span>`;
}
function pubTime(r) {
  if (r.t != null) return fmtTime(r.t, state.zone);
  return r.publikacja ? esc(r.publikacja) : "<span title='godzina publikacji nieustalona'>bez godziny</span>";
}
function sourceHead(r) {
  const extra = [
    r.gatunek && r.gatunek !== "wiadomosc" ? `<span class="pill">${esc(r.gatunek.replace(/_/g, " "))}</span>` : "",
    r.rola && r.rola !== "redakcja" ? `<span class="pill">${esc(r.rola.replace(/_/g, " "))}</span>` : "",
  ].join("");
  return `${cc(r.kraj)} <span class="kto">${esc(r.kto)}</span> ${mediaTag(r.typ)} ${extra}`;
}

function relCard(r) {
  const w = r.watek && threadOf[r.watek];
  const alt = altHeadline(r);
  const foot = [`<span>${pubTime(r)}${r.tu != null ? ` · akt. ${fmtTime(r.tu, state.zone)}` : ""}</span>`, link(r.link, "źródło")];
  foot.push(r.archiwum ? link(r.archiwum, "kopia" + (r.archiwum_czas ? " " + r.archiwum_czas.slice(5, 16).replace("T", " ") : "")) : "<span>brak kopii</span>");
  if (r.baza && EV.dni_bazy.includes(r.baza.day)) foot.push(`<a href="${ROOT}dziennik/${r.baza.day}.html#a${r.baza.id}">w dzienniku</a>`);
  if (r.czlowiek) foot.push(`<span class="pill human" title="${esc(r.sprawdzil)}">sprawdził człowiek</span>`);
  else if (r.sprawdzil) foot.push(`<span class="who" title="${esc(r.sprawdzil)}${r.wersja ? "\nWersja: " + esc(r.wersja) : ""}">jak sprawdzono</span>`);
  foot.push(`<span class="rid">${esc(r.id)}</span>`);
  return `<div class="rel" data-rid="${esc(r.id)}" ${w ? `style="border-top:3px solid ${w.kolor}"` : ""}>
    <div class="head">${sourceHead(r)}</div>
    <div class="hl">${esc(headline(r))}</div>
    ${alt ? `<div class="alt">${esc(alt)}</div>` : ""}
    ${r.zostawia_z ? `<div class="leave"><b>Zostawia z</b>${esc(r.zostawia_z)}</div>` : ""}
    <div class="foot">${foot.join("")}</div></div>`;
}

// --- widoki -------------------------------------------------------------------------------------------------------

function viewPairs() {
  if (!EV.kontrasty.length) return `<div class="notice">Karta nie ma jeszcze kontrastów.</div>`;
  return `<p class="hint">Nagłówki zestawione tak, jak porównuje je karta: obok siebie, z informacją, co czytelnik z nich wynosi.
      Pod spodem opis różnicy i zastrzeżenia. Kliknij nazwę redakcji, żeby zobaczyć pełną relację.</p>` +
    EV.kontrasty.map((k, i) => {
      const rels = k.miedzy.map(id => REL.get(id)).filter(Boolean);
      return `<section class="pair">
        <div class="pair-top"><span class="kind">${esc(RODZAJ[k.rodzaj] || k.rodzaj || "kontrast")}</span><span class="num">${i + 1} z ${EV.kontrasty.length}</span></div>
        <div class="pair-cols">${rels.map(r => { const alt = altHeadline(r); return `<div>
          <div class="small" style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">${cc(r.kraj)} <a href="#" data-show="${esc(r.id)}"><b>${esc(r.kto)}</b></a> ${mediaTag(r.typ)}</div>
          <div class="hl">${esc(headline(r))}</div>${alt ? `<div class="alt">${esc(alt)}</div>` : ""}
          ${r.zostawia_z ? `<div class="leave"><span class="muted">Zostawia z:</span> ${esc(r.zostawia_z)}</div>` : ""}
          <div class="when">${pubTime(r)} · ${link(r.link, "źródło")}</div></div>`; }).join("")}</div>
        <div class="why">${esc(k.opis || "")}</div>
        ${k.zastrzezenia ? `<div class="caveat"><b>Zastrzeżenia:</b> ${esc(k.zastrzezenia)}</div>` : ""}</section>`;
    }).join("");
}

function viewThreads() {
  if (!EV.watki.length)
    return `<div class="notice">Karta nie ma jeszcze wątków (pole <code>watki</code> i <code>watek</code> przy relacjach). Poniżej układ według krajów.</div>` + viewCountries();
  const cols = EV.watki.map(w => ({ w, rels: EV.relacje.filter(r => r.watek === w.id).sort(byTime) }));
  const loose = EV.relacje.filter(r => !r.watek || !threadOf[r.watek]).sort(byTime);
  if (loose.length) cols.push({ w: { id: "", nazwa: "Bez wątku", opis: "Relacje, których nie przypisano do żadnej opowieści.", kolor: "#999" }, rels: loose });
  const countries = countriesInOrder();
  const matrix = `<div class="matrix-wrap"><table class="heat matrix"><thead><tr><th class="theme"></th>${countries.map(c => `<th title="${esc(countryName(c))}">${cc(c)}</th>`).join("")}</tr></thead>
    <tbody>${cols.map(({ w, rels }) => `<tr><th class="theme"><span class="st" style="background:${w.kolor}"></span>${esc(w.nazwa)}</th>${countries.map(c => {
      const here = rels.filter(r => r.kraj === c);
      return here.length ? `<td style="background:${w.kolor}1f">${here.map(r => `<span class="ref" role="button" tabindex="0" data-jump="${esc(r.id)}" title="${esc(r.id)} · ${esc(r.tlumaczenie || r.naglowek)}">${esc(r.kto)}</span>`).join("")}</td>` : `<td class="empty"></td>`;
    }).join("")}</tr>`).join("")}</tbody></table></div>`;
  return `<p class="hint">Wątek to opowieść, czyli to, od czego zaczyna nagłówek. Tabela pokazuje, która opowieść pojawia się w którym kraju; kliknij redakcję, żeby przejść do jej nagłówka.</p>${matrix}
    ${cols.map(({ w, rels }) => `<section class="thread">
      <div class="thread-head" style="border-top-color:${w.kolor}"><h3 style="color:${w.kolor}">${esc(w.nazwa)}</h3>
        <span class="desc">${esc(w.opis || "")}</span><span class="countries">${[...new Set(rels.map(r => r.kraj))].map(c => cc(c)).join("")}</span></div>
      <div class="cards">${rels.map(relCard).join("")}</div></section>`).join("")}`;
}

function viewCountries() {
  return `<div class="grid-countries">${countriesInOrder().map(c => {
    const rels = EV.relacje.filter(r => r.kraj === c).sort(byTime);
    return `<section class="country-row"><h3>${cc(c)} ${esc(countryName(c))} <span class="muted small">${rels.length}</span></h3>
      <div class="cards">${rels.map(relCard).join("")}</div></section>`;
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
  const avail = window.innerWidth < 1100 ? window.innerWidth - 56 : Math.min(window.innerWidth, 1400) - 56 - 348;
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
    const bg = li % 2 ? "" : `<rect x="0" y="${l.y - 8}" width="${W}" height="${l.rows * ROW + 16}" style="fill:var(--inset)"/>`;
    const dots = l.items.map(it => {
      const cy = l.y + 6 + it.row * ROW;
      if (it.kind === "r") {
        const r = it.r, w = r.watek && threadOf[r.watek], col = w ? w.kolor : "#555";
        const upd = r.tu != null && r.tu !== r.t ? `<line class="upd" x1="${x(r.t)}" x2="${x(r.tu)}" y1="${cy}" y2="${cy}"/><circle cx="${x(r.tu)}" cy="${cy}" r="3.5" style="fill:var(--card)" stroke="${col}"/>` : "";
        return `<g class="dot" data-rid="${esc(r.id)}">${upd}<circle cx="${it.x}" cy="${cy}" r="6.5" fill="${col}"/>
          <text x="${it.x + 10}" y="${cy + 4}">${esc(it.label)}</text><title>${esc(r.id)} · ${esc(r.kto)}: ${esc(r.tlumaczenie || r.naglowek)}</title></g>`;
      }
      const col = it.kind === "f" ? "var(--ink)" : "#888";
      const tip = it.kind === "f" ? (EV.fakt.opis || "") : (it.o.co_wiadomo || "");
      return `<g class="dot fact-dot"><rect x="${it.x - 5}" y="${cy - 5}" width="10" height="10" style="fill:${col}" transform="rotate(45 ${it.x} ${cy})"/>
        <text x="${it.x + 10}" y="${cy + 4}">${esc(it.label)}</text><title>${esc(tip)}</title></g>`;
    }).join("");
    return `${bg}<text class="lane-label" x="8" y="${l.y + 10}">${esc(l.name.length > 22 ? l.name.slice(0, 21) + "…" : l.name)}</text>${dots}`;
  }).join("");
  const legend = EV.watki.length ? `<div class="legend">${EV.watki.map(w => `<span><span class="st" style="background:${w.kolor}"></span>${esc(w.nazwa)}</span>`).join("")}</div>` : "";
  const undated = EV.relacje.filter(r => r.t == null);
  const kn = EV.os_czasu.length ? `<h3>Stan wiedzy w czasie</h3><ol class="small">${EV.os_czasu.map(o => `<li><strong>${o.t != null ? fmtTime(o.t, state.zone) : esc(o.czas || "")}</strong> ${esc(o.co_wiadomo)} <span class="muted">(${/^r\d+$/.test(o.zrodlo || "") ? esc(o.zrodlo) : link(o.zrodlo, "źródło")})</span></li>`).join("")}</ol>` : "";
  return `<p class="hint">Kropka to publikacja, puste kółko na końcu przerywanej linii to aktualizacja. Kolor to wątek. Kliknij kropkę, żeby zobaczyć relację.</p>${legend}
    <div class="tl-wrap"><svg class="tl" width="${W}" height="${H}"><defs><pattern id="brk" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="3" height="8" style="fill:var(--grid)"/></pattern></defs><g class="grid">${grid}</g><g class="axis">${axis}${breaks}</g>${body}</svg></div>
    ${undated.length ? `<div class="tl-undated"><span class="muted">Bez godziny publikacji:</span> ${undated.map(r => `<a href="#" data-pick="${esc(r.id)}">${esc(r.id)} ${esc(r.kto)}</a>`).join(", ")}</div>` : ""}
    <div class="tl-detail" id="tl-detail">${state.picked ? relCard(EV.relacje.find(r => r.id === state.picked)) : ""}</div>${kn}`;
}

function viewText() {
  const search = EV.jak_szukano.length ? `<h3>Jak szukano</h3><ul class="small">${EV.jak_szukano.map(s => `<li>${esc(s)}</li>`).join("")}</ul>` : "";
  return `<div class="prose">${EV.opis_html}${search}</div>`;
}

// --- kontrasty ----------------------------------------------------------------------------------------------------

function sideContrasts() {
  if (!EV.kontrasty.length) return `<h2>Kontrasty</h2><p class="muted small">Brak.</p>`;
  return `<h2>Kontrasty · ${EV.kontrasty.length}</h2>
    <p class="muted small">Kliknij, żeby podświetlić porównywane relacje.</p>
    ${EV.kontrasty.map((k, i) => `<div class="contrast ${state.contrast === i ? "on" : ""}" role="button" tabindex="0" data-contrast="${i}">
      <div class="ids"><span class="pill">${esc(RODZAJ[k.rodzaj] || k.rodzaj || "")}</span>${k.miedzy.map(id => { const r = REL.get(id); return r ? `${cc(r.kraj)}<span>${esc(r.kto)}</span>` : esc(id); }).join(" ")}</div>
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
  return `<div class="meta"><span>${fmtDay(EV.id)}</span><span>${esc(FORMA[EV.forma] || EV.forma)}</span>
      <span>${esc(EV.dziedzina.join(", ").replace(/_/g, " "))}</span>
      <span class="pill ${EV.status === "odrzucony" ? "warn" : ""}">${esc(EV.status)}</span></div>
    <h1>${esc(EV.tytul)}</h1>
    <div class="meta" style="margin-bottom:16px"><span>${n} relacji z ${nc} krajów</span><span class="chips">${countriesInOrder().map(c => cc(c)).join("")}</span>
      <span>${human ? `sprawdzone przez człowieka: ${human} z ${n}` : "człowiek nie sprawdził jeszcze żadnej relacji"}</span></div>
    ${EV.status === "odrzucony" ? `<div class="notice">Odrzucone: ${esc(EV.powod_odrzucenia || "")}</div>` : ""}
    <div class="fact"><div class="label">Co się stało${f.t != null ? ` <span class="when">· ${fmtTime(f.t, state.zone)}</span>` : ""}</div>${esc(f.opis || "")}
      ${f.zrodlo ? `<div class="small muted" style="margin-top:6px">Źródło pierwotne: ${/^https?:/.test(f.zrodlo) ? link(f.zrodlo, f.zrodlo) : esc(f.zrodlo)}</div>` : ""}</div>`;
}

const TABS = [["zestawienia", "Obok siebie", () => EV.kontrasty.length], ["watki", "Wątki", () => EV.watki.length],
  ["os", "Oś czasu"], ["kraje", "Kraje", () => new Set(EV.relacje.map(r => r.kraj)).size], ["opis", "Opis karty"]];
function seg(name, opts) {
  return `<span class="seg">${opts.map(([v, l]) => `<button data-${name}="${v}" class="${state[name] === v ? "on" : ""}">${l}</button>`).join("")}</span>`;
}
function render() {
  const views = { zestawienia: viewPairs, watki: viewThreads, os: viewTimeline, kraje: viewCountries, opis: viewText };
  const wide = state.tab === "zestawienia" || state.tab === "opis";
  app.innerHTML = `${header()}
    <div class="tabs">${TABS.map(([id, label, n]) => `<button data-tab="${id}" class="${state.tab === id ? "on" : ""}">${label}${n && n() ? `<span class="n">${n()}</span>` : ""}</button>`).join("")}
      <span class="spacer"></span>
      <div class="toggles">${seg("lang", [["pl", "tłumaczenie"], ["orig", "oryginał"]])}${seg("zone", [["local", "czas polski"], ["utc", "UTC"]])}</div></div>
    ${wide ? `<div id="view">${views[state.tab]()}</div>` : `<div class="layout"><div id="view">${views[state.tab]()}</div><aside class="side">${sideContrasts()}</aside></div>`}`;
  applyHighlight();
}

app.addEventListener("click", e => {
  const tab = e.target.closest("[data-tab]");
  if (tab) { state.tab = tab.dataset.tab; history.replaceState(null, "", "#" + state.tab); render(); return; }
  const sw = e.target.closest("[data-lang],[data-zone]");
  if (sw) { if (sw.dataset.lang) state.lang = sw.dataset.lang; if (sw.dataset.zone) state.zone = sw.dataset.zone; render(); return; }
  const show = e.target.closest("[data-show]");
  if (show) { e.preventDefault(); state.tab = "kraje"; history.replaceState(null, "", "#kraje"); render(); jumpTo(show.dataset.show); return; }
  const c = e.target.closest("[data-contrast]");
  if (c) { const i = +c.dataset.contrast; state.contrast = state.contrast === i ? null : i; render(); return; }
  const jump = e.target.closest("[data-jump]");
  if (jump) { jumpTo(jump.dataset.jump); return; }
  const pick = e.target.closest("[data-pick]") || (state.tab === "os" && e.target.closest("g.dot[data-rid]"));
  if (pick) {
    e.preventDefault();
    state.picked = pick.dataset.pick || pick.dataset.rid;
    document.getElementById("tl-detail").innerHTML = relCard(EV.relacje.find(r => r.id === state.picked));
    applyHighlight();
  }
});
function jumpTo(rid) {
  let el = document.querySelector(`#view .rel[data-rid="${rid}"]`);
  if (!el) { state.tab = "kraje"; history.replaceState(null, "", "#kraje"); render(); el = document.querySelector(`#view .rel[data-rid="${rid}"]`); }
  if (el) { el.scrollIntoView({ behavior: "smooth", block: "center" }); el.classList.add("lit"); setTimeout(() => applyHighlight(), 1600); }
}
const initial = location.hash.slice(1);
if (TABS.some(([id]) => id === initial)) state.tab = initial;
document.title = (EV.tytul || EV.id) + " · Paralaksa";
render();
