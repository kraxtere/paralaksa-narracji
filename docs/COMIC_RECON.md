# Komiks Paralaksy: rekonesans danych (2026-09-30)

Rekonesans przed implementacją. Nic w `src/`, `config/`, workflow ani progach nie zmieniono.
Dane: `data/prod.db` (snapshot z Release po daily 29.09, otwarty tylko do odczytu, `mode=ro`), raporty `reports/2026-09-24…29.json`.
Skrypty ad hoc: `data/comic_recon.py` (liczby, wynik `data/comic/recon.json`), `data/comic_scenario.py` (krok 3).
Pakiety dnia liczone tą samą funkcją co daily (`build_data_package`, `compute_daily_metrics(save=False)`).

## Wnioski w skrócie

- **Materiał jest, ale prawie zawsze z niską pewnością.** W 3 z 6 dni (26–28.09) raport nie ma żadnej pozycji powyżej „niski”.
  Komiks musi uczciwie nosić „pewność: niska” na większości kadrów albo ukazywać się tylko w dni z materiałem ≥ „średni”.
- **Autoobraz to najpewniejszy stały materiał:** 7 krajów spełnia próg sygnałów codziennie. Najwyższe JS zawsze ma CN (0,25–0,42).
  Raport nie zawsze go jednak wybiera: 29.09 pominął CN (JS 0,41) na rzecz UK i IL.
- **„Kłótnia ze sobą” (założenie 4) prawie nie występuje w danych.** Z 164 par kraj×temat z ≥ 2 redakcjami tylko 2 mają przeciwne kierunki,
  oba to artefakty różnych aktorów. Na poziomie kraj×temat×aktor: 0. Stance jest za płaski (w większości „neutralny”, znane ograniczenie).
- **Założenie 5 jest nieaktualne:** US ma 4 aktywne źródła (pbs, fox, npr, propublica) i jest najczęstszym aktorem (1749 sygnałów).
  Bez źródeł są m.in. RU i IR; to one są naturalnymi krajami-tematami.
- **Trendy najwcześniej od 2026-10-08,** pełna 28-dniowa linia bazowa od 2026-10-22, pod warunkiem braku dziur w przebiegach.
- **Próbny scenariusz (29.09) jest dość ostry, ale walidacja formalna nie wystarcza:** przeszedł z 0 błędami,
  a przy czytaniu ma dopisaną przyczynowość, język trendu i uogólnienie „nasze media”. Potrzebny jest drugi, semantyczny sprawdzacz.

## Krok 1: rekonesans danych

### a) Materiał na kadry per dzień

„Pakiet” to dane wejściowe syntezy (liczone), „raport” to zwalidowany wynik syntezy (to, co komiks może renderować).

| dzień | sygnały | zbieżność: kandydaci / słabe (pakiet) | rozbieżności pakietu: ≥ 2 źródła po obu stronach | autoobraz w pakiecie (najwyższe JS) | raport: wzorce / rozbieżności / autoobraz / skrót / słabe / nieobecne w PL | pozycje raportu ≥ „średni” |
|---|---|---|---|---|---|---|
| 24.09 | 934 | 0 / 4 | 0 z 8 | 7 (CN 0,25; IL 0,17) | 0 / 0 / 0 / 3 / 4 / 2 | 2 (skrót) |
| 25.09 | 2043 | 1 / 5 | 0 z 8 | 10 (BR 0,35*; CN 0,29) | 1 / 2 / 2 / 1 / 3 / 2 | 3 (wzorzec „wysoki”, 2 rozbieżności) |
| 26.09 | 1155 | 0 / 9 | 0 z 8 | 10 (CN 0,42; TR 0,24*) | 0 / 1 / 2 / 2 / 3 / 3 | 0 |
| 27.09 | 1127 | 0 / 8 | 0 z 8 | 7 (CN 0,28; UK 0,13) | 0 / 2 / 4 / 2 / 3 / 1 | 0 |
| 28.09 | 1432 | 1 / 5 | 1 z 8 | 7 (CN 0,34; UK 0,17) | 0 / 2 / 1 / 2 / 3 / 3 | 0 |
| 29.09 | 1561 | 1 / 4 | 0 z 8 | 9 (BR 0,46*; CN 0,41) | 1 / 2 / 2 / 1 / 3 / 2 | 5 (wzorzec, 2 rozbieżności, autoobraz UK, skrót) |

