"""Password-protected static server for the internal site (Render web service, standard library only).

Serves ./public behind HTTP Basic Auth. Credentials come from SITE_USER and SITE_PASSWORD; without them
every request gets 503, so a misconfigured deploy never exposes the site."""
import base64
import hmac
import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "public"
USER = os.environ.get("SITE_USER", "")
PASSWORD = os.environ.get("SITE_PASSWORD", "")
EXPECTED = b"Basic " + base64.b64encode(f"{USER}:{PASSWORD}".encode()) if USER and PASSWORD else None


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("X-Robots-Tag", "noindex, nofollow")
        self.send_header("Cache-Control", "private, no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    def _allowed(self) -> bool:
        if EXPECTED is None:
            self.send_error(503, "SITE_USER / SITE_PASSWORD not set")
            return False
        if hmac.compare_digest(self.headers.get("Authorization", "").encode(), EXPECTED):
            return True
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Paralaksa", charset="UTF-8"')
        self.send_header("Content-Length", "0")
        self.end_headers()
        return False

    def do_GET(self) -> None:
        if self._allowed():
            super().do_GET()

    def do_HEAD(self) -> None:
        if self._allowed():
            super().do_HEAD()

    def list_directory(self, path):
        self.send_error(404)
        return None

    def log_message(self, format, *args) -> None:
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    ThreadingHTTPServer(("0.0.0.0", port), partial(Handler, directory=str(ROOT))).serve_forever()
