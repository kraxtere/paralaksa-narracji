import base64
import importlib.util
import subprocess
import threading
import urllib.error
import urllib.request
from functools import partial
from http.server import ThreadingHTTPServer

import pytest

from paralaksa.site import publish


def _server(monkeypatch, tmp_path, user, password):
    monkeypatch.setenv("SITE_USER", user)
    monkeypatch.setenv("SITE_PASSWORD", password)
    spec = importlib.util.spec_from_file_location("site_server", publish.HOSTING / "server.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    (tmp_path / "index.html").write_text("<h1>ok</h1>", encoding="utf-8")
    (tmp_path / "zdarzenia").mkdir()
    srv = ThreadingHTTPServer(("127.0.0.1", 0), partial(mod.Handler, directory=str(tmp_path)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def _get(url, auth=None):
    req = urllib.request.Request(url)
    if auth:
        req.add_header("Authorization", "Basic " + base64.b64encode(auth.encode()).decode())
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.read().decode(), r.headers
    except urllib.error.HTTPError as e:
        return e.code, "", e.headers


def test_server_requires_password(monkeypatch, tmp_path):
    srv, base = _server(monkeypatch, tmp_path, "zespol", "tajne-haslo")
    try:
        status, _, headers = _get(base + "/")
        assert status == 401 and "Basic" in headers["WWW-Authenticate"]
        assert _get(base + "/", "zespol:zle")[0] == 401
        status, body, headers = _get(base + "/", "zespol:tajne-haslo")
        assert status == 200 and "ok" in body and headers["X-Robots-Tag"].startswith("noindex")
        assert _get(base + "/zdarzenia/", "zespol:tajne-haslo")[0] == 404   # bez listingu katalogów
    finally:
        srv.shutdown()


def test_server_without_credentials_serves_nothing(monkeypatch, tmp_path):
    srv, base = _server(monkeypatch, tmp_path, "", "")
    try:
        assert _get(base + "/")[0] == 503
        assert _get(base + "/", ":")[0] == 503
    finally:
        srv.shutdown()


def _fake_run(visibility, calls):
    def run(args, **kw):
        calls.append(args)
        out = visibility if args[:3] == ["gh", "repo", "view"] else ""
        return subprocess.CompletedProcess(args, 0, stdout=out + "\n", stderr="")
    return run


def test_publish_refuses_public_repo(tmp_path):
    (tmp_path / "index.html").write_text("x", encoding="utf-8")
    calls = []
    with pytest.raises(RuntimeError, match="nie jest prywatne"):
        publish.publish(tmp_path, "kraxtere/paralaksa-strona", run=_fake_run("PUBLIC", calls))
    assert all(c[0] == "gh" for c in calls)
    with pytest.raises(RuntimeError, match="właściciel/nazwa"):
        publish.check_private("https://evil/x; rm", run=_fake_run("PRIVATE", []))


def test_publish_stages_site_and_force_pushes(tmp_path, monkeypatch):
    site = tmp_path / "site"
    (site / "zdarzenia").mkdir(parents=True)
    (site / "index.html").write_text("x", encoding="utf-8")
    (site / "zdarzenia" / "a.html").write_text("a", encoding="utf-8")
    seen = {}

    def run(args, cwd=None, **kw):
        if args[:2] == ["git", "push"]:
            seen["files"] = sorted(p.relative_to(cwd).as_posix() for p in cwd.rglob("*") if p.is_file())
            seen["push"] = args
        return subprocess.CompletedProcess(args, 0, stdout="PRIVATE\n", stderr="")

    publish.publish(site, "kraxtere/paralaksa-strona", run=run)
    assert seen["files"] == ["README.md", "public/index.html", "public/zdarzenia/a.html", "render.yaml",
                             "requirements.txt", "server.py"]
    assert seen["push"][-2:] == ["https://github.com/kraxtere/paralaksa-strona.git", "main"] and "--force" in seen["push"]
    with pytest.raises(RuntimeError, match="najpierw plx site"):
        publish.stage(tmp_path / "brak", tmp_path / "out")
