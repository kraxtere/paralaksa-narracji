import pytest
from typer.testing import CliRunner

from paralaksa import cli, db
from paralaksa.board.render import BoardError, clip_words, collect_board, plural_pl, render_html
from paralaksa.board.spec import EventSpec


@pytest.fixture
def seeded(conn, make_source):
    db.upsert_sources(conn, [
        make_source(id="pl1", name="Gazeta PL", country="PL", language="pl"),
        make_source(id="de1", name="Zeitung DE", country="DE", language="de", type="public"),
        make_source(id="cn1", name="State CN", country="CN", language="en", type="government"),
    ])

    def add(source_id, title, published, lang):
        return db.insert_article(conn, db.ArticleRow(
            source_id=source_id, url=f"https://{source_id}.example/{published}", url_hash=f"h-{source_id}-{published}",
            title=title, lead=None, language=lang, published_at=published, fetched_at="2026-09-23T16:00:00+00:00",
        ))

    ids = {
        "pl": add("pl1", "Polski nagłówek <b>o zdarzeniu</b>", "2026-09-23T10:00:00+00:00", "pl"),
        "de": add("de1", "Deutsche Schlagzeile", "2026-09-23T08:00:00+00:00", "de"),
        "cn": add("cn1", "Chinese headline", "2026-09-22T12:00:00+00:00", "en"),
    }
    conn.commit()
    return ids


def spec(items) -> EventSpec:
    return EventSpec(id="test", title="Zdarzenie", when="23.09", rule="test", items=items)


def test_board_orders_by_publication_and_groups_by_country(conn, seeded):
    b = collect_board(conn, spec([
        {"article_id": seeded["pl"]},
        {"article_id": seeded["de"], "translation_pl": "Niemiecki nagłówek"},
        {"article_id": seeded["cn"], "translation_pl": "Chiński nagłówek"},
    ]))
    assert [g.country for g in b.groups] == ["CN", "DE", "PL"]
    assert b.groups[2].headlines[0].translation is None   # polski nagłówek bez tłumaczenia


def test_foreign_headline_requires_translation(conn, seeded):
    with pytest.raises(BoardError, match="translation_pl"):
        collect_board(conn, spec([{"article_id": seeded["pl"]}, {"article_id": seeded["de"]}]))


def test_missing_and_duplicate_articles_rejected(conn, seeded):
    with pytest.raises(BoardError, match="brak artykułów"):
        collect_board(conn, spec([{"article_id": seeded["pl"]}, {"article_id": 999}]))
    with pytest.raises(BoardError, match="powtórzony"):
        collect_board(conn, spec([{"article_id": seeded["pl"]}, {"article_id": seeded["pl"]}]))


def test_quote_clipped_to_15_words():
    long = " ".join(f"w{i}" for i in range(20))
    assert clip_words(long) == " ".join(f"w{i}" for i in range(15)) + " …"
    assert clip_words("krótki nagłówek") == "krótki nagłówek"


def test_polish_plurals():
    assert plural_pl(1, "kraj", "kraje", "krajów") == "1 kraj"
    assert plural_pl(4, "kraj", "kraje", "krajów") == "4 kraje"
    assert plural_pl(5, "kraj", "kraje", "krajów") == "5 krajów"
    assert plural_pl(12, "kraj", "kraje", "krajów") == "12 krajów"
    assert plural_pl(22, "kraj", "kraje", "krajów") == "22 kraje"


def test_html_escapes_headlines_and_shows_attribution(conn, seeded):
    b = collect_board(conn, spec([
        {"article_id": seeded["pl"]},
        {"article_id": seeded["cn"], "translation_pl": "Chiński nagłówek"},
    ]))
    out = render_html(b)
    assert "&lt;b&gt;o zdarzeniu&lt;/b&gt;" in out
    assert "State CN" in out and "państwowe" in out and "cn1.example" in out
    assert "2 kraje · 2 nagłówki" in out


def test_cli_board_writes_html(tmp_path, seeded, conn, monkeypatch):
    db_path = tmp_path / "b.db"
    disk = db.connect(db_path)
    conn.backup(disk)
    disk.close()
    event = tmp_path / "e.yaml"
    event.write_text(
        f"id: e1\ntitle: Zdarzenie\nwhen: '23.09'\nrule: test\nitems:\n"
        f"  - article_id: {seeded['pl']}\n  - article_id: {seeded['de']}\n    translation_pl: Nagłówek\n",
        encoding="utf-8",
    )
    result = CliRunner().invoke(cli.app, ["board", str(event), "--no-png", "--db", str(db_path),
                                          "-o", str(tmp_path / "out")])
    assert result.exit_code == 0, result.output
    assert "Zeitung DE" in (tmp_path / "out" / "e1.html").read_text(encoding="utf-8")
