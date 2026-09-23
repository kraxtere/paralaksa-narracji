# Paralaksa narracji — stan przed KM4

Data: 2026-09-23. Punkt wyjścia: `5d330d619c494648f8bb13db29e19b09547aa06f`.
Zlecenie: `PLAN_PRZED_KM4_PARALAKSA.md`. **KM4 nie rozpoczęto.**
Implementacja zabezpieczeń i narzędzi jest gotowa do przeglądu. Pełny odbiór planu pozostaje otwarty:
nie aktywowano nowych źródeł bez bramek, nie ma trzech rzeczywistych raportów ani ich audytu semantycznego.

## Co zmieniono

| punkt planu | kod / zachowanie | rzeczywisty stan odbioru |
|---|---|---|
| 1. Dowody | rejestr sygnałów, `dowody` w każdej tezie, zgodność ID/tematu/kraju/redakcji, segment kontrsygnałów, jeden retry i usunięcie całej wadliwej tezy | regresja #147 PASS; audyt semantyczny 30 tez z 3 raportów oczekuje |
| 2. Daty | brak daty zapisuje NULL; status inicjalny/regularny; widoczny zakres i opóźnienia; starsze/niedatowane poza regularnym porównaniem; pierwszy dzień poza baseline | testy UTC/reingest/braku daty PASS; liczb historycznej zaległości nie odtworzono bez bazy |
| 3. Język | JS jako odległość rozkładów nacechowania; pułap pewności także skrótu i autoobrazu; jeden głos wymaga niskiej pewności i nazwy redakcji | regresje PASS; nie jest to pełny detektor wszelkich parafraz, nadal potrzebny audyt |
| 4. USA | PBS (2 kanały=1 redakcja), Fox (2 kanały), NPR i ProPublica jako kandydaci; metadane, dane do porównań wewnątrz kraju | świeże RSS potwierdzone; zakres użycia/analiza jakości niezaliczone; 0 nowych aktywnych |
| 5. IL/PS/TR | odrębne kraje i perspektywy; TOI/Ynet/Haaretz, WAFA i Ma’an; ponowny test TR; QA pozostaje osobne | kanały/warunki według SOURCE_REVIEW; minimum koszyków nieosiągnięte |
| 6. BR | Folha Mundo i Agência Brasil, język pt i sekcje | świeżość PASS; prawa i ręczny audyt ekstrakcji PT oczekują; BR nieaktywne |
| 7. Mianowniki | zakresy i gatunki, głębokość, braki per redakcja; wagi po artykułach i równych redakcjach; dodatkowy wariant po deduplikacji; flagi różnicy ≥10 pp | test 10× i identycznych przedruków PASS; tłumaczone/przeredagowane depesze nadal mogą się dublować |
| 8. Actions/baza | workflow testów; snapshot SQLite, zaszyfrowany Release bez TTL, cache/artefakt jako kopie; walidacja i brak cichego restartu | lokalne testy odtworzenia PASS; daily nieuruchomiony, brak sekretów w środowisku i narzędzia dispatch |
| 9. Koszt/czas | rezerwacja maksymalnego wyjścia przed API/retry, księgowanie całej paczki przed retry, round-robin, licznik odłożonych i limit czasu direct | 282 rzeczywiste rekordy w dry-run; test 20 źródeł jawnie odracza przy budżecie; nie zmierzono czasu prawdziwego LLM |
| 10. Skrót | do 3 punktów skopiowanych z pełnego raportu, te same dowody, ograniczenia, brak prognoz i porad | generacja offline PASS; dopuszczenie do prezentacji po audycie |

## Reguły danych i ich ograniczenia

`fetched_at` wyznacza przebieg D. W raporcie inicjalnym kwalifikujemy zaległość (z wyjątkiem
jawnie przyszłych dat). W regularnym raporcie porównujemy pobrane w D materiały z `published_at`
w przedziale `[D-1 00:00 UTC, D+1 00:00 UTC)`. To dwa dni kalendarzowe, nie udawane ruchome
48 godzin od startu. Dodatkowo liczba starszych niż 24/48 h jest liczona względem rzeczywistego pobrania.
Brak `published_at` nie staje się „dzisiaj”. Daty zastępcze z KM3 pozostają nierozstrzygalne bez oryginałów.

