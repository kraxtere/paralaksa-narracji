import base64
import http.client
import importlib.util
import io
import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from functools import partial
from http.server import ThreadingHTTPServer

import pytest

from paralaksa.site import publish

spec = importlib.util.spec_from_file_location("konta", publish.HOSTING / "konta.py")
konta = importlib.util.module_from_spec(spec)
spec.loader.exec_module(konta)

T0 = datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc)


class Clock:
    def __init__(self, t=T0):
        self.t = t

    def __call__(self):
        return self.t


def _store(clock=None):
    return konta.Store(konta.MemoryFiles(), clock or Clock())


def test_password_hash_roundtrip_and_garbage():
    h = konta.hash_password("dlugie-haslo-1", iterations=1000)
    assert h.startswith("pbkdf2_sha256$1000$") and "dlugie" not in h
    assert konta.check_password("dlugie-haslo-1", h)
    assert not konta.check_password("inne-haslo-12", h)
    assert not konta.check_password("x", None) and not konta.check_password("x", "md5$1$a$b")


def test_make_login_is_ascii_and_unique():
    assert konta.make_login("Ala Nowak", set()) == "ala-nowak"
    assert konta.make_login("Łukasz Żółć", set()) == "lukasz-zolc"
    assert konta.make_login("Ala", {"ala", "ala-2"}) == "ala-3"
    assert konta.make_login("  !!! ", set()) == "osoba"


def test_invite_accept_and_login():
    clock = Clock()
    st = _store(clock)
    st.reserved = {"wlasciciel"}
    login, token = st.invite("Ala")
    assert login == "ala" and st.invite_info(token)["imie"] == "Ala"
    assert not st.authenticate("ala", "cokolwiek-123")                 # przed ustawieniem hasła
    with pytest.raises(ValueError):
        st.accept(token, "krotkie")
    assert st.accept(token, "moje-haslo-123") == "ala"
    assert st.authenticate("ala", "moje-haslo-123") and not st.authenticate("ala", "zle-haslo-123")
    assert st.invite_info(token) is None                                # link działa raz
    saved = json.loads(st.files.get("osoby.json")[0])
    assert "moje-haslo-123" not in json.dumps(saved) and token not in json.dumps(saved)
    assert st.invite("wlasciciel")[0] == "wlasciciel-2"                  # login właściciela zajęty


def test_invite_expires_new_link_replaces_old_and_block():
    clock = Clock()
    st = _store(clock)
    login, old = st.invite("Bartek")
    _, new = st.invite(login=login)
    assert st.invite_info(old) is None and st.invite_info(new)
    clock.t += timedelta(days=konta.INVITE_DAYS, seconds=1)
    assert st.invite_info(new) is None
    with pytest.raises(LookupError):
        st.accept(new, "moje-haslo-123")
    _, token = st.invite(login=login)
    st.accept(token, "moje-haslo-123")
    st.set_blocked(login, True)
    assert not st.authenticate(login, "moje-haslo-123")
    st.set_blocked(login, False)
    assert st.authenticate(login, "moje-haslo-123")


def test_people_write_retries_after_conflict_without_duplicates():
    st = _store()
    st.files.conflicts = 1
    assert st.invite("Ala")[0] == "ala"
    assert list(json.loads(st.files.get("osoby.json")[0])["osoby"]) == ["ala"]


def test_flush_groups_by_day_and_keeps_events_on_failure():
    clock = Clock(datetime(2026, 10, 1, 23, 59, tzinfo=timezone.utc))
    st = _store(clock)
    st.record("ala", "/index.html", "v")
    clock.t += timedelta(minutes=2)
    st.record("ala", "/index.html", "p")
    st.files.conflicts = 10                                             # zapis nie przechodzi
    st.flush()
    assert len(st.pending) == 2 and st.error
    st.files.conflicts = 0
    st.flush()
    assert not st.pending and not st.error
    assert st.files.list("aktywnosc") == ["2026-10-01.jsonl", "2026-10-02.jsonl"]
    assert len(st.events(30)) == 2


def test_sessions_split_on_long_gap():
    ev = [{"t": f"2026-10-01T08:{m:02d}:00Z", "u": "ala", "p": "/", "k": k}
          for m, k in [(0, "v"), (1, "p"), (2, "v"), (3, "p")]]
    ev += [{"t": "2026-10-01T09:00:00Z", "u": "ala", "p": "/", "k": "v"},
           {"t": "2026-10-01T08:30:00Z", "u": "ola", "p": "/", "k": "p"}]
    s = konta.sessions(ev)
    ala = sorted((x for x in s if x["u"] == "ala"), key=lambda x: x["od"])
    assert [(x["minuty"], x["strony"]) for x in ala] == [(4, 2), (1, 1)]
    assert s[0]["od"] == datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)   # najnowsze najpierw


