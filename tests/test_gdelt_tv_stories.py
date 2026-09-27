import json
from types import SimpleNamespace

from paralaksa.gdelt import tv, tv_stories as S

TEXT = ("DAY-AT -A-GLANCE Russian forces closed the encirclement of Dobropolye. MAJOR DEVELOPMENTS Turnout was 59.8 percent. "
        "HYPOTHESES AND FUTURE OUTLOOK Kramatorsk will fall soon. STRATEGIC FORESIGHT Expect a surrender. "
        "LEGISLATIVE ROUNDUP The budget passed.")


def test_speculative_sections_are_left_out():
    r = tv.Report("RUSSIA24", "", TEXT)
    assert S.sections(TEXT) == ["glance", "major", "hypotheses", "foresight", "legislative"]
    assert [i for i, _ in S.usable(r)] == [0, 1, 4]


def V(*groups):
    return [{"stacje": [{"en": f} for f in g]} for g in groups]


def test_numbers_differ_beyond_written_precision():
    assert not S._numbers_differ(V(["38%"], ["38.2%"], ["38-40%"]))        # zaokrąglenie
    assert not S._numbers_differ(V(["more than 44%"], ["44.37%"]))         # przybliżenie
    assert S._numbers_differ(V(["59.8 percent"], ["59.2%"]))
    assert S._numbers_differ(V(["100,000 workers"], ["200,000"]))


def test_names_differ_not_only_in_spelling():
    assert not S._names_differ(V(["Marat Kambolov"], ["Murat Kambolov"], ["Marat Kabulov"]))
    assert not S._names_differ(V(["CNN and Politico"], ["CNN, MSNBC and Politico"]))
    assert S._names_differ(V(["Pope Leo XIV"], ["Pope Francis"]))


A = "Ukraine has been granted a license to produce Patriot missiles."
B = "Trump promised to give Ukraine a license for Patriot production."
REPORTS = {"CURRENTTIME": tv.Report("CURRENTTIME", "", f"DAY-AT -A-GLANCE {A}"),
           "ESPRESO": tv.Report("ESPRESO", "", f"DAY-AT -A-GLANCE {B}")}


def verdict(**over):
    d = {"kontrola": {"to_samo_zdarzenie": True, "wersje_wprost": True, "zaokraglenie": False, "dokladniejsza": False,
                      "pisownia": False, "akcent": False, "inna_miara": False, "to_samo": False,
                      "aktualizacja": True},
         "tytul": "Licencja na Patrioty", "typ": "status", "roznica": "Przyznana czy obiecana.", "uwaga": "", "sila": 3,
         "wersje": [{"etykieta": "przyznana", "stacje": [{"stacja": "CURRENTTIME", "zdanie": 0, "wprost": True,
                                                         "en": "has been granted", "pl": "otrzymała"}]},
                    {"etykieta": "obiecana", "stacje": [{"stacja": "ESPRESO", "zdanie": 0, "wprost": True,
                                                        "en": "Trump promised", "pl": "nie ma tego w zdaniu"}]}]}
    d.update(over)
    return json.dumps(d)


class Script:
    """Answers by the kind of prompt: claims per report, grouping, verification."""

    def __init__(self, verify=verdict()):
        self.calls, self.verify = [], verify

    def complete(self, req):
        p = req.messages[0]["content"]
        self.calls.append(p)
        if "Wypisz do" in p:
            is_ct = "granted" in p
            text = {"tezy": [{"zdarzenie": "Licencja na Patrioty", "teza": "przyznana" if is_ct else "obiecana",
                              "zdania": [0, 99]}]}
        elif "Znajdź do" in p:
            text = {"zdarzenia": [{"tytul": "Licencja", "typ": "status", "roznica": "r",
                                   "wersje": [{"etykieta": "przyznana", "tezy": ["CURRENTTIME-1"]},
                                              {"etykieta": "obiecana", "tezy": ["ESPRESO-1", "NIEMA-1"]}],
                                   "wszystkie": ["CURRENTTIME-1", "ESPRESO-1"]}]}
        else:
            return SimpleNamespace(ok=True, text=self.verify, cost_usd=0.01, error=None)
        return SimpleNamespace(ok=True, text=json.dumps(text), cost_usd=0.001, error=None)


