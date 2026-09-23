"""Loading and validating YAML configuration (settings, sources, themes)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_DIR = PROJECT_ROOT / "config"

SourceType = Literal["agency", "public", "private", "tabloid", "government"]


class Models(BaseModel):
    extract: str = "claude-haiku-4-5-20251001"
    synthesize: str = "claude-sonnet-5"
    curiosities: str = "claude-haiku-4-5-20251001"


class Thresholds(BaseModel):
    min_countries: int = 3
    min_sources_per_country: int = 2
    baseline_days: int = 28
    min_history_days_for_trends: int = 14
    absent_in_pl_ratio: float = 0.25
    emergent_similarity: float = 0.8


class IngestSettings(BaseModel):
    per_domain_delay_s: float = 2.0
    max_fulltext_words: int = 1500
    timeout_s: float = 20.0
    user_agent: str = "paralaksa-narracji/0.1"
    title_similarity: float = Field(0.9, ge=0.0, le=1.0)
    title_dedup_hours: int = 48
    stale_source_days: int = 2


class Budget(BaseModel):
    max_daily_usd: float = 3.0


class Settings(BaseModel):
    db_path: Path = Path("data/paralaksa.db")
    models: Models = Models()
    thresholds: Thresholds = Thresholds()
    ingest: IngestSettings = IngestSettings()
    budget: Budget = Budget()

    def resolved_db_path(self, root: Path = PROJECT_ROOT) -> Path:
        return self.db_path if self.db_path.is_absolute() else root / self.db_path


class Feed(BaseModel):
    url: str
    section: str | None = None


class Source(BaseModel):
    id: str
    name: str
    country: str = Field(min_length=2, max_length=2)
    language: str
    type: SourceType
    feeds: list[Feed] = []
    fulltext: bool = False
    active: bool = True
    note: str | None = None

    @field_validator("country")
    @classmethod
    def _upper_country(cls, v: str) -> str:
        return v.upper()

    @model_validator(mode="after")
    def _active_needs_feeds(self) -> Source:
        if self.active and not self.feeds:
            raise ValueError(f"aktywne źródło '{self.id}' nie ma żadnego kanału")
        return self


class Theme(BaseModel):
    id: str
    name_pl: str
    description: str


def _read_yaml(path: Path):
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_settings(config_dir: Path = DEFAULT_CONFIG_DIR) -> Settings:
    data = _read_yaml(config_dir / "settings.yaml") or {}
    return Settings.model_validate(data)


def load_sources(config_dir: Path = DEFAULT_CONFIG_DIR) -> list[Source]:
    data = _read_yaml(config_dir / "sources.yaml") or []
    sources = [Source.model_validate(item) for item in data]
    ids = [s.id for s in sources]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        raise ValueError(f"zduplikowane id źródeł: {sorted(duplicates)}")
    return sources


def load_themes(config_dir: Path = DEFAULT_CONFIG_DIR) -> list[Theme]:
    data = _read_yaml(config_dir / "themes.yaml") or []
    themes = [Theme.model_validate(item) for item in data]
    ids = [t.id for t in themes]
    if len(ids) != len(set(ids)):
        raise ValueError("zduplikowane id tematów")
    return themes
