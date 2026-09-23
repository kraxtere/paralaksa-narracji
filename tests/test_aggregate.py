from datetime import date, timedelta

import pytest

from paralaksa.aggregate.metrics import compute_daily_metrics, day_signals
from paralaksa.aggregate.package import build_data_package, known_article_ids, representative
from paralaksa.aggregate.stats import coarse_direction, distribution, js_divergence, z_score
from paralaksa.config import load_themes
from seed import DAY, article, article_with, seed_alarm_convergence, seed_sources, signal

THEMES = load_themes()


def days_before(n: int) -> str:
    return (date.fromisoformat(DAY) - timedelta(days=n)).isoformat()


# ------------------------------------------------------------------ stats

def test_z_score():
    assert z_score(0.3, [0.1, 0.2], min_history=14) is None            # za krótka historia
    assert z_score(0.3, [0.1] * 20, min_history=14) is None             # zerowa wariancja
    history = [0.1, 0.3] * 7                                             # średnia 0.2, s = 0.1038
    assert z_score(0.4, history, min_history=14) == pytest.approx(1.927, abs=1e-3)


def test_js_divergence():
    p = distribution(["alarm", "alarm", "neutralny"])
    assert js_divergence(p, p) == pytest.approx(0.0)
    assert js_divergence({"alarm": 1.0}, {"poparcie": 1.0}) == pytest.approx(1.0)
    # p=(1/2,1/2), q=(1,0): JS = 0.5*KL(p||m) + 0.5*KL(q||m), m=(3/4,1/4) -> 0.3113
    assert js_divergence({"a": 0.5, "b": 0.5}, {"a": 1.0}) == pytest.approx(0.3113, abs=1e-4)
    assert js_divergence(p, {"poparcie": 1.0}) == js_divergence({"poparcie": 1.0}, p)


def test_coarse_direction_and_distribution():
    assert [coarse_direction(s) for s in ("alarm", "krytyka", "poparcie", "uspokojenie", "neutralny")] == \
        ["negatywny", "negatywny", "pozytywny", "pozytywny", "neutralny"]
    d = distribution(["alarm", "alarm", "krytyka", "neutralny"])
    assert d["alarm"] == 0.5 and d["poparcie"] == 0.0 and sum(d.values()) == pytest.approx(1.0)


# ------------------------------------------------------------------ daily metrics

def test_daily_metrics_normalized_to_all_country_articles(conn):
    seed_sources(conn)
    a1 = article_with(conn, "pl1", theme="energy", frame="ceny rosną", intensity=4)
    signal(conn, a1, theme="energy", frame="ceny rosną", intensity=2)   # drugi sygnał tego samego artykułu
    article_with(conn, "pl2", theme="energy", frame="bezpieczeństwo dostaw", intensity=3)
    article(conn, "pl1")                      # artykuł bez sygnałów też liczy się do wolumenu
    article(conn, "pl2")
    article_with(conn, "ua1", theme="energy", frame="ataki na sieć", day=days_before(1))  # inny dzień
    conn.commit()

    rows = compute_daily_metrics(conn, DAY)
    assert len(rows) == 1
    r = rows[0]
    assert (r["theme_id"], r["country"], r["n_articles"], r["n_sources"]) == ("energy", "PL", 2, 2)
    assert r["article_share"] == pytest.approx(0.5)                      # 2 z 4 artykułów PL
    assert r["dominant_frame"] == "ceny rosną"
    assert r["mean_intensity"] == pytest.approx(3.0)
    saved = conn.execute("SELECT COUNT(*) FROM daily_metrics WHERE date = ?", (DAY,)).fetchone()[0]
    assert saved == 1


def test_daily_metrics_rerun_replaces_rows(conn):
    seed_sources(conn)
    a = article_with(conn, "pl1", theme="energy")
    conn.commit()
    compute_daily_metrics(conn, DAY)
    conn.execute("UPDATE signals SET theme_id = 'russia' WHERE article_id = ?", (a,))
    compute_daily_metrics(conn, DAY)
    themes = [r[0] for r in conn.execute("SELECT theme_id FROM daily_metrics WHERE date = ?", (DAY,))]
    assert themes == ["russia"]


# ------------------------------------------------------------------ data package (1 dzień)

@pytest.fixture
def one_day(conn, settings):
    seed_sources(conn)
    ids = seed_alarm_convergence(conn)
    return ids


def test_package_single_day_has_no_baseline(conn, settings, one_day):
    pkg = build_data_package(conn, DAY, settings, THEMES)
    assert pkg["linia_bazowa"]["dostepna"] is False
    assert "brak linii bazowej" in pkg["linia_bazowa"]["uwaga"]
    assert pkg["co_sie_przesuwa"] == [] and pkg["rozlewanie"] == []
    topic = next(t for t in pkg["tematy"] if t["temat"] == "security_defense")
    assert topic["nazwa"] != "security_defense"
    assert "srednia_28d" not in topic["kraje"]["PL"] and topic["kraje"]["PL"]["n_zrodel"] == 2
    assert topic["kraje"]["PL"]["udzial"] == 1.0