\* BR i TR na bardzo małych próbach (7/4, 11/3, 5/4 sygnałów własnych/zewnętrznych): wysoki JS z szumu, nie na kadr.

- **Zbieżność:** na pełny wzorzec (≥ 3 kraje, ≥ 2 źródła na kraj) wystarcza danych 3 z 6 dni po 1 kandydacie.
  Raport zrobił z tego wzorzec 2 razy (25 i 29.09), oba „wysoki”.
- **Rozbieżności:** pakiet zawsze ma 8 (limit), ale najsilniejsza para krajów w temacie prawie nigdy nie ma 2 niezależnych źródeł po obu stronach.
  Raport buduje 0–2 rozbieżności dziennie; „średni” tylko 25 i 29.09.
- **Autoobraz:** CN, IL, DE, UK, UA, PL i US mają ≥ 3 sygnały własne i ≥ 3 zewnętrzne każdego dnia. Raport wybrał autoobraz 11 razy w 6 dni
  (PL 3, IL 2, CN 2, UK 2, PS 1, US 1), 10 razy z pewnością „niski”.
- **Słabe sygnały** są codziennie (3–4). Nadają się na kadr narratora, nie na dialog, bo z definicji są poniżej progu.
- Jeden dobry kadr dziennie jest prawie zawsze. Cztery do sześciu kadrów z pewnością ≥ „średni” zdarzają się mniej więcej co drugi dzień.

### b) Spójność głosu kraju („jeden głos” czy „kłótnia ze sobą”)

Pomiar na segmentach kraj×temat, w których ≥ 2 niezależne grupy wydawców mają po ≥ 3 sygnały.
Grupa wydawcy jak w `independence_count`: globaltimes liczy się jako `peoples_daily`, dailysabah jako `turkuvaz`, hurriyet jako `demiroren`.
Kierunek redakcji to ta sama reguła co w pakiecie: udział nieneutralnych ≥ 0,3, potem przewaga negatywny/pozytywny.

| wynik (6 dni) | kraj×temat (164) | kraj×temat×aktor (80) |
|---|---|---|
| jeden głos (wszystkie redakcje w tym samym kierunku, JS < 0,15) | 99, **z czego 94 to „wszyscy neutralni”** | 47 |
| rozjazd: jedna redakcja z kierunkiem, druga neutralna (JS ≥ 0,3) | 21 | 10 |
| nierozstrzygnięte | 42 | 23 |
| kłótnia (przeciwne kierunki) | 2 | **0** |

- Obie „kłótnie” to CN i sojusze (27 i 29.09): Global Times krytycznie o sojuszach USA, CGTN pozytywnie o partnerstwach Chin.
  Po rozbiciu na aktora znikają, bo to różne podmioty, a nie spór redakcji.
- Przy ≥ 5 sygnałach na redakcję zostaje 57 segmentów i 0 kłótni. Przy 3 sygnałach JS przyjmuje kilka powtarzalnych wartości
  (0,138; 0,191; 0,311): to szum małych liczb.
- **Źródła tylko z leadem:** 48 z 164 segmentów zależy od redakcji z > 50% sygnałów z samego leadu. Chodzi o rp, spiegel, haaretz,
  israelhayom i scmp. IL ma 35–68% sygnałów tylko z leadu, HK 35–54%, QA 100%.
  „Rozjazdy” PL (rp neutralny, onet negatywny) i IL (haaretz vs jpost) opierają się właśnie na redakcjach z leadem, czyli na płytszym materiale.
- **Kraje z jednym wydawcą:** QA ma tylko aljazeera. PS ma w praktyce jedno źródło (alquds_ps dostaje 403 z Actions), IN też
  (indianexpress ma błędy kanału). Takie kraje zawsze mówią jednym głosem, ale z pewnością „niski” i z podpisem jednej redakcji.

