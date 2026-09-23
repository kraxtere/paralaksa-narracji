from pathlib import Path

import pytest
from pydantic import ValidationError

from paralaksa.config import Source, load_settings, load_sources, load_themes


def test_repo_config_loads():
    settings = load_settings()
    assert settings.thresholds.min_countries == 3
    assert settings.ingest.per_domain_delay_s == 2
    assert settings.ingest.max_fulltext_words == 1500
    assert settings.db_path == Path("data/paralaksa.db")


def test_repo_sources_milestone1_selection():
    sources = load_sources()
    active = [s for s in sources if s.active]
    # 10 z KM1 (PL/UA/DE/UK x2 + QA/CN) + 8 aktywowanych 2026-09-23 po realnym audycie jakości
    # (US: pbs/fox/npr/propublica, BR: folha/agenciabrasil, IL: jpost, PS: alquds_ps) z zaakceptowanym ryzykiem praw wydawcy
    # (docs/CURRENT_HANDOFF.md) zamiast formalnego audytu licencji.
    assert len(active) == 18
    by_country: dict[str, int] = {}
    for s in active:
        by_country[s.country] = by_country.get(s.country, 0) + 1
    for country in ("PL", "UA", "DE", "UK"):
        assert by_country[country] == 2
    assert by_country["US"] == 4 and by_country["BR"] == 2 and by_country["IL"] == 1 and by_country["PS"] == 1
    # 2 spoza bloku z KM1 (QA, CN) + 8 nowych (US, BR, IL, PS)
    assert sum(n for c, n in by_country.items() if c not in {"PL", "UA", "DE", "UK"}) == 10


def test_inactive_sources_have_note():
    for s in load_sources():
        if not s.active:
            assert s.note, f"nieaktywne źródło {s.id} bez komentarza"


def test_repo_themes():
    themes = load_themes()
    ids = {t.id for t in themes}
    assert len(themes) == 14
    assert {"war_readiness", "civil_preparedness", "middle_east"} <= ids


def test_source_validation_rejects_bad_type():
    with pytest.raises(ValidationError):
        Source(id="x", name="X", country="PL", language="pl", type="blog", feeds=[{"url": "https://x"}])


def test_active_source_requires_feed():
    with pytest.raises(ValidationError):
        Source(id="x", name="X", country="PL", language="pl", type="private", feeds=[])
    s = Source(id="x", name="X", country="pl", language="pl", type="private", feeds=[], active=False)
    assert s.country == "PL"


def test_duplicate_source_ids_rejected(tmp_path):
    (tmp_path / "sources.yaml").write_text(
        "- {id: a, name: A, country: PL, language: pl, type: private, active: false}\n"
        "- {id: a, name: B, country: PL, language: pl, type: private, active: false}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="zduplikowane"):
        load_sources(tmp_path)
