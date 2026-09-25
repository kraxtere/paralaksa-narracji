# CLAUDE.md

## Dla nowej sesji / agenta
Historia projektu żyje w plikach, nie w kontekście rozmowy. Zanim zaczniesz cokolwiek odtwarzać
z pamięci: `CHANGELOG.md` ma decyzje i wyniki per kamień milowy, ten plik ma bieżący stan i konwencje,
`git log` i kod są źródłem prawdy o szczegółach implementacji. Sesja, która to napisała, mogła zostać
zamknięta bez utraty informacji — nie zakładaj, że coś trzeba „przypomnieć sobie" z transkryptu.
Przy dużych wynikach (porównania modeli, zrzuty danych) pisz do plików i odsyłaj ścieżką, nie wklejaj
całości do czatu — to niepotrzebnie puchnie kontekst rozmowy.

## Projekt
**Paralaksa narracji**: codzienna analiza przekazu medialnego z wielu krajów (PL, UA, DE, UK
i spoza bloku). Porównujemy linie przekazu w tematach, nie relacje z tego samego wydarzenia.
Pełna specyfikacja: `SPEC.md`. Jest źródłem prawdy, ale nazewnictwo w repo różni się od niej:

| SPEC | repo |
|---|---|
| `radar-narracji`, „Radar narracji” | `paralaksa-narracji`, „Paralaksa narracji” |
| pakiet `src/radar` | `src/paralaksa` |
| komenda `radar` | `plx` |
| `data/radar.db` | `data/paralaksa.db` |

## Zwrot koncepcji: Paralaksa zdarzeń (2026-09-23)
Po przeglądzie prawnym kierunek to krótka forma: jedno zdarzenie, nagłówki z wielu krajów obok siebie, bez komentarza.
Koncepcja, zasady formatu i plan KM4 w nowym kierunku: `docs/PARALAKSA_ZDARZEN.md`. Prototyp: `plx board events/<id>.yaml`
(`src/paralaksa/board/`, wynik w `data/boards/`). Daily z raportem działa dalej bez zmian.
2026-09-24: format „Jedno zdarzenie. Dwie opowieści.”, ręczny pilot na kartach `events/*.md` (zasady: `events/README.md`).
Automatyzacja dopiero po pilocie.
Wyjątek: `plx events check` (`src/paralaksa/events/check.py`) podpowiada do kart kopie Wayback z dnia publikacji, h1/og:title
i datePublished/dateModified z kopii, zmiany i naprzemienność nagłówków (test A/B) oraz tytuł z naszej bazy. Raport w `data/checks/`.
Nigdy nie zmienia karty ani `sprawdzil`. Indeks CDX odmawia części domen (np. Guardian, 403), wtedy są tylko kopie najbliższe krańcom okna.
`plx events archive` (`src/paralaksa/events/archive.py`) wypełnia tylko puste `archiwum`: istniejąca kopia do 48 h po publikacji
albo nowa przez Save Page Now (SPN2, wymaga `IA_ACCESS_KEY`/`IA_SECRET_KEY`; anonimowe SPN zwraca 401, stan z 2026-09-24).

## Aktualizacja przed KM4 (2026-09-23)

Aktualny punkt wejścia: `docs/CURRENT_HANDOFF.md`, stan źródeł: `docs/SOURCE_REVIEW.md`,
obsługa: `docs/OPERATIONS.md`. Poniższe decyzje KM1–3 zachowano jako historię.
Nowe reguły mają pierwszeństwo przed dawnymi uwagami o dniu pobrania i starcie od zera:
- migracja v4, rzeczywiste braki dat publikacji; regularne porównania z okna D-1..D UTC;
- pochodzenie każdej tezy po signal_id/theme_id/kraju/redakcji, odrzucenie całej wadliwej tezy;
- JS wyłącznie rozkład stance, pewność niska przy jednej redakcji; audyt semantyczny pending;
- metadane i wagi, konserwatywna kontrola identycznej syndykacji, jawne odłożenia;
- trwały zaszyfrowany backup Release, nigdy cichy restart bazy; wymagany DB_BACKUP_KEY;
- kandydaci nieaktywni do kompletu bramek. Nie twierdzić, że rozszerzony koszyk przeszedł odbiór.

## Stan KM3 (2026-09-23)
- [x] **KM1: szkielet i ingest.** Konfiguracja YAML + pydantic, SQLite (pełny schemat §7
  + `fetch_log`, `schema_version`), ingest RSS/Atom/RDF dla 10 źródeł, pełne teksty, `plx init-db | sources | ingest`, testy.