**Proponowana miara i próg:**
- **Segment:** kraj × temat × `subject_actor`. Bez aktora wychodzą fałszywe kłótnie.
- **Kto się liczy:** każda niezależna grupa wydawcy z ≥ 5 sygnałami w segmencie. Redakcja z > 50% sygnałów z samego leadu nie może być stroną kłótni.
- **„Kłótnia”:** dwie redakcje mają przeciwne zgrubne kierunki (negatywny i pozytywny) oraz JS ich rozkładów stance ≥ 0,3.
- **Wszystko inne:** jeden głos. Podpis pokazuje tylko redakcje, których sygnały stoją za dymkiem.
  „Rozjazdu z neutralnym” nie rysujemy jako kłótni, bo neutralność to brak nacechowania, nie przeciwne zdanie.

Oczekiwana częstość przy obecnej ekstrakcji to około 0 na tydzień. Rekomendacja: w pierwszej iteracji bez dwóch głów.
Wrócić do tego po kalibracji stance albo grupowaniu ram (znane ograniczenie w `CLAUDE.md`).

### c) Aktorzy i obsada

Najczęstsze `subject_actor` (24–29.09, sygnały z okna publikacji):

| aktor | US | CN | IL | RU | PS | UA | IR | DE | UK | PL | FR | UE | ONZ | BR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sygnały | 1749 | 1030 | 586 | 514 | 476 | 425 | 334 | 272 | 246 | 228 | 141 | 131 | 118 | 79 |

Aktywne źródła według kraju: US 4; CN, HK, IL po 3; PL, UA, DE, UK, IN, TR, PS, BR po 2; QA 1.
W raportach kraje występują tak: rozbieżności CN 4, TR/DE/UA/HK/PL po 2; autoobraz PL 3, IL/CN/UK po 2.

**Proponowana obsada startowa:**
- **Mówiący (6):**
  - **PL:** kraj odbiorcy, 2 źródła; rp tylko z leadu.
  - **UA:** 2 źródła z pełnym tekstem.
  - **CN:** 3 źródła, najsilniejszy autoobraz każdego dnia.
  - **US:** 4 źródła, najczęstszy temat innych.
  - **IL:** 3 źródła, częsty aktor; uwaga na udział samego leadu.
  - **szósty, rotacyjnie:** UK albo TR. UK ma autoobraz codziennie, TR 29.09 była główną parą dla PL.
- **Kraje-tematy (bez dymka):**
  - **RU i IR:** części aktorzy bez źródeł.
  - **UE, NATO, ONZ:** jako rekwizyty lub instytucje.
- **Mówią tylko, gdy materiał ich dotyczy:** DE, HK, BR, IN, PS, QA. Poza stałą obsadą.
- **HK jako osobna postać obok CN** jest politycznie delikatne (patrz pytania).

### d) Linia bazowa

- **Dni z metrykami:** `daily_metrics` ma 7 dni (23–29.09), bez dziur. Przebieg 25.09 skończył się błędem po 53 min, ale metryki i raport są.
  28.09 był ręczny, spóźniony cron sam się pominął.
- **23.09 nie wchodzi do historii:** `_history` pomija pierwszy dzień pobrania. Historia zaczyna się 24.09 (HK, IN, PS, TR: 25.09).
- **Trendy:** `min_history_days_for_trends = 14`, więc pierwsze trendy są możliwe od **2026-10-08** (HK, IN, PS, TR od 2026-10-09).
  Pełna linia bazowa 28 dni od 2026-10-22. Każdy pominięty dzień przebiegu przesuwa te daty.

## Krok 2: propozycja

### Schemat scenariusza (JSON)

