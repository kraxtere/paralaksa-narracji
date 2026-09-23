# SPEC: Radar narracji – codzienna analiza przekazu medialnego z wielu krajów

Ten dokument jest kompletną specyfikacją dla agenta kodującego (np. Claude Code). Zadanie: zbudować od zera repozytorium git realizujące opisany system, etapami (kamienie milowe na końcu). Identyfikatory w kodzie po angielsku, raporty i komentarze dla użytkownika po polsku.

---

## 1. Cel

System codziennie zbiera publikacje z mediów kilku krajów i odpowiada na pytanie: **jaki obraz sytuacji rysuje się, gdy nałożyć na siebie przekazy z różnych krajów, i w którą stronę on się przesuwa?**

Kluczowe założenie: **nie porównujemy relacji z tego samego wydarzenia.** Porównujemy ogólne linie przekazu w tematach. Przykład docelowego wniosku:

> Temat „gotowość wojenna Polski”: media polskie akcentują gotowość i bezpieczeństwo; media ukraińskie opisują Polskę jako kraj intensywnie przygotowujący się do wojny; media brytyjskie zalecają obywatelom gromadzenie zapasów żywności. Trzy różne przekazy, wspólny kierunek: rosnące oczekiwanie konfliktu w regionie. Siła sygnału: rosnąca od 3 tygodni.

Jednostką analizy jest więc **sygnał narracyjny**: co dane medium z danego kraju mówi o danym temacie/aktorze, w jakiej ramie i z jakim nacechowaniem.

## 2. Zasada działania

```
źródła (RSS/API/GDELT)
   → pobieranie i normalizacja artykułów
   → ekstrakcja sygnałów narracyjnych (LLM, per artykuł)
   → agregacja: temat × kraj × czas
   → synteza: wzorce, zbieżności, trendy (LLM)
   → raport dzienny (Markdown) + archiwum
```

Trzy typy wzorców, których system szuka:

1. **Zbieżność kierunku**: różne kraje mówią różnymi słowami, ale wskazują w tę samą stronę (przykład powyżej).
2. **Autoobraz vs obraz zewnętrzny**: jak kraj X opisuje sam siebie w porównaniu z tym, jak opisują go media innych krajów. Rozjazd jest sygnałem.
3. **Dryf w czasie**: temat lub rama, której udział rośnie lub spada w ciągu dni i tygodni, szczególnie gdy zaczyna się pojawiać w kolejnych krajach („rozlewanie się” narracji).

Dodatkowo raport zawiera sekcję **„nieobecne w Polsce”** (tematy głośne za granicą, słabo obecne w polskich źródłach) oraz **ciekawostki**.

## 3. Zasady metodologiczne (obowiązkowe, zaimplementować w kodzie i w promptach)

Celem jest ograniczenie dopatrywania się wzorców w szumie.

- **Normalizacja do wolumenu.** Liczy się udział tematu/ramy w całości publikacji danego kraju, nie liczba bezwzględna. Każdy kraj ma różną liczbę źródeł i artykułów.
- **Linia bazowa.** Trend liczony względem średniej kroczącej (domyślnie 28 dni). Przez pierwsze 14 dni działania raport oznacza trendy jako „brak linii bazowej”.
- **Progi.** Wzorzec zbieżności wymaga sygnałów z co najmniej 3 krajów i co najmniej 2 niezależnych źródeł w każdym z nich (parametry w konfiguracji).
- **Sygnały przeciwne.** Dla każdego wzorca synteza musi wypisać sygnały, które mu przeczą. Wzorzec bez sprawdzenia kontrprzykładów jest niedopuszczalny.
- **Poziom pewności.** Każdy wniosek ma etykietę: niski / średni / wysoki, z uzasadnieniem opartym na liczbach (liczba krajów, źródeł, artykułów, zgodność ram).
- **Korelacja to nie przyczyna.** Raport opisuje, co media mówią i jak to się zmienia. Nie twierdzi, że coś „jest przygotowywane” albo „na pewno nastąpi”. Rozróżnienie: „przekaz medialny sugeruje” vs „fakt”.
- **Identyfikowalność.** Każde twierdzenie w raporcie ma odnośnik do konkretnych artykułów (id + URL). Twierdzenie bez odnośnika jest odrzucane przez walidator.
- **Typ źródła ma znaczenie.** Agencja, media publiczne, prywatne, tabloid, rządowe. Sygnał tylko z tabloidów jest oznaczany.

