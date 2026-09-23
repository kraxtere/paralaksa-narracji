from datetime import datetime, timedelta, timezone

from paralaksa import db


def _article(url="https://a.example/1", h="h1", title="T", published="2026-09-23T06:00:00+00:00"):
    return db.ArticleRow(
        source_id="test", url=url, url_hash=h, title=title, lead=None,
        language="en", published_at=published, fetched_at="2026-09-23T07:00:00+00:00",
    )


def test_schema_tables(conn):
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"sources", "articles", "signals", "daily_metrics", "reports", "fetch_log", "schema_version"} <= tables
    assert conn.execute("SELECT version FROM schema_version").fetchone()[0] == db.SCHEMA_VERSION


def test_init_db_idempotent(conn):
    db.init_db(conn)
    assert conn.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0] == 1


def test_upsert_sources_updates(conn, make_source):
    db.upsert_sources(conn, [make_source(name="Old")])
    db.upsert_sources(conn, [make_source(name="New")])
    rows = conn.execute("SELECT name FROM sources").fetchall()
    assert [r["name"] for r in rows] == ["New"]


def test_insert_article_ignores_duplicate(conn, make_source):
    db.upsert_sources(conn, [make_source()])
    assert db.insert_article(conn, _article()) is not None
    assert db.insert_article(conn, _article()) is None
    assert db.url_hash_exists(conn, "h1")
    assert conn.execute("SELECT extracted FROM articles").fetchone()[0] == 0


def test_recent_titles_window(conn, make_source):
    db.upsert_sources(conn, [make_source()])
    db.insert_article(conn, _article(title="fresh"))
    db.insert_article(conn, _article(url="https://a.example/2", h="h2", title="old", published="2026-09-01T00:00:00+00:00"))
    since = datetime(2026, 9, 21, tzinfo=timezone.utc)
    assert db.recent_titles(conn, "test", since) == ["fresh"]


def test_stale_sources(conn, make_source):
    db.upsert_sources(conn, [make_source("a"), make_source("b"), make_source("c")])
    now = datetime(2026, 9, 23, 12, tzinfo=timezone.utc)
    iso = lambda d: db.to_iso(now - timedelta(days=d))
    # a: obserwowane od 3 dni, nowe artykuły tylko 3 dni temu -> stale
    db.log_fetch(conn, "a", "u", iso(3), "ok", 10, 5)
    db.log_fetch(conn, "a", "u", iso(1), "ok", 10, 0)
    # b: nowe artykuły wczoraj -> ok
    db.log_fetch(conn, "b", "u", iso(3), "ok", 10, 5)
    db.log_fetch(conn, "b", "u", iso(1), "ok", 10, 2)
    # c: obserwowane dopiero od wczoraj -> jeszcze bez ostrzeżenia
    db.log_fetch(conn, "c", "u", iso(1), "error", error="boom")
    assert db.stale_sources(conn, ["a", "b", "c"], days=2, now=now) == ["a"]
