# Uruchomienie i odzyskiwanie stanu

## Warunki pierwszego uruchomienia

W Actions wymagane są sekrety `DEEPSEEK_API_KEY`, `ANTHROPIC_API_KEY` (według wybranych modeli)
i nowy `DB_BACKUP_KEY` — silne losowe hasło przechowywane także poza GitHubem w menedżerze haseł.
Nie wpisywać wartości do repozytorium, logów ani argumentów poleceń.
W tej sesji nie było kluczy API ani dostępu do ich ustawiania. Nie zmieniono modeli produkcyjnych.

**Jeżeli istnieje lokalna baza pierwszego raportu, przenieść ją, zamiast tworzyć pustą.**
`data/paralaksa.db` z KM3 migruje automatycznie z v3 do v4 z zachowaniem danych.
Zrób lokalną kopię przed migracją. Test obejmuje migrację z v1 oraz powtórny init-db.
Historycznych, zastępczych dat publikacji zapisanych przez KM3 nie da się wiarygodnie
odtworzyć bez źródłowego RSS; migracja nie zgaduje tych dat.

## Trwały backup

Autorytatywny backup jest zaszyfrowanym plikiem w wydaniu GitHub `database-backup`:
`latest.db.enc` + suma SHA-256 i datowane przez numer przebiegu snapshoty. Release nie ma
30-dniowego TTL artefaktów. Snapshot powstaje przez SQLite Backup API, a nie kopię otwartej bazy.
Cache i artefakt Actions zawierają **wyłącznie zaszyfrowaną bazę**. Pełne teksty nie trafiają jawnie do gita.

Szyfrowanie: OpenSSL AES-256-CBC, PBKDF2, 200000 iteracji, losowa sól. Suma SHA-256 wykrywa
uszkodzenia transmisji; nie jest podpisem kryptograficznym. Dostęp do modyfikacji Release musi być chroniony.
Utrata `DB_BACKUP_KEY` oznacza utratę możliwości odszyfrowania. Rotacja wymaga odszyfrowania starym
kluczem i ponownego zaszyfrowania nowym. Nie usuwać jedynej poprawnej kopii podczas rotacji.

Runner najpierw pobiera aktualny Release. Przy jego niedostępności może wykorzystać cache
z jawnym ostrzeżeniem; należy wtedy porównać historię. Brak obu kopii zatrzymuje przebieg.
`initialize_empty=true` w ręcznym workflow jest wyłącznie świadomą inicjalizacją pierwszej bazy,
nie mechanizmem naprawy. Domyślnie `false`. Po błędzie ekstrakcji/raportu snapshot zachowuje częściowy postęp,
a workflow nadal kończy się błędem.

## Ręczne przywrócenie (Linux/macOS; Bash)

Ustaw `DB_BACKUP_KEY` w środowisku bez wypisywania jego wartości. Potrzebne są `gh`, OpenSSL i Python.

```bash
mkdir -p state-cache data
gh release download database-backup -p latest.db.enc -p latest.db.enc.sha256 -D state-cache
(cd state-cache && sha256sum --check latest.db.enc.sha256)
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -in state-cache/latest.db.enc -out data/restored.db -pass env:DB_BACKUP_KEY
python scripts/db_state.py data/restored.db
```

Porównaj liczbę artykułów, sygnałów, `MIN/MAX(fetched_at)` i daty raportów z ostatnim udanym przebiegiem.
Dopiero po tej kontroli zastąp `data/paralaksa.db` odzyskaną bazą. Nie uruchamiaj pustego `init-db`,
aby „naprawić” brak cache. Przy uszkodzeniu latest pobierz poprzedni `db-RUN-ATTEMPT.enc`.
Dodatkową kopię zaszyfrowanego Release przechowuj poza GitHubem, jeżeli historia stanie się krytyczna.

## Zainicjowanie Release z istniejącej bazy

```bash
python scripts/db_state.py data/paralaksa.db --snapshot data/snapshot.db
openssl enc -aes-256-cbc -salt -pbkdf2 -iter 200000 -in data/snapshot.db -out state-cache/latest.db.enc -pass env:DB_BACKUP_KEY
(cd state-cache && sha256sum latest.db.enc > latest.db.enc.sha256)
gh release create database-backup --title 'Encrypted database backups' --notes 'Recovery: docs/OPERATIONS.md'
gh release upload database-backup state-cache/latest.db.enc state-cache/latest.db.enc.sha256
```

Jeżeli Release już istnieje, pomiń create. Przed zastąpieniem jego plików zachowaj poprzedni snapshot.

## Raporty, koszt i niekompletność

- `plx extract --dry-run`: prognoza kosztu, bez API. Koszt rzeczywisty zależy od sygnałów i ponowień.
- `--limit N`: jawny limit, round-robin po kraju/redakcji, najnowsze materiały najpierw;
  wszystkie odłożone rekordy pozostają w bazie i w liczniku odłożonych.
- Rezerwacja przed wywołaniem używa maksymalnego wyjścia, nie tylko średniej z dry-run.
  Koszty równoległej paczki zapisuje się przed próbami naprawy odpowiedzi.
- Tryb direct kończy przydzielanie po 2400 s, po zakończeniu bieżącej paczki. Limit nie przerywa
  trwającego requestu. Actions ma 60 min. Batch Anthropic pozostaje innym trybem z timeoutem dostawcy;
  produkcyjny DeepSeek działa direct. Nie ma pomiaru czasu większego koszyka z prawdziwym LLM.
- `report` i `run-daily` zwracają kod 1 przy pominiętej/pustej syntezie, błędach walidacji,
  brakach ekstrakcji lub brakujących aktywnych źródłach. Raport niepełny zapisuje się z ostrzeżeniami.
- Powstają `.md`, `.json`, `.short.md`, `.status.json` oraz `.audit.json`.
  Skrót kopiuje do 3 zwalidowanych punktów z pełnego raportu; nie jest osobną generacją LLM.
- Audyt losowy jest deterministyczny (ziarno = data), maksymalnie 30 pozycji na raport,
  z kontekstem i sygnałami. Status `pending` oznacza niewykonany audyt, a nie zaliczenie.
  Należy sprawdzić co najmniej 30 tez łącznie z 3 kolejnych raportów i zapisać werdykty oraz recenzenta.
- Kontrola ID/tematu/kraju nie jest kontrolą wynikania semantycznego. Raport jawnie o tym ostrzega.

## Odbiór operacyjny przed KM4

1. Ustawić sekrety i przenieść istniejącą bazę.
2. Ręcznie wywołać Actions → daily → Run workflow. Zachować URL, koszt, czas, liczby rekordów.
3. Sprawdzić dwa kolejne przebiegi harmonogramu 10:30 UTC. Historia ma rosnąć; odłożone pozycje mają być widoczne.
4. Przećwiczyć odzyskanie z Release bez cache i kontrolę błędnej/nieobecnej bazy.
5. Ukończyć audyt semantyczny trzech regularnych raportów. Dopiero wtedy zatwierdzić ich skróty do prezentacji.

Weryfikacja offline i jeden techniczny ingest nie zastępują tych trzech rzeczywistych dni.