def test_convergence_candidate_with_counter_signals(conn, settings, one_day):
    pkg = build_data_package(conn, DAY, settings, THEMES)
    [cand] = pkg["zbieznosc_kandydaci"]
    assert cand["temat"] == "security_defense" and cand["kierunek"] == "negatywny"
    assert [k["kraj"] for k in cand["kraje"]] == ["DE", "PL", "UA", "UK"]
    assert all(k["spelnia_prog_zrodel"] for k in cand["kraje"])
    counter_ids = {s["article_id"] for s in cand["sygnaly_przeciwne"]}
    assert one_day["counter"][0] in counter_ids
    # reprezentatywne sygnały: alarm (najsilniejszy) przed krytyką, różne źródła
    pl = next(k for k in cand["kraje"] if k["kraj"] == "PL")
    assert [s["stance"] for s in pl["sygnaly"]] == ["alarm", "krytyka"]
    assert {s["zrodlo"] for s in pl["sygnaly"]} == {"pl1", "pl2"}


def test_convergence_below_threshold_is_weak(conn, settings):
    seed_sources(conn)
    for c in ("ua", "de"):                                   # 2 kraje z 2 źródłami + QA z jednym
        for n in (1, 2):
            article_with(conn, f"{c}{n}", theme="energy", stance="alarm")
    article_with(conn, "qa1", theme="energy", stance="alarm")
    conn.commit()
    pkg = build_data_package(conn, DAY, settings, THEMES)
    assert pkg["zbieznosc_kandydaci"] == []
    [weak] = pkg["zbieznosc_slabe"]
    assert weak["temat"] == "energy" and "QA" in weak["powod"]
    assert {k["kraj"]: k["spelnia_prog_zrodel"] for k in weak["kraje"]} == {"DE": True, "QA": False, "UA": True}


def test_neutral_country_has_no_direction(conn, settings):
    seed_sources(conn)
    for c in ("pl", "ua", "de"):
        for n in (1, 2):
            article_with(conn, f"{c}{n}", theme="energy", stance="neutralny")
    conn.commit()
    pkg = build_data_package(conn, DAY, settings, THEMES)
    assert pkg["zbieznosc_kandydaci"] == [] and pkg["zbieznosc_slabe"] == []


def test_absent_in_poland(conn, settings):
    seed_sources(conn)
    for c in ("ua", "de"):
        article_with(conn, f"{c}1", theme="migration_borders")
        article(conn, f"{c}2")                                # udział 0.5 w UA i DE
    for _ in range(3):
        article_with(conn, "pl1", theme="energy")             # PL pisze o czym innym
    article_with(conn, "pl2", theme="migration_borders")      # 1/4 = 0.25 >= 0.25*0.5 -> nie jest "nieobecny"
    conn.commit()
    assert build_data_package(conn, DAY, settings, THEMES)["nieobecne_w_polsce"] == []

    conn.execute("DELETE FROM signals WHERE theme_id = 'migration_borders' AND article_id IN "
                 "(SELECT a.id FROM articles a WHERE a.source_id = 'pl2')")
    conn.commit()
    [item] = build_data_package(conn, DAY, settings, THEMES)["nieobecne_w_polsce"]
    assert item["temat"] == "migration_borders" and item["udzial_pl"] == 0.0
    assert item["udzialy"] == {"DE": 0.5, "UA": 0.5} and len(item["article_ids"]) == 2


def test_self_image_js(conn, settings):
    seed_sources(conn)
    for n in (1, 2, 1):
        article_with(conn, f"de{n}", theme="elections_politics", actor="DE", stance="poparcie")
    for src in ("uk1", "uk2", "ua1"):
        article_with(conn, src, theme="elections_politics", actor="DE", stance="krytyka")
    article_with(conn, "pl1", theme="russia", actor="PL", stance="alarm")  # za mało danych o PL
    conn.commit()
    pkg = build_data_package(conn, DAY, settings, THEMES)
    [de] = pkg["autoobraz"]
    assert de["kraj"] == "DE" and de["n_wlasne"] == 3 and de["n_zewnetrzne"] == 3
    assert de["js"] == pytest.approx(1.0)
    assert de["kraje_zewnetrzne"] == {"UK": 2, "UA": 1}
    assert {"kraj": "PL", "n_wlasne": 1, "n_zewnetrzne": 0} in pkg["autoobraz_pominiete"]


def test_divergences_ranked_by_js(conn, settings):
    seed_sources(conn)
    for _ in range(3):
        article_with(conn, "pl1", theme="energy", stance="alarm")
        article_with(conn, "uk1", theme="energy", stance="poparcie")
        article_with(conn, "pl1", theme="russia", stance="krytyka")
        article_with(conn, "uk1", theme="russia", stance="krytyka")
    conn.commit()
    div = build_data_package(conn, DAY, settings, THEMES)["rozbieznosci"]
    assert [d["temat"] for d in div] == ["energy", "russia"]
    assert div[0]["max_js"] == pytest.approx(1.0) and div[1]["max_js"] == pytest.approx(0.0)


