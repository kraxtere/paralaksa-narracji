from pathlib import Path

import pytest

from paralaksa import db
from paralaksa.config import Settings, Source

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.init_db(c)
    yield c
    c.close()


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def make_source():
    def _make(id="test", url="https://news.example.com/rss.xml", fulltext=False, **kw) -> Source:
        return Source(
            id=id,
            name=kw.pop("name", "Test News"),
            country=kw.pop("country", "UK"),
            language=kw.pop("language", "en"),
            type=kw.pop("type", "private"),
            feeds=[{"url": url, "section": kw.pop("section", "world")}],
            fulltext=fulltext,
            **kw,
        )

    return _make