```json
{
  "data": "2026-09-29", "tytul": "…", "format": ["1080x1920", "1080x1350"],
  "kadry": [{
    "nr": 1,
    "typ": "autoobraz | obraz_z_zewnatrz | rozbieznosc | zbieznosc | narrator",
    "material": "M3",                 // pozycja raportu: sekcja + indeks, nadane przez kod
    "scena": "opis dla rysownika / wybór szablonu",
    "narrator": "≤ 140 znaków albo pusty",
    "dymki": [{
      "kraj": "PL",                   // tylko kraj z aktywnymi źródłami i będący stroną materiału
      "tekst": "≤ 110 znaków",
      "podpis": "wg: onet, rp",        // KOD: redakcje z dowodów tej strony
      "article_ids": [3849, 3866]      // KOD: z dowodów tej strony
    }],
    "tematy": ["RU"],                  // kraje/instytucje bez głosu, jako rekwizyt
    "article_ids": [3849, 3866],       // KOD: suma dymków albo całego materiału
    "pewnosc": "niski | średni | wysoki"  // KOD: kopiowana z pozycji raportu, nigdy podnoszona
  }]
}
```

Zasada, która robi najwięcej: **model wybiera materiał i pisze tekst; odnośniki, pewność, podpis i strony kopiuje kod z raportu.**
Model nie może więc przypisać przekazu złej redakcji ani podnieść pewności, a raport jest już zwalidowany.

### Walidacja

**Użyć wprost z `report/validate.py`:**
- `long_quotes` / `shorten_quotes` / `MAX_QUOTE_WORDS`: cytaty maks. 15 słów.
- Reguły tekstowe z `language_errors`:
  - „media/mediów” bez „analizowanych”;
  - kraj z jednym źródłem nazwany „mediami kraju”;
  - „dziś”;
  - trend bez linii bazowej;
  - JS jako podobieństwo ram.
  Dziś te reguły działają na obiekcie `ReportOutput`, więc przy implementacji trzeba wydzielić je do funkcji na pojedynczym tekście.
  Zmiana w `src/`, poza tym rekonesansem.
- Logika `attribution_errors`: redakcja wymieniona w dymku musi być w podpisie tego dymku.

**Dodać:**
- **Mówca:** kraj z aktywnymi źródłami i stroną materiału. Dla autoobrazu strona własna = `kraj`, zewnętrzna = kraje dowodów ≠ `kraj`.
- **Długość:** limit znaków dymku i narratora; 4–6 kadrów.
- **Cytat:** każdy cytat „…” musi być dosłownym fragmentem tekstu materiału. Zapobiega zmyślonym cytatom.
- **Słownik trendu dla dialogu:** oprócz raportowego też „coraz (bardziej|częściej|…)”, „rosną/narasta”, „znowu”, „jak zwykle”.
  W próbie przeszły „coraz bardziej sami” i „presja rośnie”.
- **Konwencja pierwszej osoby:** „u nas”, „nasze media” to głos kraju, nie „analizowanych źródeł”.
  Albo zakazać, albo wymusić podpis przy każdym dymku (patrz pytania).
- **Sprawdzacz semantyczny (Haiku), wzorowany na historiach TV:**
  - pytania kontrolne na kadr: czy dymek dodaje przyczynę, skutek, ocenę albo fakt spoza materiału? Czy uogólnia?
  - odrzucenie decyduje kod.
  - w próbie przeszło „Rosja przegrywa… **i dlatego** sieje sabotaż”, choć materiał podaje dwie osobne ramy bez związku przyczynowego.
- **Kadr z pewnością „niski”:** znacznik pewności widoczny w grafice (ikona albo pasek), nie tylko w metadanych.

### Punkt wpięcia

- **Polecenie:** `plx comic --date D [--render] [--format 1080x1920|1080x1350]`, lokalnie, jak `plx site`. Na razie nie w daily.
  Czyta `reports/D.json`, nie przelicza pakietu.
- **Wyjście:** proponuję `data/comics/D.json` i `data/comics/D/*.png`, **nie `reports/comics/`**. Repozytorium jest publiczne,
  a `reports/` commituje daily, więc PNG w `reports/comics/` byłyby de facto publikacją (patrz pytania).
