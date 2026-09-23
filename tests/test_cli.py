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


def _fake_llm_everywhere(monkeypatch):
    """One fake for extraction (prompt with 'Tytuł:') and synthesis (anything else)."""
    from fake_llm import FakeAnthropic, message, valid_json_for
    from paralaksa.extract import llm_client

    def responder(params):
        if "Tytuł:" in params["messages"][0]["content"]:
            return message(valid_json_for(params))
        return message('{"w_skrocie": [], "wzorce_zbieznosci": []}', 20_000, 500)

    fake = FakeAnthropic(responder)
    real_init = llm_client.LLMClient.__init__
    monkeypatch.setattr(llm_client.LLMClient, "__init__",
                        lambda self, pricing, **kw: real_init(self, pricing, client=fake))
    return fake


def test_aggregate_and_report(config_dir, tmp_path, mock_network, monkeypatch):
    fake = _fake_llm_everywhere(monkeypatch)
    runner.invoke(cli.app, ["init-db", "--config-dir", str(config_dir)])
    runner.invoke(cli.app, ["ingest", "--config-dir", str(config_dir)])
    runner.invoke(cli.app, ["extract", "--config-dir", str(config_dir)])
    today = db.utc_now().date().isoformat()

    result = runner.invoke(cli.app, ["aggregate", "--config-dir", str(config_dir)])
    assert result.exit_code == 0, result.output
    assert f"{today}: zapisano 1 wierszy daily_metrics (1 tematów, 1 krajów)" in result.output

    out = tmp_path / "reports"
    result = runner.invoke(cli.app, ["report", "--config-dir", str(config_dir), "--out-dir", str(out)])
    assert result.exit_code == 0, result.output
    assert (out / f"{today}.md").exists() and "Synteza: claude-sonnet-5 | wywołania: 1" in result.output
    synth_calls = [c for c in fake.messages.calls if "Tytuł:" not in c["messages"][0]["content"]]
    assert len(synth_calls) == 1
    conn = db.connect(tmp_path / "test.db")
    assert conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0] == 1


def test_report_bad_date(config_dir):
    result = runner.invoke(cli.app, ["report", "--config-dir", str(config_dir), "--date", "23.09.2026"])
    assert result.exit_code == 2 and "Niepoprawna data" in result.output


def test_run_daily(config_dir, tmp_path, mock_network, monkeypatch):
    _fake_llm_everywhere(monkeypatch)
    out = tmp_path / "reports"
    result = runner.invoke(cli.app, ["run-daily", "--config-dir", str(config_dir), "--out-dir", str(out)])
    assert result.exit_code == 0, result.output
    for step in ("== ingest", "Razem nowych artykułów: 4", "== extract", "sygnały: 4", "== aggregate + report"):
        assert step in result.output, step
    report_md = (out / f"{db.utc_now().date().isoformat()}.md").read_text(encoding="utf-8")
    assert "## Metadane" in report_md and "| UK | test | 4 | 4 |" in report_md

    result = runner.invoke(cli.app, ["run-daily", "--skip-ingest", "--config-dir", str(config_dir),
                                     "--out-dir", str(out)])
    assert result.exit_code == 0, result.output
    assert "== ingest" not in result.output and "Artykuły: 0" in result.output


def test_ingest_unknown_source(config_dir):
    result = runner.invoke(cli.app, ["ingest", "--config-dir", str(config_dir), "--source", "nope"])
    assert result.exit_code == 2