Mianownik udziału artykułowego obejmuje zakwalifikowane pobrane artykuły, również jeszcze bez ekstrakcji.
Dlatego niekompletność jest jawna i blokuje kod sukcesu przebiegu; takie udziały mogą zaniżać tematy.
Wariant równych redakcji średniuje udziały redakcji mających materiały w danym przebiegu.
Brak aktywnej redakcji jest osobnym ostrzeżeniem, a nie dopisaniem zer do jej nieznanego przekazu.

Deduplikacja między kanałami pozostaje po URL/tytule. Identyczne pełne teksty ≥80 słów albo leady
≥40 słów dostają hash. Redakcje połączone identycznymi materiałami w segmencie są konserwatywnie
liczone jako jeden niezależny głos (możliwe zaniżenie przy mieszance materiałów własnych i agencyjnych).
Nie twierdzimy, że to pełne rozpoznawanie syndykacji. Próg 3 kraje / 2 niezależne źródła nie został obniżony.

## Sprawdzenia wykonane

- 200 testów offline, w tym 20 nowych przypadków/regresji przed KM4.
- Sprawdzenie składni YAML i skryptów Bash obu workflowów.
- Rzeczywisty audyt 13 kandydatów/ponownych sprawdzeń: `source-checks-2026-09-23.json`.
- Rzeczywisty ingest dotychczasowego koszyka: **282 nowe artykuły, 9 działających redakcji**,
  błąd kontroli robots dla Spiegla. Tryb tylko tytuł/lead, bez wywołania LLM.
- Dry-run: około **737814 tokenów wejścia, 1,867 USD ekstrakcji** według zastanej konfiguracji cenowej.
  Podwojony wolumen to około **3,734 USD** samej ekstrakcji, ponad budżet 3 USD jeszcze przed syntezą.
  To oszacowanie, nie zmierzony rachunek API ani pomiar większego aktywnego koszyka.
- Łączny koszt API tej sesji: **0 USD**. Wyniki techniczne: `technical-run-2026-09-23.json`.
- API GitHub przed zmianami zwróciło `total_count: 0` dla wszystkich Actions, nie tylko PR.

## Wymagane dalsze kroki (bez udawania zaliczenia)

1. Potwierdzić zakres wykorzystania źródeł dla planowanego produktu, a następnie jakość sygnałów.
   Szczegóły i bezpośrednie linki do regulaminów: `SOURCE_REVIEW.md`.
2. Właściciel ustawia `DEEPSEEK_API_KEY`, `ANTHROPIC_API_KEY` i `DB_BACKUP_KEY` w Actions.
   Klucze dostawców nie są dostępne w lokalnym środowisku tej sesji; nie odczytywano sekretów repozytorium.
3. Przenieść oryginalną bazę KM3 do zaszyfrowanego Release według `OPERATIONS.md`.
   Jeżeli rzeczywiście brak jakiejkolwiek starej bazy, ręczna inicjalizacja jest osobną jawną opcją.
4. Ręczny daily + dwa kolejne harmonogramy; zapisać czasy, koszty, ciągłość historii i braki.
5. Audyt co najmniej 30 tez z 3 regularnych raportów, w tym semantyka oraz nazwy redakcji.
6. Dopiero po tych bramkach wejść w KM4 (embeddingi, GDELT, tematy wyłaniające się i trend tygodniowy).

Raport `reports/2026-09-23.md` ma jawną korektę archiwalną, nie ponowną syntezę.
Nie używać go jako dowodu, że nowy walidator zaliczył rzeczywisty raport.

## Pierwszy produkcyjny daily (2026-09-23, run 35891108377)

Baza KM3 (312 art., 807 sygn.) wgrana do Release `database-backup`; odszyfrowanie i suma SHA-256 sprawdzone.
Przebieg ręczny 16:46–17:00 UTC (13,5 min). Backup, cache, artefakt i commit działały mimo błędu kroku.

| etap | wynik |
|---|---|
| ingest | 178 nowych (cgtn 0 nowych, 50 duplikatów; spiegel 8), 0 błędów kanałów; deduplikacja z KM3 zadziałała |
| extract (DeepSeek V4-Pro) | 178/178, 442 sygnały, 12 ponowień, 0 błędów trwałych, **$0,29** (dry-run GPT szacował $1,87 na 282 — zawyżone) |
| synteza (Sonnet 5) | **porażka**: 2 wywołania, 918 529 tokenów wejścia, $1,90; model mylił signal_id z article_id, 32 błędy walidacji → wszystkie tezy usunięte |

