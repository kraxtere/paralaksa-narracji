"""Password-protected static server for the internal site (Render web service, standard library only).

Serves ./public to logged-in people only. The owner's credentials come from SITE_USER and SITE_PASSWORD; without them
every request gets 503, so a misconfigured deploy never exposes the site. Only the app manifest, icons, the login form
and invite links are served without logging in (browsers fetch the manifest and icons without credentials when
installing the app). Logging in sets a signed cookie for COOKIE_DAYS (works in in-app browsers and installed apps);
HTTP Basic Auth still works for scripts.

Other people get their own logins (konta.py): the owner adds them on /osoby, each gets a one-time invite link and sets
a password. Pages report reading time (a heartbeat every minute while the tab is visible, "h" when it is hidden); people,
invites and activity are kept in a private GitHub repo (ACTIVITY_TOKEN), because Render's free disk is wiped on every
sleep and deploy."""
from __future__ import annotations

import base64
import hashlib
import hmac
import html
import json
import os
import re
import signal
import sys
import threading
import time
import urllib.parse
from datetime import timedelta
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import konta  # noqa: E402

ROOT = Path(__file__).resolve().parent / "public"
USER = os.environ.get("SITE_USER", "")
PASSWORD = os.environ.get("SITE_PASSWORD", "")
PUBLIC = {"/manifest.webmanifest", "/icon-192.png", "/icon-512.png", "/icon-maskable-512.png", "/apple-touch-icon.png"}
EXPECTED = b"Basic " + base64.b64encode(f"{USER}:{PASSWORD}".encode()) if USER and PASSWORD else None
CSRF = hmac.new(PASSWORD.encode(), b"paralaksa-osoby", "sha256").hexdigest()[:32]
SECRET = hmac.new(PASSWORD.encode(), b"paralaksa-sesja", "sha256").digest()     # podpis ciasteczek logowania
OWNER_FP = hashlib.sha256(f"{USER}\0{PASSWORD}".encode()).hexdigest()           # zmiana hasła właściciela wylogowuje
COOKIE, COOKIE_DAYS = "plx", 90
STORE: "konta.Store | None" = None          # ustawiane w __main__ (konta.from_env) albo w testach
STORE_ERROR = "zapis kont nie został uruchomiony"
FLUSH_S = 180
FAIL_MAX, FAIL_WINDOW_S = 20, 900           # nieudane logowania z jednego adresu na kwadrans
FAILS: dict[str, list[float]] = {}
FAIL_LOCK = threading.Lock()
TITLES: dict[str, str] = {}                 # ścieżka strony -> <title>, do listy czytanych stron

HEARTBEAT = (b'<script>(()=>{let last="";const cur=()=>location.pathname+location.hash,send=k=>fetch("/_ping?k="+k+'
             b'"&p="+encodeURIComponent(cur()),{cache:"no-store",credentials:"same-origin",keepalive:true}).catch(()=>{}),'
             b'ping=()=>{if(document.visibilityState==="visible"){last=cur();send("p")}};'
             b'setInterval(ping,' + str(konta.PING_S * 1000).encode() + b');'
             b'document.addEventListener("visibilitychange",()=>document.visibilityState==="visible"?ping():send("h"));'
             b'addEventListener("click",()=>setTimeout(()=>{if(cur()!==last)ping()},300));'
             b'if(location.hash)ping();else last=cur()})()</script>')
OWNER_LINK = (b'<a href="/osoby" style="position:fixed;right:10px;bottom:10px;z-index:99;padding:6px 10px;'
              b'background:#1d1b18;color:#f4f0e8;border-radius:8px;font:13px Segoe UI,sans-serif;text-decoration:none">'
              b'Osoby</a>')
