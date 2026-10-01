"""Codex CLI as a local text/vision model (the owner's ChatGPT Pro limit instead of paid API; decision 2026-09-30).

Local steps and experiments only: the CLI is tied to the owner's login on this machine, so it refuses to run in CI.
Model names: "codex" (account default model, effort medium), "codex:low|medium|high", or with a Codex model:
"codex:gpt-6.1-sol:medium". Never "ultra" (eats the limit), nor "xhigh"/"max".
Codex runs read-only in an empty temporary folder, without session files; it only answers, it never touches the repo.
"""

from __future__ import annotations

import base64
import glob
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable

from paralaksa.extract.llm_client import LLMRequest, LLMResult

EFFORTS = {"low", "medium", "high"}
PREAMBLE = ("Odpowiedz wyłącznie treścią odpowiedzi na poniższe polecenie, bez komentarzy i bez uruchamiania poleceń "
            "ani czytania plików. Obrazy (jeśli są) dołączono do wiadomości.\n\n")


def find_codex() -> str | None:
    if os.environ.get("PLX_CODEX"):
        return os.environ["PLX_CODEX"]
    found = sorted(glob.glob(os.path.expandvars(r"%LOCALAPPDATA%\OpenAI\Codex\bin\*\codex.exe")), key=os.path.getmtime)
    return found[-1] if found else None


REFUSED = {"ultra", "xhigh", "max"}


def parse_model(model: str) -> tuple[str | None, str]:
    """"codex[:model][:effort]" -> (Codex model or None for the account default, effort)."""
    codex_model, effort = None, "medium"
    for part in model.split(":")[1:]:
        if part in EFFORTS:
            effort = part
        elif part in REFUSED or not part:
            raise ValueError(f"nieznany poziom rozumowania Codex '{part}' (dozwolone: {', '.join(sorted(EFFORTS))})")
        else:
            codex_model = part
    return codex_model, effort


def effort_of(model: str) -> str:
    return parse_model(model)[1]


def _prompt_and_images(messages: list[dict[str, Any]], folder: Path) -> tuple[str, list[Path]]:
    parts, images = [], []
    for m in messages:
        content = m["content"]
        if isinstance(content, str):
            parts.append(content)
            continue
        for block in content:
            if block.get("type") == "text":
                parts.append(block["text"])
            elif block.get("type") == "image":
                ext = block["source"].get("media_type", "image/png").split("/")[-1]
                path = folder / f"obraz-{len(images) + 1}.{ext}"
                path.write_bytes(base64.b64decode(block["source"]["data"]))
                images.append(path)
    return PREAMBLE + "\n\n".join(parts), images


class CodexClient:
    """Duck-type compatible with LLMClient.complete(); cost is 0 (subscription limit, not billed per token)."""

    def __init__(self, exe: str | None = None, timeout_s: int = 900,
                 run: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> None:
        if os.environ.get("GITHUB_ACTIONS") or os.environ.get("CI"):
            raise RuntimeError("Codex działa tylko lokalnie (konto właściciela); w CI użyj modelu API")
        self.exe = exe or find_codex()
        if not self.exe:
            raise RuntimeError("nie znaleziono codex.exe (zainstaluj Codex albo ustaw PLX_CODEX)")
        self.timeout_s, self._run = timeout_s, run

    def complete(self, req: LLMRequest) -> LLMResult:
        result = LLMResult(custom_id=req.custom_id, model=req.model, mode="direct")
        with tempfile.TemporaryDirectory(prefix="plx-codex-") as tmp:
            folder = Path(tmp)
            prompt, images = _prompt_and_images(req.messages, folder)
            out = folder / "odpowiedz.txt"
            codex_model, effort = parse_model(req.model)
            args = [self.exe, "exec", "--skip-git-repo-check", "--ephemeral", "--sandbox", "read-only", "-C", str(folder),
                    *(["-m", codex_model] if codex_model else []),
                    "-c", f'model_reasoning_effort="{effort}"', "-o", str(out)]
            for img in images:
                args += ["-i", str(img)]
            try:
                proc = self._run(args, input=prompt.encode("utf-8"), capture_output=True, timeout=self.timeout_s)
            except subprocess.TimeoutExpired:
                result.error, result.retryable = f"Codex: przekroczony czas {self.timeout_s} s", True
                return result
            if proc.returncode != 0 or not out.exists():
                tail = (proc.stderr or b"").decode("utf-8", "replace")[-400:]
                result.error, result.retryable = f"Codex: kod {proc.returncode}: {tail}", True
                return result
            result.text = out.read_text(encoding="utf-8").strip()
        result.stop_reason = "end"
        return result
