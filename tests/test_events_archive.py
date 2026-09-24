from datetime import date
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from paralaksa import cli
from paralaksa.events.archive import SaveError, archive_card, save_page, write_archive
from paralaksa.events.check import Snapshot, load_card
from paralaksa.ingest.http import PoliteClient

URL = "https://news.example/a/1"
URL2 = "https://news.example/b/2"

CARD = """---
id: 2026-01-09-test
tytul: Zdarzenie testowe
fakt: {czas: null, opis: test, zrodlo_pierwotne: null}
relacje:
  - id: r1
    kto: Gazeta
    link: https://news.example/a/1
    publikacja: '2026-01-09T12:00+01:00'
    archiwum: {link: null, wykonano: null}   # do zrobienia
    sprawdzil: null
  - id: r2
    kto: Portal
    link: https://news.example/b/2
    publikacja: null
    archiwum: {link: null, wykonano: null}
    sprawdzil: null
  - id: r3
    kto: Z archiwum
    link: https://news.example/c/3
    archiwum: {link: 'https://web.archive.org/web/20260109120000/https://news.example/c/3', wykonano: '2026-01-09T12:00Z'}
  - id: r4
    kto: Bez linku
    link: null
kontrasty: []
---

## Fakt
"""


class Wayback:
    """Mock web.archive.org: CDX per URL, SPN2 save + status."""

    def __init__(self, cdx: dict[str, list[str]], statuses: list[dict] | None = None, save_status: int = 200):
        self.cdx, self.statuses, self.save_status = cdx, list(statuses or []), save_status
        self.saved: list[str] = []
        self.auth: list[str | None] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/robots.txt":
            return httpx.Response(404)
        if path == "/cdx/search/cdx":
            url = request.url.params["url"]
            rows = [["timestamp", "original"]] + [[ts, url] for ts in self.cdx.get(url, [])]
            return httpx.Response(200, json=rows)
        if path == "/save" and request.method == "POST":
            self.auth.append(request.headers.get("Authorization"))
            self.saved.append(httpx.QueryParams(request.content.decode())["url"])
            if self.save_status != 200:
                return httpx.Response(self.save_status, json={"message": "nope"})
            return httpx.Response(200, json={"url": self.saved[-1], "job_id": "spn2-abc"})
        if path == "/save/status/spn2-abc":
            return httpx.Response(200, json=self.statuses.pop(0))
        return httpx.Response(404)


def client_for(handler) -> PoliteClient:
    return PoliteClient("test-agent", per_domain_delay_s=0, transport=httpx.MockTransport(handler), sleep=lambda s: None)


@pytest.fixture
def card_file(tmp_path: Path) -> Path:
    p = tmp_path / "2026-01-09-test.md"
    p.write_text(CARD, encoding="utf-8")
    return p


def run(card_file, wb, auth="LOW k:s", **kw):
    return archive_card(card_file, client_for(wb), auth, today=date(2026, 1, 20), sleep=lambda s: None, **kw)


def test_existing_copy_after_publication_written_other_fields_untouched(card_file):
    wb = Wayback({URL: ["20260109100000", "20260109113000", "20260110080000"], URL2: ["20260110090000"]})
    res = run(card_file, wb)
    assert wb.saved == []  # kopie już są, nic nowego nie zapisujemy
    assert res.written == 2
    card = load_card(card_file)
    r1, r2, r3 = card["relacje"][:3]
    # publikacja 12:00+01:00 = 11:00 UTC, więc pierwsza kopia po niej to 11:30
    assert r1["archiwum"] == {"link": f"https://web.archive.org/web/20260109113000/{URL}", "wykonano": "2026-01-09T11:30Z"}
    assert r2["archiwum"]["link"] == f"https://web.archive.org/web/20260110090000/{URL2}"
    assert r3["archiwum"]["wykonano"] == "2026-01-09T12:00Z"
    assert r1["sprawdzil"] is None and r2["sprawdzil"] is None
    text = card_file.read_text(encoding="utf-8")
    assert "pierwsza po publikacji (plx events archive); do zrobienia" in text  # stary komentarz zostaje
    assert text.endswith("## Fakt\n")
    assert [r.action for r in res.relations] == ["istniejąca", "istniejąca", "jest", "pominięta"]


def test_save_page_now_when_no_copy(card_file):
    wb = Wayback({URL: ["20260109113000"]}, statuses=[
        {"status": "pending"}, {"status": "success", "timestamp": "20260120101500", "original_url": URL2}])
    res = run(card_file, wb)
    assert wb.saved == [URL2] and wb.auth == ["LOW k:s"]
    r2 = load_card(card_file)["relacje"][1]
    assert r2["archiwum"] == {"link": f"https://web.archive.org/web/20260120101500/{URL2}", "wykonano": "2026-01-20T10:15Z"}
    assert "nie z dnia publikacji" in card_file.read_text(encoding="utf-8")
    assert res.relations[1].action == "własna"


