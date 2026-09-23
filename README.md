# Paralaksa narracji

Codzienna analiza przekazu medialnego z wielu krajów. System zbiera publikacje z mediów
PL, UA, DE, UK i spoza bloku i porównuje **linie przekazu w tematach**: zbieżność kierunku,
autoobraz vs obraz zewnętrzny, dryf w czasie. Pełna specyfikacja: [SPEC.md](SPEC.md).

> Stan: **kamień milowy 1**, czyli szkielet, konfiguracja, baza SQLite i ingest RSS dla 10 źródeł.
> Ekstrakcja sygnałów (LLM), agregacja i raport dzienny to kolejne etapy (SPEC §15).

## Instalacja

Wymagany Python 3.12.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env   # ANTHROPIC_API_KEY – potrzebny od KM2
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
```

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

GitHub Actions i lokalny cron zostaną opisane w KM3 (`plx run-daily`).