def test_sessions_hidden_tab_stops_the_clock_and_lists_pages():
    ev = [("08:00:00", "v", "/index.html"), ("08:00:01", "p", "/index.html#kraje"), ("08:01:01", "p", "/index.html#kraje"),
          ("08:01:31", "h", "/index.html#kraje"), ("08:05:00", "v", "/zdarzenia/a.html")]
    s = konta.sessions([{"t": f"2026-10-01T{t}Z", "u": "ala", "p": p, "k": k} for t, k, p in ev])
    assert len(s) == 1 and s[0]["strony"] == 2 and s[0]["minuty"] == 3          # 1 + 60 + 30 + 60 s
    assert s[0]["miejsca"] == {"/index.html": 1.0, "/index.html#kraje": 90.0, "/zdarzenia/a.html": 60.0}


def test_late_hidden_signal_of_the_previous_page_is_ignored():
    ev = [("08:00:00.0", "v", "/a"), ("08:00:30.0", "v", "/b"), ("08:00:30.5", "h", "/a"), ("08:01:30.0", "p", "/b"),
          ("08:01:40.0", "h", "/b")]
    evs = [{"t": f"2026-10-01T{t[:8]}Z", "u": "ala", "p": p, "k": k} for t, k, p in ev]
    evs[2]["t"] = "2026-10-01T08:00:31Z"                                           # „h” strony A po wejściu na B
    s = konta.sessions(evs)
    assert s[0]["miejsca"] == {"/a": 30.0, "/b": 70.0}                              # 60 + 10 s na B, nie 1 s
    assert sum((iv["do"] - iv["od"]).total_seconds() for iv in konta.intervals(evs)) == 100.0


def test_session_cookie_signature_expiry_and_password_change():
    secret, fp = b"s" * 32, {"ala": "hash-1"}
    value = konta.sign_session(secret, "ala", 2000, "hash-1")
    assert konta.read_session(secret, value, fp.get, 1000) == ("ala", 2000)
    assert konta.read_session(secret, value, fp.get, 2001) is None                   # wygasło
    assert konta.read_session(b"x" * 32, value, fp.get, 1000) is None                # inny klucz
    assert konta.read_session(secret, value.replace("2000", "9000"), fp.get, 1000) is None
    assert konta.read_session(secret, "śmieci", fp.get, 1000) is None
    fp["ala"] = "hash-2"                                                              # nowe hasło wylogowuje
    assert konta.read_session(secret, value, fp.get, 1000) is None


def test_delete_keeps_name_but_ends_the_account():
    st = _store()
    login, token = st.invite("Ala")
    st.accept(token, "moje-haslo-123")
    st.delete(login)
    person = st.people()[login]
    assert person["usunieta"] and person["imie"] == "Ala" and not person["hash"]
    assert not st.authenticate(login, "moje-haslo-123") and st.fingerprint(login) is None
    with pytest.raises(KeyError):
        st.invite(login=login)
    st.set_blocked(login, False)
    assert st.fingerprint(login) is None
    assert st.invite("Ala")[0] == "ala-2"                                            # login nie wraca do obiegu


def test_intervals_match_session_counting():
    ev = [("08:00:00", "v", "/a"), ("08:00:20", "p", "/b"), ("08:01:20", "h", "/b"), ("09:00:00", "v", "/c")]
    ivs = konta.intervals([{"t": f"2026-10-01T{t}Z", "u": "ala", "p": p, "k": k} for t, k, p in ev])
    assert [(iv["p"], (iv["do"] - iv["od"]).total_seconds()) for iv in ivs] == [("/a", 20), ("/b", 60), ("/c", 60)]


def _http_error(code):
    return urllib.error.HTTPError("https://api.github.com", code, "x", {}, io.BytesIO(b"{}"))


def test_github_files_maps_api_responses():
    calls = []

    def urlopen(req, timeout):
        calls.append((req.get_method(), req.full_url, req.headers.get("Authorization")))
        if req.full_url.endswith("brak.json?ref=main"):
            raise _http_error(404)
        if req.get_method() == "PUT":
            raise _http_error(409)
        body = json.dumps({"content": base64.b64encode("zażółć".encode()).decode(), "sha": "abc"}).encode()
        return io.BytesIO(body)

    gh = konta.GitHubFiles("kraxtere/repo", "tok", urlopen=urlopen)
    assert gh.get("brak.json") == (None, None)
    assert gh.get("osoby.json") == ("zażółć", "abc")
    with pytest.raises(konta.Conflict):
        gh.put("osoby.json", "x", "abc", "m")
    assert calls[0] == ("GET", "https://api.github.com/repos/kraxtere/repo/contents/brak.json?ref=main", "Bearer tok")