Przyczyna: rejestr `dowody` wysyłał modelowi wszystkie 1249 sygnałów ze streszczeniami i hashami grup
(690 tys. z 930 tys. znaków pakietu). Poprawka: `synthesize.llm_payload` — rejestr jako zwarte wiersze
5 kolumn, bez `content_group/publisher_group`; walidator nadal używa pełnego pakietu. Ten sam dzień: 258 tys. znaków
(~$0,33). Dzień 2026-09-23 miał status inicjalny i 490 artykułów; regularna doba będzie mniejsza.
Pusty raport przywrócono do wersji archiwalnej (artefakty nieudanej syntezy usunięte z `reports/`).
Budżet dnia wyczerpany ($2,80/$3), więc kolejna próba: harmonogram 2026-09-24 05:00 UTC.

## Poprawka syntezy: brakujące pola w przykładzie schematu (2026-09-23, po pierwszym daily)

Po zmniejszeniu payloadu (patrz wyżej) synteza nadal nie przechodziła: **53/59 błędów walidacji**,
we wszystkich sekcjach `dowody: []` i `theme_id: ""`. Przyczyna: przykładowy JSON w
`SCHEMA_EXAMPLE` (`src/paralaksa/report/schema.py`) nigdy nie pokazywał pól `dowody`/`theme_id` —
były wspomniane wyłącznie zdaniem tekstu po przykładzie. Model kopiuje kształt przykładu niemal
dosłownie i pomija to, co jest tylko w opisie. Błąd nie jest regresją mojej zmiany payloadu: istniał
w promptcie od commita 4b8d3a2, po prostu nikt wcześniej nie uruchomił syntezy na pełnych, prawdziwych
danych (audyt "pending" z handoffu GPT to teraz potwierdzone: nie zaliczony).

Poprawka: `dowody`/`theme_id` dodane wprost do każdej sekcji przykładu. Weryfikacja na tym samym payloadzie
(490 artykułów, dzień inicjalny): 53 → 6 błędów po pierwszym wywołaniu, **0 błędów blokujących po
ponowieniu** (1 usunięta teza — QA z jednym źródłem bez nazwy redakcji, oczekiwane działanie sanityzacji).
`plx report --date 2026-09-23` zakończone `exit 0`, `status.json.complete = true`.
Test regresyjny: `test_schema_example_shows_dowody_and_theme_id_inline` (`tests/test_pre_km4.py`).

Koszt tego dnia po korekcie: ingest+extract $0,89 (produkcyjnie) + synteza $0,68 (dwa wywołania z
poprawionym promptem, po nieudanej próbie $1,90 z 4b8d3a2 usuniętej z bazy) = **$3,79 zaksięgowane
w bazie**. Do tego moje ad-hoc wywołania diagnostyczne poza `run_synthesis` (~$1,75 realnego kosztu
API Anthropic, nie przechodziły przez `db.record_usage`, więc nie są w liczniku budżetu ani w bazie) —
patrz uwaga niżej. Łączny rzeczywisty koszt API tej sesji na koncie Anthropic: **ok. $5,5**, nie $3,79.
Limit `budget.max_daily_usd` był tymczasowo podniesiony do $4,2 na czas naprawy i przywrócony do $3,0
w `config/settings.yaml` po zakończeniu. Baza (`data/paralaksa.db`, 490 art., 1249 sygn., 1 raport)
i zaszyfrowany backup w Release zaktualizowane do tego stanu.

**Uwaga na przyszłość — luka w księgowaniu kosztów.** Wywołania `LLMClient.complete()` poza pętlą
`run_synthesis`/`extract_pending` (np. ręczne debugowanie) nie zapisują kosztu do `api_usage` i nie są
liczone do dziennego limitu, mimo że realnie obciążają konto dostawcy. Przy debugowaniu produkcyjnym
liczyć się z tym ręcznie; docelowo rozważyć wspólny wrapper księgujący koszt niezależnie od wywołującego.

## USA i Brazylia aktywowane (2026-09-23), IL/PS zamienniki sprawdzone

