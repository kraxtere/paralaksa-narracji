"""App icons (PNG) and the web app manifest, so browsers offer to install the site as an app.

The icons are the logo's sign („Gazeta w kadrze”, assets/logo/ikona-ciemne-tlo.svg) on the dark background, rendered once
with Chrome into assets/icons/ (the build only copies them): rounded 192 and 512, a maskable 512 with a wider margin
(the system cuts its own shape) and the Apple icon (square, iOS rounds the corners)."""
from __future__ import annotations

import json
from pathlib import Path

ICON_DIR = Path(__file__).parent / "assets" / "icons"
ICONS = ("icon-192.png", "icon-512.png", "icon-maskable-512.png", "apple-touch-icon.png")
PUBLIC_FILES = ("manifest.webmanifest", *ICONS)   # serwer wydaje je bez hasła (przeglądarka pobiera je bez logowania)


def icon_png(name: str) -> bytes:
    return (ICON_DIR / name).read_bytes()


def manifest() -> str:
    return json.dumps({
        "name": "Paralaksa", "short_name": "Paralaksa", "lang": "pl",
        "description": "Jedno zdarzenie, wiele opowieści. Wersja wewnętrzna.",
        "start_url": "./", "scope": "./", "display": "standalone",   # serwer otwiera pod / najnowszy dzień wersji 2.0
        "background_color": "#151513", "theme_color": "#1c1c1a",
        "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
                  {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
                  {"src": "icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}],
    }, ensure_ascii=False, indent=1)