- [x] **KM2: ekstrakcja sygnałów.** Prompt (`prompts/extract_signals.md`), klient LLM z retry
  (`LLMClient` – Anthropic, `DeepSeekClient` – OpenAI-compatible), Message Batches API (Anthropic,
  próg 50 artykułów), walidacja pydantic sygnałów, kontrola kosztów dziennych. Model produkcyjny:
  **DeepSeek V4-Pro**, decyzja i metodologia niżej.
- [x] **KM3: agregacja i raport.** Metryki dzienne, pakiet danych SPEC §9.3 (zbieżność kierunku przez
  zgrubny kierunek stance zamiast embeddingów; dodatkowo „rozbieżne przekazy”), synteza LLM z walidatorem
  i jednym ponowieniem, render Markdown do `reports/`, `plx aggregate | report | run-daily`, workflow Actions.
  Model syntezy: **Sonnet 5 bez myślenia**, decyzja niżej. Bez „Ciekawostek” (KM4).
- [ ] KM4: pełna lista źródeł, GDELT, Global Times przez sitemap, tematy wyłaniające się, ciekawostki, raport tygodniowy.

Po każdym KM: commit, wpis w `CHANGELOG.md`, aktualizacja README i tego pliku.

## Komendy
```powershell
py -3.12 -m venv .venv; .venv\Scripts\python -m pip install -e ".[dev]"   # uv nie jest zainstalowany
.venv\Scripts\python -m pytest -q        # testy offline (httpx.MockTransport)
.venv\Scripts\plx init-db
.venv\Scripts\plx sources
.venv\Scripts\plx ingest [--no-fulltext] [-s ID ...] [--db PATH]
.venv\Scripts\plx extract [--dry-run] [--limit N] [--no-batch] [--db PATH]   # wymaga DEEPSEEK_API_KEY w .env
.venv\Scripts\plx aggregate [--date D] [--db PATH]
.venv\Scripts\plx report [--date D] [--out-dir DIR] [--db PATH]
.venv\Scripts\plx run-daily [--skip-ingest] [--no-fulltext] [--limit N] [--out-dir DIR]
.venv\Scripts\plx board events\<id>.yaml [-o data/boards] [--no-png]   # plansza 1080×1920, PNG przez Chrome/Edge
.venv\Scripts\plx events check events\<karta>.md|events [--dni 2] [--max-fetch 12] [-o data/checks]   # podpowiedzi z Wayback, karty nie zmienia
.venv\Scripts\plx events archive events\<karta>.md|events [--na-sucho] [--bez-wpisu]   # wypełnia puste archiwum (Wayback / Save Page Now)
```
Pełny ingest z pełnymi tekstami trwa ok. 2–2,5 min (~310 artykułów przy pierwszym uruchomieniu).
Pełny `extract` na DeepSeek V4-Pro (tryb bezpośredni, concurrency=4): ~15–20 min na ~310 artykułów.

## Układ kodu
- `src/paralaksa/config.py`: modele `Settings`, `Source`, `Feed`, `Theme`; `load_settings/sources/themes()`;
  `Pricing`/`DeepSeekPricing` (cennik, `is_deepseek_peak`).
- `src/paralaksa/db.py`: schemat, `connect`, `init_db`, `insert_article` (INSERT OR IGNORE), `log_fetch`, `stale_sources`.
- `src/paralaksa/ingest/http.py`: `PoliteClient`: UA, cache robots.txt, 2 s na domenę (wstrzykiwalne `transport/sleep/clock`).
- `src/paralaksa/ingest/rss.py`: `parse_feed`, `ingest_sources` (pełne teksty pobierane round-robin po domenach).
- `src/paralaksa/ingest/dedup.py`: `clean_url` (zapisywany URL) vs `normalize_url` (tylko do hasha).
- `src/paralaksa/ingest/prefilter.py`: odrzut sportu, rozrywki, pogody, horoskopów.
- `src/paralaksa/ingest/fulltext.py`: trafilatura, usuwanie banerów cookies, obcięcie do 1500 słów.
- `src/paralaksa/extract/llm_client.py`: `LLMClient` (Anthropic: bezpośrednio + Message Batches),
  `DeepSeekClient` (OpenAI-compatible, duck-type zgodny z `.complete()`, brak Batches API u DeepSeek),
  `build_client(model, ...)` wybiera klienta po prefiksie modelu (`deepseek*` → `DeepSeekClient`,
  wymaga `DEEPSEEK_API_KEY`; inaczej → `LLMClient`).
