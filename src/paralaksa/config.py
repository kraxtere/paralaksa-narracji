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
    extract: str = "claude-sonnet-5"
    synthesize: str = "claude-sonnet-5"
    curiosities: str = "claude-haiku-4-5-20251001"


class Thresholds(BaseModel):
    min_countries: int = 3
    min_sources_per_country: int = 2
    baseline_days: int = 28
    min_history_days_for_trends: int = 14
    absent_in_pl_ratio: float = 0.25
    emergent_similarity: float = 0.8
    # KM3: progi pomocnicze agregacji (SPEC §9.3 nie podaje liczb).
    absent_in_pl_min_share: float = 0.10     # "wysoki udział" tematu w kraju dla sekcji "Nieobecne w Polsce"
    direction_min_nonneutral: float = 0.3    # min. udział sygnałów nie-neutralnych, żeby kraj miał kierunek
    spillover_days: int = 7                  # okno "rozlewania się"
    min_signals_self_image: int = 3          # min. sygnałów po każdej stronie porównania autoobrazu


class IngestSettings(BaseModel):
    per_domain_delay_s: float = 2.0
    max_fulltext_words: int = 1500
    timeout_s: float = 20.0
    user_agent: str = "paralaksa-narracji/0.1"
    title_similarity: float = Field(0.9, ge=0.0, le=1.0)
    title_dedup_hours: int = 48
    stale_source_days: int = 2


class ExtractSettings(BaseModel):
    max_runtime_s: float = Field(2400, gt=0)
    batch_threshold: int = 50
    max_concurrency: int = Field(4, ge=1)
    max_tokens: int = 4000
    # Dla Sonnet 5 (Anthropic): "disabled"/"adaptive" + "low".."high". Dla modeli deepseek-*:
    # "disabled"/"enabled" (DeepSeek nazywa to inaczej niż Anthropic) + "low"/"high"/"max".
    # Haiku 4.5 nie obsługuje żadnego z tych pól i są wtedy pomijane.
    thinking: Literal["disabled", "adaptive", "enabled"] = "disabled"
    effort: Literal["low", "medium", "high", "max"] | None = None
    batch_poll_interval_s: float = 30.0
    batch_timeout_h: float = 24.0
    est_output_tokens: int = 800


class ReportSettings(BaseModel):
    output_dir: Path = Path("reports")
    representative_signals_per_item: int = Field(4, ge=1, le=5)
    # Synteza to jedno wywołanie dziennie na dużym payloadzie; przy myśleniu tokeny rozumowania
    # liczą się do max_tokens, stąd zapas. Wartości thinking/effort jak w ExtractSettings.
    max_tokens: int = 16000
    thinking: Literal["disabled", "adaptive", "enabled"] = "disabled"
    effort: Literal["low", "medium", "high", "max"] | None = None
    est_output_tokens: int = 6000

    def resolved_output_dir(self, root: Path | None = None) -> Path:
        return self.output_dir if self.output_dir.is_absolute() else (root or PROJECT_ROOT) / self.output_dir


class ModelPrice(BaseModel):
    input: float   # USD / 1M tokenów
    output: float


class DeepSeekModelPrice(BaseModel):
    """Ceny USD / 1M tokenów; DeepSeek różnicuje godziny szczytu i trafienia w cache."""
    input_peak: float
    input_off_peak: float
    cache_hit: float           # ta sama stawka niezależnie od pory (wg cennika)
    output_peak: float
    output_off_peak: float


# Godziny szczytu wg cennika DeepSeek: 01:00–04:00 i 06:00–10:00 UTC, pon.–pt. (poza chińskimi świętami,
# których nie modelujemy). Poza tymi przedziałami: 50% ceny.
DEEPSEEK_PEAK_WINDOWS_UTC = [(1, 4), (6, 10)]


def is_deepseek_peak(at) -> bool:
    if at.weekday() >= 5:  # sobota, niedziela
        return False
    hour = at.hour
    return any(start <= hour < end for start, end in DEEPSEEK_PEAK_WINDOWS_UTC)


