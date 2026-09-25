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
