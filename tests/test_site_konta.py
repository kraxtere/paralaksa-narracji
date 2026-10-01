import base64
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
