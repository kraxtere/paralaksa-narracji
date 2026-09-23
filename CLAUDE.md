# CLAUDE.md

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
- [ ] KM2: ekstrakcja sygnałów (prompt, klient LLM z retry, Batches API, walidacja, koszty).
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
```
Pełny ingest z pełnymi tekstami trwa ok. 2–2,5 min (~310 artykułów przy pierwszym uruchomieniu).

## Układ kodu
- `src/paralaksa/config.py`: modele `Settings`, `Source`, `Feed`, `Theme`; `load_settings/sources/themes()`.
- `src/paralaksa/db.py`: schemat, `connect`, `init_db`, `insert_article` (INSERT OR IGNORE), `log_fetch`, `stale_sources`.
- `src/paralaksa/ingest/http.py`: `PoliteClient`: UA, cache robots.txt, 2 s na domenę (wstrzykiwalne `transport/sleep/clock`).
- `src/paralaksa/ingest/rss.py`: `parse_feed`, `ingest_sources` (pełne teksty pobierane round-robin po domenach).
- `src/paralaksa/ingest/dedup.py`: `clean_url` (zapisywany URL) vs `normalize_url` (tylko do hasha).
- `src/paralaksa/ingest/prefilter.py`: odrzut sportu, rozrywki, pogody, horoskopów.
- `src/paralaksa/ingest/fulltext.py`: trafilatura, usuwanie banerów cookies, obcięcie do 1500 słów.

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