- **Kod:** `src/paralaksa/comic/`:
  - `scenario.py`: materiały, prompt, walidacja;
  - `render.py`: szablony;
  - `assets/`: SVG postaci i czcionka.

### Render SVG → PNG (Windows i ubuntu)

**Rekomendacja: HTML + SVG w bezgłowym Chromium, tą samą ścieżką co `plx board`** (`board/render.py`, 1080×1920 przez Chrome/Edge).
- **Zależności:** Chrome/Edge jest na Windowsie, a Chrome na obrazie `ubuntu-latest` w Actions. Bez nowych bibliotek natywnych.
  Kod wyszukiwania przeglądarki już jest i działa.
- **Tekst:** łamanie tekstu w dymkach to w SVG najtrudniejsza część, bo SVG nie zawija wierszy.
  HTML/CSS robi to sam, z dzieleniem wyrazów (`hyphens: auto`, `lang="pl"`) i dopasowaniem rozmiaru.
- **Postacie:** jako SVG wstawione w HTML, np. kolory i rekwizyty zmieniane klasą CSS.
- **Czcionka:** jedna czcionka OFL z polskimi znakami (np. Noto Sans albo komiksowa typu Bangers z pełnym Latin Extended),
  osadzona jako woff2, żeby render był identyczny na obu systemach.

**Odrzucone:**
- **CairoSVG:** na Windowsie wymaga ręcznej instalacji biblioteki cairo.
- **resvg (`resvg-py`):** dobry, ma wheele na Windows i Linux, ale wymaga samodzielnego łamania tekstu i dopasowania czcionki.
  Rozsądny zapas, gdyby Chromium zawiodło.
- **Pillow (rysowanie od zera):** za dużo pracy przy dymkach.

### Koszt dzienny

| krok | model | koszt |
|---|---|---|
| scenariusz (~4 tys. tokenów wejścia, ~2 tys. wyjścia) | Sonnet 5 | ok. 0,05 $ (zmierzone: 0,051 $) |
| sprawdzacz semantyczny (4–6 kadrów) | Haiku 4.5 | ok. 0,005–0,01 $ (szacunek) |
| render | — | 0 |
| **razem** | | **ok. 0,06 $ na dzień, ok. 1,8 $ na miesiąc** |

DeepSeek Pro zamiast Sonneta byłby około 10× tańszy, ale nie testowałem tu jakości humoru ani wierności.

## Krok 3: próbny scenariusz (29.09)

Pliki: `data/comic/scenariusz-2026-09-29.md` (do czytania), `.json` (z materiałami i surową odpowiedzią), `.raw.txt`.

**Koszt:** 2 wywołania Sonnet 5. Pierwsze nie dało się sparsować: znany problem „…" z prostym cudzysłowem zamykającym;
dodałem naprawę z `tv_stories._json`. Drugie kosztowało 0,051 $. Pierwszego skrypt nie zmierzył,
przy tym samym promptcie to ok. 0,05 $, więc razem **ok. 0,10 $, na granicy limitu.**

**Scenariusz, 6 kadrów:**
1. wstęp narratora;
2. UK pije herbatę, a US z megafonem („Możliwy spisek przeciwko bazie USA”);
3. IL (haaretz) i TR (dailysabah);
4. PL i TR o wojnie;
5. zbieżność PL/TR/US o zagrożeniach hybrydowych („wysoki”);
6. PL 2,6% i TR 50% udziału Bliskiego Wschodu.

**Ocena:**
- **Ostrość jest umiarkowana.** Najlepsze są kadry, w których materiał ma konkretny kontrast:
  - UK/US: „bez paniki” vs „rząd za miękki”;
  - PL/TR: 2,6% vs 50%.
  Kadry z autoobrazu IL i „zbieżności” są rozmyte, bo materiał jest rozmyty.
