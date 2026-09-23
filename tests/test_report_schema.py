import pytest

from paralaksa.aggregate.package import build_data_package, known_article_ids
from paralaksa.config import load_themes
from paralaksa.report.schema import ReportOutput, parse_report
from paralaksa.report.validate import long_quotes, sanitize_report, shorten_quotes, validate_report
from report_fixtures import as_text, mutate, valid_report
from seed import DAY, seed_alarm_convergence, seed_sources

THEMES = load_themes()


@pytest.fixture
def data(conn, settings):
    seed_sources(conn)
    ids = seed_alarm_convergence(conn)
    package = build_data_package(conn, DAY, settings, THEMES)
    return ids, package, known_article_ids(conn, DAY)


def check(report: dict, package, known) -> list[str]:
    parsed, errors = parse_report(as_text(report))
    assert parsed is not None, errors
    return validate_report(parsed, package, known)


def test_valid_report_passes(data):
    ids, package, known = data
    assert check(valid_report(ids), package, known) == []


def test_parse_errors():
    assert parse_report("nie ma tu JSON-a")[1][0].startswith("niepoprawny JSON")
    report, errors = parse_report('{"w_skrocie": [{"tekst": "x", "pewnosc": "pewny"}]}')
    assert report is None and "w_skrocie.0.pewnosc" in errors[0]
    report, errors = parse_report('{"wzorce_zbieznosci": [{"temat": "x"}]}')
    assert report is None and any("sygnaly_przeciwne" in e for e in errors)   # brak sekcji = błąd


def test_missing_references_detected(data):
    ids, package, known = data
    r = mutate(valid_report(ids), lambda r: r["w_skrocie"][0].update(article_ids=[]))
    assert any("w_skrocie.0: twierdzenie bez odnośnika" in e for e in check(r, package, known))
    r = mutate(valid_report(ids), lambda r: r["slabe_sygnaly"][0].update(article_ids=[999_999]))
    assert any("nieistniejące article_ids [999999]" in e for e in check(r, package, known))
    r = mutate(valid_report(ids), lambda r: r["wzorce_zbieznosci"][0]["kraje"][0].update(article_ids=[]))
    assert any("kraje.PL: twierdzenie bez odnośnika" in e for e in check(r, package, known))


def test_counter_signals_may_be_empty_but_must_exist(data):
    ids, package, known = data
    r = mutate(valid_report(ids), lambda r: r["wzorce_zbieznosci"][0]["sygnaly_przeciwne"].update(
        tekst="Brak sygnałów przeciwnych w danych.", article_ids=[]))
    assert check(r, package, known) == []
    r = mutate(valid_report(ids), lambda r: r["wzorce_zbieznosci"][0]["sygnaly_przeciwne"].update(article_ids=[42_000]))
    assert any("sygnaly_przeciwne: nieistniejące" in e for e in check(r, package, known))


def test_pattern_thresholds_and_trend(data):
    ids, package, known = data
    r = mutate(valid_report(ids), lambda r: r["wzorce_zbieznosci"][0].update(temat="energy"))
    assert any("nie jest kandydatem" in e for e in check(r, package, known))
    r = mutate(valid_report(ids), lambda r: r["wzorce_zbieznosci"][0].update(
        kraje=r["wzorce_zbieznosci"][0]["kraje"][:2]))
    assert any("wymagane co najmniej 3" in e for e in check(r, package, known))
    r = valid_report(ids, trend="rośnie od 5 dni")
    assert any("trend: brak linii bazowej" in e for e in check(r, package, known))


def test_long_quotes():
    long = "„" + " ".join(["słowo"] * 16) + "”"
    assert long_quotes("krótki „cytat w cudzysłowie” jest ok") == []
    assert len(long_quotes(f"media piszą {long}")) == 1
    assert len(long_quotes('"' + " ".join(["word"] * 20) + '"')) == 1
    assert shorten_quotes(long).count("słowo") == 15


def test_long_quote_in_report_detected(data):
    ids, package, known = data
    quote = "„" + " ".join(["słowo"] * 20) + "”"
    r = mutate(valid_report(ids), lambda r: r["w_skrocie"][0].update(tekst=f"Media piszą {quote}."))
    assert any("cytat dłuższy niż 15 słów" in e for e in check(r, package, known))


def test_sanitize_drops_unbacked_claims(data):
    ids, package, known = data
    quote = "„" + " ".join(["słowo"] * 20) + "”"

    def break_it(r):
        r["w_skrocie"].append({"tekst": f"Bez źródła {quote}", "pewnosc": "niski", "article_ids": [999]})
        r["w_skrocie"][0]["tekst"] += f" {quote}"
        r["wzorce_zbieznosci"][0]["trend"] = "rośnie"
        r["wzorce_zbieznosci"][0]["kraje"][0]["article_ids"] = [999] + ids["pl"]
        r["slabe_sygnaly"][0]["article_ids"] = [999]
    parsed, _ = parse_report(as_text(mutate(valid_report(ids), break_it)))
    clean = sanitize_report(parsed, package, known)
    assert validate_report(clean, package, known) == []
    assert len(clean.w_skrocie) == 1 and clean.slabe_sygnaly == []
    assert clean.wzorce_zbieznosci[0].trend == "brak linii bazowej"
    assert clean.wzorce_zbieznosci[0].kraje[0].article_ids == ids["pl"]


def test_sanitize_drops_pattern_below_threshold(data):
    ids, package, known = data
    r = mutate(valid_report(ids), lambda r: r["wzorce_zbieznosci"][0].update(temat="energy"))
    parsed, _ = parse_report(as_text(r))
    assert sanitize_report(parsed, package, known).wzorce_zbieznosci == []


def test_empty_report_is_valid(data):
    _, package, known = data
    assert validate_report(ReportOutput(), package, known) == []
