# Paralaksa narracji

Codzienna analiza przekazu medialnego z wielu krajów. System zbiera publikacje z mediów
PL, UA, DE, UK i spoza bloku i porównuje **linie przekazu w tematach**: zbieżność kierunku,
autoobraz vs obraz zewnętrzny, dryf w czasie. Pełna specyfikacja: [SPEC.md](SPEC.md).

> Stan: **kamień milowy 3**. KM1: szkielet, konfiguracja, baza SQLite, ingest RSS dla 10 źródeł.
> KM2: ekstrakcja sygnałów narracyjnych (LLM, model produkcyjny: DeepSeek V4-Pro – patrz CLAUDE.md).
> KM3: agregacja (metryki dzienne, pakiet danych), synteza LLM z walidatorem, raport Markdown
> w `reports/`, `plx run-daily` i harmonogram GitHub Actions. Ciekawostki, GDELT i tematy
> wyłaniające się to KM4 (SPEC §15).

## Instalacja

Wymagany Python 3.12.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env   # ANTHROPIC_API_KEY, DEEPSEEK_API_KEY – potrzebne od KM2
```

(Linux/macOS: `python3.12 -m venv .venv && source .venv/bin/activate`. Można też użyć `uv sync`.)

## Użycie

```bash
plx init-db                  # tworzy data/paralaksa.db i wczytuje źródła
plx sources                  # lista źródeł: aktywne i nieaktywne (z powodem)
plx ingest                   # pobiera nowe artykuły z aktywnych kanałów (+ pełne teksty)
plx ingest --no-fulltext     # tylko RSS (tytuł + lead)
plx ingest -s bbc -s guardian
plx -v ingest                # z logami
plx extract --dry-run        # szacunek kosztu, bez wywołań API
plx extract                  # ekstrakcja sygnałów narracyjnych (LLM) z nieprzetworzonych artykułów
plx aggregate [--date D]     # metryki dzienne (udziały tematów per kraj) -> daily_metrics
plx report [--date D]        # pakiet danych + synteza LLM + walidacja -> reports/D.md
plx run-daily                # ingest -> extract -> aggregate -> report (jedną komendą)
plx run-daily --skip-ingest  # bez pobierania, np. po ręcznym ingest
```

Dzień raportu to dzień **pobrania** artykułów (UTC). Raport opisuje przekaz medialny, nie fakty:
każde twierdzenie ma odnośniki do artykułów, każdy wzorzec – sygnały przeciwne i poziom pewności.
Przez pierwsze 14 dni działania nie ma linii bazowej i raport nie formułuje trendów.

`plx ingest` wypisuje dla każdego źródła, ile wpisów pobrano, ile jest nowych, ile odrzucił
filtr (sport, rozrywka, pogoda, horoskopy), ile było duplikatów i ile pełnych tekstów pobrano.
Ostrzega też o źródłach, które od 2 dni nie dały nowych artykułów.

## Konfiguracja

- `config/settings.yaml`: modele, progi, opóźnienia, ścieżka bazy.
- `config/sources.yaml`: źródła i kanały RSS (zweryfikowane 2026-09-23). Nieaktywne mają pole `note`.
- `config/themes.yaml`: taksonomia 14 tematów startowych.

## Zasady pobierania

- identyfikujący User-Agent, respektowanie `robots.txt` (kanały i pełne teksty),
- odstęp 2 s między zapytaniami do tej samej domeny,
- bez obchodzenia paywalli (`fulltext: false` dla rp.pl, Spiegla),
- pełne teksty (maks. 1500 słów) tylko lokalnie, do analizy; nigdy nie są publikowane.

## Testy

```bash
pytest -q
```

Testy działają offline: kanały i strony są podstawiane przez `httpx.MockTransport`.

## Harmonogram

**GitHub Actions** (`.github/workflows/daily.yml`): codziennie o 05:00 UTC (i ręcznie przez
„Run workflow”) uruchamia `plx run-daily` i commituje raport do `reports/`. Baza SQLite nie trafia
do gita – przechodzi między uruchomieniami przez cache Actions (z kopią zapasową jako artefakt,
30 dni). Cache znika po 7 dniach bez uruchomienia; wtedy baza startuje od zera (bez linii bazowej).

Wymagane sekrety repozytorium (Settings → Secrets and variables → Actions):
`DEEPSEEK_API_KEY` (ekstrakcja) i `ANTHROPIC_API_KEY` (gdy w `settings.yaml` jest model Claude).

**Lokalnie** (alternatywa): Harmonogram zadań Windows albo cron, np.
`0 5 * * * cd /ścieżka/paralaksa-narracji && .venv/bin/plx run-daily >> data/run-daily.log 2>&1`.