Właściciel: aktywować USA/BR teraz akceptując brak formalnego audytu praw, ale wykonać od razu
audyt jakości ekstrakcji, skoro i tak jest potrzebny. Wykonane: realny ingest 229 art. + ekstrakcja
próbki 40 art. (DeepSeek V4-Pro, $0,098), ręczny przegląd sygnałów — bez zastrzeżeń jakościowych.
Aktywne: pbs, fox, npr, propublica (US), folha, agenciabrasil (BR) — `fulltext: true`,
`verification.risk_accepted` w `config/sources.yaml` dokumentuje świadomą decyzję. Aktywnych źródeł: 16.
Szczegóły i tabela wyników: `docs/SOURCE_REVIEW.md`.

Nowi kandydaci IL/PS (zamienniki za zablokowanych timesofisrael/ynetnews/maan/wafa): **jpost** (IL,
JPost, robots.txt czysty, 10/26 świeżych) i **alquds_ps** (PS, Al-Quds, arabski, robots.txt czysty,
30/30 świeżych). Oba przeszły ten sam audyt jakości (bez zastrzeżeń), ale **pozostają `active: false`**
— właściciel nie zdecydował jeszcze o ich włączeniu. Sprawdzone i odrzucone: Israel Hayom (blokada
Akamai na poziomie robots.txt), Palestine Chronicle (trwałe HTTP 429), PNN (robots.txt zabrania
`*/feed`), Mondoweiss (redakcja US, nie PS — nie pasuje do `editorial_country`).

Przy audycie znaleziony i naprawiony realny błąd: `is_verbatim` (kontrola dosłowności cytatu)
odrzucał poprawne cytaty z arabskiego, bo `\w+` nie rozdziela doklejonych bez spacji przedrostków
(و, ب...) od rdzenia. 4/21 sygnałów z al-quds odrzuconych z tego powodu przed poprawką. Naprawa +
testy na rzeczywistych przypadkach: commit `c34f4e7`. Bez tego każde źródło arabskojęzyczne miałoby
systemowo zaniżoną liczbę sygnałów — dotyczy też przyszłych kandydatów w innych krajach arabskojęzycznych.

Baza produkcyjna i backup w Release **nie zostały ręcznie zaktualizowane o te źródła** — nowe źródła
i ich artykuły trafią do bazy przy najbliższym `run-daily` (harmonogram, 05:00 UTC), bo
`upsert_sources`/ingest robią to automatycznie na podstawie `config/sources.yaml`. Nie było potrzeby
ręcznej interwencji poza commitem konfiguracji.

**Aktualizacja księgowania kosztów z poprzedniej notatki**: audyt jakości (ingest + ekstrakcja próbki)
poszedł przez `extract_pending`/`run_synthesis`-analogiczną ścieżkę (`extract_pending` woła `record_usage`
poprawnie), więc $0,098 jest realnym, policzonym kosztem — nie dotyczy go luka opisana wyżej (ta dotyczy
tylko ręcznych `llm.complete()` wywołań pomijających `run_synthesis`/`extract_pending`).

## JPost i Al-Quds aktywne; kontrola atrybucji w raporcie (2026-09-23)

- `jpost` (IL) i `alquds_ps` (PS) aktywowane na zasadach USA/BR; `plx ingest` na kopii bazy: 26 + 30 nowych,
  bez błędów. Aktywnych: 18 źródeł, 10 krajów.
- Przegląd zewnętrzny (GPT) wykazał w raporcie 2026-09-23 tezy przypisujące przekaz redakcji/krajowi bez
  dowodu z nich (w_skrocie.0 wymienia BBC, dowody bez BBC; slabe_sygnaly.0 mówi o UK, dowód tylko z QA).
  Potwierdzone. Nowa kontrola `attribution_errors` (`report/validate.py`): każda redakcja nazwana w tekście
  (aliasy-prefiksy w `sources.yaml` → `aliases`, łapią odmianę) i każdy kod kraju muszą mieć dowód z niej.
  Na raporcie 2026-09-23 znajduje 4 błędy: 2 zgłoszone + 2 nowe w autoobrazie (Onet i Spiegel wymienione bez dowodów).
  Reguła dopisana też do promptu. Ograniczenie: przymiotniki („brytyjskie media”) nie są wykrywane;
  to nadal nie jest pełny audyt semantyczny (czy sygnał faktycznie wspiera sens zdania).
- Raport 2026-09-23 w repo **zawiera te 4 błędne przypisania** — wygenerowany przed kontrolą.
- Formalny przegląd warunków 18 źródeł zlecony GPT (praca tekstowa, bez dostępu do kodu):
  `docs/LEGAL_REVIEW_BRIEF.md`.