CSS = ("body{margin:0;background:#f4f0e8;color:#1d1b18;font:15px/1.5 Segoe UI,sans-serif}main{max-width:820px;margin:auto;"
       "padding:16px}h1{color:#8a3b2a}table{border-collapse:collapse;width:100%;margin:8px 0 20px}td,th{border-bottom:1px solid "
       "#ddd5c7;padding:6px 8px;text-align:left;vertical-align:top}th{font-weight:600}.box{background:#fbf8f2;border:1px solid "
       "#ddd5c7;border-radius:12px;padding:12px 14px;margin:12px 0}.s{color:#7a746a;font-size:.85em}input{font:inherit;padding:"
       "6px 8px;border:1px solid #bdb6a8;border-radius:6px}button{font:inherit;padding:6px 12px;border:0;border-radius:6px;"
       "background:#8a3b2a;color:#fff;cursor:pointer}button.l{background:#5a554c;padding:4px 8px;font-size:.85em;margin:2px 0}form.i{display:inline}code{word-break:break-all;"
       "background:#efe8da;padding:2px 4px;border-radius:4px}a{color:#8a3b2a}summary{cursor:pointer;color:#8a3b2a}"
       "ol{margin:4px 0;padding-left:20px}.t{overflow-x:auto}")


def local(dt) -> str:
    try:
        from zoneinfo import ZoneInfo
        return dt.astimezone(ZoneInfo("Europe/Warsaw")).strftime("%d.%m %H:%M")
    except Exception:
        return dt.strftime("%d.%m %H:%M UTC")


def page(title: str, body: str) -> bytes:
    return (f'<!doctype html><html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,'
            f' initial-scale=1"><meta name="robots" content="noindex, nofollow"><title>{html.escape(title)} · Paralaksa</title>'
            f'<link rel="manifest" href="/manifest.webmanifest"><link rel="apple-touch-icon" href="/apple-touch-icon.png">'
            f'<style>{CSS}</style></head><body><main>{body}</main></body></html>').encode()


def safe_next(target: str) -> str:
    """Only paths on this site after logging in (no //host or backslash tricks)."""
    if not target.startswith("/") or target.startswith("//") or "\\" in target or target.startswith("/logowanie"):
        return "/"
    return target


