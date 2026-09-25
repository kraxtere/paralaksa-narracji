# Dwa źródła na kraj — 2026-09-25

- 9 nowych aktywnych źródeł po audycie jakości (54 art., $0,086): The Hindu, Indian Express (IN), Daily Sabah, Hürriyet (TR),
  RTHK, Hong Kong Free Press (HK), Israel Hayom, Haaretz (IL, tylko lead), WAFA (PS, przez dzienną mapę strony).
  30 źródeł, 13 krajów; tylko Katar ma jednego wydawcę (reszta katarskich mediów blokuje automaty). Szczegóły: `docs/SOURCE_REVIEW.md`.
- Poprawka robots.txt: reguły z `*` i `$` (RFC 9309) były ignorowane przez `urllib.robotparser`, np. `Disallow: */feed`.
- Kanały z datą w adresie, zwykła mapa strony (nagłówek z adresu, data z `lastmod`), usuwanie stopki WordPressa z leadów.

# Strona wewnętrzna: zdarzenia i dziennik — 2026-09-25

- `plx site` buduje statyczną stronę do oceny wewnętrznej (`data/site/`, poza gitem; `--zip` do przesłania). Bez publikacji.
- Zdarzenia: widoki Wątki (zestawienie wątek × kraj, kolumny opowieści), Oś czasu (kraje w pasach, publikacja i aktualizacja, przerwy > 12 h zwinięte,
  kolor = wątek), Kraje, Opis karty. Kontrasty podświetlają relacje we wszystkich widokach. Przełączniki oryginał/tłumaczenie
  i czas polski/UTC. Odnośnik z relacji do naszej bazy, jeśli artykuł w niej jest.
- Dziennik: raport syntezy z klikanymi odnośnikami, mapa kraje × tematy (kreskowanie: jedno źródło), porównanie krajów w temacie
  (rozkład tonu, najczęstsze ramy, nagłówki), lista artykułów z filtrami. Karty zdarzeń z tych dni podlinkowane.
- Karty: nowe pola `watki`/`watek` i `typ` źródła; uzupełnione w kartach Xi i Nawrockiego.

# Chiny, Hongkong i koszt ekstrakcji — 2026-09-25

- Nowe źródła: Global Times (Google News sitemap), China News Service 中新网 (po chińsku), SCMP (HK, tylko lead).
  Pierwsze pobranie na żywo: 48 / 54 / 93 artykuły. CN ma teraz 3 źródła i może przejść próg 2 źródeł na kraj.
- Ekstrakcja pomija artykuły, które nie wejdą do porównań (spóźnione, przyszłe, bez daty poza przebiegiem inicjalnym):
  `extracted = 3`, bez wywołania modelu. 24.09 było ich 120 z 463 (26%).
- Cron 05:00 → 10:30 UTC. 24.09 GitHub uruchomił przebieg o 09:36, więc ekstrakcja trafiła w szczyt DeepSeek (06–10 UTC,
  cena ×2). Łącznie oba kroki powinny obniżyć koszt ekstrakcji z ok. 1,37 $ do ok. 0,5 $ przy tej samej liczbie artykułów.
- Tekst po chińsku/japońsku/koreańsku przycinany po znakach (1,3 znaku na słowo limitu), bo licznik słów go nie przycinał.
# Paralaksa zdarzeń — karty zdarzeń, pilot — 2026-09-24

- GPT uzupełnił karty (linki, godziny, liczby) i dodał 5 prób (3 kandydatów, 2 odrzucone). Weryfikacja przez kopie Wayback
  z dnia zdarzenia: 17 archiwów, poprawione wersje Folhi, Independentu, Reutersa i godziny DW.
- `plx events check`: podpowiedzi do kart z Wayback (CDX + kopie), metadanych stron i naszej bazy; wykrywa zmianę
  nagłówka i nagłówki na przemian (Independent 8.05.2024: dwie wersje przez godzinę, to nie „wyostrzenie tytułu”).
  Karty nie zmienia. 14 testów offline.
- Pole `gatunek` w relacji; karta o zbożu przeniesiona do formy `os_czasu` (zapowiedź vs podpisany akt).
- Droga „od wiadomości”: 4 karty wytypowane z naszej bazy (22–23.09) i uzupełnione relacjami spoza bazy:
  oligarchowie/Azerbejdżan (Rzeczpospolita z dwoma nagłówkami o jednej decyzji), śmigłowiec koło Braniewa
  (trzy zdarzenia jednego dnia, nie mylić), „Fort Trump” („jeśli” vs „potwierdzona”), Trump w ONZ (komentarze).
- `plx events archive`: wypełnia puste `archiwum` w kartach istniejącą kopią Wayback (do 48 h po publikacji) albo nową
  przez Save Page Now (konto archive.org, klucze w `.env`). Późniejszych kopii ani kopii po przekierowaniu
  na inny adres (paywall rp, Ukrinform) nie wpisuje. 12 testów offline. Pierwszy przebieg: 17 nowych archiwów.

- Kierunek doprecyzowany: „Jedno zdarzenie. Dwie opowieści.” Jednostką jest zdarzenie, relacje dopinane do niego.
- `events/_szablon_zdarzenia.md`: karta z nagłówkiem YAML (status, forma, fakt, oś czasu, relacje z rolą źródła,
  wersją i archiwum, kontrasty między parami) + sekcje Fakt / Przekaz / Hipoteza odbioru / Ilustracja. Zasady: `events/README.md`.