## 4. Stos technologiczny

- Python 3.12, zarządzanie zależnościami: `uv` (lub `pip` + `pyproject.toml`)
- Pobieranie: `feedparser`, `httpx`, ekstrakcja treści: `trafilatura`
- Baza: SQLite (przez `sqlite3` lub `SQLModel`), jeden plik `data/radar.db`
- Wykrywanie języka: `langdetect` lub metadane źródła
- Embeddingi (klasteryzacja tematów wyłaniających się): `sentence-transformers`, model wielojęzyczny (np. `paraphrase-multilingual-MiniLM-L12-v2`)
- LLM: Anthropic API (`anthropic` SDK), klucz w zmiennej `ANTHROPIC_API_KEY`
- Konfiguracja: YAML (`pydantic` do walidacji)
- CLI: `typer`
- Testy: `pytest`
- Harmonogram: GitHub Actions (cron) lub lokalny cron; oba warianty opisane w README

## 5. Struktura repozytorium

```
radar-narracji/
├── README.md
├── SPEC.md                    # ten plik
├── pyproject.toml
├── .env.example               # ANTHROPIC_API_KEY=
├── .gitignore                 # data/, .env, reports/ (opcjonalnie)
├── config/
│   ├── settings.yaml          # progi, modele, okna czasowe
│   ├── sources.yaml           # lista źródeł
│   └── themes.yaml            # taksonomia tematów startowych
├── prompts/
│   ├── extract_signals.md
│   ├── synthesize_report.md
│   └── curiosities.md
├── src/radar/
│   ├── __init__.py
│   ├── cli.py                 # radar ingest | extract | aggregate | report | run-daily
│   ├── config.py
│   ├── db.py                  # schemat i dostęp
│   ├── ingest/
│   │   ├── rss.py
│   │   ├── gdelt.py           # kamień milowy 4
│   │   └── fulltext.py
│   ├── extract/
│   │   ├── llm_client.py      # wrapper: retry, rate limit, batch, liczenie kosztów
│   │   └── signals.py
│   ├── aggregate/
│   │   ├── metrics.py         # udziały, trendy, autoobraz vs obraz zewn.
│   │   └── emergent.py        # klasteryzacja nowych tematów
│   ├── synthesize/
│   │   ├── report.py
│   │   └── validate.py        # sprawdza odnośniki i format
│   └── render/
│       └── markdown.py
├── reports/                   # YYYY-MM-DD.md
├── data/                      # radar.db (poza gitem)
├── tests/
└── .github/workflows/daily.yml
```

## 6. Konfiguracja źródeł (`config/sources.yaml`)

Format wpisu:

```yaml
- id: pap
  name: Polska Agencja Prasowa
  country: PL
  language: pl
  type: agency          # agency | public | private | tabloid | government
  feeds:
    - url: TODO         # agent: znajdź i zweryfikuj aktualny adres RSS
      section: swiat
  fulltext: true        # czy pobierać pełny tekst (sprawdź robots.txt i regulamin)
  active: true
```

Startowa lista (agent ma znaleźć i zweryfikować działające kanały RSS; źródła bez działającego RSS oznaczyć `active: false` z komentarzem):

- **PL:** PAP, Polskie Radio 24 / Polskie Radio (serwis zagraniczny), Rzeczpospolita, Gazeta Wyborcza, Onet, Wirtualna Polska
- **UA:** Ukrinform, Suspilne, Ukraińska Prawda, Kyiv Independent
- **DE:** Deutsche Welle, Tagesschau, Der Spiegel, FAZ
- **UK:** BBC News (World, Europe), The Guardian, The Telegraph, Sky News
- **Spoza bloku (dla kontrastu):** Al Jazeera English, The Hindu (sekcja world), Daily Sabah lub Hürriyet Daily News (TR), Global Times (CN, jako oficjalna rama Pekinu)
- **Dodatkowo:** Reuters, AP, AFP w takim zakresie, w jakim udostępniają publiczne RSS