- `src/paralaksa/extract/schema.py`: `Signal` (pydantic), `parse_extraction` (walidacja + naprawa
  evidence_span, sprawdzenie dosłowności cytatu w tekście źródłowym).
- `src/paralaksa/extract/signals.py`: `extract_pending`/`estimate_pending` – pętla ekstrakcji per artykuł,
  budżet dzienny, ponowienie przy błędzie walidacji, wybór trybu batch/direct.
- `src/paralaksa/aggregate/metrics.py`: `compute_daily_metrics` (udział = artykuły kraju z tematem / wszystkie
  artykuły kraju danego dnia), `day_signals`. Przebieg D wyznacza `fetched_at`; regularne porównania tylko dla `published_at` w oknie D-1..D UTC (szczegóły: `docs/CURRENT_HANDOFF.md`).
- `src/paralaksa/aggregate/stats.py`: `z_score`, `js_divergence` (log2), `coarse_direction` (stance → kierunek).
- `src/paralaksa/aggregate/package.py`: `build_data_package` – pakiet SPEC §9.3 (+ „rozbieżności” między
  krajami); historia/linia bazowa z `daily_metrics`. Payload bez URL-i (model cytuje `article_id`).
- `src/paralaksa/report/schema.py`: `ReportOutput` (pydantic), `parse_report`, `SCHEMA_EXAMPLE` dla promptu.
- `src/paralaksa/report/validate.py`: `validate_report` (odnośniki, progi, trend bez linii bazowej, cytaty
  > 15 słów), `sanitize_report` (ostatnia deska po nieudanym ponowieniu: usuwa twierdzenia bez odnośników).
- `src/paralaksa/report/synthesize.py`: `run_synthesis` – jedno wywołanie, jedno ponowienie z listą błędów,
  budżet dzienny; `report/render.py`: `collect_meta`, `render_markdown`; `report/pipeline.py`: `generate_report`.
- `.github/workflows/daily.yml`: cron 05:00 UTC, baza jako zaszyfrowany snapshot w Release `database-backup` (cache i artefakt to kopie), commit `reports/`. Kod 1 tylko przy ostrzeżeniach blokujących (synteza, ekstrakcja, brak >1/3 aktywnych źródeł); pojedynczy kanał/źródło to ostrzeżenie informacyjne.

## Konwencje
- Identyfikatory i docstringi po angielsku; komunikaty CLI, komentarze w YAML i raporty po polsku.
- Daty w bazie: ISO 8601 UTC (`db.to_iso`).
- **Nie normalizuj zapisywanego URL.** Ukraińska Prawda zwraca 403 bez końcowego `/`.
  Deduplikacja idzie po `url_hash(normalize_url(...))`, a w bazie i raportach jest `clean_url(...)`.
- Prefiltr jest celowo ostrożny. Ogólne słowa („football”, „celebrity”) liczą się tylko w sekcji URL
  i kategoriach kanału, nie w tytule, bo artykuł polityczny może je zawierać.
- Testy bez sieci. Nowe przypadki z prawdziwych kanałów dodawaj jako fixtures w `tests/fixtures/`.

## Zasady obowiązkowe (SPEC §3, §6, §16)
- Normalizacja do wolumenu, linia bazowa 28 dni, progi (≥3 kraje, ≥2 źródła/kraj), sygnały przeciwne,
  poziom pewności, każde twierdzenie z odnośnikiem (id + URL). Implementacja w KM2–3.
- Opisujemy przekaz medialny, nie fakty; bez prognoz jako faktów.
- Pobieranie: respektuj robots.txt, nie obchodź paywalli ani ochrony antybotowej, identyfikujący UA.
- Pełne teksty tylko lokalnie (`data/`, poza gitem), nigdy w raportach; cytaty maks. 15 słów.
- Źródła rosyjskie, także objęte sankcjami UE (RT, RIA, Izwiestia), są dozwolone i w kartach zdarzeń wymagane
  (decyzja właściciela 2026-09-25, zmienia wcześniejszy zakaz). Daily: lista źródeł bez zmian, dopóki właściciel nie zdecyduje.
  Taksonomii tematów nie zmieniamy automatycznie.

## Decyzje modelowe (ekstrakcja sygnałów, KM2)

