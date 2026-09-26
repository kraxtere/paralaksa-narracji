"""Working views built only on the TV reports (`tv.py`): one self-contained HTML file with five concepts side by side.

Board of the day (new names × channels), one topic across blocs (with who stays silent), two channels side by side,
one channel over the week, and a phrase search over every sentence. Draft views to decide what a TV page should be;
nothing here is published. Sentences are the reports' (Gemini) wording in English, not the channels' own."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

from paralaksa.gdelt import tv

BLOCS: list[tuple[str, list[str]]] = [
    ("Polska i Ukraina", ["TVPINFO", "ESPRESO"]),
    ("Rosja i Białoruś", ["RUSSIA1", "RUSSIA24", "1TV", "NTV", "BELARUSTV"]),
    ("Po rosyjsku spoza Rosji", ["CURRENTTIME"]),
    ("Europa", ["LRT", "DR1", "M1", "BBCNEWS", "FRANCE24"]),
    ("Bliski Wschód i Turcja", ["KAN11", "PRESSTV", "TRTWORLD"]),
    ("Chiny", ["CCTV13"]),
]
GLANCE = 520          # znaków streszczenia dnia w widokach
DIARY_NAMES = 8       # nowych nazw kanału na dzień
SHARED_MIN = 1        # nazwa w obu stacjach co najmniej tyle razy


def glance(text: str) -> str:
    """The first sentences of 'Day at a glance'."""
    part = text.split("MAJOR DEVELOPMENTS")[0].replace("DAY-AT -A-GLANCE", "").replace("DAY-AT-A-GLANCE", "").strip()
    out = ""
    for s in tv.sentences(part):
        if out and len(out) + len(s) > GLANCE:
            break
        out = f"{out} {s}".strip()
    return out


def day_data(today: dict[str, tv.Report], before: dict[str, tv.Report]) -> dict:
    names, counts = tv.vocabulary(today.values())
    _, counts_before = tv.vocabulary(before.values())
    forms: dict[str, Counter] = {}
    for r in today.values():
        for w in tv.WORD.findall(r.text):
            k = tv.key(w)
            if k in names:
                forms.setdefault(k, Counter())[w] += 1
    display = {k: c.most_common(1)[0][0] for k, c in forms.items() if c.most_common(1)[0][0][0].isupper()}
    diary = {}
    for code in today:
        prev = counts_before.get(code, Counter())
        fresh = [(n, k) for k, n in counts[code].items() if k in display and n >= 2 and not prev[k]] if before else []
        diary[code] = [display[k] for n, k in sorted(fresh, key=lambda x: (-x[0], x[1]))[:DIARY_NAMES]]
    return {
        "reports": {c: {"title": r.title, "glance": glance(r.text), "sentences": tv.sentences(r.text),
                        "shows": len(set(r.shows))} for c, r in today.items()},
        "groups": [{k: g[k] for k in ("label", "keys", "channels", "before", "snippets")}
                   for g in (tv.trends(today, before) if before else [])],
        "names": {c: {k: n for k, n in counts[c].items() if k in display and n >= SHARED_MIN} for c in today},
        "display": display,
        "df": {k: sum(1 for c in today if counts[c][k]) for k in display},
        "diary": diary,
    }


def build(days: list[str], cache: Path) -> dict:
    """Data for the views from cached reports; a day without cached reports is skipped."""
    load = {d: tv.load(d, tv.CHANNELS, cache, lambda url: None) for d in [tv.previous_day(days[0]), *days]}
    out = {}
    for d in days:
        if load[d]:
            out[d] = day_data(load[d], load[tv.previous_day(d)])
    return {
        "channels": {c: {"kraj": k, "nazwa": n} for c, (k, n) in tv.CHANNELS.items()},
        "blocs": [{"nazwa": b, "kanaly": cs} for b, cs in BLOCS],
        "days": sorted(out, reverse=True),
        "data": out,
        "pdf": tv.URL,
    }


def render(payload: dict) -> str:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return PAGE.replace("__DATA__", data)


PAGE = r"""<!doctype html>
<html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex, nofollow"><title>Telewizja: widoki robocze</title>
<style>
:root{--bg:#fbfaf7;--fg:#1c1c1a;--mut:#6b6a64;--line:#e2dfd6;--card:#fff;--acc:#e0643c;--acc2:#2f6f8f;--mark:#ffe7a3}
@media (prefers-color-scheme:dark){:root{--bg:#151513;--fg:#ecebe6;--mut:#9d9b93;--line:#33322e;--card:#1e1e1b;--acc:#f07a52;--acc2:#6fb3d2;--mark:#6a5410}}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif;background:var(--bg);color:var(--fg)}
header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);padding:10px 16px;z-index:5}
h1{font-size:17px;margin:0 0 6px}.note{color:var(--mut);font-size:13px}
nav{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}nav button,select,input{font:inherit;color:var(--fg);background:var(--card);border:1px solid var(--line);border-radius:8px;padding:5px 10px}
nav button.on{border-color:var(--acc);color:var(--acc);font-weight:600}
main{padding:16px;max-width:1200px;margin:0 auto}.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:12px}
.scroll{overflow-x:auto}table.board{border-collapse:collapse;font-size:13px}
.board th,.board td{border-bottom:1px solid var(--line);padding:4px 6px;text-align:center;white-space:nowrap}
.board th.topic,.board td.topic{text-align:left;white-space:normal;min-width:200px;max-width:300px}
.board .bloc{font-size:11px;color:var(--mut);font-weight:500}.board th.ch{writing-mode:vertical-rl;transform:rotate(180deg);font-weight:500;height:110px}
.dot{cursor:pointer;color:var(--acc);font-size:16px}.dot.sel{outline:2px solid var(--acc2);border-radius:50%}.no{color:var(--line)}
.panel{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:12px 0}
.bl{margin:18px 0 6px;font-size:12px;letter-spacing:.05em;text-transform:uppercase;color:var(--mut)}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:10px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}.card b{display:block;margin-bottom:4px}
.silent{color:var(--mut);font-size:13px}.two{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media (max-width:760px){.two{grid-template-columns:1fr}}
.pair td{vertical-align:top;border-bottom:1px solid var(--line);padding:8px 6px;font-size:13.5px}.pair td.k{font-weight:600;white-space:nowrap}
.chip{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:1px 9px;margin:2px 3px 2px 0;font-size:12.5px;cursor:pointer;background:var(--card)}
.chip:hover{border-color:var(--acc)}.day{border-left:3px solid var(--acc);padding-left:12px;margin:14px 0}.t{font-weight:600;font-size:13.5px}
a{color:var(--acc2)}mark{background:var(--mark);color:inherit}.hit{margin:4px 0 4px 0}.hit b{font-weight:600}.small{font-size:12.5px;color:var(--mut)}
</style></head><body>
<header><h1>Telewizja: widoki robocze</h1>
<div class="note">Dane: raporty GDELT „Today's Media Trends” (streszczenia dnia wydań kanału przez Gemini, po angielsku). Zdanie to słowa raportu, nie stacji: przed użyciem sprawdzić w transkrypcji (Visual Explorer). Brak wzmianki w raporcie nie dowodzi milczenia stacji.</div>
<nav id="tabs"></nav></header>
<main id="main"></main>
<script type="application/json" id="data">__DATA__</script>
<script>
const P=JSON.parse(document.getElementById("data").textContent);
const CH=P.channels, ORDER=P.blocs.flatMap(b=>b.kanaly);
const TABS=[["board","Tablica dnia"],["topic","Jeden temat"],["pair","Dwie stacje"],["diary","Kanał w czasie"],["search","Szukaj frazy"]];
const S={tab:"board",day:P.days[0],topic:0,cell:null,a:"RUSSIA24",b:"ESPRESO",ch:"TVPINFO",q:""};
{const h=location.hash.slice(1);if(TABS.some(t=>t[0]===h))S.tab=h}
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const norm=s=>s.normalize("NFKD").replace(/[̀-ͯ]/g,"").replace(/ł/g,"l").replace(/Ł/g,"L").toLowerCase();
const WORD=/[A-Za-zÀ-ɏ][A-Za-zÀ-ɏ0-9'’]*/g;
const key=w=>norm(w.replace(/['’]s$/,""));
const has=(s,k)=>(s.match(WORD)||[]).some(w=>key(w)===k);
const lab=c=>`${CH[c].nazwa} <span class="small">${CH[c].kraj}</span>`;
const D=()=>P.data[S.day];
function daySel(){return `<select onchange="S.day=this.value;S.topic=0;S.cell=null;draw()">${P.days.map(d=>`<option ${d===S.day?"selected":""}>${d}</option>`).join("")}</select>`}
function chSel(prop){return `<select onchange="S.${prop}=this.value;draw()">${ORDER.map(c=>`<option value="${c}" ${S[prop]===c?"selected":""}>${CH[c].nazwa} (${CH[c].kraj})</option>`).join("")}</select>`}
function mark(s,q){if(!q)return esc(s);const n=norm(s),i=n.indexOf(norm(q));if(i<0)return esc(s);return esc(s.slice(0,i))+"<mark>"+esc(s.slice(i,i+q.length))+"</mark>"+esc(s.slice(i+q.length))}
function sentenceWith(c,k){const r=D().reports[c];return r?(r.sentences.find(s=>has(s,k))||""):""}

function board(){
  const g=D().groups;
  if(!g.length)return `<div class="bar">${daySel()}</div><p>Brak nowych nazw (albo brak dnia poprzedniego do porównania).</p>`;
  let h=`<div class="bar">${daySel()}<span class="note">Wiersz: nazwa nowa w ≥3 stacjach (wczoraj ≤1). Kropka: raport stacji o niej wspomina; kliknij, żeby zobaczyć zdanie.</span></div><div class="scroll"><table class="board"><tr><th></th>`;
  P.blocs.forEach(b=>h+=`<th class="bloc" colspan="${b.kanaly.length}">${esc(b.nazwa)}</th>`);
  h+=`</tr><tr><th class="topic">nazwa (wczoraj)</th>`+ORDER.map(c=>`<th class="ch" title="${esc((D().reports[c]||{}).title||"brak raportu")}">${esc(CH[c].nazwa)}</th>`).join("")+"</tr>";
  g.forEach((x,i)=>{h+=`<tr><td class="topic"><a href="#" onclick="S.tab='topic';S.topic=${i};draw();return false">${esc(x.label)}</a> <span class="small">(${x.before})</span></td>`;
    ORDER.forEach(c=>{const on=x.channels.includes(c),sel=S.cell&&S.cell[0]===i&&S.cell[1]===c;
      h+=on?`<td><span class="dot ${sel?"sel":""}" onclick="S.cell=[${i},'${c}'];draw()">●</span></td>`:`<td class="no">·</td>`});h+="</tr>"});
  h+="</table></div>";
  if(S.cell){const [i,c]=S.cell;h+=`<div class="panel"><b>${lab(c)}: ${esc(g[i].label)}</b><div>${esc(g[i].snippets[c])}</div></div>`}
  return h}

function topic(){
  const g=D().groups;if(!g.length)return `<div class="bar">${daySel()}</div><p>Brak tematów.</p>`;
  const x=g[Math.min(S.topic,g.length-1)];
  let h=`<div class="bar">${daySel()}<select onchange="S.topic=+this.value;draw()">${g.map((t,i)=>`<option value="${i}" ${i===S.topic?"selected":""}>${esc(t.label)} (${t.channels.length})</option>`).join("")}</select></div>`;
  h+=`<p class="note">Jedno zdarzenie, wiele stacji: zdanie z raportu każdej stacji, pogrupowane regionami. Na dole stacje, w których raporcie ta nazwa nie pada.</p>`;
  P.blocs.forEach(b=>{const on=b.kanaly.filter(c=>x.channels.includes(c));if(!on.length)return;
    h+=`<div class="bl">${esc(b.nazwa)}</div><div class="cards">`+on.map(c=>`<div class="card"><b>${lab(c)}</b>${mark(x.snippets[c],"")}</div>`).join("")+"</div>"});
  const off=ORDER.filter(c=>D().reports[c]&&!x.channels.includes(c));
  h+=`<div class="bl">Nie wspominają (według raportów)</div><div class="silent">${off.map(c=>CH[c].nazwa).join(", ")||"—"}</div>`;
  return h}

function pair(){
  const d=D(),A=S.a,B=S.b,ra=d.reports[A],rb=d.reports[B];
  let h=`<div class="bar">${daySel()} ${chSel("a")} <span>vs</span> ${chSel("b")}</div>`;
  if(!ra||!rb)return h+"<p>Brak raportu jednej ze stacji.</p>";
  h+=`<div class="two">`+[[A,ra],[B,rb]].map(([c,r])=>`<div class="card"><b>${lab(c)}</b><div class="t">${esc(r.title)}</div><p>${esc(r.glance)}</p></div>`).join("")+"</div>";
  const na=d.names[A]||{},nb=d.names[B]||{};
  const n=Object.keys(d.reports).length,rare=k=>d.df[k]<=Math.ceil(n/2);   // pomijamy nazwy obecne w większości stacji
  const shared=Object.keys(na).filter(k=>nb[k]&&rare(k)).sort((x,y)=>d.df[x]-d.df[y]||Math.min(nb[y],na[y])-Math.min(nb[x],na[x])).slice(0,18);
  h+=`<h3>Wspólne nazwy: to samo, dwa ujęcia</h3><p class="note">Najpierw nazwy rzadkie tego dnia (w najmniejszej liczbie stacji); pomijamy obecne w ponad połowie stacji.</p><table class="pair">`+shared.map(k=>`<tr><td class="k">${esc(d.display[k])}</td><td>${esc(sentenceWith(A,k))}</td><td>${esc(sentenceWith(B,k))}</td></tr>`).join("")+"</table>";
  const only=(x,y)=>Object.keys(x).filter(k=>!y[k]&&rare(k)).sort((p,q)=>x[q]-x[p]).slice(0,14).map(k=>`<span class="chip" onclick="S.tab='search';S.q=${esc(JSON.stringify(d.display[k]))};draw()">${esc(d.display[k])} ${x[k]}</span>`).join("");
  h+=`<div class="two"><div><h3>Tylko ${esc(CH[A].nazwa)}</h3>${only(na,nb)}</div><div><h3>Tylko ${esc(CH[B].nazwa)}</h3>${only(nb,na)}</div></div>`;
  return h}

function diary(){
  let h=`<div class="bar">${chSel("ch")}<span class="note">Dzień po dniu: tytuł raportu, początek streszczenia i nazwy nowe w tej stacji (≥2 razy, dzień wcześniej 0). Kliknij nazwę, żeby zobaczyć ją we wszystkich stacjach.</span></div>`;
  P.days.forEach(d=>{const r=P.data[d].reports[S.ch];if(!r)return;
    h+=`<div class="day"><div class="small">${d} · wydań: ${r.shows} · <a href="${P.pdf.replace("{day}",d.replaceAll("-","")).replace("{code}",S.ch)}" target="_blank">PDF</a></div><div class="t">${esc(r.title)}</div><p>${esc(r.glance)}</p><div>`+
      (P.data[d].diary[S.ch]||[]).map(n=>`<span class="chip" onclick="S.tab='search';S.q=${esc(JSON.stringify(n))};draw()">${esc(n)}</span>`).join("")+"</div></div>"});
  return h}

function search(){
  let h=`<div class="bar"><input id="q" placeholder="fraza, np. Starlink, Bucha, Jarosław" value="${esc(S.q)}" size="34" oninput="S.q=this.value;clearTimeout(window.tq);window.tq=setTimeout(drawResults,250)"><span class="note">Wielkość liter i znaki diakrytyczne bez znaczenia. Raporty po angielsku.</span></div><div id="res"></div>`;
  return h}
function drawResults(){
  const q=S.q.trim(),el=document.getElementById("res");if(!el)return;if(q.length<3){el.innerHTML="";return}
  const nq=norm(q);let h="",total=0;
  P.days.forEach(d=>{let part="";ORDER.forEach(c=>{const r=P.data[d].reports[c];if(!r)return;const hits=r.sentences.filter(s=>norm(s).includes(nq));if(!hits.length)return;total+=hits.length;
    part+=`<div class="hit"><b>${esc(CH[c].nazwa)}</b> <span class="small">${CH[c].kraj}</span>: ${mark(hits[0],q)}${hits.length>1?` <span class="small">(+${hits.length-1})</span>`:""}</div>`});
    if(part)h+=`<div class="day"><div class="t">${d}</div>${part}</div>`});
  el.innerHTML=(total?`<p class="note">${total} zdań</p>`:"<p>Brak.</p>")+h}

function draw(){
  history.replaceState(null,"","#"+S.tab);
  document.getElementById("tabs").innerHTML=TABS.map(([k,n])=>`<button class="${S.tab===k?"on":""}" onclick="S.tab='${k}';draw()">${n}</button>`).join("");
  document.getElementById("main").innerHTML={board,topic,pair,diary,search}[S.tab]();
  if(S.tab==="search"){drawResults();const i=document.getElementById("q");i.focus();i.setSelectionRange(i.value.length,i.value.length)}}
draw();
</script></body></html>
"""