Zasady: tylko publicznie dostępne treści, respektować `robots.txt`, rozsądne opóźnienia między zapytaniami (domyślnie 2 s na domenę), identyfikujący User-Agent. Pełne teksty przechowywane lokalnie wyłącznie do analizy, nigdy nie publikowane ani nie wstawiane do raportu dłuższymi fragmentami.

Źródła objęte sankcjami UE (np. RT, Sputnik) nie są dodawane.

## 7. Model danych (SQLite)

```sql
CREATE TABLE sources (
  id TEXT PRIMARY KEY, name TEXT, country TEXT, language TEXT, type TEXT
);

CREATE TABLE articles (
  id INTEGER PRIMARY KEY,
  source_id TEXT REFERENCES sources(id),
  url TEXT UNIQUE,
  url_hash TEXT UNIQUE,
  title TEXT,
  lead TEXT,
  fulltext TEXT,              -- NULL, jeśli niedostępny
  language TEXT,
  published_at TEXT,          -- ISO 8601 UTC
  fetched_at TEXT,
  extracted INTEGER DEFAULT 0 -- 0/1
);

CREATE TABLE signals (
  id INTEGER PRIMARY KEY,
  article_id INTEGER REFERENCES articles(id),
  theme_id TEXT,              -- z themes.yaml lub 'emergent:<slug>'
  subject_actor TEXT,         -- kraj/organizacja/osoba, o której mowa (kod ISO dla krajów)
  frame TEXT,                 -- krótka etykieta ramy, np. 'przygotowania do wojny'
  stance TEXT,                -- alarm | uspokojenie | neutralny | krytyka | poparcie
  intensity INTEGER,          -- 1–5
  signal_type TEXT,           -- fakt | ocena | prognoza | zalecenie_dla_obywateli | wypowiedz_polityka
  summary_pl TEXT,            -- 1–2 zdania własnymi słowami, po polsku
  evidence_span TEXT,         -- krótki fragment (max 15 słów) uzasadniający, tylko do audytu
  model TEXT,
  created_at TEXT
);

CREATE TABLE daily_metrics (
  date TEXT, theme_id TEXT, country TEXT,
  article_share REAL,         -- udział w publikacjach kraju
  n_articles INTEGER, n_sources INTEGER,
  dominant_frame TEXT, mean_intensity REAL,
  PRIMARY KEY (date, theme_id, country)
);

CREATE TABLE reports (
  date TEXT PRIMARY KEY, path TEXT, created_at TEXT, cost_usd REAL
);
```

## 8. Taksonomia tematów (`config/themes.yaml`)

Tematy startowe (każdy z id, nazwą PL, krótkim opisem dla LLM):

- `security_defense`: obronność, zbrojenia, wojsko, NATO na wschodniej flance
- `war_readiness`: gotowość wojenna, mobilizacja, ochrona ludności, schrony
- `civil_preparedness`: zalecenia dla obywateli (zapasy, ewakuacja, poradniki)
- `russia`: działania i intencje Rosji
- `ukraine_war`: przebieg wojny, negocjacje, pomoc dla Ukrainy
- `alliances`: NATO, UE, relacje transatlantyckie, spójność sojuszy
- `energy`: energia, surowce, ceny, infrastruktura krytyczna
- `economy_sanctions`: gospodarka, sankcje, handel
- `migration_borders`: migracja, granice, hybrydowe działania na granicy
- `hybrid_info`: dezinformacja, sabotaż, cyberataki
- `china_indo_pacific`: Chiny, Tajwan, Indo-Pacyfik
- `us_policy`: polityka USA wobec Europy i świata
- `middle_east`: Bliski Wschód
- `elections_politics`: wybory i polityka wewnętrzna o znaczeniu międzynarodowym

Tematy spoza listy: LLM przypisuje `emergent:<slug>`. Moduł `emergent.py` raz dziennie łączy podobne sluge przez embeddingi (próg podobieństwa w `settings.yaml`) i proponuje nowe tematy. Awans do taksonomii tylko ręcznie (komenda `radar themes promote <slug>`).

## 9. Etapy przetwarzania

### 9.1 Ingest (`radar ingest`)

