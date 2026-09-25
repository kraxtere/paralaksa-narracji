"use strict";
const DATA = JSON.parse(document.getElementById("data").textContent);
const ROOT = document.body.dataset.root || "";
const app = document.getElementById("app");

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function h(html) { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstElementChild; }
function cc(code, names) {
  const n = (names || DATA.kraje || {})[code];
  return `<span class="pill cc" title="${esc(n || code)}">${esc(code || "?")}</span>`;
}
function countryName(code) { return (DATA.kraje || {})[code] || code; }
const TZ = { local: "Europe/Warsaw", utc: "UTC" };
function fmtTime(ms, zone, withDate = true) {
  if (ms == null) return "";
  const o = { timeZone: TZ[zone] || zone, hour: "2-digit", minute: "2-digit" };
  if (withDate) Object.assign(o, { day: "numeric", month: "short" });
  return new Date(ms).toLocaleString("pl-PL", o) + (zone === "utc" ? " UTC" : "");
}
function link(url, label) { return url ? `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(label)}</a>` : ""; }
const STANCES = ["alarm", "krytyka", "neutralny", "poparcie", "uspokojenie"];
function stanceDot(st) { return `<span class="st st-${esc(st)}" title="${esc(st)}"></span>`; }
// typ medium: państwowe i prorządowe wyróżnione, bo zmieniają sposób czytania nagłówka
const MEDIA = { "państwowe": ["state", "państwowe"], "prorządowe": ["state", "prorządowe"], government: ["state", "rządowe"],
  state: ["state", "państwowe"], emigracyjne: ["exile", "emigracyjne"], publiczne: ["", "publiczne"], public: ["", "publiczne"],
  prywatne: ["", "prywatne"], private: ["", "prywatne"], agency: ["", "agencja"] };
function mediaTag(typ) {
  if (!typ) return "";
  const [cls, label] = MEDIA[typ] || ["", typ];
  return `<span class="tag ${cls}">${esc(label)}</span>`;
}
const MONTHS = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia", "września", "października", "listopada", "grudnia"];
function fmtDay(iso) {
  const [y, m, d] = String(iso).slice(0, 10).split("-").map(Number);
  return m ? `${d} ${MONTHS[m - 1]} ${y}` : esc(iso);
}
// elementy z role="button" działają też z klawiatury
document.addEventListener("keydown", e => {
  if ((e.key === "Enter" || e.key === " ") && e.target.matches && e.target.matches('[role="button"]')) { e.preventDefault(); e.target.click(); }
});
// tryb jasny/ciemny: stan ustawia skrypt w <head>, tu tylko przełącznik i jego podpis
const themeBtn = document.getElementById("theme");
function themeLabel() {
  const dark = document.documentElement.dataset.theme === "dark";
  themeBtn.querySelector(".lbl").textContent = dark ? "tryb jasny" : "tryb ciemny";
  themeBtn.setAttribute("aria-label", dark ? "Włącz tryb jasny" : "Włącz tryb ciemny");
}
themeBtn.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("plx-theme", next); } catch (e) { /* file:// bez localStorage: wybór tylko do przeładowania */ }
  themeLabel();
});
themeLabel();
