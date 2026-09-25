// Strona startowa: lista kart zdarzeń i dni dziennika.
const FORMA = { dwie_opowiesci: "dwie opowieści", kilka_perspektyw: "kilka perspektyw", os_czasu: "oś czasu" };
const state = { rejected: false };

function render() {
  const evs = DATA.zdarzenia.filter(e => state.rejected || e.status !== "odrzucony");
  const hidden = DATA.zdarzenia.length - evs.length;
  app.innerHTML = `<h1>Paralaksa</h1>
    <p class="muted">Jedno zdarzenie, wiele opowieści. Wersja wewnętrzna do oceny, zbudowana ${esc(DATA.zbudowano)}.</p>
    <h2 id="zdarzenia">Zdarzenia <span class="muted small">(${DATA.zdarzenia.length} kart)</span></h2>
    <div class="filters"><label><input type="checkbox" id="rej" ${state.rejected ? "checked" : ""}> pokaż odrzucone${hidden ? ` (${hidden})` : ""}</label></div>
    <div class="list-events">${evs.map(e => `<a class="box-card ${e.status === "odrzucony" ? "rejected" : ""}" href="zdarzenia/${esc(e.id)}.html">
      <div class="meta"><span>${esc(e.id.slice(0, 10))}</span><span>${esc(FORMA[e.forma] || e.forma)}</span>
        ${e.status === "odrzucony" ? `<span class="pill warn">odrzucony</span>` : ""}${e.watki ? `<span class="pill typ">${e.watki} wątków</span>` : ""}</div>
      <div class="t">${esc(e.tytul)}</div>
      <div class="small muted">${e.n_relacji} relacji, ${e.n_kontrastow} kontrastów · ${e.kraje.map(c => esc(c)).join(" ")}</div></a>`).join("")}</div>
    <h2 id="dziennik">Dziennik <span class="muted small">(automatyczny przebieg dzienny)</span></h2>
    ${DATA.dni.length ? `<table class="days"><thead><tr><th>dzień</th><th>przebieg</th><th>artykuły w oknie</th><th>kraje</th><th>sygnały</th><th>koszt</th></tr></thead>
      <tbody>${DATA.dni.map(d => `<tr><td><a href="dziennik/${esc(d.dzien)}.html">${esc(d.dzien)}</a></td><td>${esc(d.status)}${d.raport ? "" : ", bez raportu"}</td>
        <td>${d.artykuly} z ${d.pobrane}</td><td>${d.kraje.length} <span class="muted small">${esc(d.kraje.join(" "))}</span></td><td>${d.sygnaly}</td><td>${d.koszt.toFixed(2)} $</td></tr>`).join("")}</tbody></table>`
      : `<p class="muted">Brak bazy przy budowie strony.</p>`}`;
}
app.addEventListener("change", e => { if (e.target.id === "rej") { state.rejected = e.target.checked; render(); } });
render();
