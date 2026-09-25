from datetime import datetime, timezone

import httpx
import pytest

from paralaksa.ingest.fulltext import extract_text, strip_boilerplate, truncate_words
from paralaksa.ingest.http import PoliteClient
from paralaksa.ingest.rss import clean_html, clean_link, ingest_sources, parse_feed

NOW = datetime(2026, 9, 23, 9, 0, tzinfo=timezone.utc)


def make_client(routes: dict[str, httpx.Response | bytes | str], calls: list[str] | None = None, **kw) -> PoliteClient:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if calls is not None:
            calls.append(url)
        resp = routes.get(url)
        if resp is None:
            if url.endswith("/robots.txt"):
                return httpx.Response(404)
            return httpx.Response(404, text="not found")
        return resp if isinstance(resp, httpx.Response) else httpx.Response(200, content=resp)

    return PoliteClient("paralaksa-test/0.1", per_domain_delay_s=0, transport=httpx.MockTransport(handler), **kw)


# ------------------------------------------------------------------ parse_feed

def test_parse_rss2(fixtures_dir):
    entries = parse_feed((fixtures_dir / "rss2.xml").read_bytes())
    assert len(entries) == 5  # wpis bez tytułu pominięty
    first = entries[0]
    assert first.title == "NATO strengthens eastern flank amid rising tensions"
    assert first.lead == "Allies agreed to deploy additional troops & air defence."
    assert first.published == datetime(2026, 9, 23, 5, 30, tzinfo=timezone.utc)
    assert first.categories == ["Europe"]
    assert entries[4].published is None


def test_parse_atom(fixtures_dir):
    entries = parse_feed((fixtures_dir / "atom.xml").read_bytes())
    assert [e.url for e in entries] == [
        "https://nachrichten.example.de/ausland/ostflanke-123.html",
        "https://nachrichten.example.de/wetter/sturm-456.html",
    ]
    assert entries[0].published == datetime(2026, 9, 23, 5, 45, tzinfo=timezone.utc)
    assert entries[0].lead == "Die Bundesregierung kündigt neue Maßnahmen an."


def test_parse_rdf(fixtures_dir):
    (entry,) = parse_feed((fixtures_dir / "rdf.xml").read_bytes())
    assert entry.title == "Україна отримала нову партію ППО"
    assert entry.published == datetime(2026, 9, 23, 5, 54, 2, tzinfo=timezone.utc)


def test_parse_invalid_feed_raises():
    with pytest.raises(ValueError):
        parse_feed(b"<html><body>Not found.</body></html>")


def test_parse_empty_valid_feed():
    assert parse_feed(b'<?xml version="1.0"?><rss version="2.0"><channel><title>t</title></channel></rss>') == []


def test_clean_link():
    assert clean_link("https://www.ukrinform.uahttps://archive.example/v/1") == "https://archive.example/v/1"
    assert clean_link(" https://a.example/x ") == "https://a.example/x"
    assert clean_link("javascript:void(0)") is None


def test_strip_boilerplate():
    text = (
        "By continuing to browse our site you agree to our use of cookies, revised Privacy Policy.\n"
        "Trump said the deal gives the US control.\n"
        "EU debates new rules on tracking cookies in browsers."
    )
    assert strip_boilerplate(text) == (
        "Trump said the deal gives the US control.\nEU debates new rules on tracking cookies in browsers."
    )


def test_clean_html():
    assert clean_html("<p>A&nbsp;<b>b</b></p>\n c") == "A b c"
    assert clean_html("") is None


# ------------------------------------------------------------------ ingest

def test_ingest_stores_filters_and_dedups(conn, settings, make_source, fixtures_dir):
    feed_url = "https://news.example.com/rss.xml"
    source = make_source(url=feed_url)
    routes = {feed_url: (fixtures_dir / "rss2.xml").read_bytes()}

    with make_client(routes) as client:
        (result,) = ingest_sources(conn, client, [source], settings, fulltext=False, now=NOW)
    assert result.fetched == 5
    assert result.filtered == 1  # Champions League
    assert result.new == 4
    assert result.errors == []

    rows = conn.execute("SELECT url, title, language, published_at FROM articles ORDER BY id").fetchall()
    assert rows[0]["url"] == "https://news.example.com/world/nato-eastern-flank"  # bez utm_*
    assert rows[0]["published_at"] == "2026-09-23T05:30:00+00:00"
    assert rows[0]["language"] == "en"
    undated = [r for r in rows if r["title"] == "Item without a date"][0]
    assert undated["published_at"] is None  # brak daty nie jest datą pobrania

    # Drugie uruchomienie: nic nowego
    with make_client(routes) as client:
        (again,) = ingest_sources(conn, client, [source], settings, fulltext=False, now=NOW)
    assert again.new == 0
    assert again.duplicates == 4
    log = conn.execute("SELECT status, n_items, n_new FROM fetch_log ORDER BY id").fetchall()
    assert [tuple(r) for r in log] == [("ok", 5, 4), ("ok", 5, 0)]


