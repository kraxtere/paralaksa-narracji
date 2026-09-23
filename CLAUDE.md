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

## Stan (2026-09-23)
- [x] **KM1: szkielet i ingest.** Konfiguracja YAML + pydantic, SQLite (pełny schemat §7
  + `fetch_log`, `schema_version`), ingest RSS/Atom/RDF dla 10 źródeł, pełne teksty, `plx init-db | sources | ingest`, testy.
- [x] **KM2: ekstrakcja sygnałów.** Prompt (`prompts/extract_signals.md`), klient LLM z retry
  (`LLMClient` – Anthropic, `DeepSeekClient` – OpenAI-compatible), Message Batches API (Anthropic,
  próg 50 artykułów), walidacja pydantic sygnałów, kontrola kosztów dziennych. Model produkcyjny:
  **DeepSeek V4-Pro**, decyzja i metodologia niżej.
- [ ] KM3: agregacja, synteza, walidator, render Markdown, `plx run-daily`, GitHub Actions.
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
- Bez źródeł objętych sankcjami UE (RT, Sputnik). Taksonomii tematów nie zmieniamy automatycznie.

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

## Znane ograniczenia
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
