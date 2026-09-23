# Przegląd commita 4b8d3a2 (przed KM4) i przygotowanie odbioru

Data: 2026-09-23. Zakres: kod rdzenia (db, ingest/http, extract/signals, report/pipeline, cli),
workflow `daily.yml`, `scripts/db_state.py`, dokumentacja. Bez zmian w kodzie; poprawki po akceptacji.

## Sprawdzenia
- `pytest -q`: **200 passed**.
- Migracja kopii bazy KM3 (v3 → v4, `plx init-db --db data/migrate-test.db`): bez strat.
  | | v3 (backup) | v4 (po migracji) |
  |---|---|---|
  | artykuły / nieekstrahowane / bez daty | 312 / 0 / 0 | 312 / 0 / 0 |
  | sygnały | 807 | 807 |
  | daily_metrics / raporty | 207 / 1 | 207 / 1 |
  | api_usage (USD) | 0,601 | 0,601 |
  | źródła w tabeli | 24 | 35 (doszli kandydaci, nieaktywni) |
- `db_state.py` na zmigrowanej bazie: integralność OK.
- Dry-run na zmigrowanej bazie: 0 oczekujących (lokalnie nie było nowego ingestu). Szacunek GPT
  (~1,87 USD za ~282 artykuły) pozostaje jedyną prognozą dla pierwszego daily.
- Kopia nietknięta: `data/paralaksa.km3-v3.bak.db` (poza gitem).

## Ustalenia

### Ryzyka (warto poprawić przed daily)
1. **Daily prawie zawsze skończy się kodem 1.** `pipeline.py`: `complete` wymaga braku *jakichkolwiek*
   ostrzeżeń, a ostrzeżeniem jest m.in. błąd dowolnego kanału tego dnia (`fetch_log.status != 'ok'`)
   albo brak materiałów z jednego aktywnego źródła. Spiegel już dziś daje `robots_disallowed`.
   Skutek: czerwony workflow codziennie, więc przestaje sygnalizować prawdziwe awarie.
   Propozycja: rozdzielić ostrzeżenia na blokujące (brak syntezy, błąd walidacji, niepełna ekstrakcja)
   i informacyjne (pojedynczy kanał, jedno brakujące źródło), a kod 1 zwracać tylko przy blokujących.
2. **Robots: błąd sieci = zakaz na cały przebieg.** `http.py`: wyjątek przy pobieraniu robots.txt
   lub status 5xx ustawia `disallow_all` i zapisuje go w cache na całą sesję. Tak jest bezpieczniej,
   ale przejściowy timeout wyłącza redakcję na dobę. Prawdopodobna przyczyna Spiegla: sprawdzić ręcznie
   `https://www.spiegel.de/robots.txt`. Propozycja: jedno ponowienie przed uznaniem za zakaz.
3. **`db_state.py` nie wypisuje liczb**, choć `OPERATIONS.md` każe porównać liczby artykułów/sygnałów
   i `MIN/MAX(fetched_at)` po odtworzeniu. Propozycja: drukować te liczby (i wersję schematu), żeby
   były w logu Actions.

### Kosmetyka i dług
4. `pipeline.py` robi dużo inline (audyt, skrót, status, importy wewnątrz funkcji, `_refs` prywatne
   z `render`). Działa, ale warto wydzielić `write_artifacts()`.
5. `daily.yml` „Raport statusu” dokleja wszystkie `reports/*.status.json` z historii, a nie tylko bieżący dzień.
6. Release `database-backup` dostaje nowy plik `db-RUN-ATTEMPT.enc` przy każdym przebiegu, bez rotacji.
   Po kilku miesiącach warto przycinać, np. zostawiać 30 ostatnich.
7. **CLAUDE.md jest niespójny z nowymi regułami**: „Dzień artykułu = dzień pobrania”, „Cache Actions
   znika po 7 dniach, baza zaczyna od zera”, opis `daily.yml` („baza w cache Actions”). Nagłówek
   „Aktualizacja przed KM4” to ogranicza, ale sekcje niżej wprowadzają w błąd. Do aktualizacji.

### Bez zastrzeżeń
- Migracje stosowane rosnąco (`sorted`), `published_at` dopuszcza NULL już od v1.
- Rezerwacja budżetu według `max_tokens` i zapis kosztów paczki przed ponowieniami są poprawne.
- Workflow: sekret tylko przez `env`/`-pass env:`, brak cichego `init-db`, snapshot przez Backup API.

## Co musi zrobić właściciel (poza zasięgiem sesji)
1. GitHub → Settings → Secrets and variables → Actions: `DEEPSEEK_API_KEY`, `ANTHROPIC_API_KEY`,
   `DB_BACKUP_KEY` (losowe, np. `openssl rand -base64 32`, kopia w menedżerze haseł).
2. Zainstalować `gh`: `winget install GitHub.cli`, potem `gh auth login`.
3. Następnie (mogę przeprowadzić): zaszyfrować snapshot `data/paralaksa.db` i wgrać do Release
   według `OPERATIONS.md` → „Zainicjowanie Release”; próba odszyfrowania i porównanie liczb;
   `gh workflow run daily.yml`; zapis czasu i kosztu w `CURRENT_HANDOFF.md`.

## Wprowadzone poprawki (po akceptacji)
- Ryzyko 1: podział ostrzeżeń. Blokujące (kod 1): brak/nieudana synteza, niepełna ekstrakcja,
  brak materiałów z >1/3 aktywnych źródeł. Informacyjne (widoczne w raporcie i `status.json` → `warnings`,
  ale nie w `blocking`): błąd pojedynczego kanału, pojedyncze brakujące źródło, sanityzacja po ponowieniu.
- Ryzyko 2: robots.txt — 2 próby przy błędzie sieci, 5xx i 429; dopiero potem ostrożny zakaz.
  Spiegel sprawdzony ręcznie: nasz UA ma `Allow`, więc wcześniejszy zakaz był błędem przejściowym.
  Pozostałe 4xx znów oznaczają brak reguł (RFC 9309), 401/403 nadal blokują.
- Ryzyko 3: `db_state.py` wypisuje schemat, liczby artykułów/sygnałów, zakres `fetched_at` i ostatnie raporty.
- Punkt 7: CLAUDE.md zaktualizowany.

## Kontrola źródeł na żywo (2026-09-23, `data/source-checks-now.json`)
Wszystkie 10 aktywnych: OK (w tym spiegel 20/20 świeżych). Kandydaci OK: wp, gazeta, kyivindependent, dw, faz,
skynews (tylko 4 wpisy), thehindu, dailysabah, hurriyet, pbs, fox, npr, propublica (2 świeże/48 h), folha,
agenciabrasil. Problemy: **timesofisrael** — robots.txt wprost `Disallow: /feed/`; **maannews** — Cloudflare
challenge (ochrona antybotowa); **ynetnews** — kanał działa, ale 0 wpisów z ostatnich 48 h; haaretz, wafa — bez kanału.
Tych ograniczeń nie obchodzimy (SPEC §16).
