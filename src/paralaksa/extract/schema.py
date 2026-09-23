"""Schema of the extraction output and its validation.

Validation is per signal: one bad signal does not discard the whole article.
Over-long evidence spans are repaired deterministically (cut to the first 15 words,
which keeps them verbatim) instead of paying for a retry.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

Stance = Literal["alarm", "uspokojenie", "neutralny", "krytyka", "poparcie"]
SignalType = Literal["fakt", "ocena", "prognoza", "zalecenie_dla_obywateli", "wypowiedz_polityka"]
SourceDepth = Literal["lead_only", "fulltext"]

MAX_SIGNALS = 5
MAX_EVIDENCE_WORDS = 15
EMERGENT_RE = re.compile(r"^emergent:[a-z0-9]+(?:-[a-z0-9]+)*$")
# Pełne nazwy państw (en/pl) i częste warianty -> kod ISO; klucze wielkimi literami.
ACTOR_ALIASES = {
    "USA": "US", "U.S.": "US", "UNITED STATES": "US", "STANY ZJEDNOCZONE": "US",
    "EU": "UE", "EUROPEAN UNION": "UE", "UNIA EUROPEJSKA": "UE",
    "PRC": "CN", "CHINA": "CN", "CHINY": "CN",
    "RUSSIA": "RU", "ROSJA": "RU", "UKRAINE": "UA", "UKRAINA": "UA",
    "POLAND": "PL", "POLSKA": "PL", "GERMANY": "DE", "NIEMCY": "DE",
    "UNITED KINGDOM": "UK", "UK": "UK", "GB": "UK", "WIELKA BRYTANIA": "UK", "BRITAIN": "UK",
    "FRANCE": "FR", "FRANCJA": "FR", "ITALY": "IT", "WŁOCHY": "IT", "SPAIN": "ES", "HISZPANIA": "ES",
    "IRAN": "IR", "ISRAEL": "IL", "IZRAEL": "IL", "TURKEY": "TR", "TÜRKIYE": "TR", "TURCJA": "TR",
    "QATAR": "QA", "KATAR": "QA", "SAUDI ARABIA": "SA", "ARABIA SAUDYJSKA": "SA",
    "INDIA": "IN", "INDIE": "IN", "JAPAN": "JP", "JAPONIA": "JP", "TAIWAN": "TW", "TAJWAN": "TW",
    "BELARUS": "BY", "BIAŁORUŚ": "BY", "DENMARK": "DK", "DANIA": "DK",
    "GREENLAND": "GL", "GRENLANDIA": "GL", "GHANA": "GH", "SOUTH AFRICA": "ZA", "RPA": "ZA",
    "VENEZUELA": "VE", "WENEZUELA": "VE", "SYRIA": "SY", "LEBANON": "LB", "LIBAN": "LB",
    "PALESTINE": "PS", "PALESTYNA": "PS", "YEMEN": "YE", "JEMEN": "YE", "CANADA": "CA", "KANADA": "CA",
}
# Cyrylica w polach, które mają być po polsku, oznacza, że model przepisał język źródła.
CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")


class Signal(BaseModel):
    theme_id: str
    subject_actor: str = Field(min_length=1, max_length=60)
    frame: str = Field(min_length=1, max_length=120)
    stance: Stance
    intensity: int = Field(ge=1, le=5)
    signal_type: SignalType
    summary_pl: str = Field(min_length=1, max_length=600)
    evidence_span: str = Field(min_length=1)

    @field_validator("theme_id")
    @classmethod
    def _normalize_emergent(cls, v: str) -> str:
        v = v.strip()
        if v.lower().startswith("emergent:"):
            slug = re.sub(r"[\s_]+", "-", v.split(":", 1)[1].strip().lower())
            return "emergent:" + re.sub(r"-{2,}", "-", slug).strip("-")
        return v

    @field_validator("subject_actor")
    @classmethod
    def _single_actor(cls, v: str) -> str:
        v = v.strip()
        if re.search(r"[;,/&+]", v):
            raise ValueError(f"subject_actor '{v}' zawiera kilku aktorów; jeden aktor na sygnał")
        if ":" in v:
            raise ValueError(f"subject_actor '{v}' nie jest aktorem (kod ISO, organizacja albo region)")
        return ACTOR_ALIASES.get(v.upper(), v)

    @field_validator("frame", "summary_pl")
    @classmethod
    def _polish_text(cls, v: str) -> str:
        if CYRILLIC_RE.search(v):
            raise ValueError("pole musi być po polsku (bez cyrylicy); przetłumacz na polski")
        return v

    @field_validator("evidence_span")
    @classmethod
    def _evidence_short(cls, v: str) -> str:
        if "..." in v or "…" in v:
            raise ValueError("evidence_span nie może łączyć fragmentów wielokropkiem; podaj jeden ciągły cytat")
        n = len(v.split())
        if n > MAX_EVIDENCE_WORDS:
            raise ValueError(f"evidence_span ma {n} słów (maks. {MAX_EVIDENCE_WORDS})")
        return v


class ExtractionResult(BaseModel):
    signals: list[Signal] = Field(max_length=MAX_SIGNALS)


@dataclass
class ParseOutcome:
    signals: list[Signal] = field(default_factory=list)   # poprawne sygnały
    errors: list[str] = field(default_factory=list)       # błędy pojedynczych sygnałów
    fatal: str | None = None                               # odpowiedź w ogóle nieużywalna
    repairs: int = 0                                       # obcięte evidence_span

    @property
    def clean(self) -> bool:
        return self.fatal is None and not self.errors


def _extract_json_text(text: str) -> str:
    """Tolerate ```json fences and prose around the object."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end < start:
        raise ValueError("odpowiedź nie zawiera obiektu JSON")
    return text[start : end + 1]


def _words(text: str) -> list[str]:
    return re.findall(r"\w+", text.casefold())


def is_verbatim(span: str, source: str) -> bool:
    """Span occurs in the source as a contiguous word sequence (punctuation/case-insensitive)."""
    span_words = _words(span)
    if not span_words:
        return False
    return f" {' '.join(span_words)} " in f" {' '.join(_words(source))} "


def _format_error(i: int, err: dict) -> str:
    loc = ".".join(str(p) for p in err["loc"])
    return f"signals.{i}.{loc}: {err['msg']}"


def parse_extraction(text: str, theme_ids: set[str], source_text: str | None = None) -> ParseOutcome:
    """Parse model output and validate each signal.

    With `source_text`, each evidence_span must be a verbatim fragment of it.
    """
    out = ParseOutcome()
    try:
        data = json.loads(_extract_json_text(text))
    except (ValueError, json.JSONDecodeError) as e:
        out.fatal = f"niepoprawny JSON: {e}"
        return out
    raw_signals = data.get("signals") if isinstance(data, dict) else None
    if not isinstance(raw_signals, list):
        out.fatal = "brak listy 'signals' w odpowiedzi"
        return out
    if len(raw_signals) > MAX_SIGNALS:
        out.errors.append(f"signals: {len(raw_signals)} sygnałów (maks. {MAX_SIGNALS}); pozostawiono pierwsze {MAX_SIGNALS}")
        raw_signals = raw_signals[:MAX_SIGNALS]

    for i, raw in enumerate(raw_signals):
        if not isinstance(raw, dict):
            out.errors.append(f"signals.{i}: sygnał nie jest obiektem")
            continue
        span = raw.get("evidence_span")
        if isinstance(span, str) and len(span.split()) > MAX_EVIDENCE_WORDS and "..." not in span and "…" not in span:
            raw = {**raw, "evidence_span": " ".join(span.split()[:MAX_EVIDENCE_WORDS])}
            out.repairs += 1
        try:
            signal = Signal.model_validate(raw)
        except ValidationError as e:
            out.errors.extend(_format_error(i, err) for err in e.errors())
            continue
        if signal.theme_id not in theme_ids and not EMERGENT_RE.match(signal.theme_id):
            out.errors.append(f"signals.{i}.theme_id: nieznany temat '{signal.theme_id}' (użyj id z listy lub emergent:<slug>)")
            continue
        if source_text is not None and not is_verbatim(signal.evidence_span, source_text):
            out.errors.append(f"signals.{i}.evidence_span: fragment nie występuje dosłownie w artykule: '{signal.evidence_span}'")
            continue
        out.signals.append(signal)
    return out