def test_without_keys_no_save_and_hint(card_file):
    wb = Wayback({})
    res = run(card_file, wb, auth=None)
    assert wb.saved == []
    assert res.written == 0
    assert card_file.read_text(encoding="utf-8") == CARD
    assert "IA_ACCESS_KEY" in res.relations[0].message


def test_dry_run_neither_saves_nor_writes(card_file):
    wb = Wayback({URL: ["20260109113000"]})
    res = run(card_file, wb, dry_run=True)
    assert wb.saved == [] and res.written == 0
    assert card_file.read_text(encoding="utf-8") == CARD
    assert "zrobiłbym" in res.relations[1].message


def test_save_error_leaves_card(card_file):
    wb = Wayback({}, statuses=[{"status": "error", "status_ext": "error:blocked-url", "message": "blocked"}])
    wb.cdx = {URL: ["20260109113000"]}
    res = run(card_file, wb)
    assert res.relations[1].action == "błąd" and "blocked-url" in res.relations[1].message
    assert load_card(card_file)["relacje"][1]["archiwum"]["link"] is None


def test_save_page_http_401_explains_keys():
    with pytest.raises(SaveError, match="IA_ACCESS_KEY"):
        save_page(client_for(Wayback({}, save_status=401)), URL, "LOW k:s", sleep=lambda s: None)


def test_save_page_times_out():
    ticks = iter(range(0, 1000, 100))
    wb = Wayback({}, statuses=[{"status": "pending"}] * 10)
    with pytest.raises(SaveError, match="brak wyniku"):
        save_page(client_for(wb), URL, "LOW k:s", sleep=lambda s: None, clock=lambda: next(ticks), timeout_s=250)


def test_write_archive_keeps_crlf_and_refuses_other_layout(tmp_path):
    p = tmp_path / "k.md"
    p.write_bytes(CARD.replace("\n", "\r\n").encode("utf-8"))
    snap = Snapshot("20260109113000", URL)
    assert write_archive(p, "r1", snap, "notka")
    raw = p.read_bytes().decode("utf-8")
    assert "\r\n" in raw and "\n" not in raw.replace("\r\n", "")
    assert load_card(p)["relacje"][0]["archiwum"]["link"] == snap.link
    assert not write_archive(p, "r1", snap, "notka")  # już wypełnione: nie nadpisuje
    assert not write_archive(p, "r9", snap, "notka")


def test_cli_archive(card_file, monkeypatch):
    wb = Wayback({URL: ["20260109113000"], URL2: ["20260110090000"]})
    real = PoliteClient
    monkeypatch.setattr(cli, "PoliteClient", lambda *a, **k: real(
        "test-agent", per_domain_delay_s=0, transport=httpx.MockTransport(wb), sleep=lambda s: None))
    monkeypatch.delenv("IA_ACCESS_KEY", raising=False)
    monkeypatch.delenv("IA_SECRET_KEY", raising=False)
    result = CliRunner().invoke(cli.app, ["events", "archive", str(card_file)])
    assert result.exit_code == 0, result.output
    assert "wpisano 2 archiwów" in result.output
    assert load_card(card_file)["relacje"][1]["archiwum"]["link"].endswith(URL2)


def test_late_existing_copy_reported_not_written(card_file):
    wb = Wayback({URL: ["20260115080000"], URL2: ["20260109200000"]})
    res = run(card_file, wb)
    assert res.relations[0].action == "późna" and "nie wpisuję" in res.relations[0].message
    assert wb.saved == []  # nowa kopia byłaby jeszcze późniejsza
    assert load_card(card_file)["relacje"][0]["archiwum"]["link"] is None
    assert res.written == 1


def test_redirected_capture_rejected(card_file):
    wb = Wayback({URL: ["20260109113000"]}, statuses=[
        {"status": "success", "timestamp": "20260120101500", "original_url": "https://news.example/?mp=promo"}])
    res = run(card_file, wb)
    assert res.relations[1].action == "błąd" and "przekierowanie" in res.relations[1].message
    assert load_card(card_file)["relacje"][1]["archiwum"]["link"] is None


def test_same_url_with_trailing_slash_accepted(card_file):
    wb = Wayback({URL: ["20260109113000"]}, statuses=[
        {"status": "success", "timestamp": "20260120101500", "original_url": "http://news.example/b/2/"}])
    assert run(card_file, wb).relations[1].action == "własna"