- 4 karty startowe z ręcznego rozpoznania GPT (niezweryfikowane, bez linków): Mercosur, Ineos Hull, śmigłowce 2023
  (oś czasu), alarm-ptaki (odrzucony: kontrast pozorny).
- Pilot ręczny; API (GDELT, wyszukiwarki) dopiero po ~5 kartach, na podstawie notatek z pilota.

# Paralaksa zdarzeń — prototyp — 2026-09-23

- Zwrot koncepcji po przeglądzie prawnym: krótka forma z nagłówków, bez komentarza (`docs/PARALAKSA_ZDARZEN.md`).
- `plx board`: plansza 1080×1920 (HTML + PNG przez przeglądarkę headless) z kuratorowanego YAML zdarzenia;
  dobór jawną regułą, kolejność wg czasu publikacji, oryginał + tłumaczenie robocze, cytat maks. 15 słów.
- Dwa zdarzenia przykładowe w `events/` (sankcje UE 22.09, wizyta Xi w USA). 7 nowych testów.
- Daily i raport bez zmian. To nie jest ukończony KM4.

---

# Aktualizacja przed KM4 — 2026-09-23

- Dodano migrację bazy v4, metadane redakcji/kanału/gatunku oraz identycznej syndykacji.
- Powiązano tezy z rejestrem sygnałów (temat, kraj, redakcja, article_id i signal_id),
  dodano regresję #147, walidację języka JS, ostrożną pewność także skrótu/autoobrazu.
- Błędne tezy usuwa się w całości po ponowieniu; semantyka pozostaje jawnie nieaudytowana.
- Naprawiono zastępowanie brakującej daty publikacji datą pobrania; raporty inicjalne,
  okno regularne i opóźnienia są widoczne; inicjalny dzień nie wchodzi do baseline.
- Dodano mianowniki, wariant równych wag redakcji, deduplikację identycznych treści,
  dane do porównań redakcji wewnątrz kraju, JSON audytu i skrót.
- Dodano 11 kandydatów US/IL/PS/BR i ponownie sprawdzono 2 TR; brak aktywacji bez kompletu bramek.
- Round-robin i jawne odłożenia, rezerwacje kosztu również przy retry, limit czasu direct,
  kod błędu zamiast pozornie pełnego raportu.
- Actions: osobny workflow testów, zaszyfrowane snapshoty w Release/cache/artefakcie,
  kontrola stanu, sekretów oraz instrukcja odtwarzania.
- Pierwszy raport oznaczono jako archiwalny inicjalny i dodano jawną korektę znanych usterek.
- Granice odbioru i wyniki: `docs/CURRENT_HANDOFF.md`. To nie jest ukończony KM4.

---

# Changelog

## [0.3.0] – 2026-09-23 – Kamień milowy 3: agregacja i raport dzienny

- Metryki dzienne (`aggregate/metrics.py`): udział tematu w publikacjach kraju (normalizacja do wolumenu),
  liczba artykułów i źródeł, rama dominująca, średnia intensywność → `daily_metrics`. Dzień = dzień pobrania.
- Pakiet danych SPEC §9.3 (`aggregate/package.py`): udziały + średnia 28 dni + z-score (od 14 dni historii),
  top 3 ramy per temat × kraj, autoobraz vs obraz zewnętrzny (odległość Jensena–Shannona), kandydaci na
  zbieżność kierunku (zgrubny kierunek stance zamiast embeddingów – KM4) ze słabymi sygnałami i sygnałami
  przeciwnymi, rozlewanie się, nieobecne w Polsce, dodatkowo rozbieżne przekazy między krajami.
- Synteza (`report/synthesize.py`, `prompts/synthesize_report.md`): jedno wywołanie LLM na dzień, walidator
  (`report/validate.py`: odnośniki do istniejących artykułów, sygnały przeciwne, pewność, progi, trend bez
  linii bazowej, cytaty > 15 słów), jedno ponowienie z listą błędów, potem sanityzacja i ostrzeżenia w raporcie.
  Kontrola dziennego budżetu obejmuje syntezę.
- Render Markdown (SPEC §10, bez „Ciekawostek”) z metadanymi: źródła/artykuły/sygnały per kraj, udział
  materiału „tylko lead”, flaga materiału niepełnego, koszt API dnia, wersje modeli i promptów.
- Komendy `plx aggregate`, `plx report`, `plx run-daily` (ingest → extract → aggregate → report);
  migracja bazy v3 (`reports.warnings`).
- GitHub Actions (`.github/workflows/daily.yml`): codziennie 05:00 UTC, baza w cache (+ artefakt), commit raportu.
- **Decyzja modelowa** (CLAUDE.md): synteza na Sonnet 5 bez myślenia po porównaniu 6 wariantów
  (Sonnet 5 i DeepSeek V4-Pro, z myśleniem i bez) na pełnym dniu danych.
- Pierwszy raport: `reports/2026-09-23.md` (807 sygnałów, synteza $0,14).
- 180 testów (offline).

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
