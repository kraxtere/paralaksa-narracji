# CLAUDE.md

## Oszczędzanie kontekstu (decyzja właściciela 2026-10-02, obowiązkowe)
Limit konta jest wąskim gardłem. Każdy krok czyta cały kontekst od nowa, więc:
- Nie czytaj całych dużych plików: `grep -n`, potem `Read` z `offset/limit` na potrzebny fragment. CHANGELOG i logi: tylko ostatnie wpisy (`head`/`tail`).
- Wyjście komend przycinaj (`| tail -20`, `-q`, bez pętli z `print` co porcję). Testy: najpierw tylko dotyczące zmiany, pełny `pytest -q` raz przed commitem.
- Zrzuty ekranu i obrazki tylko gdy wygląd trzeba ocenić albo właściciel prosi.
- Historii nie odtwarzaj z pamięci: sięgaj do `docs/HISTORIA_CLAUDE.md` (pełna dawna wersja tego pliku: decyzje modelowe, KM1–3,
  szczegóły modułów strony, GDELT, źródła) albo `git log`, i tylko po potrzebny fragment (`grep`).
- Odpowiedzi krótkie. Bez agentów, chyba że właściciel poprosi.

## Projekt
**Paralaksa narracji / zdarzeń**: codzienny przegląd prasy z 17 krajów (43 źródła, `config/sources.yaml`), strona wewnętrzna
prywatna: dostęp przez link zaproszenia, noindex (wersja 2.0 obrazkowa). Spec: `SPEC.md` (radar→paralaksa,
`src/radar`→`src/paralaksa`, `radar`→`plx`, `data/paralaksa.db`).
Stan i obsługa: `docs/CURRENT_HANDOFF.md`, `docs/OPERATIONS.md`, `docs/SOURCE_REVIEW.md`, `docs/PARALAKSA_ZDARZEN.md`, `CHANGELOG.md`.
Procedura dnia strony 2.0: `scripts/v2/README.md`.

## Komendy (szczegóły flag: `plx <cmd> --help`)
```powershell
.venv\Scripts\python -m pytest -q          # testy offline
.venv\Scripts\plx ingest | extract | aggregate | report | run-daily --bez-raportu
.venv\Scripts\plx site --db data/prod.db [--publikuj] [--z-tv]
.venv\Scripts\plx events check|archive events\<karta>.md ; plx board events\<id>.yaml
.venv\Scripts\plx gdelt rezonans|szukaj|tv|tv-widoki|tv-historie
```

## Mapa kodu (skrót)
- `src/paralaksa/`: `config.py`, `db.py`, `ingest/` (RSS, robots, pełne teksty), `extract/` (sygnały; `llm_client.py`, `codex_client.py`:
  model `codex[:model][:effort]`, tylko lokalnie, nigdy „ultra”), `aggregate/`, `report/` (okładka przez Codex lokalnie), `site/`
  (`plx site`: `build.py`, `data.py`, `stories.py`, `titles.py`, `publish.py`, `assets/pasek.js` wspólny pasek 2.0, `hosting/server.py`
  Render + konta + push), `gdelt/`, `events/`, `board/`.
- `scripts/v2/`: strona 2.0 (widok_obrazkowy, widok_powitanie, os_czasu, streszczenia, dzien_prasy, kraje → `D/kraje.html`
  „Czym żyje kraj”, jeden kraj naraz `#KRAJ`, `kraje.py ciag D` + `strona` → oś kraju `kraje/KRAJ.html`). Wyniki w `data/widok/`.
  `paski.py`: wspólne paski (1 obrazek Codex z N pasami, cięcie po ramkach, oryginały, 8/4 procesy); od 01.10 okładka
  pasami i paski krajów na stronach tematów (`widok_obrazkowy.py paski`), od 02.10 także dni 23–30.09 (`start.png` i plakaty nieużywane).
- `.github/workflows/daily.yml`: cron, baza w zaszyfrowanym Release, bez syntezy.

## Konwencje
- Identyfikatory/docstringi po angielsku; CLI, YAML, raporty, strona po polsku. Daty w bazie ISO 8601 UTC.
- Nie normalizuj zapisywanego URL (`clean_url` zapis, `normalize_url` tylko hash).
- Testy bez sieci; fixtures w `tests/fixtures/`. Kolory strony tylko przez zmienne CSS; nie używać `data-theme` na klikanych elementach.
- Po zmianie: wpis w `CHANGELOG.md`; ten plik aktualizuj tylko o rzeczy potrzebne w każdej sesji (resztę do `docs/`).

## Zasady obowiązkowe
- Opisujemy przekaz medialny, nie fakty. Progi SPEC (≥3 kraje, ≥2 źródła/kraj), odnośniki do każdego twierdzenia; progów nie obniżać.
- robots.txt, bez obchodzenia paywalli i antybotów, UA bez zmian. Pełne teksty tylko lokalnie (`data/`), cytaty maks. 15 słów.
- Strona prywatna: dostęp przez link zaproszenia, noindex (hasło ma tylko właściciel); `SITE_USER/SITE_PASSWORD`,
  `VAPID_PRIVATE_KEY` tylko w Renderze/.env, nigdy w repo ani w czacie.
- Źródła rosyjskie dozwolone. Taksonomii tematów nie zmieniać automatycznie. Pole `sprawdzil` w kartach tylko człowiek.
- Codex/GPT tylko do treści, nie do kodu. Nie commitować `AGENTS.md`.
