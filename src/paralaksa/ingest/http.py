"""Polite HTTP client: identifying User-Agent, robots.txt, per-domain delay."""

from __future__ import annotations

import logging
import time
from typing import Callable
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

log = logging.getLogger(__name__)


class RobotsDisallowed(Exception):
    """URL is disallowed by the site's robots.txt."""


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
        self._robots: dict[str, RobotFileParser | None] = {}
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

    def _robots_for(self, url: str) -> RobotFileParser | None:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            parser: RobotFileParser | None = RobotFileParser()
            try:
                self._wait_for_domain(parts.netloc)
                resp = self._client.get(f"{origin}/robots.txt")
                if resp.status_code in (401, 403):
                    parser.disallow_all = True
                elif resp.status_code >= 400:
                    parser.allow_all = True
                else:
                    parser.parse(resp.text.splitlines())
            except httpx.HTTPError as e:
                log.warning("Nie udało się pobrać robots.txt z %s: %s", origin, e)
                parser = None  # brak informacji: nie blokujemy, ale logujemy
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