- **Walidacja formalna dała 0 błędów, a przy czytaniu wychodzą 4 problemy:**
  1. dopisana przyczynowość („i dlatego sieje sabotaż”, kadr 4);
  2. język trendu („coraz bardziej sami”, kadr 3; „presja Rosji rosną”, kadr 5; błąd gramatyczny też);
  3. uogólnienie „nasze media” dla jednej redakcji z samym leadem (haaretz, kadr 3);
  4. zła etykieta typu kadru: autoobraz oznaczony jako „rozbieżność” (kadr 3).
  Drobniejsze: kadr 1 bez treści dostał odnośniki M1; kadr 4 opiera się na skrócie zamiast na odpowiadającej mu rozbieżności.
- **Najmocniejszy materiał dnia nie trafił do komiksu:** autoobraz CN (JS 0,41) był w pakiecie, ale raport go nie wybrał.
  Komiks renderujący tylko raport dziedziczy wybór syntezy.

## Telewizja jako materiał komiksu (dopisane na prośbę właściciela)

Właściciel chce mocno rozważyć telewizję jako główne źródło komiksu. Nie chodzi wyłącznie o sprzeczności.
Chodzi o zwykły codzienny przegląd „co mówi dziś świat”, z perspektywy międzynarodowej, także w dzień, w którym nic nadzwyczajnego się nie dzieje.
Poniżej kontekst dla agenta, który nie zna tej części repo.

### Skąd są dane

- **Źródło:** GDELT „Today's Media Trends”. Raport PDF na kanał i dzień, publikowany dzień później (D+1).
  Każdy raport to **streszczenie całego dnia wydań kanału napisane przez model Gemini** na podstawie transkrypcji z TV News Archive
  (Internet Archive). To interpretacja modelu, nie przekaz stacji słowo w słowo.
  Transkrypcji nie pobieramy automatycznie: są za podpisanym ciasteczkiem, w Internet Archive prywatne.
  Ręczna weryfikacja jest możliwa w Visual Explorer.
- **17 kanałów w 6 blokach** (`gdelt/tv.py: CHANNELS`, `gdelt/tv_views.py: BLOCS`):
  - Polska i Ukraina: TVP Info, Espreso;
  - **Rosja i Białoruś: Rossija 1, Rossija 24, Pierwyj kanał, NTV, Belarus 24**;
  - po rosyjsku spoza Rosji: Current Time (RFE/RL);
  - Europa: LRT (LT), DR1 (DK), M1 (HU), BBC News, France 24;
  - Bliski Wschód i Turcja: Kan 11 (IL), **Press TV (IR)**, TRT World;
  - Chiny: CCTV-13.
- **To rozwiązuje problem krajów bez głosu:** w prasie RU i IR nie mają źródeł, więc w komiksie z raportu mogą być tylko tematem.
  W telewizji mają własne stacje i mogą mówić. Podpis byłby wtedy np. „wg streszczenia GDELT: Rossija 1, NTV”.
- **Pliki** (lokalnie, poza gitem), `data/gdelt/tv/<dzień>/`:
  - `<KOD>.json`: tekst raportu (ok. 60 tys. znaków) i lista audycji;
  - `<KOD>.pl.json`: tłumaczenie na polski zdanie po zdaniu;
  - `<KOD>.claims.json`: **do 25 tez o konkretnych zdarzeniach na kanał, po polsku, z numerami zdań źródłowych**.
    Przykład (Rossija 1, 28.09): „Rosyjskie siły miały zaciskać pierścień wokół Dobropillyi…”.
    Tezy są wypisane z pominięciem sekcji spekulacyjnych Gemini (prognozy, ryzyka, „red team”);
  - `historie.json`: „Historie dnia” (0–5 dziennie), czyli różne wersje tego samego zdarzenia w stacjach, zweryfikowane.
- **Obecny widok:** zakładka Telewizja na stronie wewnętrznej (`telewizja.html`, `site/assets/tv.js`).
  Kod: `gdelt/tv.py`, `tv_views.py`, `tv_pl.py`, `tv_stories.py`. Budowane tylko przy `plx site`, nigdy w daily.
- **Koszt dziś:** tłumaczenie ok. 0,12–0,15 $ na dzień, historie TV ok. 0,07–0,11 $ na dzień.

### Co to daje komiksowi

