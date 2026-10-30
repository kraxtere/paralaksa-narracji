"""Publish the built site to a separate private GitHub repo (deployed by Render as a password-protected web service).

Every publish replaces the repo content with a single fresh commit (force push), so the repo never grows with
old builds. Refuses to push unless GitHub reports the repo as private."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

HOSTING = Path(__file__).resolve().parent / "hosting"
HOSTING_FILES = ("server.py", "konta.py", "powiadomienia.py", "render.yaml", "requirements.txt", "README.md")
REPO_RE = re.compile(r"^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$")

Runner = Callable[..., subprocess.CompletedProcess]


def stage(site_dir: Path, dest: Path) -> None:
    """Lay out the deploy repo: hosting files at the root, the built site in public/."""
    if not (site_dir / "index.html").is_file():
        raise RuntimeError(f"brak zbudowanej strony w {site_dir} (najpierw plx site)")
    dest.mkdir(parents=True, exist_ok=True)
    for name in HOSTING_FILES:
        shutil.copy2(HOSTING / name, dest / name)
    shutil.copytree(site_dir, dest / "public", ignore=shutil.ignore_patterns("*.zip"))


def stage_hf(site_dir: Path, dest: Path) -> None:
    """Hugging Face Space (Docker): same layout as stage(), plus Dockerfile and the Space README (YAML header)."""
    stage(site_dir, dest)
    (dest / "render.yaml").unlink()
    shutil.copy2(HOSTING / "hf" / "Dockerfile", dest / "Dockerfile")
    shutil.copy2(HOSTING / "hf" / "README.md", dest / "README.md")


CF_HEADERS = """/*
  X-Robots-Tag: noindex, nofollow
  X-Content-Type-Options: nosniff
/*.html
  Cache-Control: no-cache
/*.js
  Cache-Control: no-cache
/*.json
  Cache-Control: no-cache
/*.webp
  Cache-Control: public, max-age=86400
/*.png
  Cache-Control: public, max-age=86400
/*.jpg
  Cache-Control: public, max-age=86400
/*.svg
  Cache-Control: public, max-age=86400
"""
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CF_TOKEN_RE = re.compile(r"^[A-Za-z0-9]{16,64}$")


def latest_day(site_dir: Path) -> str | None:
    """Newest day of version 2.0 (v2/dni.json), if its page was built."""
    try:
        days = json.loads((site_dir / "v2" / "dni.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    day = days[0] if isinstance(days, list) and days else ""
    return day if isinstance(day, str) and DAY_RE.match(day) and (site_dir / "v2" / day / "index.html").is_file() else None


def _root_redirect(dest: Path, day: str) -> None:
    """The old root "Przegląd" moves to /przeglad.html (links from dziennik/ and zdarzenia/ follow); / jumps to the newest day.
    Target is the directory form /v2/DAY/ (Pages answers .html and index.html with a 308 to it)."""
    old = dest / "index.html"
    old.rename(dest / "przeglad.html")
    page = dest / "przeglad.html"
    page.write_text(page.read_text(encoding="utf-8").replace('href="index.html', 'href="przeglad.html'), encoding="utf-8")
    for folder in ("dziennik", "zdarzenia"):
        for sub in (dest / folder).glob("*.html"):
            text = sub.read_text(encoding="utf-8")
            if 'href="../index.html' in text:
                sub.write_text(text.replace('href="../index.html', 'href="../przeglad.html'), encoding="utf-8")
    target = f"/v2/{day}/"
    old.write_text(
        '<!doctype html>\n<html lang="pl"><head><meta charset="utf-8"><meta name="robots" content="noindex, nofollow">'
        f'<meta http-equiv="refresh" content="0; url={target}"><title>Paralaksa</title>'
        f'<script>location.replace("{target}" + location.hash)</script></head>'
        f'<body><p><a href="{target}">Paralaksa</a></p></body></html>\n', encoding="utf-8")


def stage_cf(site_dir: Path, dest: Path, analytics_token: str = "") -> None:
    """Cloudflare Pages: only the built site (no server), plus _headers, robots.txt and a root page that jumps to the newest day.
    The static pages already carry no backend hooks (the person menu, heartbeat and push exist only when the Render server
    injects window.plxJa), so nothing is rewritten except the optional Web Analytics beacon (cookie-free)."""
    if not (site_dir / "index.html").is_file():
        raise RuntimeError(f"brak zbudowanej strony w {site_dir} (najpierw plx site)")
    shutil.copytree(site_dir, dest, ignore=shutil.ignore_patterns("*.zip"), dirs_exist_ok=True)
    (dest / "_headers").write_text(CF_HEADERS, encoding="utf-8")
    (dest / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
    day = latest_day(dest)
    if day:                                                 # a root _redirects rule did not win over the root index.html on Pages
        _root_redirect(dest, day)
    if analytics_token:
        if not CF_TOKEN_RE.match(analytics_token):
            raise RuntimeError("CF_ANALYTICS_TOKEN ma nieprawidłowy format")
        beacon = ('<script defer src="https://static.cloudflareinsights.com/beacon.min.js" '
                  f"data-cf-beacon='{{\"token\": \"{analytics_token}\"}}'></script>")
        for page in dest.rglob("*.html"):
            text = page.read_text(encoding="utf-8")
            if "</body>" in text:
                page.write_text(text.replace("</body>", beacon + "</body>", 1), encoding="utf-8")


def publish_cf(site_dir: Path, project: str, api_token: str, account_id: str, analytics_token: str = "",
               run: Runner = subprocess.run) -> str:
    """Direct upload with wrangler (`npx wrangler pages deploy`): no extra repo, no git history growing. The API token and
    account id go only into the child's environment (never into files or arguments)."""
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,56}", project):
        raise RuntimeError(f"CF_PROJECT ma postać małe-litery-cyfry-myślniki, jest: {project!r}")
    if not api_token or not account_id:
        raise RuntimeError("brak CLOUDFLARE_API_TOKEN lub CLOUDFLARE_ACCOUNT_ID w .env")
    message = f"Strona {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC"
    npx = (shutil.which("npx.cmd") if sys.platform == "win32" else None) or shutil.which("npx") or "npx"
    with tempfile.TemporaryDirectory(prefix="plx-cf-", ignore_cleanup_errors=True) as tmp:
        work = Path(tmp) / "public"
        stage_cf(site_dir, work, analytics_token)
        env = {**os.environ, "CLOUDFLARE_API_TOKEN": api_token, "CLOUDFLARE_ACCOUNT_ID": account_id}
        try:
            _run(run, [npx, "--yes", "wrangler", "pages", "deploy", str(work), "--project-name", project,
                       "--branch", "main", "--commit-message", message, "--commit-dirty=true"], env=env)
        except RuntimeError as e:
            raise RuntimeError(str(e).replace(api_token, "***")) from None
    return message


def _run(run: Runner, args: list[str], cwd: Path | None = None, env: dict | None = None) -> str:
    kw = {"env": env} if env is not None else {}
    res = run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", **kw)
    if res.returncode != 0:
        raise RuntimeError(f"{' '.join(args[:3])}: {(res.stderr or res.stdout).strip()}")
    return (res.stdout or "").strip()


def check_private(repo: str, run: Runner = subprocess.run) -> None:
    if not REPO_RE.match(repo):
        raise RuntimeError(f"SITE_REPO ma postać właściciel/nazwa, jest: {repo!r}")
    visibility = _run(run, ["gh", "repo", "view", repo, "--json", "visibility", "-q", ".visibility"])
    if visibility != "PRIVATE":
        raise RuntimeError(f"repo {repo} nie jest prywatne ({visibility or 'brak odpowiedzi'}); strony nie publikuję")


def publish(site_dir: Path, repo: str, run: Runner = subprocess.run) -> str:
    """Push the site as one commit to the main branch of `repo` (owner/name). Returns the commit message."""
    check_private(repo, run)
    message = f"Strona {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC"
    with tempfile.TemporaryDirectory(prefix="plx-strona-", ignore_cleanup_errors=True) as tmp:
        work = Path(tmp) / "repo"
        stage(site_dir, work)
        _run(run, ["git", "init", "-q", "-b", "main"], work)
        _run(run, ["git", "add", "-A"], work)
        _run(run, ["git", "commit", "-q", "-m", message], work)
        _run(run, ["git", "push", "-q", "--force", f"https://github.com/{repo}.git", "main"], work)
    return message


def publish_hf(site_dir: Path, space: str, token: str, run: Runner = subprocess.run) -> str:
    """Force-push one commit to the Hugging Face Space repo (user/name). The token lives only in the push URL
    (no remote is stored in .git/config) and is masked in errors. Files are under 10 MB, so no Git LFS is needed."""
    if not REPO_RE.match(space):
        raise RuntimeError(f"HF_SPACE ma postać użytkownik/nazwa, jest: {space!r}")
    if not token:
        raise RuntimeError("brak HF_TOKEN w .env")
    message = f"Strona {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC"
    with tempfile.TemporaryDirectory(prefix="plx-hf-", ignore_cleanup_errors=True) as tmp:
        work = Path(tmp) / "repo"
        stage_hf(site_dir, work)
        _run(run, ["git", "init", "-q", "-b", "main"], work)
        _run(run, ["git", "add", "-A"], work)
        _run(run, ["git", "commit", "-q", "-m", message], work)
        try:
            _run(run, ["git", "push", "-q", "--force", f"https://user:{token}@huggingface.co/spaces/{space}", "main"], work)
        except RuntimeError as e:
            raise RuntimeError(str(e).replace(token, "***")) from None
    return message
