"""Schema of the synthesis output (JSON from `prompts/synthesize_report.md`), sections as in SPEC §10.

References are article ids only; URLs are resolved from the database at render time.
"""

from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

Confidence = Literal["niski", "średni", "wysoki"]


class Evidence(BaseModel):
    signal_id: int
    article_id: int
    theme_id: str
    kraj: str
    zrodlo: str


class Referenced(BaseModel):
    dowody: list[Evidence] = Field(default_factory=list)


class Claim(Referenced):
    theme_id: str = ""

    tekst: str = Field(min_length=1)
    article_ids: list[int] = []


class ConfidenceNote(BaseModel):
    poziom: Confidence
    uzasadnienie: str = Field(min_length=1)


class Summary(Claim):
    pewnosc: Confidence


class CountryLine(Referenced):
    kraj: str
    n_zrodel: int = Field(ge=0)
    rama: str
    stance: str
    article_ids: list[int] = []


class CounterSignals(Referenced):
    tekst: str = Field(min_length=1)       # gdy brak w danych: napisz to wprost
    article_ids: list[int] = []


class Pattern(BaseModel):
    temat: str
    kierunek: str
    kraje: list[CountryLine]
    wspolny_kierunek: str = Field(min_length=1)
    sygnaly_przeciwne: CounterSignals
    pewnosc: ConfidenceNote
    trend: str


class Divergence(BaseModel):
    temat: str
    tekst: str = Field(min_length=1)
    kraje: list[CountryLine]
    pewnosc: ConfidenceNote


class SelfImage(Referenced):
    pewnosc: Confidence = "niski"
    kraj: str
    jak_opisuje_siebie: str
    jak_opisuja_go_inni: str
    komentarz: str
    article_ids: list[int] = []


class TopicClaim(Claim):
    temat: str


class ReportOutput(BaseModel):
    w_skrocie: list[Summary] = []
    wzorce_zbieznosci: list[Pattern] = []
    rozbieznosci: list[Divergence] = []
    autoobraz: list[SelfImage] = []
    co_sie_przesuwa: list[Claim] = []
    nieobecne_w_polsce: list[TopicClaim] = []
    slabe_sygnaly: list[Claim] = []


# Przykład wstawiany w miejsce {schema} w promptcie (zwięźlej niż pełny JSON Schema).
SCHEMA_EXAMPLE = json.dumps({
    "w_skrocie": [{"tekst": "...", "pewnosc": "niski|średni|wysoki", "article_ids": [1, 2]}],
    "wzorce_zbieznosci": [{
        "temat": "<id tematu>", "kierunek": "...",
        "kraje": [{"kraj": "PL", "n_zrodel": 2, "rama": "...", "stance": "...", "article_ids": [1]}],
        "wspolny_kierunek": "...",
        "sygnaly_przeciwne": {"tekst": "... albo: brak sygnałów przeciwnych w danych", "article_ids": [3]},
        "pewnosc": {"poziom": "niski|średni|wysoki", "uzasadnienie": "liczby: kraje, źródła, artykuły"},
        "trend": "rośnie od N dni | nowy | stabilny | brak linii bazowej",
    }],
    "rozbieznosci": [{
        "temat": "<id tematu>", "tekst": "czym różnią się przekazy",
        "kraje": [{"kraj": "UA", "n_zrodel": 2, "rama": "...", "stance": "...", "article_ids": [4]}],
        "pewnosc": {"poziom": "niski|średni|wysoki", "uzasadnienie": "..."},
    }],
    "autoobraz": [{"kraj": "DE", "jak_opisuje_siebie": "...", "jak_opisuja_go_inni": "...",
                   "komentarz": "...", "article_ids": [5, 6]}],
    "co_sie_przesuwa": [{"tekst": "...", "article_ids": [7]}],
    "nieobecne_w_polsce": [{"temat": "<id tematu>", "tekst": "...", "article_ids": [8]}],
    "slabe_sygnaly": [{"tekst": "...", "article_ids": [9]}],
}, ensure_ascii=False, indent=1)

SCHEMA_EXAMPLE += "\nKażda pozycja z article_ids musi mieć dowody: [{signal_id: int, article_id: int, theme_id: str, kraj: str, zrodlo: str}], przepisane z DANE.dowody. Każda teza tekstowa (w_skrocie, slabe_sygnaly, co_sie_przesuwa, nieobecne_w_polsce) ma także theme_id. Autoobraz ma pewnosc: niski|średni|wysoki. article_ids muszą dokładnie odpowiadać artykułom z dowody."


def _extract_json_text(text: str) -> str:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end < start:
        raise ValueError("odpowiedź nie zawiera obiektu JSON")
    return text[start : end + 1]


def parse_report(text: str) -> tuple[ReportOutput | None, list[str]]:
    """Parse and structurally validate; (None, errors) when unusable."""
    try:
        data = json.loads(_extract_json_text(text))
    except (ValueError, json.JSONDecodeError) as e:
        return None, [f"niepoprawny JSON: {e}"]
    try:
        return ReportOutput.model_validate(data), []
    except ValidationError as e:
        return None, [f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in e.errors()]
