// Strona startowa: karty zdarzeń (z zapowiedzią dwóch nagłówków) i dni dziennika.
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

function dayCard(d) {
  return `<a class="day" href="dziennik/${esc(d.dzien)}.html">
    <div class="meta"><span class="pill ${d.status === "inicjalny" ? "warn" : ""}">${esc(d.status)}</span>${d.raport ? "" : `<span class="pill warn">bez raportu</span>`}</div>
    <div class="d">${fmtDay(d.dzien)}</div>
    <div class="nums"><div><b>${d.artykuly}</b><span>artykułów w oknie</span></div><div><b>${d.kraje.length}</b><span>krajów</span></div><div><b>${d.sygnaly}</b><span>sygnałów</span></div></div>
    <div class="small muted">${d.kraje.map(c => cc(c)).join(" ")}</div>
    <div class="small muted" style="margin-top:6px">pobrano ${d.pobrane} · koszt ${d.koszt.toFixed(2)} $</div></a>`;
}

function render() {
  const evs = DATA.zdarzenia.filter(e => state.rejected || e.status !== "odrzucony");
  const hidden = DATA.zdarzenia.length - DATA.zdarzenia.filter(e => e.status !== "odrzucony").length;
  app.innerHTML = `<div class="intro"><h1>Paralaksa</h1>
    <p class="lede">Jedno zdarzenie, wiele opowieści. Zestawiamy nagłówki z różnych krajów i pokazujemy, od czego każda redakcja zaczyna.</p>
    <p class="small muted">Wersja wewnętrzna do oceny, zbudowana ${esc(DATA.zbudowano)}.</p></div>
    <h2 id="zdarzenia">Zdarzenia · ${DATA.zdarzenia.length - hidden}</h2>
    ${hidden ? `<div class="filters"><label><input type="checkbox" id="rej" ${state.rejected ? "checked" : ""}> pokaż odrzucone (${hidden})</label></div>` : ""}
    ${groups(evs).map(g => `<div class="month">${esc(g.label)}</div><div class="list-events">${g.items.map(evCard).join("")}</div>`).join("")}
    <h2 id="dziennik">Dziennik · automatyczny przebieg dzienny</h2>
    ${DATA.dni.length ? `<div class="days-grid">${DATA.dni.map(dayCard).join("")}</div>` : `<p class="muted">Brak bazy przy budowie strony.</p>`}`;
}
app.addEventListener("change", e => { if (e.target.id === "rej") { state.rejected = e.target.checked; render(); } });
render();