def test_from_env_without_token_is_owner_only():
    store, why = konta.from_env({})
    assert store is None and "ACTIVITY_TOKEN" in why


# --- serwer ------------------------------------------------------------------------------------------------------------

def _server(monkeypatch, tmp_path, store):
    monkeypatch.setenv("SITE_USER", "wlasciciel")
    monkeypatch.setenv("SITE_PASSWORD", "tajne-haslo")
    sspec = importlib.util.spec_from_file_location("site_server_konta", publish.HOSTING / "server.py")
    mod = importlib.util.module_from_spec(sspec)
    sspec.loader.exec_module(mod)
    mod.STORE = store
    (tmp_path / "index.html").write_text("<html><body><h1>ok</h1></body></html>", encoding="utf-8")
    (tmp_path / "a.png").write_bytes(b"png")
    srv = ThreadingHTTPServer(("127.0.0.1", 0), partial(mod.Handler, directory=str(tmp_path)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return mod, srv, f"http://127.0.0.1:{srv.server_address[1]}"


def _req(url, auth=None, data=None):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode() if data is not None else None)
    if auth:
        req.add_header("Authorization", "Basic " + base64.b64encode(auth.encode()).decode())
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")


def test_server_invite_flow_heartbeat_and_owner_panel(monkeypatch, tmp_path):
    store = _store()
    mod, srv, base = _server(monkeypatch, tmp_path, store)
    try:
        owner = "wlasciciel:tajne-haslo"
        status, body = _req(base + "/", owner)
        assert status == 200 and "/_ping" in body and 'href="/osoby"' in body
        assert _req(base + "/osoby", owner)[0] == 200
        assert _req(base + "/osoby", owner, {"akcja": "dodaj", "imie": "Ala"})[0] == 403           # bez tokenu CSRF
        status, body = _req(base + "/osoby", owner, {"akcja": "dodaj", "imie": "Ala", "csrf": mod.CSRF})
        assert status == 200 and "/zaproszenie/" in body
        token = body.split("/zaproszenie/")[1].split("<")[0]

        assert _req(base + "/zaproszenie/zly-token")[0] == 404
        status, body = _req(base + f"/zaproszenie/{token}")                                     # bez hasła
        assert status == 200 and "Ustaw hasło" in body and "ala" in body
        assert "różnią" in _req(base + f"/zaproszenie/{token}", data={"haslo": "moje-haslo-123", "haslo2": "inne"})[1]
        status, body = _req(base + f"/zaproszenie/{token}", data={"haslo": "moje-haslo-123", "haslo2": "moje-haslo-123"})
        assert status == 200 and "Gotowe" in body

        ala = "ala:moje-haslo-123"
        status, body = _req(base + "/", ala)
        assert status == 200 and "/_ping" in body and 'href="/osoby"' not in body
        assert _req(base + "/a.png", ala) == (200, "png")
        assert _req(base + "/_ping?p=/index.html", ala)[0] == 204
        assert _req(base + "/osoby", ala)[0] == 403
        assert _req(base + "/", "ala:zle-haslo-123")[0] == 401
        kinds = [(e["u"], e["k"]) for e in store.events(30)]               # część zapisana już przy wejściu na /osoby
        assert ("ala", "v") in kinds and ("ala", "p") in kinds and ("wlasciciel", "v") in kinds

        status, body = _req(base + "/osoby", owner)                                              # zapis i zestawienie
        assert status == 200 and "Ala" in body and "aktywna" in body and not store.pending
    finally:
        srv.shutdown()


def test_server_without_store_keeps_owner_access(monkeypatch, tmp_path):
    mod, srv, base = _server(monkeypatch, tmp_path, None)
    try:
        assert _req(base + "/", "wlasciciel:tajne-haslo")[0] == 200
        assert _req(base + "/zaproszenie/cokolwiek")[0] == 404
        assert "nie działają" in _req(base + "/osoby", "wlasciciel:tajne-haslo")[1]
    finally:
        srv.shutdown()


def _raw(base, method, path, headers=None, data=None):
    """One request without following redirects: (status, body, Location, Set-Cookie)."""
    conn = http.client.HTTPConnection(base.removeprefix("http://"), timeout=5)
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    hdrs = dict(headers or {})
    if body is not None:
        hdrs["Content-Type"] = "application/x-www-form-urlencoded"
    conn.request(method, path, body=body, headers=hdrs)
    r = conn.getresponse()
    out = r.status, r.read().decode(errors="replace"), r.getheader("Location"), r.getheader("Set-Cookie")
    conn.close()
    return out


def _cookie(set_cookie):
    return {"Cookie": set_cookie.split(";")[0]}


def test_server_login_form_sets_cookie(monkeypatch, tmp_path):
    mod, srv, base = _server(monkeypatch, tmp_path, _store())
    try:
        status, _, location, _ = _raw(base, "GET", "/zdarzenia/x.html?a=1")
        assert status == 303 and location == "/logowanie?next=/zdarzenia/x.html%3Fa%3D1"
        assert _raw(base, "GET", "/_ping")[0] == 401
        assert "Zły login" in _raw(base, "POST", "/logowanie", data={"login": "wlasciciel", "haslo": "zle"})[1]
        status, _, location, set_cookie = _raw(base, "POST", "/logowanie",
                                               data={"login": "wlasciciel", "haslo": "tajne-haslo", "next": "/index.html"})
        assert status == 303 and location == "/index.html" and "HttpOnly" in set_cookie and "SameSite=Lax" in set_cookie
        status, body, _, again = _raw(base, "GET", "/", _cookie(set_cookie))
        assert status == 200 and "/_ping" in body and 'href="/osoby"' in body and again is None   # świeże: bez odnowienia
        assert _raw(base, "GET", "/", {"Cookie": "plx=a.1.b"})[0] == 303
        assert _raw(base, "POST", "/logowanie", data={"login": "wlasciciel", "haslo": "tajne-haslo",
                                                      "next": "//evil.example"})[2] == "/"
        assert "Max-Age=0" in _raw(base, "GET", "/wyloguj")[3]
    finally:
        srv.shutdown()


def test_server_login_attempts_are_limited(monkeypatch, tmp_path):
    mod, srv, base = _server(monkeypatch, tmp_path, _store())
    mod.FAIL_MAX = 3
    try:
        for _ in range(3):
            _raw(base, "POST", "/logowanie", data={"login": "ktos", "haslo": "zle-haslo-123"})
        body = _raw(base, "POST", "/logowanie", data={"login": "wlasciciel", "haslo": "tajne-haslo"})[1]
        assert "Za dużo" in body
    finally:
        srv.shutdown()


def test_server_invite_logs_in_new_password_logs_out_and_delete(monkeypatch, tmp_path):
    store = _store()
    mod, srv, base = _server(monkeypatch, tmp_path, store)
    (tmp_path / "zdarzenie.html").write_text("<html><head><title>Zdarzenie X · Paralaksa</title></head><body></body>"
                                             "</html>", encoding="utf-8")
    try:
        login, token = store.invite("Ala")
        page = _raw(base, "GET", f"/zaproszenie/{token}")[1]
        assert "Ustaw hasło" in page and "czas" not in page.lower()
        status, body, _, set_cookie = _raw(base, "POST", f"/zaproszenie/{token}",
                                           data={"haslo": "moje-haslo-123", "haslo2": "moje-haslo-123"})
        assert status == 200 and "zalogowane" in body and "czas" not in body.lower()
        ala = _cookie(set_cookie)
        assert _raw(base, "GET", "/zdarzenie.html", ala)[0] == 200
        assert _raw(base, "GET", "/_ping?k=h&p=/zdarzenie.html%23kraje", ala)[0] == 204
        assert [e["k"] for e in store.pending if e["u"] == login] == ["v", "h"]

        _, token = store.invite(login=login)                                     # nowy link = nowe hasło
        store.accept(token, "inne-haslo-123")
        assert _raw(base, "GET", "/", ala)[0] == 303                             # stare ciasteczko już nie działa
        status, _, _, set_cookie = _raw(base, "POST", "/logowanie", data={"login": "ALA", "haslo": "inne-haslo-123"})
        assert status == 303 and set_cookie
        ala = _cookie(set_cookie)

        owner = _cookie(_raw(base, "POST", "/logowanie", data={"login": "wlasciciel", "haslo": "tajne-haslo"})[3])
        body = _raw(base, "GET", "/osoby", owner)[1]
        assert "Usuń" in body and "Zdarzenie X" in body
        body = _raw(base, "POST", "/osoby", owner, {"akcja": "usun", "login": login, "csrf": mod.CSRF})[1]
        assert "Usunięto konto: Ala" in body and "ala · usunięta" in body and "Nowy link" not in body
        assert _raw(base, "GET", "/", ala)[0] == 303
        assert _req(base + "/", "ala:inne-haslo-123")[0] == 401
    finally:
        srv.shutdown()


def test_server_admin_form_accepts_origin_null_but_not_foreign(monkeypatch, tmp_path):
    """Referrer-Policy: no-referrer makes browsers send „Origin: null” with the form (seen on a phone, 2026-10-01)."""
    mod, srv, base = _server(monkeypatch, tmp_path, _store())
    try:
        owner = _cookie(_raw(base, "POST", "/logowanie", data={"login": "wlasciciel", "haslo": "tajne-haslo"})[3])
        form = {"akcja": "dodaj", "imie": "Ala", "csrf": mod.CSRF}
        status, body, _, _ = _raw(base, "POST", "/osoby", {**owner, "Origin": "null"}, form)
        assert status == 200 and "/zaproszenie/" in body
        assert _raw(base, "POST", "/osoby", {**owner, "Origin": base}, {**form, "imie": "Ola"})[0] == 200
        assert _raw(base, "POST", "/osoby", {**owner, "Origin": "https://obca.example"}, form)[0] == 403
        assert _raw(base, "POST", "/osoby", {**owner, "Origin": "null"}, {**form, "csrf": "zly"})[0] == 403
    finally:
        srv.shutdown()


def test_server_root_opens_newest_v2_day(monkeypatch, tmp_path):
    mod, srv, base = _server(monkeypatch, tmp_path, None)
    try:
        owner = {"Authorization": "Basic " + base64.b64encode(b"wlasciciel:tajne-haslo").decode()}
        assert _raw(base, "GET", "/", owner)[0] == 200                          # bez wersji 2.0: stara strona
        (tmp_path / "v2" / "2026-09-30").mkdir(parents=True)
        (tmp_path / "v2" / "2026-09-30" / "index.html").write_text("<html><body>v2</body></html>", encoding="utf-8")
        (tmp_path / "v2" / "dni.json").write_text('["2026-09-30", "2026-09-29"]', encoding="utf-8")
        status, _, location, _ = _raw(base, "GET", "/", owner)
        assert status == 302 and location == "/v2/2026-09-30/index.html"
        assert "<h1>ok</h1>" in _raw(base, "GET", "/index.html", owner)[1]   # stara wersja dalej pod /index.html
        assert _raw(base, "GET", "/")[2].startswith("/logowanie")             # bez logowania nic nie zdradza
    finally:
        srv.shutdown()


def test_sections_and_timeline_for_the_owner_panel(monkeypatch, tmp_path):
    mod, srv, base = _server(monkeypatch, tmp_path, None)
    srv.shutdown()
    sec = mod.section_of
    assert sec("/v2/2026-09-30/sprawa-2.html") == "sprawy" and sec("/v2/2026-09-30/roznica-1.html") == "roznice"
    assert sec("/v2/2026-09-30/obraz-kraju.html") == "obraz" and sec("/v2/2026-09-30/temat-russia.html") == "tematy"
    assert sec("/v2/2026-09-30/index.html@tematy") == "tematy" and sec("/v2/2026-09-30/index.html@okladka") == "okladka"
    assert sec("/v2/2026-09-30/index.html") == "okladka" and sec("/v2/index.html") == "okladka"
    assert sec("/dziennik/2026-09-30.html#raport") == "stara" and sec("/index.html") == "stara"
    t = lambda h, m: konta.parse_iso(f"2026-10-01T{h:02d}:{m:02d}:00Z")
    ivs = [{"u": "ala", "od": t(6, 0), "do": t(6, 1), "p": "/v2/2026-10-01/temat-russia.html"},
           {"u": "ala", "od": t(6, 1), "do": t(6, 2), "p": "/v2/2026-10-01/index.html@tematy"},   # sklejone z poprzednim
           {"u": "ala", "od": t(6, 2), "do": t(6, 3), "p": "/index.html"},
           {"u": "ala", "od": t(21, 59), "do": t(22, 1), "p": "/index.html"}]                   # 23:59–00:01 w Polsce
    html_ = mod.timeline(ivs)
    assert html_.count('class="tl"') == 2 and "cz 01.10" in html_ and "pt 02.10" in html_
    morning = mod.timeline(ivs[:3])                                                    # skala tylko 4–10, nie cała doba
    assert ">4<" in morning and ">10<" in morning and ">11<" not in morning
    assert html_.count("Tematy dnia") == 1 and "08:00–08:02 · Tematy dnia" in html_
    assert mod.by_section(ivs) == {"tematy": 120.0, "stara": 180.0}
    assert "Stara wersja 3 min" in mod.mix_bar(mod.by_section(ivs))
