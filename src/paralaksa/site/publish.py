"""Publish the built site to a separate private GitHub repo (deployed by Render as a password-protected web service).

Every publish replaces the repo content with a single fresh commit (force push), so the repo never grows with
old builds. Refuses to push unless GitHub reports the repo as private."""
from __future__ import annotations

import re
import shutil
import subprocess
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


def _run(run: Runner, args: list[str], cwd: Path | None = None) -> str:
    res = run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8")
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