- Pobierz wszystkie aktywne kanały, zapisz nowe artykuły (deduplikacja po znormalizowanym URL, dodatkowo po podobieństwie tytułu w obrębie źródła i 48 h).
- Pobierz pełny tekst tam, gdzie `fulltext: true`; w razie błędu zostaw `title + lead`.
- Filtr tematyczny wstępny: odrzuć sport, rozrywkę, pogodę, horoskopy (po sekcji kanału lub prostą klasyfikacją słów kluczowych), żeby nie płacić za ekstrakcję śmieci.
- Log: liczba artykułów na źródło; ostrzeżenie, gdy źródło nic nie zwróciło przez 2 dni.

### 9.2 Ekstrakcja sygnałów (`radar extract`)

- Dla każdego nieprzetworzonego artykułu: wywołanie LLM z promptem `prompts/extract_signals.md`, wyjście wyłącznie w JSON zgodnym ze schematem (walidacja pydantic, 1 ponowienie przy błędzie).
- Jeden artykuł może dać 0–5 sygnałów.
- Tańszy model do ekstrakcji (domyślnie `claude-haiku-4-5-20251001`), konfigurowalny.
- Użyć Message Batches API, gdy liczba artykułów > 50 (niższy koszt); w przeciwnym razie wywołania bezpośrednie z limitem współbieżności.
- Do promptu przekazywać: tytuł, lead, maks. 1500 słów tekstu, kraj i typ źródła, listę tematów.

### 9.3 Agregacja (`radar aggregate`)

Dla każdej daty oblicz i zapisz `daily_metrics`, a do raportu przygotuj pakiet danych (JSON), który zawiera:

- **Udziały tematów** per kraj, dziś i średnia 28-dniowa, różnica w punktach procentowych i jako z-score.
- **Ramy dominujące** per temat × kraj (top 3 ramy z liczbą artykułów i źródeł).
- **Autoobraz vs obraz zewnętrzny**: dla każdego kraju K, sygnały z `subject_actor = K` rozdzielone na źródła z K oraz spoza K. Porównanie rozkładu `stance` i średniej `intensity`. Miara rozjazdu: odległość Jensena–Shannona rozkładów stance.
- **Kandydaci na zbieżność kierunku**: tematy, w których ≥ 3 kraje spełniają próg źródeł i których ramy (po embeddingu etykiet ram) wskazują ten sam kierunek, np. wszystkie w grupie „alarm / przygotowania”.
- **Rozlewanie się**: tematy lub ramy, które w ostatnich 7 dniach pojawiły się w kraju, gdzie wcześniej ich nie było.
- **Nieobecne w Polsce**: tematy z wysokim udziałem w ≥ 2 krajach i udziałem w PL poniżej 25% ich średniej.

Pakiet danych zawiera przy każdej pozycji listę id artykułów, żeby synteza mogła się do nich odwoływać.

### 9.4 Synteza (`radar report`)

- LLM (mocniejszy model, domyślnie `claude-sonnet-5`, konfigurowalny) dostaje pakiet danych z 9.3 plus po 3–5 reprezentatywnych sygnałów na pozycję (summary_pl + kraj + typ źródła + URL). **Nie dostaje pełnych tekstów.**
- Prompt: `prompts/synthesize_report.md`. Wyjście: JSON z sekcjami, następnie renderowane do Markdown.
- `validate.py` sprawdza: każde twierdzenie ma ≥ 1 odnośnik do istniejącego artykułu; każdy wzorzec ma sekcję sygnałów przeciwnych i poziom pewności; brak cytatów dłuższych niż 15 słów. Przy niepowodzeniu jedno ponowienie z listą błędów, potem raport z oznaczeniem ostrzeżeń.

### 9.5 Ciekawostki

Osobne, tanie wywołanie (`prompts/curiosities.md`) na artykułach spoza głównych tematów lub z `emergent:*`: 3–5 pozycji, każda 1–2 zdania z linkiem. Kryterium: nieoczywiste, mało nagłośnione w PL, ciekawe poznawczo (nauka, technologia, historia, nietypowe decyzje państw).

### 9.6 Uruchomienie dzienne (`radar run-daily`)

