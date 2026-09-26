"""App icons (PNG) and the web app manifest, so browsers offer to install the site as an app.

The logo is two circles, so it is rasterised here with analytic anti-aliasing (no image library needed). Geometry
follows `build.logo_mark` on its 32×32 grid: a disc at (12.5, 16) and a ring at (19.5, 16), both r = 8, ring 2.6 wide."""
from __future__ import annotations

from functools import lru_cache
import json
import math
import struct
import zlib

BACKGROUND = (0x1C, 0x1C, 0x1A)
INK = (0xFF, 0xFF, 0xFF)
RING = (0xE0, 0x64, 0x3C)
DISC_C, RING_C, R, RING_W = (12.5, 16.0), (19.5, 16.0), 8.0, 2.6

# plik → (rozmiar, zaokrąglone tło, skala logo); maskowalna i Apple wypełniają kwadrat, system sam przycina rogi
ICONS = {
    "icon-192.png": (192, True, 1.0),
    "icon-512.png": (512, True, 1.0),
    "icon-maskable-512.png": (512, False, 0.72),
    "apple-touch-icon.png": (180, False, 0.86),
}
PUBLIC_FILES = ("manifest.webmanifest", *ICONS)   # serwer wydaje je bez hasła (przeglądarka pobiera je bez logowania)


def _clamp(v: float) -> float:
    return 0.0 if v < 0 else 1.0 if v > 1 else v


def _rounded_rect_cover(x: float, y: float, size: int, rx: float) -> float:
    h = size / 2
    qx, qy = abs(x - h) - (h - rx), abs(y - h) - (h - rx)
    d = math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - rx
    return _clamp(0.5 - d)


@lru_cache(maxsize=None)
def render_icon(size: int, rounded: bool, scale: float) -> bytes:
    """RGBA PNG of the logo on the dark background (about 2 s for all icons, so cached per process)."""
    s = size / 32 * scale
    off = size / 2 - 16 * s                       # logo wyśrodkowane
    dc = (off + DISC_C[0] * s, off + DISC_C[1] * s)
    rc = (off + RING_C[0] * s, off + RING_C[1] * s)
    r, r_in, r_out = R * s, (R - RING_W / 2) * s, (R + RING_W / 2) * s
    rows = bytearray()
    for py in range(size):
        rows.append(0)                            # filtr PNG: brak
        y = py + 0.5
        for px in range(size):
            x = px + 0.5
            a = _rounded_rect_cover(x, y, size, 7 / 32 * size) if rounded else 1.0
            col = BACKGROUND
            if a:
                d1 = math.hypot(x - dc[0], y - dc[1])
                c1 = _clamp(r - d1 + 0.5)
                d2 = math.hypot(x - rc[0], y - rc[1])
                c2 = _clamp(min(d2 - r_in, r_out - d2) + 0.5)
                col = tuple(b + (i - b) * c1 for b, i in zip(col, INK))
                col = tuple(b + (i - b) * c2 for b, i in zip(col, RING))
            rows += bytes((round(col[0]), round(col[1]), round(col[2]), round(a * 255)))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(rows), 9)) + chunk(b"IEND", b""))


def manifest() -> str:
    return json.dumps({
        "name": "Paralaksa", "short_name": "Paralaksa", "lang": "pl",
        "description": "Jedno zdarzenie, wiele opowieści. Wersja wewnętrzna.",
        "start_url": "./index.html", "scope": "./", "display": "standalone",
        "background_color": "#151513", "theme_color": "#1c1c1a",
        "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
                  {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
                  {"src": "icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}],
    }, ensure_ascii=False, indent=1)
