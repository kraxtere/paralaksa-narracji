"""Curated event spec: which stored headlines belong to one event and their working translations."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class BoardItem(BaseModel):
    article_id: int
    # Tłumaczenie robocze na polski; wymagane dla nagłówków w innym języku niż polski.
    translation_pl: str | None = None


class EventSpec(BaseModel):
    id: str
    title: str = Field(min_length=1)          # neutralny opis zdarzenia (z leadów, bez oceny)
    when: str = Field(min_length=1)           # np. "22–23.09.2026"
    rule: str = Field(min_length=1)           # jawna reguła doboru nagłówków
    items: list[BoardItem] = Field(min_length=2)


def load_event(path: Path) -> EventSpec:
    return EventSpec.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