`ingest → extract → aggregate → report`, zapis do `reports/YYYY-MM-DD.md`, wpis w tabeli `reports` z kosztem API. Opcjonalnie wysyłka e-mailem (SMTP z `.env`), wyłączona domyślnie.

## 10. Struktura raportu dziennego

```markdown
# Radar narracji – 2026-09-22

## W skrócie
3–5 zdań: najważniejsze wzorce dnia, każde z poziomem pewności.

## Wzorce zbieżności
### <temat>: <kierunek>
- PL (źródła: n): rama, stance – [odnośniki]
- UA (…): …
- DE / UK / spoza bloku: …
**Wspólny kierunek:** …
**Sygnały przeciwne:** …
**Pewność:** średnia – uzasadnienie liczbowe
**Trend:** rośnie od N dni / nowy / stabilny / brak linii bazowej

## Autoobraz vs obraz zewnętrzny
Tabela: kraj | jak opisuje siebie | jak opisują go inni | rozjazd (JS) | komentarz

## Co się przesuwa
Tematy i ramy z największą zmianą względem 28 dni; przypadki rozlewania się na nowe kraje.

## Nieobecne w Polsce
Tematy głośne gdzie indziej, słabo obecne w PL.

## Ciekawostki
3–5 pozycji.

## Metadane
Liczba źródeł / artykułów / sygnałów per kraj, źródła nieaktywne, koszt API, wersje modeli i promptów.
```

## 11. Prompty (treść startowa, pliki w `prompts/`)

### 11.1 `extract_signals.md`

```
Jesteś analitykiem mediów. Otrzymujesz jeden artykuł z medium z kraju {country} (typ źródła: {source_type}).
Twoim zadaniem jest wydobyć sygnały narracyjne: co ten tekst przekazuje o konkretnych tematach i aktorach, w jakiej ramie i z jakim nacechowaniem.

Tematy (użyj id; jeśli żaden nie pasuje, użyj "emergent:<krótki-slug-po-angielsku>"):
{themes}

Zasady:
- Opisuj przekaz artykułu, nie oceniaj, czy jest prawdziwy.
- "frame" to krótka etykieta (2–5 słów, po polsku), jak artykuł ujmuje sprawę, np. "Polska gotowa i bezpieczna", "Polska zbroi się na wojnę", "obywatele powinni gromadzić zapasy".
- "subject_actor": o kim jest sygnał (kod ISO kraju, np. PL, UA, RU, albo nazwa organizacji: NATO, UE).
- "signal_type": fakt | ocena | prognoza | zalecenie_dla_obywateli | wypowiedz_polityka.
- "stance": alarm | uspokojenie | neutralny | krytyka | poparcie.
- "intensity": 1 (wzmianka) – 5 (główny, silnie nacechowany przekaz).
- "summary_pl": 1–2 zdania własnymi słowami po polsku.
- "evidence_span": maks. 15 słów z tekstu, które uzasadniają sygnał.
- Zwróć 0–5 sygnałów. Jeśli artykuł nie dotyczy geopolityki ani stosunków międzynarodowych, zwróć pustą listę.

Zwróć wyłącznie JSON:
{"signals": [{"theme_id": "...", "subject_actor": "...", "frame": "...", "stance": "...", "intensity": 3, "signal_type": "...", "summary_pl": "...", "evidence_span": "..."}]}

ARTYKUŁ
Tytuł: {title}
Lead: {lead}
Tekst: {text}
```

### 11.2 `synthesize_report.md`