- **Gotowa forma „per stacja”:** jedno zdanie na kanał o tym samym zdarzeniu albo o głównym temacie dnia każdej stacji.
  Da się to zrobić bez szukania sprzeczności: „Dobropole: co powiedziała każda telewizja” albo „Czym żyły dziś telewizje świata”.
- **Tezy już istnieją i mają zdania źródłowe,** więc kadr ma odnośnik (kanał + numer zdania raportu + link do PDF).
  Pełni rolę article_ids z prasy.
- **Postacie:** kraje, jak w decyzji właściciela, z mikrofonem albo telewizorem jako rekwizytem.
  RU ma cztery stacje, więc „jeden głos” lub „chór” rosyjskich stacji jest naturalny.
  Current Time to rosyjskojęzyczne RFE/RL, nie Rosja: osobna postać albo podpis.

### Zastrzeżenia

- **Pośrednik:** to streszczenia modelu Gemini, a nie słowa z anteny, więc łańcuch jest dłuższy niż w prasie.
  Każdy kadr musi mówić „wg streszczenia GDELT”, a przed publikacją fragment trzeba sprawdzić w transkrypcji.
- **Prawa:** warunki użycia raportów GDELT w publikacji (TikTok/Instagram) nie są sprawdzone.
- **Brak odpowiednika w prasie:** telewizja nie ma liczb z bazy (stance, JS, progi), więc „pewność” trzeba zdefiniować na nowo,
  np. liczba stacji, dosłowność tezy, zgodność w weryfikacji.
- **Pułapka:** historie TV czasem traktują milczenie jako wersję. Przykład: Dobropole 27 i 28.09, gdzie stacja ukraińska mówi o czymś innym.
  W przeglądzie „co mówi każda stacja” to nie problem: brak wzmianki pokazuje się wprost jako „nie mówi”.

## Pytania do właściciela

1. **Pewność:** czy publikujemy komiks także w dni, gdy wszystkie kadry mają pewność „niski” (3 z 6 ostatnich dni),
   czy tylko przy materiale ≥ „średni”?
2. **Materiał:** czy komiks może brać autoobraz wprost z pakietu (liczby są policzone kodem, np. CN codziennie), z tekstem pisanym
   przez model do kadru i tą samą walidacją? Czy wyłącznie to, co wybrała synteza?
3. **Pierwsza osoba:** czy postać może mówić „u nas” / „nasze media”? To czytelniejsze, ale sugeruje głos narodu, nie analizowanych redakcji.
   Alternatywa: trzecia osoba albo podpis „wg: …” przy każdym dymku jako warunek (tak jest w próbie).
4. **HK i CN:** czy HK jest osobną postacią obok CN? Raport 29.09 zestawia je jako rozbieżność.
5. **Gdzie leżą PNG:** repozytorium jest publiczne, a decyzja z 25.09 to brak otwartej publikacji.
   Czy komiksy mają trafiać do `data/comics/` (lokalnie) albo do prywatnej strony, dopóki nie zapadnie decyzja o publikacji na TikToku/Instagramie?
6. **Dwie głowy:** czy odkładamy je do czasu kalibracji stance? Przy obecnych danych reguła da około 0 przypadków na tydzień.
7. **Szóste miejsce w obsadzie:** UK czy TR? I czy US mówi? Dane przeczą założeniu, że US nie ma źródeł.

## Załącznik: próbny scenariusz 29.09 (wynik skryptu, bez poprawek)

### 29 września 2026: ten sam dzień, inne gazety (2026-09-29)

koszt: 0.0509 $; błędy walidacji: 0

#### Kadr 1 · narrator · M1 (autoobraz) · pewność: średni
_Scena:_ Stół redakcyjny z gazetami z całego świata rozłożonymi jak karty; nad nimi wisi kalendarz z datą 29.09.2026.

**Narrator:** Te same wydarzenia, inne kadry. Sprawdzamy, co i jak pokazały analizowane źródła – bez dodawania niczego od siebie.
<sub>artykuły: 4023, 4038, 4343, 4381</sub>