class DeepSeekPricing(BaseModel):
    models: dict[str, DeepSeekModelPrice] = {
        "deepseek-v4-pro": DeepSeekModelPrice(
            input_peak=1.32, input_off_peak=0.66, cache_hit=0.022, output_peak=3.96, output_off_peak=1.98
        ),
        "deepseek-flash": DeepSeekModelPrice(
            input_peak=0.30, input_off_peak=0.15, cache_hit=0.003, output_peak=1.20, output_off_peak=0.60
        ),
    }

    def cost(self, model: str, input_tokens: int, output_tokens: int, cache_hit_tokens: int = 0, at=None) -> float:
        price = self.models.get(model)
        if price is None:
            raise ValueError(f"brak cennika dla modelu '{model}' w settings.yaml (pricing.deepseek.models)")
        peak = is_deepseek_peak(at) if at is not None else True  # brak `at`: zakładamy szczyt (bezpieczny szacunek)
        input_price = price.input_peak if peak else price.input_off_peak
        output_price = price.output_peak if peak else price.output_off_peak
        cache_miss_tokens = max(input_tokens - cache_hit_tokens, 0)
        usd = (cache_miss_tokens * input_price + cache_hit_tokens * price.cache_hit + output_tokens * output_price)
        return usd / 1_000_000


class Pricing(BaseModel):
    batch_discount: float = 0.5
    models: dict[str, ModelPrice] = {
        "claude-haiku-4-5-20251001": ModelPrice(input=1.0, output=5.0),
        "claude-haiku-4-5": ModelPrice(input=1.0, output=5.0),
        "claude-sonnet-5": ModelPrice(input=2.0, output=10.0),
    }
    deepseek: DeepSeekPricing = DeepSeekPricing()

    def cost(self, model: str, input_tokens: int, output_tokens: int, batch: bool = False, at=None) -> float:
        if model.startswith("deepseek"):
            return self.deepseek.cost(model, input_tokens, output_tokens, at=at)
        price = self.models.get(model)
        if price is None:
            raise ValueError(f"brak cennika dla modelu '{model}' w settings.yaml (pricing.models)")
        usd = (input_tokens * price.input + output_tokens * price.output) / 1_000_000
        return usd * self.batch_discount if batch else usd


class Budget(BaseModel):
    max_daily_usd: float = Field(3.0, gt=0)


class Settings(BaseModel):
    db_path: Path = Path("data/paralaksa.db")
    models: Models = Models()
    thresholds: Thresholds = Thresholds()
    ingest: IngestSettings = IngestSettings()
    extract: ExtractSettings = ExtractSettings()
    report: ReportSettings = ReportSettings()
    pricing: Pricing = Pricing()
    budget: Budget = Budget()

    def resolved_db_path(self, root: Path = PROJECT_ROOT) -> Path:
        return self.db_path if self.db_path.is_absolute() else root / self.db_path


class Feed(BaseModel):
    url: str
    section: str | None = None
    genre: Literal["news", "opinion", "unknown"] = "unknown"


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
    editorial_country: str | None = None
    ownership: str = "niezweryfikowane"
    publisher_group: str | None = None
    channel_scope: str = "zakres określony przez kanały; próbka nie jest reprezentatywna"
    activated_at: str | None = None
    license_note: str = "wymaga okresowego przeglądu warunków wydawcy"
    verification: dict = Field(default_factory=dict)
    # Nazwy, pod którymi redakcja pojawia się w tekście raportu (prefiksy: łapią odmianę, np. "Guardian" → "Guardiana").
    aliases: list[str] = []

    @field_validator("country")
    @classmethod
    def _upper_country(cls, v: str) -> str:
        return v.upper()

    @model_validator(mode="after")
    def _active_needs_feeds(self) -> Source:
        if self.active and not self.feeds:
            raise ValueError(f"aktywne źródło '{self.id}' nie ma żadnego kanału")
        if self.active and self.verification and not all(
            self.verification.get(k) is True for k in ("feed", "fresh", "robots", "usage", "quality")
        ):
            raise ValueError(f"źródło '{self.id}' nie przeszło wszystkich bramek aktywacji")
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