```
Jesteś analitykiem porównującym przekazy medialne z różnych krajów. Otrzymujesz zagregowane dane z dnia {date}: udziały tematów, dominujące ramy, porównanie autoobrazu i obrazu zewnętrznego, zmiany względem 28 dni oraz reprezentatywne sygnały z odnośnikami.

Twoje zadanie: opisać, jaki obraz sytuacji wyłania się z nałożenia przekazów z różnych krajów i w którą stronę się przesuwa.

Szukaj szczególnie:
1. Zbieżności kierunku: różne kraje, różne słowa, ten sam kierunek.
2. Rozjazdów między tym, jak kraj opisuje siebie, a tym, jak opisują go inni.
3. Dryfu: ram i tematów, które rosną lub przenoszą się do kolejnych krajów.

Twarde zasady:
- Opisujesz przekaz medialny, nie rzeczywistość. Pisz "media X przedstawiają…", "przekaz sugeruje…", nigdy "X przygotowuje się do…" jako fakt.
- Każde twierdzenie ma listę article_ids z dostarczonych danych. Nie wymyślaj artykułów.
- Każdy wzorzec ma: sygnały przeciwne (jeśli ich nie ma w danych, napisz to wprost), poziom pewności (niski/średni/wysoki) z uzasadnieniem liczbowym.
- Nie ogłaszaj wzorca poniżej progów: {min_countries} krajów, {min_sources} źródeł na kraj. Takie przypadki możesz wymienić w sekcji "słabe sygnały".
- Jeśli brak linii bazowej (mniej niż 14 dni danych), nie formułuj trendów.
- Bez cytatów dłuższych niż 15 słów.

Zwróć wyłącznie JSON zgodny ze schematem:
{schema}

DANE:
{payload}
```

### 11.3 `curiosities.md`

```
Z poniższych sygnałów wybierz 3–5 najciekawszych poznawczo informacji, które mogły umknąć polskiemu czytelnikowi. Każda: 1–2 zdania po polsku własnymi słowami, kraj źródła, article_id. Pomijaj sensację i plotki. Zwróć JSON: {"items": [{"text": "...", "country": "..", "article_id": 0}]}
```

## 12. Ustawienia (`config/settings.yaml`, wartości domyślne)

```yaml
models:
  extract: claude-haiku-4-5-20251001
  synthesize: claude-sonnet-5
  curiosities: claude-haiku-4-5-20251001
thresholds:
  min_countries: 3
  min_sources_per_country: 2
  baseline_days: 28
  min_history_days_for_trends: 14
  absent_in_pl_ratio: 0.25
  emergent_similarity: 0.8
ingest:
  per_domain_delay_s: 2
  max_fulltext_words: 1500
budget:
  max_daily_usd: 3.0     # przerwij ekstrakcję po przekroczeniu i oznacz raport
```

## 13. Harmonogram

- `.github/workflows/daily.yml`: cron codziennie o 05:00 UTC, uruchamia `radar run-daily`, commituje raport do `reports/`. Baza SQLite jako artefakt/cache między uruchomieniami (albo alternatywnie: uruchomienie lokalne przez cron, opisane w README).
- Sekret `ANTHROPIC_API_KEY` w ustawieniach repozytorium.

## 14. Testy i kryteria akceptacji

- Testy jednostkowe: parsowanie RSS (fixtures), deduplikacja, walidacja JSON ekstrakcji, obliczenia metryk (udziały, z-score, JS divergence) na danych syntetycznych, walidator raportu (brakujące odnośniki muszą być wykrywane).
- Test end-to-end z zamockowanym LLM: z 20 artykułów testowych powstaje poprawny raport.
- Kryteria akceptacji MVP: `radar run-daily` działa jedną komendą, raport powstaje w < 15 min, koszt dzienny poniżej limitu, każde twierdzenie w raporcie ma działający link.

## 15. Kamienie milowe

1. **Szkielet i ingest:** repo, konfiguracja, baza, RSS dla ~10 źródeł (po 2 z PL, UA, DE, UK + 2 spoza bloku), CLI `ingest`, testy.
2. **Ekstrakcja:** prompt, klient LLM z retry, batch, walidacja, zapis sygnałów, licznik kosztów.
3. **Agregacja i raport:** metryki, pakiet danych, synteza, walidator, render Markdown, `run-daily`, workflow GitHub Actions.
4. **Rozszerzenia:** pełna lista źródeł, GDELT jako drugi strumień, tematy wyłaniające się (embeddingi), ciekawostki, raport tygodniowy (trendy 7/28 dni), opcjonalnie e-mail.

Po każdym kamieniu: commit, krótki wpis w `CHANGELOG.md`, aktualizacja README.

## 16. Czego nie robić

- Nie publikować pełnych tekstów ani długich fragmentów artykułów.
- Nie dodawać źródeł objętych sankcjami ani obchodzić paywalli.
- Nie formułować w raporcie prognoz jako faktów.
- Nie zmieniać taksonomii tematów automatycznie; tylko propozycje.
