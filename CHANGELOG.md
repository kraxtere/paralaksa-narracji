# GDELT przez BigQuery: kandydaci na karty i brakujące relacje — 2026-09-26

- DOC API GDELT nie nadaje się do pracy: większość zapytań kończy się 429, jedna karta ok. 15 min (próba 2026-09-26).
  Strona www GDELT używa tego samego API. Działa publiczny zbiór `gdelt-bq.gdeltv2` w BigQuery (darmowy tryb piaskownicy,
  1 TB zapytań miesięcznie): doba nagłówków ok. 0,2 GB, zapytanie w kilka sekund. Każde zapytanie najpierw na sucho, twardy
  limit `--max-gb` (domyślnie 5). Logowanie: `gcloud auth application-default login`, projekt w `.env` jako `GCP_PROJECT`.
- `plx gdelt rezonans --dzien D`: osoby i organizacje (GKG, nazwy po angielsku dla wszystkich języków), o których pisało wyraźnie
  więcej redakcji niż średnio w 7 dniach wcześniej; ich nagłówki z wielu języków; jedno wywołanie modelu ekstrakcji grupuje je
  w wydarzenia i tłumaczy. Powody pokazane osobno (redakcje, języki, wzrost), bez jednej liczby. Rozrywka i sport pominięte.
  25.09: 5–6 kandydatów (Leon XIV we Francji, Netanjahu w ONZ, kolacja Trump–Xi, ataki dronów Rosja–Ukraina, lotnisko Berlusconiego),
  0,2–0,5 GB i ok. 0,03 $. Ograniczenie: wydarzenie bez wyraźnej osoby (Kolumbia zrywa stosunki z Iranem) może nie wypłynąć.
- `plx gdelt szukaj events/<karta>.md`: model podaje frazy w 13 językach i alfabetach, BigQuery szuka nagłówków od dnia przed
  kartą do `--dni-po` dni po, model sprawdza każdy nagłówek (czy o tym zdarzeniu, także reakcje) i tłumaczy. Redakcje już w karcie
  osobno, odrzucone w JSON. Karty nie zmienia. Fort Trump: 36 relacji spoza karty w 11 językach, w tym strona rosyjska, której
  karta nie miała (Wiesti, RIA, Lenta, Wzgląd); Braniewo: 51 w 8 językach. Koszt ok. 0,8 GB i 0,01 $ na kartę.
  Pierwsza wersja polecenia dawała prawie same frazy angielskie i model przepisywał oryginały zamiast tłumaczyć; stąd frazy per język
  i kontrola przepisanych tłumaczeń. Sito nie jest pełne (Kommersant przy Fort Trump odpadł przez frazę z „Polską”).
- Przy sprawach lokalnych GDELT nie pomaga (Kłodawa: 1 artykuł). Wyniki to podpowiedzi: nagłówek, godzinę i gatunek sprawdza się
  na stronie redakcji. Nagłówki trafiają do DeepSeek (jak historie dnia). Zależność opcjonalna: `pip install -e ".[gdelt]"`.

# Strona wewnętrzna: tryb ciemny i logo — 2026-09-25

- Tryb ciemny: przy pierwszym wejściu według ustawień systemu, przełącznik w pasku, wybór zapamiętany w przeglądarce.
  Wszystkie kolory strony idą przez zmienne CSS (`site.css`, zestaw `[data-theme="dark"]`), także mapa cieplna i oś czasu w JS.
- Logo: ten sam punkt widziany z dwóch miejsc (pełne koło i przesunięty pierścień). W pasku, jako ikona karty (data URI,
  strona nadal bez plików zewnętrznych) i jako `logo.svg` / `logo-ciemne-tlo.svg` obok strony.

# Strona wewnętrzna: najważniejsze z dnia — 2026-09-25

- Dziennik ma nową pierwszą zakładkę „Najważniejsze”: historie dnia (wydarzenia opisywane w co najmniej 3 krajach, po jednym
  nagłówku z kraju w tłumaczeniu z oryginałem pod spodem), „Co się wyróżnia” (największe odchylenia udziału tematu w kraju od średniej
  pozostałych, bez modelu) i „W skrócie” z raportu. Strona główna pokazuje historie ostatniego dnia.
- Historie dnia liczy `plx site` (nie daily): dwa wywołania DeepSeek V4-Pro na dzień, ok. 0,03–0,04 $, wynik w `data/stories/`.
  Pierwsza wersja bez weryfikacji dokleja artykuły nie na temat, żeby dobić do 3 krajów (np. dowódca NATO o Putinie przy przemówieniu
  prezydenta Iranu). Drugi krok przypisuje każdy artykuł do wydarzenia albo go odrzuca. Po nim na 12 historiach z 23–24.09 zostały
  2–3 wątpliwe przypisania na ok. 60, zawsze z widocznym oryginałem.
- Weryfikacja w porcjach po 60 artykułów: 25.09 (1094 artykuły po dodaniu źródeł, 141 kandydatów przy wizycie Xi) jedna odpowiedź
  przekroczyła 8000 tokenów i strona wyszła bez historii. Po podziale: 6 historii, 0,049 $. Słabość do obserwacji: nagłówek kraju
  bywa o wątku pobocznym (protest w Nowym Jorku zamiast przemówienia Netanjahu), choć artykuł o samym wydarzeniu jest na liście.
- Tematy nazwane przez model poza taksonomią (156 dziennie) schowane z mapy, porównania i filtrów. „Artykuły” → „Wszystkie artykuły”.

# Strona wewnętrzna: nowy wygląd — 2026-09-25

- Zdarzenie: nowa pierwsza zakładka „Obok siebie” (kontrast = nagłówki w kolumnach, „zostawia z”, opis różnicy, zastrzeżenia).
  Wątki pionowo z kartami w siatce, bez przewijania w bok. W tabeli wątków i w kontrastach nazwy redakcji zamiast numerów relacji.
- Strona główna: karta zdarzenia z dwoma zestawionymi nagłówkami (pierwszy kontrast, inaczej pierwsze relacje dwóch wątków),
  zdarzenia według miesięcy, dni dziennika jako kafelki.
- Dziennik: liczby dnia w kafelkach, puste sekcje raportu zwinięte do jednej linii, odnośniki z nazwą redakcji, kolor pewności, legenda mapy.
- Typ medium wyróżniony (państwowe/prorządowe, emigracyjne). Nagłówki szeryfowe, układ na telefon, obsługa klawiatury.

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