#### Kadr 2 · obraz_z_zewnatrz · M1 (autoobraz) · pewność: średni
_Scena:_ UK w mundurze strażnika bazy, spokojnie pije herbatę; obok US z megafonem i miną alarmisty.

**Narrator:** Ta sama baza wojskowa – dwa zupełnie różne tony.
- **UK:** U nas? Ochrona bazy, spór z Argentyną, trochę polityki wewnętrznej. Bez paniki.  
  <sub>wg: bbc, guardian · #4023, #4038</sub>
- **US:** „Możliwy spisek przeciwko bazie USA”! Ten rząd jest stanowczo za miękki!  
  <sub>wg: fox, pbs · #4343, #4381</sub>
<sub>artykuły: 4023, 4038, 4343, 4381</sub>

#### Kadr 3 · rozbieznosc · M2 (autoobraz) · pewność: niski
_Scena:_ IL trzyma gazetę z nagłówkiem o rządzie, wygląda na zmęczonego; TR wskazuje palcem, trzyma transparent.

**Narrator:** Oba głosy krytyczne wobec Izraela, ale nie po równo ostre (pewność: niska).
- **IL:** Nasze media piszą wprost: rząd rządzi iluzją, a my jesteśmy coraz bardziej sami.  
  <sub>wg: haaretz · #4414, #4417</sub>
- **TR:** „Izrael łamie rozejm, zabija i eskaluje przemoc” – to nie jest subtelne.  
  <sub>wg: dailysabah · #4314</sub>
<sub>artykuły: 4314, 4414, 4417</sub>

#### Kadr 4 · rozbieznosc · M6 (skrot) · pewność: średni
_Scena:_ PL trzyma zdjęcie zniszczeń z poważną miną; TR stoi przy mapie frontu, komentuje spokojnie.

**Narrator:** Ta sama wojna, inna temperatura relacji.
- **PL:** Rosja atakuje cywilów i dzieci, a potem ukrywa własne porażki na froncie.  
  <sub>wg: onet, rp · #3849, #3866</sub>
- **TR:** Rosja przegrywa na polu bitwy – i dlatego sieje sabotaż po Europie.  
  <sub>wg: dailysabah, hurriyet · #4320, #4330</sub>
<sub>artykuły: 3849, 3866, 4320, 4330</sub>

#### Kadr 5 · zbieznosc · M5 (zbieznosc) · pewność: wysoki
_Scena:_ Krąg krajów wskazuje na różne cienie zagrożeń – rosyjski niedźwiedź, irański cień, świecący układ AI.

**Narrator:** Różne słowa, ten sam niepokój: zagrożenie hybrydowe wszędzie.
- **PL:** Dezinformacja i presja Rosji rosną nad Europą.  
  <sub>wg: onet, rp · #3873, #3855, #3875</sub>
- **TR:** Sabotaż Rosji, złamane porozumienia Iranu – zagrożenie dla całej Europy.  
  <sub>wg: dailysabah, hurriyet · #4320, #4328, #4316, #4330</sub>
- **US:** Obce państwo mogło stać za spiskiem, a AI wymyka się spod kontroli.  
  <sub>wg: fox, npr, pbs · #4337, #4381, #4384, #4343</sub>
<sub>artykuły: 3855, 3873, 3875, 4316, 4320, 4328, 4330, 4337, 4343, 4381, 4384</sub>

#### Kadr 6 · rozbieznosc · M10 (nieobecne_w_pl) · pewność: niski
_Scena:_ PL czyta cienki pasek gazety z napisem „2,6%”; TR dźwiga grubą teczkę z napisem „50%”.

**Narrator:** Ten sam dzień, inna waga: dla jednych połowa gazety, dla innych jeden akapit.
- **PL:** Bliski Wschód u nas? Głównie przy okazji incydentu na Al-Aksa.  
  <sub>wg: onet · #3877</sub>
- **TR:** U nas to połowa wiadomości dnia, nie dodatek.  
  <sub>wg: dailysabah, hurriyet · #4314, #4326</sub>
<sub>artykuły: 3877, 4314, 4326</sub>
