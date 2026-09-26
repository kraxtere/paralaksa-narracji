// Strona startowa: historie dnia i dziennik u góry, pod nimi karty zdarzeń (z zapowiedzią dwóch nagłówków).
const FORMA = { dwie_opowiesci: "dwie opowieści", kilka_perspektyw: "kilka perspektyw", os_czasu: "oś czasu" };
const state = { rejected: false };
const CAPS = ["Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"];

function evCard(e) {
  const vs = e.zapowiedz.length === 2 ? `<div class="vs">${e.zapowiedz.map(z => `<div>
      <div class="src">${cc(z.kraj)} <span>${esc(z.kto)}</span> ${mediaTag(z.typ)}</div>
      <div class="h">${esc(z.naglowek)}</div></div>`).join("")}</div>` : "";
  const counts = [`${e.n_relacji} relacji`, e.n_kontrastow ? `${e.n_kontrastow} kontrastów` : "", e.watki ? `${e.watki} wątków` : ""].filter(Boolean).join(" · ");
  return `<a class="ev ${e.status === "odrzucony" ? "rejected" : ""}" href="zdarzenia/${esc(e.id)}.html">
    <div class="meta"><span>${fmtDay(e.id)}</span><span>${esc(FORMA[e.forma] || e.forma || "")}</span>
      ${e.status === "odrzucony" ? `<span class="pill warn">odrzucony</span>` : ""}
      ${e.czlowiek ? `<span class="pill human">sprawdzone przez człowieka: ${e.czlowiek}</span>` : ""}</div>
    <div class="t">${esc(e.tytul)}</div>${vs}
    <div class="foot">${e.kraje.map(c => cc(c)).join("")}<span class="sep"></span><span>${counts}</span></div></a>`;
}

function groups(evs) {
  // bieżące zdarzenia według miesięcy, starsze przykłady razem
  const built = DATA.zbudowano.slice(0, 7), [by, bm] = built.split("-").map(Number);
  const out = [];
  evs.forEach(e => {
    const [y, m] = e.id.slice(0, 7).split("-").map(Number);
    const recent = (by - y) * 12 + (bm - m) <= 2;
    const label = recent ? `${CAPS[m - 1]} ${y}` : "Starsze przykłady";
    let g = out.find(g => g.label === label);
    if (!g) out.push(g = { label, items: [] });
    g.items.push(e);
  });
  return out;
}

const RECENT_DAYS = 7;

function dayRow(d) {
  return `<li><a href="dziennik/${esc(d.dzien)}.html" title="pobrano ${d.pobrane} · koszt ${d.koszt.toFixed(2)} $">
    <span class="d">${fmtDay(d.dzien)}</span><span class="n">${d.artykuly} art. · ${d.kraje.length} krajów · ${d.sygnaly} sygnałów</span>
    ${d.status === "inicjalny" ? `<span class="pill warn">inicjalny</span>` : ""}${d.raport ? "" : `<span class="pill warn">bez raportu</span>`}</a></li>`;
}

function daysPanel() {
  // dziennik u góry obok historii dnia: ostatni tydzień, starsze dni po rozwinięciu
  const head = `<div class="meta"><span>Dziennik</span><span>automatyczny przebieg dzienny</span></div>`;
  if (!DATA.dni.length) return `<div class="days-panel" id="dziennik">${head}<p class="small muted">Brak bazy przy budowie strony.</p></div>`;
  const older = DATA.dni.slice(RECENT_DAYS);
  return `<div class="days-panel" id="dziennik">${head}<ul>${DATA.dni.slice(0, RECENT_DAYS).map(dayRow).join("")}</ul>
    ${older.length ? `<details><summary class="small">starsze dni (${older.length})</summary><ul>${older.map(dayRow).join("")}</ul></details>` : ""}</div>`;
}

function latest() {
  const d = DATA.dni.find(d => d.historie && d.historie.length);
  if (!d) return "";
  return `<div class="latest"><div class="meta"><span>Dziennik, ${fmtDay(d.dzien)}</span><span>historie opisywane w wielu krajach</span></div>
    <ul>${d.historie.map(h => `<li><a href="dziennik/${esc(d.dzien)}.html">${esc(h.tytul)}</a><span class="chips">${h.kraje.map(c => cc(c)).join("")}</span></li>`).join("")}</ul>
    <div class="small" style="margin-top:6px"><a href="dziennik/${esc(d.dzien)}.html">wszystko z tego dnia →</a></div></div>`;
}

function render() {
  const evs = DATA.zdarzenia.filter(e => state.rejected || e.status !== "odrzucony");
  const hidden = DATA.zdarzenia.length - DATA.zdarzenia.filter(e => e.status !== "odrzucony").length;
  app.innerHTML = `<div class="intro"><h1>Paralaksa</h1>
    <p class="lede">Jedno zdarzenie, wiele opowieści. Zestawiamy nagłówki z różnych krajów i pokazujemy, od czego każda redakcja zaczyna.</p>
    <p class="small muted">Wersja wewnętrzna do oceny, zbudowana ${esc(DATA.zbudowano)}.</p></div>
    <div class="top-row ${latest() ? "" : "single"}">${latest()}${daysPanel()}</div>
    <h2 id="zdarzenia">Zdarzenia · ${DATA.zdarzenia.length - hidden}</h2>
    ${hidden ? `<div class="filters"><label><input type="checkbox" id="rej" ${state.rejected ? "checked" : ""}> pokaż odrzucone (${hidden})</label></div>` : ""}
    ${groups(evs).map(g => `<div class="month">${esc(g.label)}</div><div class="list-events">${g.items.map(evCard).join("")}</div>`).join("")}`;
}
app.addEventListener("change", e => { if (e.target.id === "rej") { state.rejected = e.target.checked; render(); } });
render();
