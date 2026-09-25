"""Polite HTTP client: identifying User-Agent, robots.txt, per-domain delay."""

from __future__ import annotations

import logging
import re
import time
from typing import Callable
from urllib.parse import unquote, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

log = logging.getLogger(__name__)


ROBOTS_ATTEMPTS = 2


class RobotsDisallowed(Exception):
    """URL is disallowed by the site's robots.txt."""


def _rule_regex(path: str) -> re.Pattern[str]:
    """Google/RFC 9309 pattern: `*` matches any sequence, trailing `$` anchors the end."""
    anchored = path.endswith("$")
    body = re.escape(path[:-1] if anchored else path).replace(r"\*", ".*")
    return re.compile(body + ("$" if anchored else ""))


class RobotsRules(RobotFileParser):
    """RobotFileParser with RFC 9309 matching: wildcards and longest match wins (Allow on ties).

    The stdlib parser compares plain prefixes, so `Disallow: */feed` never matched `/feed`.
    """

    def can_fetch(self, useragent: str, url: str) -> bool:
        if self.disallow_all:
            return False
        if self.allow_all:
            return True
        if not self.last_checked:
            return False
        parts = urlsplit(url)
        target = unquote(parts.path or "/") + (f"?{unquote(parts.query)}" if parts.query else "")
        entry = next((e for e in self.entries if e.applies_to(useragent)), self.default_entry)
        if entry is None:
            return True
        best: tuple[int, bool] | None = None
        for line in entry.rulelines:
            path = unquote(line.path)
            if not path or not _rule_regex(path).match(target):
                continue
            key = (len(path), line.allowance)  # dłuższa reguła wygrywa, przy remisie Allow
            if best is None or key > best:
                best = key
        return True if best is None else best[1]


class PoliteClient:
    def __init__(
        self,
        user_agent: str,
        per_domain_delay_s: float = 2.0,
        timeout_s: float = 20.0,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.user_agent = user_agent
        self.delay = per_domain_delay_s
        self._sleep = sleep
        self._clock = clock
        self._last_request: dict[str, float] = {}
        self._robots: dict[str, RobotsRules | None] = {}
        self._client = httpx.Client(
            headers={"User-Agent": user_agent},
            timeout=timeout_s,
            follow_redirects=True,
            transport=transport,
        )

    def __enter__(self) -> PoliteClient:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _wait_for_domain(self, host: str) -> None:
        last = self._last_request.get(host)
        if last is not None:
            remaining = self.delay - (self._clock() - last)
            if remaining > 0:
                self._sleep(remaining)
        self._last_request[host] = self._clock()

    def _robots_for(self, url: str) -> RobotsRules | None:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            parser = RobotsRules()
            parser.disallow_all = True  # nie pobieraj przy nieznanych regułach
            # Przejściowy błąd sieci/serwera nie powinien wyłączać redakcji na cały przebieg.
            for attempt in range(ROBOTS_ATTEMPTS):
                try:
                    self._wait_for_domain(parts.netloc)
                    resp = self._client.get(f"{origin}/robots.txt")
                except httpx.HTTPError as e:
                    log.warning("Nie udało się pobrać robots.txt z %s (próba %d): %s", origin, attempt + 1, e)
                    continue
                if resp.status_code >= 500 or resp.status_code == 429:
                    log.warning("robots.txt z %s: HTTP %s (próba %d)", origin, resp.status_code, attempt + 1)
                    continue
                parser = RobotsRules()
                if resp.status_code in (401, 403):
                    parser.disallow_all = True
                elif resp.status_code >= 400:  # 404/410 i inne 4xx: brak reguł
                    parser.allow_all = True
                else:
                    parser.parse(resp.text.splitlines())
                break
            self._robots[origin] = parser
        return self._robots[origin]

    def allowed(self, url: str) -> bool:
        parser = self._robots_for(url)
        return True if parser is None else parser.can_fetch(self.user_agent, url)

    def get(self, url: str) -> httpx.Response:
        if not self.allowed(url):
            raise RobotsDisallowed(url)
        self._wait_for_domain(urlsplit(url).netloc)
        resp = self._client.get(url)
        resp.raise_for_status()
        return resp