**Sonnet 5 zamiast Haiku 4.5** (SPEC §9.2 proponuje tańszy model domyślnie): porównanie 2026-09-23
na 20 artykułach pokazało, że Haiku częściej gubi drugorzędne sygnały i miesza aktorów w artykułach
wieloaktorowych; Sonnet 5 wybrany jako baseline jakości mimo wyższej ceny.

**DeepSeek V4-Pro zamiast Sonnet 5 do produkcji** (odejście od doboru powyżej i od SPEC §4/§9.2):
porównanie 2026-09-23 na 26 artykułach (wcześniejsze 20 + 6 o Chinach z różnych stron, celowo dobranych
pod kątem testu neutralności wobec dostawcy z siedzibą w Chinach):
- DeepSeek V4-Pro **bez myślenia** dał **82/82 sygnałów** — identyczna liczba co Sonnet 5 — za
  **~7,7× niższą cenę** ($0,051 vs $0,396 na próbce).
- Na jedynym jawnie krytycznym wobec Chin artykule w próbce (F-35 w Hongkongu) V4-Pro był *surowszy*
  w ocenie niż Sonnet, nie łagodniejszy — brak dowodu na spłaszczanie/cenzurowanie przekazu.
- Jedna nieprawidłowość przypisania aktora na artykule 294 (własny materiał CGTN: rama przypisana
  US zamiast CN) — pojedynczy przypadek, do obserwacji przy pełnym przebiegu, nie ustalony wzorzec.
- **Myślenie (`thinking: enabled`) nie działa przy obecnym promptcie**: nawet `reasoning_effort: low`
  zużywa >4000 tokenów na samo rozumowanie i ucina odpowiedź (7/8 artykułów nieudanych w teście) —
  strukturalna cecha długiego promptu (instrukcje + lista tematów), nie kwestia doboru poziomu.
  Odpuszczone; `extract.thinking` zostaje `disabled`.

**Konsekwencje decyzji o DeepSeek** (świadomie zaakceptowane):
- Brak Message Batches API u DeepSeek → ekstrakcja zawsze idzie bezpośrednio (`run_direct`),
  `extract.batch_threshold` nie ma znaczenia dla tego modelu (por. SPEC §9.2, która zakłada Batches
  powyżej 50 artykułów).
- Treść artykułów trafia na serwery DeepSeek (poza Anthropic) — świadoma zgoda użytkownika.
- Cennik DeepSeek zależy od pory dnia (szczyt/poza szczytem, `is_deepseek_peak`); przebiegi nie są
  automatycznie planowane pod tańsze okna.
- Narzędzie do przyszłych porównań: `data/compare_models.py` (poza gitem, jednorazowe/ad-hoc użycie).

## Decyzje modelowe (synteza raportu, KM3)

**Sonnet 5 bez myślenia** (zgodnie z domyślnym SPEC §9.4, ale po teście). Porównanie 2026-09-23 na pełnym
pakiecie dnia (807 sygnałów, ~34–52 tys. tokenów wejścia zależnie od tokenizera), 6 wariantów, po jednym
przebiegu każdy (wyniki: `data/compare_synth/<wariant>/2026-09-23.md` + `summary.json`, skrypt
`data/compare_synthesis.py`, oba poza gitem):

| wariant | walidacja 1. odpowiedzi | koszt | czas |
|---|---|---|---|
| Sonnet 5, myślenie wył. | 2 błędy (puste article_ids), po ponowieniu OK | $0,29 (2 wywołania) | 85 s |
| Sonnet 5, adaptive | uszkodzony JSON; po ponowieniu 1 błąd → sanityzacja | $0,43 (2 wywołania) | 223 s |
| DeepSeek V4-Pro, wył. | OK | $0,028 | 54 s |
| DeepSeek V4-Pro, low | OK | $0,039 | 156 s |
| DeepSeek V4-Pro, high | OK | $0,050 | 244 s |
| DeepSeek V4-Pro, max | ucięte przy 16 000 tokenów (całość na rozumowanie) | $0,055 | 349 s |

- **Jakość (przegląd ręczny) zadecydowała na korzyść Sonnet.** Kluczowa różnica to kalibracja pewności
  i trzymanie się progów (SPEC §3): Sonnet dawał „niski” tam, gdzie kraj ma 1 źródło albo porównanie
  obejmuje 2 kraje, i to uzasadniał. DeepSeek bez myślenia dawał „wysoki” na takich samych danych,
  nazwał temat „nowym” bez linii bazowej i miał usterki językowe („autoresponder” zamiast „autoobraz”);
  z myśleniem (low/high) kalibracja wyraźnie lepsza, ale nadal „średni” przy krajach z jednym źródłem.
  Sonnet (oba warianty) uwzględnił autoobraz Chin (najwyższe JS dnia), DeepSeek bez myślenia go pominął.
