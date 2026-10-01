"""Ad hoc: logo (ikona strony) każdego źródła do widoku 2.0 -> data/logos/<id>.png (64×64).
Ze strony głównej wydawcy: apple-touch-icon, potem największa ikona z <link rel=icon>, na końcu /favicon.ico. Respektuje robots.txt.
  python scripts/v2/loga.py [ID ...]
"""
import io
import re
import sys
import urllib.robotparser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx
from PIL import Image

from paralaksa.config import load_settings, load_sources

OUT = Path("data/logos")
UA = load_settings().ingest.user_agent
HOME = {"bbc": "https://www.bbc.com/", "folha": "https://www1.folha.uol.com.br/", "fox": "https://www.foxnews.com/",
        "npr": "https://www.npr.org/", "israelhayom": "https://www.israelhayom.com/", "izvestia": "https://iz.ru/",
        "globaltimes": "https://www.globaltimes.cn/", "hurriyet": "https://www.hurriyetdailynews.com/"}


def allowed(url: str, cache: dict) -> bool:
    base = "{0.scheme}://{0.netloc}".format(urlsplit(url))
    if base not in cache:
        rp = urllib.robotparser.RobotFileParser()
        try:
            r = httpx.get(base + "/robots.txt", headers={"User-Agent": UA}, timeout=15, follow_redirects=True)
            if r.status_code in (401, 403):
                rp.disallow_all = True
            elif r.status_code < 400:
                rp.parse(r.text.splitlines())
            else:
                rp.allow_all = True
        except httpx.HTTPError:
            rp.disallow_all = True
        cache[base] = rp
    return cache[base].can_fetch(UA, url)


def icon_candidates(home: str, page: str) -> list[str]:
    found = []
    for tag in re.findall(r"<link\b[^>]*>", page, flags=re.I):
        rel = (re.search(r'rel=["\']([^"\']+)', tag, re.I) or [None, ""])[1].lower()
        href = re.search(r'href=["\']([^"\']+)', tag, re.I)
        if not href or "icon" not in rel or "mask" in rel:
            continue
        size = re.search(r'sizes=["\'](\d+)x', tag, re.I)
        score = (2 if "apple" in rel else 1, int(size[1]) if size else 0)
        found.append((score, urljoin(home, href[1].replace("&amp;", "&"))))
    return [u for _, u in sorted(found, reverse=True)] + [urljoin(home, "/favicon.ico")]


def fetch_logo(src, robots: dict) -> str:
    feed = src.feeds[0].url
    home = HOME.get(src.id) or "{0.scheme}://{0.netloc}/".format(urlsplit(feed))
    with httpx.Client(headers={"User-Agent": UA}, timeout=20, follow_redirects=True) as c:
        page = ""
        if allowed(home, robots):
            try:
                page = c.get(home).text
            except httpx.HTTPError:
                pass
        for url in icon_candidates(home, page):
            if url.endswith(".svg") or not allowed(url, robots):
                continue
            try:
                r = c.get(url)
                im = Image.open(io.BytesIO(r.content))
                if getattr(im, "n_frames", 1) > 1 or im.format == "ICO":
                    im = max((im.ico.getimage(s) for s in im.ico.sizes()), key=lambda i: i.width) \
                        if im.format == "ICO" else im
                im = im.convert("RGBA")
                im.thumbnail((64, 64))
                im.save(OUT / f"{src.id}.png")
                return f"{im.width}px {url}"
            except Exception:
                continue
    return "BRAK"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    want = set(sys.argv[1:])
    robots: dict = {}
    for s in load_sources():
        if (want and s.id not in want) or (not want and not s.active) or not s.feeds:
            continue
        print(f"{s.id:14} {fetch_logo(s, robots)}")


if __name__ == "__main__":
    main()
