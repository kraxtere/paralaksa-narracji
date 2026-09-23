import json

import pytest

from paralaksa.extract.schema import MAX_EVIDENCE_WORDS, is_verbatim, parse_extraction

THEMES = {"ukraine_war", "russia", "us_policy"}
SOURCE = "Rosja przeprowadziła zmasowany atak na Kijów w nocy. Prezydent Zełenski wezwał sojuszników do dostaw obrony powietrznej."


def sig(**kw) -> dict:
    base = {
        "theme_id": "ukraine_war", "subject_actor": "RU", "frame": "Rosja atakuje Kijów",
        "stance": "alarm", "intensity": 4, "signal_type": "fakt",
        "summary_pl": "Rosja zaatakowała Kijów.", "evidence_span": "zmasowany atak na Kijów w nocy",
    }
    return {**base, **kw}


def parse(signals, source=SOURCE, wrap=True):
    text = json.dumps({"signals": signals}, ensure_ascii=False) if wrap else signals
    return parse_extraction(text, THEMES, source)


def test_valid_signal():
    out = parse([sig()])
    assert out.clean and len(out.signals) == 1
    assert out.signals[0].subject_actor == "RU"


def test_empty_list_is_valid():
    out = parse([])
    assert out.clean and out.signals == []


@pytest.mark.parametrize("field,value", [
    ("stance", "entuzjazm"), ("signal_type", "plotka"), ("intensity", 0), ("intensity", 7),
])
def test_enum_and_range_errors(field, value):
    out = parse([sig(**{field: value})])
    assert out.signals == [] and len(out.errors) == 1 and field in out.errors[0]


def test_long_evidence_is_truncated_not_rejected():
    long_span = SOURCE  # cały tekst: dosłowny, ale ponad 15 słów
    assert len(long_span.split()) > MAX_EVIDENCE_WORDS
    out = parse([sig(evidence_span=long_span)])
    assert out.clean and out.repairs == 1
    assert len(out.signals[0].evidence_span.split()) == MAX_EVIDENCE_WORDS


def test_ellipsis_evidence_rejected():
    out = parse([sig(evidence_span="zmasowany atak ... obrony powietrznej")])
    assert out.signals == [] and "wielokropk" in out.errors[0]


def test_non_verbatim_evidence_rejected():
    out = parse([sig(evidence_span="Rosja zaatakowała Kijów rakietami")])
    assert out.signals == [] and "dosłownie" in out.errors[0]


def test_is_verbatim_ignores_case_and_punctuation():
    assert is_verbatim("ROSJA przeprowadziła, zmasowany atak", SOURCE)
    assert not is_verbatim("atak zmasowany", SOURCE)       # kolejność słów ma znaczenie
    assert not is_verbatim("Kij", SOURCE)                  # tylko całe słowa
    assert not is_verbatim("", SOURCE)


# Realne przypadki z audytu al-quds (2026-09-23): model cytuje poprawnie, ale bez arabskiego
# przedrostka doklejonego bez spacji do następnego słowa (و "i", ب "przez/w").
@pytest.mark.parametrize("span,source", [
    ("برر جيش الاحتلال قرار تشغيل الفرقة 98", "الاحتلال. وبرر جيش الاحتلال قرار تشغيل الفرقة 98 بأنه"),
    ("تضع إيران شرط إنهاء الحرب", "نقاشاً. وتضع إيران شرط إنهاء الحرب على"),
    ("إصابة أحد عناصر الشرطة", "وإعلامية بإصابة أحد عناصر الشرطة الإسرائيلية"),
])
def test_is_verbatim_tolerates_arabic_proclitic_drop(span, source):
    assert is_verbatim(span, source)


def test_is_verbatim_arabic_proclitic_drop_does_not_over_match():
    # Tolerancja jest wąska: tylko 1-3 znaki z domkniętego zbioru przedrostków (و ف ب ك ل ا).
    assert not is_verbatim("قصف", "الاستهدافقصف")   # różnica to cały rdzeń "الاستهداف", nie przedrostek
    assert not is_verbatim("زمة", "أزمة")            # różnica to "أ" (hamza), spoza dozwolonego zbioru


@pytest.mark.parametrize("actor", ["US;DK", "US, DK", "US/DK", "emergent:x"])
def test_bad_actor_rejected(actor):
    out = parse([sig(subject_actor=actor)])
    assert out.signals == [] and "subject_actor" in out.errors[0]


@pytest.mark.parametrize("actor,expected", [("USA", "US"), ("Ghana", "GH"), ("Iran", "IR"), ("Afryka", "Afryka"), ("NATO", "NATO")])
def test_actor_aliases(actor, expected):
    assert parse([sig(subject_actor=actor)]).signals[0].subject_actor == expected


@pytest.mark.parametrize("field", ["frame", "summary_pl"])
def test_cyrillic_in_polish_fields_rejected(field):
    out = parse([sig(**{field: "Росія атакує Київ"})])
    assert out.signals == [] and "po polsku" in out.errors[0]


def test_cyrillic_evidence_allowed():
    source = "Росія атакувала Київ дронами вночі"
    out = parse([sig(evidence_span="Росія атакувала Київ")], source=source)
    assert out.clean


def test_theme_validation_and_emergent_normalization():
    out = parse([sig(theme_id="sport"), sig(theme_id="emergent:Greenland_Sovereignty dispute")])
    assert len(out.errors) == 1 and "nieznany temat" in out.errors[0]
    assert out.signals[0].theme_id == "emergent:greenland-sovereignty-dispute"


def test_partial_validity_keeps_good_signals():
    out = parse([sig(), sig(stance="zły"), sig(subject_actor="UA")])
    assert len(out.signals) == 2 and len(out.errors) == 1 and "signals.1" in out.errors[0]


def test_more_than_five_signals():
    out = parse([sig()] * 7)
    assert len(out.signals) == 5 and "maks. 5" in out.errors[0]


def test_json_in_code_fence_and_prose():
    text = "Oto wynik:\n```json\n" + json.dumps({"signals": [sig()]}, ensure_ascii=False) + "\n```"
    assert parse(text, wrap=False).clean


@pytest.mark.parametrize("text", ["to nie jest JSON", '{"signals": "x"}', "[1, 2]", '{"sygnaly": []}'])
def test_fatal_outputs(text):
    out = parse(text, wrap=False)
    assert out.fatal is not None and out.signals == []
