import shutil

import httpx
import pytest
from typer.testing import CliRunner

from paralaksa import cli, db
from paralaksa.config import DEFAULT_CONFIG_DIR
from paralaksa.ingest.http import PoliteClient

runner = CliRunner()

SOURCES_YAML = """
- id: test
  name: Test News
  country: UK
  language: en
  type: private
  feeds:
    - url: https://news.example.com/rss.xml
      section: world
  fulltext: false
  active: true
- id: dead
  name: Dead Feed
  country: PL
  language: pl
  type: agency
  feeds: []
  active: false
  note: "brak RSS"
"""


@pytest.fixture
def config_dir(tmp_path):
    d = tmp_path / "config"
    d.mkdir()
    shutil.copy(DEFAULT_CONFIG_DIR / "themes.yaml", d / "themes.yaml")
    (d / "settings.yaml").write_text(f"db_path: {(tmp_path / 'test.db').as_posix()}\n", encoding="utf-8")
    (d / "sources.yaml").write_text(SOURCES_YAML, encoding="utf-8")
    return d


@pytest.fixture
def mock_network(monkeypatch, fixtures_dir):
    feed = (fixtures_dir / "rss2.xml").read_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://news.example.com/rss.xml":
            return httpx.Response(200, content=feed)
        return httpx.Response(404)

    real_init = PoliteClient.__init__

    def fake_init(self, user_agent, per_domain_delay_s=2.0, timeout_s=20.0, **kw):
        real_init(self, user_agent, 0, timeout_s, transport=httpx.MockTransport(handler))

    monkeypatch.setattr(PoliteClient, "__init__", fake_init)


def test_init_db(config_dir, tmp_path):
    result = runner.invoke(cli.app, ["init-db", "--config-dir", str(config_dir)])
    assert result.exit_code == 0, result.output
    conn = db.connect(tmp_path / "test.db")
    assert conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0] == 2


def test_sources_lists_inactive_with_note(config_dir):
    result = runner.invoke(cli.app, ["sources", "--config-dir", str(config_dir)])
    assert result.exit_code == 0
    assert "Aktywne źródła (1)" in result.output
    assert "dead" in result.output and "brak RSS" in result.output


def test_ingest_command(config_dir, tmp_path, mock_network):
    result = runner.invoke(cli.app, ["ingest", "--config-dir", str(config_dir)])
    assert result.exit_code == 0, result.output
    assert "Razem nowych artykułów: 4" in result.output
    result = runner.invoke(cli.app, ["ingest", "--config-dir", str(config_dir)])
    assert "Razem nowych artykułów: 0" in result.output


def test_extract_dry_run_and_run(config_dir, tmp_path, mock_network, monkeypatch):
    from fake_llm import FakeAnthropic
    from paralaksa.extract import llm_client

    runner.invoke(cli.app, ["ingest", "--config-dir", str(config_dir)])
    result = runner.invoke(cli.app, ["extract", "--dry-run", "--config-dir", str(config_dir)])
    assert result.exit_code == 0, result.output
    assert "Artykuły do ekstrakcji: 4 (tryb: direct" in result.output

    real_init = llm_client.LLMClient.__init__
    monkeypatch.setattr(llm_client.LLMClient, "__init__",
                        lambda self, pricing, **kw: real_init(self, pricing, client=FakeAnthropic()))
    result = runner.invoke(cli.app, ["extract", "--config-dir", str(config_dir)])
    assert result.exit_code == 0, result.output
    assert "przetworzone: 4 | sygnały: 4" in result.output
    conn = db.connect(tmp_path / "test.db")
    assert conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0] == 4


def test_extract_uses_deepseek_client_for_deepseek_model(config_dir, tmp_path, mock_network, monkeypatch):
    from fake_llm import FakeOpenAI
    from paralaksa.extract import llm_client

    (config_dir / "settings.yaml").write_text(
        f"db_path: {(tmp_path / 'test.db').as_posix()}\nmodels:\n  extract: deepseek-v4-pro\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    runner.invoke(cli.app, ["ingest", "--config-dir", str(config_dir)])

    real_init = llm_client.DeepSeekClient.__init__
    monkeypatch.setattr(llm_client.DeepSeekClient, "__init__",
                        lambda self, pricing, **kw: real_init(self, pricing, client=FakeOpenAI()))
    result = runner.invoke(cli.app, ["extract", "--config-dir", str(config_dir)])
    assert result.exit_code == 0, result.output
    assert "przetworzone: 4 | sygnały: 4" in result.output


def test_ingest_unknown_source(config_dir):
    result = runner.invoke(cli.app, ["ingest", "--config-dir", str(config_dir), "--source", "nope"])
    assert result.exit_code == 2
