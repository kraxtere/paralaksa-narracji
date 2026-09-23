# Changelog

## [0.2.0] – 2026-09-23 – Kamień milowy 2: ekstrakcja sygnałów

- Ekstrakcja sygnałów narracyjnych z LLM: prompt `prompts/extract_signals.md`, schemat pydantic
  (`extract/schema.py`) z walidacją per sygnał (naprawa `evidence_span`, sprawdzenie dosłowności
  cytatu w tekście źródłowym, normalizacja aktorów, wykrywanie cyrylicy w polach polskich).
- Klienci LLM (`extract/llm_client.py`): `LLMClient` (Anthropic, bezpośrednio + Message Batches API,
  próg 50 artykułów) i `DeepSeekClient` (OpenAI-compatible, tylko wywołania bezpośrednie – DeepSeek
  nie ma Batches API); `build_client()` wybiera klienta po prefiksie nazwy modelu.
- Pipeline ekstrakcji (`extract/signals.py`): ponowienie przy błędzie walidacji z listą błędów w
  promptcie, kontrola dziennego budżetu (`budget.max_daily_usd`) z bezpiecznym odłożeniem nadwyżki,
  zapis kosztu per wywołanie (`api_usage`). Komenda `plx extract [--dry-run] [--limit] [--no-batch]`.
- **Decyzje modelowe** (metodologia i wyniki w CLAUDE.md): Sonnet 5 wybrany zamiast Haiku 4.5 jako
  baseline jakości (porównanie na 20 artykułach); następnie **DeepSeek V4-Pro wybrany jako model
  produkcyjny** zamiast Sonnet 5 (porównanie na 26 artykułach, w tym 6 o Chinach pod kątem testu
  neutralności: te same 82/82 sygnały co Sonnet za ~7,7× niższą cenę, myślenie odpuszczone jako
  niedziałające przy tym promptcie).
- Pełny przebieg na bazie produkcyjnej: ekstrakcja sygnałów dla wszystkich zaległych artykułów z KM1.
- 135 testów (offline, `httpx.MockTransport` / fake klienty LLM).

## [0.1.0] – 2026-09-23 – Kamień milowy 1: szkielet i ingest

- Szkielet repozytorium: pakiet `src/paralaksa`, komenda `plx` (typer), `pyproject.toml`.
- Konfiguracja YAML z walidacją pydantic: `settings.yaml`, `sources.yaml`, `themes.yaml` (14 tematów).
- Baza SQLite (`data/paralaksa.db`) z pełnym schematem ze SPEC §7 oraz tabelami `fetch_log` i `schema_version`.
- Ingest RSS/Atom/RDF dla 10 aktywnych źródeł (po 2 z PL, UA, DE, UK, plus Al Jazeera i CGTN):
  deduplikacja po znormalizowanym URL i podobieństwie tytułów (48 h), filtr wstępny
  (sport, rozrywka, pogoda, horoskopy), pełne teksty przez trafilatura, robots.txt, 2 s na domenę.
- Komendy: `plx init-db`, `plx sources`, `plx ingest`.
- Źródła bez działającego RSS (PAP, Polskie Radio, Suspilne, Telegraph, Global Times) oznaczone
  `active: false` z komentarzem; zweryfikowane kanały zapasowe do włączenia w KM4.
- Testy (pytest, offline).