def test_generate_three_steps_verbatim_marks_and_cache(tmp_path):
    client = Script()
    pl = {"CURRENTTIME": {"sentences": ["Ukraina otrzymała licencję."]}, "ESPRESO": None}
    out = S.generate(lambda m: client, "2026-09-25", REPORTS, pl, tmp_path)
    assert not out["errors"] and len(client.calls) == 4
    (h,) = out["historie"]
    ct, es = h["wersje"][0]["stacje"][0], h["wersje"][1]["stacje"][0]
    assert (ct["stacja"], ct["en"], ct["pl"]) == ("CURRENTTIME", "has been granted", "otrzymała")
    assert es["pl"] == ""   # słowa spoza zdania nie są podświetlane
    claims = json.loads((tmp_path / "2026-09-25" / "ESPRESO.claims.json").read_text(encoding="utf-8"))
    assert claims["tezy"][0]["zdania"] == [0]   # numer spoza raportu odrzucony

    again = Script()
    assert S.generate(lambda m: again, "2026-09-25", REPORTS, pl, tmp_path)["historie"] == out["historie"]
    assert again.calls == [] and S.cached(tmp_path, "2026-09-25", REPORTS) == out["historie"]


def test_verification_rejections_are_decided_in_code(tmp_path):
    def run(v):
        return S.generate(lambda m: Script(v), "2026-09-25", REPORTS, {}, tmp_path / str(hash(v)))["historie"]

    assert run(verdict(kontrola={"to_samo_zdarzenie": True, "wersje_wprost": True, "zaokraglenie": False,
                                 "dokladniejsza": True, "pisownia": False, "akcent": False, "inna_miara": False,
                                 "to_samo": False})) == []
    bare = json.loads(verdict())
    bare["wersje"][1]["stacje"][0]["wprost"] = False   # milczenie albo wniosek: stacja wypada, zostaje jedna wersja
    assert run(json.dumps(bare)) == []


def test_broken_verification_drops_the_candidate_but_saves_the_day(tmp_path):
    client = Script("{\"kontrola\": }")
    out = S.generate(lambda m: client, "2026-09-25", REPORTS, {}, tmp_path)
    assert not out["errors"] and out["warnings"] and out["historie"] == [] and out["niesprawdzone"] == 1
    assert len(client.calls) == 2 + 1 + 2   # tezy, zdarzenia, weryfikacja z jednym ponowieniem
    assert S.cached(tmp_path, "2026-09-25", REPORTS) == []
    kand = S.generate(lambda m: Script(), "2026-09-25", REPORTS, {}, tmp_path)   # zapisany dzień: bez wywołań
    assert kand["historie"] == []


def test_failed_claims_are_an_error_and_nothing_is_saved(tmp_path):
    class Down(Script):
        def complete(self, req):
            return SimpleNamespace(ok=False, text=None, cost_usd=0, error="503")

    out = S.generate(lambda m: Down(), "2026-09-25", REPORTS, {}, tmp_path)
    assert out["errors"] and not (tmp_path / "2026-09-25" / "historie.json").exists()


def test_views_carry_saved_stories(tmp_path):
    from paralaksa.gdelt import tv_views

    for day in ("2026-09-24", "2026-09-25"):
        (tmp_path / day).mkdir()
        for c, r in REPORTS.items():
            (tmp_path / day / f"{c}.json").write_text(json.dumps(
                {"code": c, "title": "T", "text": r.text, "shows": []}), encoding="utf-8")
    S.generate(lambda m: Script(), "2026-09-25", REPORTS, {}, tmp_path)
    p = tv_views.build(["2026-09-25"], tmp_path)
    assert p["data"]["2026-09-25"]["stories"][0]["typ"] == "status" and p["types"]["status"]
    (tmp_path / "2026-09-26").mkdir()
    for c, r in REPORTS.items():
        (tmp_path / "2026-09-26" / f"{c}.json").write_text(json.dumps(
            {"code": c, "title": "T", "text": r.text, "shows": []}), encoding="utf-8")
    assert tv_views.build(["2026-09-26"], tmp_path)["data"]["2026-09-26"]["stories"] is None   # nie zbudowano


def test_polish_quote_closed_with_ascii_is_repaired():
    assert S._json('{"r": "to „fałszywa flaga" według M1", "n": 1}') == {"r": "to „fałszywa flaga” według M1", "n": 1}


def test_verification_answers_are_reused_after_a_rule_change(tmp_path, monkeypatch):
    client = Script()
    S.generate(lambda m: client, "2026-09-25", REPORTS, {}, tmp_path)
    monkeypatch.setattr(S, "PROMPT_VERSION", "zmiana-regul")   # nowa wersja: historie liczone od nowa
    again = Script()
    out = S.generate(lambda m: again, "2026-09-25", REPORTS, {}, tmp_path)
    assert again.calls == [] and len(out["historie"]) == 1   # tezy, kandydaci i odpowiedzi z dysku