def test_ingest_title_dedup_within_source(conn, settings, make_source):
    feed_url = "https://news.example.com/rss.xml"
    rss = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
    <item><title>NATO strengthens eastern flank</title><link>https://news.example.com/a</link>
      <pubDate>Wed, 23 Sep 2026 07:00:00 GMT</pubDate></item>
    <item><title>NATO strengthens eastern flank.</title><link>https://news.example.com/a-updated</link>
      <pubDate>Wed, 23 Sep 2026 08:00:00 GMT</pubDate></item>
    </channel></rss>"""
    with make_client({feed_url: rss}) as client:
        (result,) = ingest_sources(conn, client, [make_source(url=feed_url)], settings, fulltext=False, now=NOW)
    assert result.new == 1
    assert result.duplicates == 1


def test_ingest_feed_error_is_logged(conn, settings, make_source):
    feed_url = "https://news.example.com/rss.xml"
    with make_client({feed_url: httpx.Response(500)}) as client:
        (result,) = ingest_sources(conn, client, [make_source(url=feed_url)], settings, fulltext=False, now=NOW)
    assert result.new == 0
    assert len(result.errors) == 1
    assert conn.execute("SELECT status FROM fetch_log").fetchone()[0] == "error"


def test_ingest_respects_robots(conn, settings, make_source):
    feed_url = "https://news.example.com/rss.xml"
    routes = {
        "https://news.example.com/robots.txt": httpx.Response(200, text="User-agent: *\nDisallow: /rss.xml\n"),
        feed_url: b"<rss/>",
    }
    calls: list[str] = []
    with make_client(routes, calls) as client:
        (result,) = ingest_sources(conn, client, [make_source(url=feed_url)], settings, fulltext=False, now=NOW)
    assert feed_url not in calls
    assert "robots" in result.errors[0]
    assert conn.execute("SELECT status FROM fetch_log").fetchone()[0] == "robots_disallowed"


def test_ingest_fulltext(conn, settings, make_source, fixtures_dir):
    feed_url = "https://news.example.com/rss.xml"
    article_url = "https://news.example.com/world/nato-eastern-flank"
    rss = f"""<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
    <item><title>NATO strengthens eastern flank</title><link>{article_url}</link>
      <pubDate>Wed, 23 Sep 2026 07:00:00 GMT</pubDate></item>
    <item><title>Broken article</title><link>https://news.example.com/world/broken</link>
      <pubDate>Wed, 23 Sep 2026 07:00:00 GMT</pubDate></item>
    </channel></rss>""".encode()
    routes = {feed_url: rss, article_url: (fixtures_dir / "article.html").read_bytes()}
    settings.ingest.max_fulltext_words = 20

    with make_client(routes) as client:
        (result,) = ingest_sources(conn, client, [make_source(url=feed_url, fulltext=True)], settings, now=NOW)
    assert result.new == 2
    assert result.fulltext_ok == 1
    texts = dict(conn.execute("SELECT url, fulltext FROM articles").fetchall())
    assert "Allied defence ministers agreed" in texts[article_url]
    assert len(texts[article_url].split()) == 20
    assert texts["https://news.example.com/world/broken"] is None  # zostaje tytuł + lead


def test_fulltext_skipped_for_source_without_flag(conn, settings, make_source, fixtures_dir):
    feed_url = "https://news.example.com/rss.xml"
    calls: list[str] = []
    with make_client({feed_url: (fixtures_dir / "rss2.xml").read_bytes()}, calls) as client:
        ingest_sources(conn, client, [make_source(url=feed_url, fulltext=False)], settings, now=NOW)
    assert all(c in (feed_url, "https://news.example.com/robots.txt") for c in calls)


# ------------------------------------------------------------------ polite client

def test_per_domain_delay():
    clock = [0.0]
    sleeps: list[float] = []

    def sleep(s: float) -> None:
        sleeps.append(s)
        clock[0] += s

    routes = {
        "https://a.example/1": b"x", "https://a.example/2": b"x", "https://b.example/1": b"x",
    }
    client = make_client(routes, sleep=sleep, clock=lambda: clock[0])
    client.delay = 2.0
    client.get("https://a.example/1")  # robots.txt, potem strona po 2 s
    client.get("https://b.example/1")  # inna domena: robots.txt od razu, strona po 2 s
    client.get("https://a.example/2")  # od ostatniego zapytania do a.example minęły już 2 s
    client.close()
    assert sleeps == [2.0, 2.0]


def test_fulltext_helpers(fixtures_dir):
    text = extract_text((fixtures_dir / "article.html").read_text(encoding="utf-8"))
    assert "Allied defence ministers" in text
    assert "Copyright" not in text
    assert truncate_words("a b c d", 2) == "a b"
    assert truncate_words("a b", 5) == "a b"


def test_parse_google_news_sitemap():
    xml = """<?xml version="1.0" encoding="utf-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
  <url><loc>https://www.globaltimes.cn/page/202609/1.shtml</loc>
    <news:news><news:publication><news:name>Global Times</news:name><news:language>en</news:language></news:publication>
      <news:publication_date>2026-09-25T07:48:03+08:00</news:publication_date>
      <news:title>China sweep 3 golds in canoe sprint</news:title><news:keywords>canoe,gold,</news:keywords></news:news></url>
  <url><loc>https://www.globaltimes.cn/page/202609/2.shtml</loc></url>
</urlset>"""
    entries = parse_feed(xml.encode("utf-8"))
    assert len(entries) == 1  # bez news:title pomijamy
    e = entries[0]
    assert e.url == "https://www.globaltimes.cn/page/202609/1.shtml" and e.lead is None
    assert e.published == datetime(2026, 9, 24, 23, 48, 3, tzinfo=timezone.utc)
    assert e.categories == ["canoe", "gold"]


def test_truncate_words_cjk_by_characters():
    zh = "日本政府及执政党相关人士近日透露" * 200  # bez spacji: jedno „słowo”
    out = truncate_words(zh, 100)
    assert len(out) == 130
    assert truncate_words("one two three", 2) == "one two"