def minutes(seconds: float) -> str:
    return "<1 min" if seconds < 60 else f"{round(seconds / 60)} min"


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".webmanifest": "application/manifest+json"}

    def end_headers(self) -> None:
        self.send_header("X-Robots-Tag", "noindex, nofollow")
        self.send_header("Cache-Control", "private, no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    # --- kto pyta ----------------------------------------------------------------------------------------------------
    @property
    def route(self) -> str:
        return urllib.parse.urlsplit(self.path).path

    def _ip(self) -> str:
        return (self.headers.get("X-Forwarded-For") or self.client_address[0]).split(",")[0].strip()

    def _limited(self) -> bool:
        now = time.time()
        with FAIL_LOCK:
            recent = [t for t in FAILS.get(self._ip(), []) if now - t < FAIL_WINDOW_S]
            if recent:
                FAILS[self._ip()] = recent
            else:
                FAILS.pop(self._ip(), None)
            return len(recent) >= FAIL_MAX

    def _failed(self) -> None:
        with FAIL_LOCK:
            if len(FAILS) > 10_000:
                FAILS.clear()
            FAILS.setdefault(self._ip(), []).append(time.time())

    @staticmethod
    def _fingerprint(login: str) -> str | None:
        if login == USER:
            return OWNER_FP
        return STORE.fingerprint(login) if STORE is not None else None

    def _cookie(self) -> str:
        for part in self.headers.get("Cookie", "").split(";"):
            name, _, value = part.strip().partition("=")
            if name == COOKIE:
                return value
        return ""

    def _session_cookie(self, login: str | None) -> tuple[str, str]:
        """Set-Cookie for `login` (fresh COOKIE_DAYS), or one that logs out when `login` is None."""
        secure = "; Secure" if self.headers.get("X-Forwarded-Proto") == "https" else ""
        if login is None:
            return "Set-Cookie", f"{COOKIE}=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax{secure}"
        exp = int(time.time()) + COOKIE_DAYS * 86400
        value = konta.sign_session(SECRET, login, exp, self._fingerprint(login) or "")
        return "Set-Cookie", f"{COOKIE}={value}; Max-Age={COOKIE_DAYS * 86400}; Path=/; HttpOnly; SameSite=Lax{secure}"

    def _who(self) -> str | None:
        self.session_exp = None
        cookie = self._cookie()
        if cookie and EXPECTED is not None:
            found = konta.read_session(SECRET, cookie, self._fingerprint, time.time())
            if found:
                self.session_exp = found[1]
                return found[0]
        header = self.headers.get("Authorization", "")
        if not header.startswith("Basic "):
            return None
        if EXPECTED is not None and hmac.compare_digest(header.encode(), EXPECTED):
            return USER
        if STORE is not None and not self._limited():
            try:
                login, password = base64.b64decode(header[6:]).decode("utf-8").split(":", 1)
            except Exception:
                login = password = ""
            if login and login != USER and STORE.authenticate(login, password):
                return login
        self._failed()
        return None

    def _login_or_refuse(self) -> str | None:
        if EXPECTED is None:
            self.send_error(503, "SITE_USER / SITE_PASSWORD not set")
            return None
        who = self._who()
        if who is not None:
            return who
        if self.headers.get("Authorization", "").startswith("Basic "):       # skrypty: zwykłe HTTP Basic Auth
            body = page("Logowanie", '<p><a href="/logowanie">Zaloguj się</a></p>')
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="Paralaksa", charset="UTF-8"')
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.command in ("GET", "HEAD") and self.route != "/_ping":
            self._redirect("/logowanie?next=" + urllib.parse.quote(self.path, safe="/"))
        else:
            self._send(b"", 401, head=True)
        return None

    def _send(self, body: bytes, status: int = 200, ctype: str = "text/html; charset=utf-8", head: bool = False,
              headers: list[tuple[str, str]] = ()) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for name, value in headers:
            self.send_header(name, value)
        self.end_headers()
        if not head:
            self.wfile.write(body)

    def _latest_v2(self) -> str | None:
        """Newest day of version 2.0 (v2/dni.json from the build), if it was built."""
        try:
            days = json.loads((Path(self.directory) / "v2" / "dni.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        day = days[0] if isinstance(days, list) and days else ""
        if not (isinstance(day, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", day)):
            return None
        return day if (Path(self.directory) / "v2" / day / "index.html").is_file() else None

    def _redirect(self, location: str, headers: list[tuple[str, str]] = (), status: int = 303) -> None:
        self.send_response(status)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        for name, value in headers:
            self.send_header(name, value)
        self.end_headers()

    # --- GET / HEAD / POST -------------------------------------------------------------------------------------------
    def do_GET(self) -> None:
        self._handle(head=False)

    def do_HEAD(self) -> None:
        self._handle(head=True)

    def _handle(self, head: bool) -> None:
        route = self.route
        if route in PUBLIC:
            return super().do_HEAD() if head else super().do_GET()
        if route.startswith("/zaproszenie/"):
            return self._invite(route.removeprefix("/zaproszenie/"), head=head)
        if route == "/logowanie":
            return self._login_form(head=head)
        if route == "/wyloguj":
            return self._redirect("/logowanie", [self._session_cookie(None)])
        who = self._login_or_refuse()
        if who is None:
            return
        if route == "/_ping":
            if STORE is not None:
                query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                STORE.record(who, query.get("p", [""])[0], "h" if query.get("k") == ["h"] else "p")
            self.send_response(204)
            self.end_headers()
            return
        if route == "/osoby":
            return self._admin(who, head=head) if who == USER else self.send_error(403)
        if route == "/" and (latest := self._latest_v2()):     # wersja 2.0 jest podstawowa; stara pod /index.html
            return self._redirect(f"/v2/{latest}/index.html", status=302)
        target = Path(self.translate_path(self.path))
        if target.is_dir() and (target / "index.html").is_file() and route.endswith("/"):
            target = target / "index.html"
        if target.is_file() and target.suffix == ".html":
            return self._html(target, who, head)
        return super().do_HEAD() if head else super().do_GET()

    def do_POST(self) -> None:
        route = self.route
        length = min(int(self.headers.get("Content-Length") or 0), 10_000)
        form = {k: v[0] for k, v in urllib.parse.parse_qs(self.rfile.read(length).decode("utf-8", "replace")).items()}
        if route.startswith("/zaproszenie/"):
            return self._invite(route.removeprefix("/zaproszenie/"), form=form)
        if route == "/logowanie":
            return self._login_form(form=form)
        who = self._login_or_refuse()
        if who is None:
            return
        if route != "/osoby" or who != USER:
            return self.send_error(403)
        origin = self.headers.get("Origin")
        if form.get("csrf") != CSRF or (origin and urllib.parse.urlsplit(origin).netloc != self.headers.get("Host")):
            return self.send_error(403, "Formularz z innej strony")
        self._admin(who, form=form)

    def _html(self, target: Path, who: str, head: bool) -> None:
        """Static page plus the reading-time heartbeat (and the owner's link to /osoby); keeps the login cookie fresh."""
        body = target.read_bytes()
        extra = HEARTBEAT + (OWNER_LINK if who == USER else b"")
        i = body.rfind(b"</body>")
        body = body[:i] + extra + body[i:] if i >= 0 else body + extra
        if STORE is not None and not head:
            STORE.record(who, self.route, "v")
        exp = getattr(self, "session_exp", None)
        fresh = exp is not None and exp - time.time() > (COOKIE_DAYS - 1) * 86400
        self._send(body, head=head, headers=[] if fresh else [self._session_cookie(who)])

    # --- logowanie i zaproszenia (bez hasła) ---------------------------------------------------------------------------
    def _login_form(self, form: dict | None = None, head: bool = False) -> None:
        if EXPECTED is None:
            return self.send_error(503, "SITE_USER / SITE_PASSWORD not set")
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        target = safe_next((form or {}).get("next") or query.get("next", ["/"])[0])
        error = ""
        if form is not None:
            login, password = form.get("login", "").strip(), form.get("haslo", "")
            if self._limited():
                error = "Za dużo nieudanych prób. Spróbuj za kwadrans."
            else:
                who = None
                if login == USER and hmac.compare_digest(password.encode(), PASSWORD.encode()):
                    who = USER
                elif STORE is not None and login.lower() != USER and STORE.authenticate(login.lower(), password):
                    who = login.lower()
                if who:
                    return self._redirect(target, [self._session_cookie(who)])
                self._failed()
                error = "Zły login albo hasło."
        body = ("<h1>Paralaksa</h1>" + (f'<p style="color:#b00020">{html.escape(error)}</p>' if error else "")
                + '<form method="post" action="/logowanie" class="box">'
                f'<input type="hidden" name="next" value="{html.escape(target)}">'
                '<p><label>Login<br><input name="login" autocomplete="username" autocapitalize="none" spellcheck="false" '
                'required></label></p><p><label>Hasło<br><input type="password" name="haslo" autocomplete="current-password" '
                'required></label></p><button>Zaloguj</button></form>'
                '<p class="s">Nie pamiętasz hasła? Poproś o nowy link.</p>')
        self._send(page("Logowanie", body), head=head)

    def _invite(self, token: str, form: dict | None = None, head: bool = False) -> None:
        info = STORE.invite_info(token) if STORE is not None and token else None
        if info is None:
            return self._send(page("Link nie działa", "<h1>Link nie działa</h1><p>Ten link wygasł albo został już użyty. "
                                   "Poproś o nowy.</p>"), 404, head=head)
        error = ""
        if form is not None:
            if form.get("haslo", "") != form.get("haslo2", ""):
                error = "Hasła się różnią."
            else:
                try:
                    login = STORE.accept(token, form.get("haslo", ""))
                    return self._send(page("Gotowe", f"<h1>Gotowe</h1><p>Twój login: <b>{html.escape(login)}</b>. To "
                                           "urządzenie jest już zalogowane. Na innym zaloguj się tym loginem i hasłem.</p>"
                                           '<p><a href="/">Przejdź do Paralaksy</a></p>'),
                                      headers=[self._session_cookie(login)])
                except (ValueError, LookupError) as e:
                    error = str(e)
        body = (f"<h1>Paralaksa</h1><p>Cześć {html.escape(info['imie'])}! Ustaw hasło do wewnętrznej wersji Paralaksy.</p>"
                f"<p>Twój login: <b>{html.escape(info['login'])}</b></p>"
                + (f'<p style="color:#b00020">{html.escape(error)}</p>' if error else "")
                + '<form method="post" class="box"><input type="hidden" name="login" autocomplete="username" value="'
                f'{html.escape(info["login"])}"><p><label>Hasło (min. 10 znaków)<br><input type="password" name="haslo" '
                'autocomplete="new-password" required minlength="10"></label></p><p><label>Powtórz hasło<br><input '
                'type="password" name="haslo2" autocomplete="new-password" required minlength="10"></label></p>'
                '<button>Ustaw hasło</button></form><p class="s">Link działa raz, do '
                f"{local(konta.parse_iso(info['wygasa']))}.</p>")
        self._send(page("Zaproszenie", body), head=head)

    # --- panel właściciela ---------------------------------------------------------------------------------------------
    def _admin(self, who: str, form: dict | None = None, head: bool = False) -> None:
        if STORE is None:
            return self._send(page("Osoby", f"<h1>Osoby</h1><p>Konta nie działają: {html.escape(STORE_ERROR)}.</p>"), head=head)
        notice = ""
        try:
            if form:
                action, login = form.get("akcja", ""), form.get("login") or None
                if action in ("dodaj", "link"):
                    if action == "dodaj" and not form.get("imie", "").strip():
                        raise ValueError("Podaj imię.")
                    login, token = STORE.invite(form.get("imie", ""), None if action == "dodaj" else login)
                    proto = self.headers.get("X-Forwarded-Proto", "http")
                    url = f"{proto}://{self.headers.get('Host', '')}/zaproszenie/{token}"
                    notice = (f'<div class="box"><b>Link dla {html.escape(STORE.people()[login]["imie"])}</b> (login '
                              f"{html.escape(login)}):<br><code>{html.escape(url)}</code><br><span class=\"s\">Wyślij go tej "
                              f"osobie. Działa raz, przez {konta.INVITE_DAYS} dni. Nie zapisujemy go nigdzie, więc skopiuj "
                              "teraz.</span></div>")
                elif action in ("zablokuj", "odblokuj") and login:
                    STORE.set_blocked(login, action == "zablokuj")
                elif action == "usun" and login:
                    name = STORE.people()[login]["imie"]
                    STORE.delete(login)
                    notice = f'<div class="box">Usunięto konto: {html.escape(name)}. Historia wizyt została.</div>'
            STORE.flush()
            events = STORE.events(30)
        except Exception as e:
            notice += f'<p style="color:#b00020">{html.escape(str(e))}</p>'
            events = []
        people = STORE.people()
        sess = konta.sessions(events)
        now = STORE.clock()
        week = [s for s in sess if s["od"] >= now - timedelta(days=7)]

        def total(rows, u):
            return sum(s["minuty"] for s in rows if s["u"] == u)

        def btn(action, login, label, cls="", ask=""):
            confirm = f' data-q="{html.escape(ask)}" onsubmit="return confirm(this.dataset.q)"' if ask else ""
            return (f'<form method="post" class="i"{confirm}><input type="hidden" name="csrf" value="{CSRF}"><input '
                    f'type="hidden" name="akcja" value="{action}"><input type="hidden" name="login" '
                    f'value="{html.escape(login)}"><button class="{cls}">{label}</button></form>')

        def places(s):
            seen = s["miejsca"]                      # bez pustego wejścia, gdy strona od razu ustawia zakładkę (#...)
            items = "".join(f'<li>{html.escape(self._title(p))} <span class="s">{minutes(sec)}</span></li>'
                            for p, sec in seen.items()
                            if "#" in p or sec >= 5 or not any(q.startswith(p + "#") for q in seen))
            return f"<details><summary>{s['strony']}</summary><ol>{items}</ol></details>" if items else str(s["strony"])

        rows = []
        for login, p in sorted(people.items(), key=lambda kv: kv[1]["imie"].lower()):
            if p.get("usunieta"):
                continue
            status = "zablokowana" if p.get("zablokowana") else ("aktywna" if p.get("hash") else "czeka na ustawienie hasła")
            last = next((s["do"] for s in sess if s["u"] == login), None)
            rows.append(f"<tr><td>{html.escape(p['imie'])}<br><span class=\"s\">{html.escape(login)}</span></td>"
                        f"<td>{status}</td><td>{local(last) if last else '–'}</td><td>{total(week, login)} min</td>"
                        f"<td>{total(sess, login)} min</td><td>{btn('link', login, 'Nowy link', 'l')} "
                        + (btn("odblokuj", login, "Odblokuj", "l") if p.get("zablokowana") else btn("zablokuj", login, "Zablokuj", "l"))
                        + " " + btn("usun", login, "Usuń", "l", f"Usunąć konto: {p['imie']}? Historia wizyt zostanie.")
                        + "</td></tr>")
        names = {**{k: v["imie"] + (" (usunięta)" if v.get("usunieta") else "") for k, v in people.items()},
                 USER: f"{USER} (Ty)"}
        srows = "".join(f"<tr><td>{html.escape(names.get(s['u'], s['u']))}</td><td>{local(s['od'])}</td>"
                        f"<td>{local(s['do'])}</td><td>{s['minuty']}</td><td>{places(s)}</td></tr>" for s in sess[:200])
        body = (f'<p><a href="/">← Paralaksa</a> · <a href="/wyloguj">Wyloguj</a></p><h1>Osoby</h1>{notice}'
                f'<form method="post" class="box"><input type="hidden" name="csrf" value="{CSRF}"><input type="hidden" '
                'name="akcja" value="dodaj"><label>Imię nowej osoby <input name="imie" maxlength="60" required></label> '
                '<button>Dodaj i utwórz link</button></form>'
                '<div class="t"><table><tr><th>Osoba</th><th>Status</th><th>Ostatnio</th><th>7 dni</th><th>30 dni</th>'
                "<th></th></tr>"
                + ("".join(rows) or '<tr><td colspan="6" class="s">Nikogo jeszcze nie dodano.</td></tr>') + "</table></div>"
                '<h2>Sesje (30 dni)</h2><div class="t"><table><tr><th>Osoba</th><th>Od</th><th>Do</th><th>Minuty</th>'
                "<th>Strony</th></tr>"
                + (srows or '<tr><td colspan="5" class="s">Brak zapisanych wizyt.</td></tr>') + "</table></div>"
                f'<p class="s">Czas liczony, gdy karta ze stroną jest otwarta i widoczna (sygnał co minutę, koniec od razu '
                f"po schowaniu karty albo aplikacji); przerwa ponad {konta.SESSION_GAP_S // 60} min zaczyna nową sesję. "
                "Kliknij liczbę stron, żeby zobaczyć, co było czytane. Godziny polskie."
                + (f" Uwaga: {html.escape(STORE.error)}" if STORE.error else "") + "</p>")
        self._send(page("Osoby", body), head=head)

    def _title(self, place: str) -> str:
        """Readable name of a visited page: its <title> from the built site, plus the #tab."""
        path, _, tab = place.partition("#")
        if path not in TITLES:
            name = path
            try:
                root = Path(self.directory).resolve()
                target = (root / urllib.parse.unquote(path).lstrip("/")).resolve()
                if target.is_dir():
                    target = target / "index.html"
                if (root == target.parent or root in target.parents) and target.is_file():
                    found = re.search(rb"<title>(.*?)</title>", target.read_bytes()[:20_000], re.S)
                    if found:
                        name = html.unescape(found.group(1).decode("utf-8", "replace")).replace(" · Paralaksa", "").strip()
            except OSError:
                pass
            TITLES[path] = name or path
        return TITLES[path] + (f" » {urllib.parse.unquote(tab)}" if tab else "")

    def list_directory(self, path):
        self.send_error(404)
        return None

    def log_message(self, format, *args) -> None:
        pass


def _flush_loop() -> None:
    while True:
        threading.Event().wait(FLUSH_S)
        if STORE is not None:
            STORE.flush()


def main() -> None:
    global STORE, STORE_ERROR
    STORE, STORE_ERROR = konta.from_env(os.environ)
    if STORE is not None:
        STORE.reserved = {USER}                     # nikt nie dostanie loginu właściciela
    print("konta:", "zapis w repo" if STORE else STORE_ERROR, flush=True)
    port = int(os.environ.get("PORT", "10000"))
    srv = ThreadingHTTPServer(("0.0.0.0", port), partial(Handler, directory=str(ROOT)))

    def stop(*_):                                   # Render usypia albo wdraża: najpierw zapis aktywności
        if STORE is not None:
            STORE.flush()
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, stop)
    threading.Thread(target=_flush_loop, daemon=True).start()
    srv.serve_forever()


if __name__ == "__main__":
    main()