- **Myślenie**: u Sonnet adaptive dało nieco bogatszy raport (więcej rozbieżności, Bliski Wschód), ale +48%
  kosztu, 2,6× dłużej i gorszą niezawodność JSON – nie warto. U DeepSeek myślenie poprawia jakość, a `max`
  nie mieści się w 16 000 tokenów (jak w KM2: rozumowanie zjada limit).
- **Tania alternatywa**: DeepSeek V4-Pro z `thinking: enabled`, `effort: high` (~$0,05/dzień zamiast ~$0,14–0,29)
  – zmiana dwóch linii w `settings.yaml` (`models.synthesize`, `report.thinking/effort`).
- **Poprawki promptu po teście** (problemy wspólne dla modeli): niepusta lista article_ids w „w_skrocie”,
  zakaz powtarzania ograniczeń danych w „w_skrocie”, „wysoki” tylko przy spełnionych progach. Przebieg
  produkcyjny po poprawce: Sonnet bez ponowienia, $0,14, żadnego „wysoki” poniżej progów.

## Znane ograniczenia
- **Zbieżność kierunku prawie zawsze pusta przy obecnej ekstrakcji.** ~83% sygnałów ma stance `neutralny`
  (673/807), więc zgrubny kierunek z rozkładu stance rzadko wychodzi poza „neutralny” (2026-09-23: 0 kandydatów,
  2 słabe). Do tego źródła jednokrajowe (QA, CN) nigdy nie spełnią progu 2 źródeł. Właściwe grupowanie ram
  przez embeddingi (KM4) albo kalibracja stance w promptcie ekstrakcji to kolejny krok; nie obniżać progów SPEC.
- **Pierwszy przebieg (2026-09-23) jest inicjalny**: zawiera zaległość z RSS (publikacje 09-08…09-23)
  i nie wchodzi do linii bazowej. Kolejne dni porównują tylko okno publikacji D-1..D UTC.
- **Baza w Actions** żyje w zaszyfrowanym Release (`docs/OPERATIONS.md`); brak backupu zatrzymuje przebieg, nigdy cichy restart.
- **rp i spiegel bez pełnego tekstu** (paywall, nie obchodzimy). W KM2 ekstrakcja dla nich działa
  tylko na tytule i leadzie (lead rp ok. 200 znaków, Spiegel ok. 225). Sygnały będą płytsze: mniej sygnałów na artykuł,
  niższa `intensity`, uboższe ramy. To oznacza, że PL (rp) i DE (spiegel) są asymetryczne względem źródeł z pełnym
  tekstem (onet, tagesschau). Przy interpretacji porównań między krajami i w metadanych raportu (KM3) trzeba to uwzględnić.
  Rozważyć w KM2: flagę „tylko lead” w sygnałach lub wagę per źródło.
- **Prefiltr odcina całe sekcje.** Artykuły z `/sport/` czy `/weather/` odpadają nawet z kątem
  politycznym (np. BBC Sport o meczu Izrael–Irlandia, El Niño w BBC Weather). To świadomy kompromis.
  Kontrola z 2026-09-23: z 319 wpisów odrzucono 5, wszystkie przejrzane ręcznie.

## Źródła (`config/sources.yaml`, weryfikacja 2026-09-23)
Aktywne (10): rp, onet (PL); ukrinform, pravda_ua (UA, po ukraińsku); tagesschau, spiegel (DE);
bbc (world + europe), guardian (UK); aljazeera (QA), cgtn (CN). `fulltext: false`: rp i spiegel (paywall).

Nieaktywne, bo nie działa RSS: PAP (Incapsula), Polskie Radio, Suspilne (403), Telegraph (402), Global Times
(`rss/outbrain.xml` to nieaktualny kanał syndykacji; w KM4 przez `https://www.globaltimes.cn/sitemap.xml`).
Nieaktywne, ale zweryfikowane, do włączenia w KM4: wp, gazeta (to nie Wyborcza), kyivindependent, dw, faz, skynews,
thehindu, dailysabah, hurriyet. Martwe: Xinhua RSS (2018), China Daily RSS (404). Reuters/AP/AFP bez publicznego RSS.