def test_emergent_singletons_collapsed(conn, settings):
    seed_sources(conn)
    article_with(conn, "pl1", theme="emergent:one-off")
    article_with(conn, "uk1", theme="emergent:twice")
    article_with(conn, "uk2", theme="emergent:twice")
    conn.commit()
    pkg = build_data_package(conn, DAY, settings, THEMES)
    assert [t["temat"] for t in pkg["tematy"]] == ["emergent:twice"]
    assert pkg["tematy_wylaniajace_sie_pojedyncze"] == 1


def test_representative_spreads_sources_and_limits():
    from paralaksa.aggregate.metrics import SignalRow

    def row(i, src, stance="neutralny", intensity=3, article=None):
        return SignalRow(i, article or i, "t", "UA", "r", stance, intensity, "ocena", "s", "fulltext",
                         src, "UA", "agency", "u")
    sigs = [row(1, "a", "alarm", 5), row(2, "a", "alarm", 4), row(3, "b", "neutralny", 1),
            row(4, "a", "alarm", 5, article=1)]              # ten sam artykuł co sygnał 1
    picked = representative(sigs, 2)
    assert [s["article_id"] for s in picked] == [1, 3]       # najsilniejszy + inne źródło
    assert len(representative(sigs, 5)) == 3                 # jeden sygnał na artykuł


# ------------------------------------------------------------------ data package (historia)

def seed_history(conn, theme: str, country: str, shares: dict[str, float]) -> None:
    """Metrics of past days written directly, to test the baseline path without 28 real days."""
    conn.executemany(
        "INSERT INTO daily_metrics (date, theme_id, country, article_share, n_articles, n_sources, "
        "dominant_frame, mean_intensity) VALUES (?, ?, ?, ?, 1, 1, 'rama', 3)",
        [(d, theme, country, s) for d, s in shares.items()],
    )
    conn.commit()


def test_package_with_baseline_z_score_and_shift(conn, settings):
    seed_sources(conn)
    history = {days_before(n): (0.1 if n % 2 else 0.2) for n in range(1, 21)}   # 20 dni, średnia 0.15
    seed_history(conn, "security_defense", "PL", history)
    article_with(conn, "pl1", theme="security_defense")                        # dziś: udział 0.5
    article(conn, "pl2")
    conn.commit()

    pkg = build_data_package(conn, DAY, settings, THEMES)
    assert pkg["linia_bazowa"]["dostepna"] is True and pkg["linia_bazowa"]["dni_historii"]["PL"] == 20
    pl = next(t for t in pkg["tematy"] if t["temat"] == "security_defense")["kraje"]["PL"]
    assert pl["srednia_28d"] == pytest.approx(0.15) and pl["roznica_pp"] == pytest.approx(35.0)
    assert pl["z"] > 6
    [shift] = pkg["co_sie_przesuwa"]
    assert shift["temat"] == "security_defense" and shift["kraj"] == "PL" and shift["article_ids"]


def test_theme_missing_today_still_shows_drop_with_baseline(conn, settings):
    seed_sources(conn)
    seed_history(conn, "energy", "PL", {days_before(n): 0.3 for n in range(1, 16)})
    article_with(conn, "pl1", theme="russia")
    conn.commit()
    pkg = build_data_package(conn, DAY, settings, THEMES)
    energy = next(t for t in pkg["tematy"] if t["temat"] == "energy")
    assert energy["kraje"]["PL"]["udzial"] == 0.0 and energy["kraje"]["PL"]["roznica_pp"] == pytest.approx(-30.0)


def test_spillover_new_theme_in_country(conn, settings):
    seed_sources(conn)
    earlier = {days_before(n): 0.2 for n in range(7, 27)}                      # 20 dni przed oknem 7 dni
    seed_history(conn, "ukraine_war", "UK", earlier)                           # UK ma historię
    seed_history(conn, "civil_preparedness", "DE", earlier)                    # temat był wcześniej w DE
    seed_history(conn, "civil_preparedness", "UK", {days_before(2): 0.1})      # w UK pojawia się w oknie
    aid = article_with(conn, "uk1", theme="civil_preparedness")
    article_with(conn, "uk1", theme="ukraine_war")                             # stały temat: nie jest nowy
    conn.commit()

    [item] = build_data_package(conn, DAY, settings, THEMES)["rozlewanie"]
    assert (item["temat"], item["kraj"]) == ("civil_preparedness", "UK")
    assert item["pierwszy_dzien"] == days_before(2) and item["dni_obecnosci"] == 2
    assert item["kraje_wczesniej"] == ["DE"] and item["article_ids"] == [aid]


def test_known_article_ids_include_history(conn, settings):
    seed_sources(conn)
    old = article_with(conn, "pl1", day=days_before(3))
    today = article_with(conn, "pl1")
    no_signals = article(conn, "pl1")
    future = article_with(conn, "pl1", day="2026-09-30")
    conn.commit()
    assert known_article_ids(conn, DAY) == {old, today}
    assert no_signals not in known_article_ids(conn, DAY) and future not in known_article_ids(conn, DAY)
    assert len(day_signals(conn, DAY)) == 1
