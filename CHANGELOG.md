# Czytanie na głos wszędzie, gdzie jest tekst — 2026-10-02

- `pasek.js`: przyciski wykrywane po strukturze, bez zmian w HTML: karty krajów (strony tematów, zestawień Spraw/Różnic/Obrazu kraju,
  „Czym żyje kraj”), karty dni na osiach krajów (data czytana słownie, „30 września”), karty zdarzeń osi czasu (tytuł + opis),
  streszczenia artykułów. „Czytaj temat” na stronach tematów i zestawień (wstęp + karty krajów po kolei).
- Bez przycisków: okładka dnia i „Dzień prasy” (same kafelki), stara wersja strony.

# Okładka dnia 2.0: styl dawnego plakatu z gazetkami, bez napisów w obrazku — 2026-10-02

- Nazwy (decyzja właściciela): winieta „Co tam w prasie piszczy” z datą w ceglanym polu, sekcje jako ceglane belki: „Tego
  dnia”, „Tonacje”, „Autoportret”; kafel „Czym żyją kraje” z podpisem „Tylko u nas: …” (też tytuł `kraje.html`).
- Gazetki „jak Wally”: rozstawione w różnych miejscach sceny w zabawnych sytuacjach (wąż strażacki, aparat, drabina),
  nigdy w głównych rolach; scen nie łagodzimy. Scena wypełnia pas do dołu (bez pustego paska pod tytuł).
- Kafelki tematów: co dzień nowa panorama ok. 3:1 ze scenami z opisów krajów tego dnia (zamiast stałego symbolu tematu),
  2 pasy na obrazek poziomy (`paski.prompt(landscape=True)`), gazetki do 4 krajów tematu.
- Oś czasu „Dzień po dniu”: kwadratowe kadry zamiast okrągłych (`pasek.js`).
- Przełącznik dni (dostępność, dla starszych osób): osobny wiersz paska na całą szerokość, duże przyciski ‹ › (54 px,
  z datą sąsiedniego dnia) i data słownie na środku (lista dni); na stronach tematów i spraw duży przycisk „Wróć do dnia”.
- Temat `alliances`: nazwa „Układy mocarstw” zamiast „Sojusze” (decyzja właściciela). Kafel krajów: „Tylko u nas: o tym,
  co nie wychodzi za granicę”. Nowy wygląd od 01.10; starsze dni zostają jak były (historia).

- Zmiana decyzji: styl E2 i ręczne sceny wyglądały generycznie. Pasy okładki (`okladka.py`) mają sceny i styl dawnego
  plakatu `powitanie.png` (komiks, gazetki z szalikami, najwyżej 4 w pasie), bez tytułów, podpisów i nazw, z `NO_TEXT` i
  spokojnym dołem pasa. Usunięte: `IMAGE_STYLE`, `SCENE_RULES`, `paski.styled_prompt`, opisy scen `okladka-sceny.json`.
  Zasada o flagach jednym zdaniem w `okladka.STYLE`. Układ HTML bez zmian. Pasy 01.10 wygenerowane ponownie (E2 w `_stare/okladka-e2/`).

# Okładka dnia 2.0 z pasów, napisy w HTML, wspólny styl obrazków — 2026-10-02

- Test stylów (A–C, D1–D5, E1/E2/E4 w `data/widok/_styl-test/`): wybrany E2, komiks malowany gwaszem z konturem. Stała
  `IMAGE_STYLE` + `SCENE_RULES` w `widok_obrazkowy.py`, `paski.styled_prompt` (styl na początku, wspólna część bez techniki,
  światła i palety). Kafelki tematów i paski krajów bez zmian (`paski.prompt`).
- `scripts/v2/okladka.py`: górny blok „Przegląd prasy” z pasów: pas na sprawę, różnicę i obraz kraju (dane jak dawny plakat:
  `widok_powitanie.poster_data`); opisy scen przez Codex (`okladka-sceny.json`, ręczna poprawka dozwolona), sceny z
  detalami miejsca i 2–6 postaciami; flagi i barwy tylko gdy jednoznacznie wynikają z danych. Wszystkie napisy w HTML: tytuł
  dnia, sekcje, „Ciąg dalszy · od DD.MM”, tytuł, liczba krajów i flagi na gradiencie u dołu pasa, kolumny krajów pod pasem,
  stopka. Strony spraw/różnic/obrazu kraju biorą pas zamiast wycinka plakatu. Testy: `tests/test_okladka.py`.
- Kolumny krajów pod pasem: pełne zdania przycięte do 4 linii, „więcej ›” rozwija (wspólny mechanizm `data-zwin` w
  `pasek.js`; link tylko na pasie, kolumny poza nim). Nagłówek kolumny zewnętrznej: „Z zewnątrz”. Scena różnicy i obrazu
  kraju nie powtarza głównego motywu żadnej sprawy z tej samej okładki (zasada w `okladka.scenes_prompt`).
- Próba na 01.10: 2 obrazki (6 pasów) + 1 ponowienie (pas „Obronność” z fałszywym sztandarem); nieopublikowane.

# Czytanie na głos na stronie 2.0 — 2026-10-02

- `pasek.js`: Web Speech API (`speechSynthesis`, pl-PL, głos „Natural/Online”, potem „Google”, potem dowolny `pl-*`; czeka na
  `voiceschanged`). Bez wsparcia albo bez polskiego głosu przyciski się nie pojawiają (dodaje je JS). Tekst dzielony na zdania
  (kolejka, obejście ucinania w Chrome), jedno czytanie naraz, stop przy `pagehide`, zmianie kraju w `kraje-nav` i zwinięciu streszczenia.
- Strona tematu: „🔊 Czytaj temat” przy podsumowaniu (podsumowanie, potem karty krajów: nazwa + opis, bez artykułów) z
  wyróżnieniem `.czyta` i przewijaniem; w trybie jednego kraju przełącza kraj sama. Głośniczek przy pigułce każdego kraju
  i przy rozwiniętym streszczeniu artykułu (tytuł + streszczenie). HTML: tylko `data-czytaj="temat|kraj"` w `widok_obrazkowy.py`.
- Wygląd po uwagach z telefonu: wypełniony przycisk z ikoną SVG i napisem („Czytaj temat”, „Czytaj”, „Stop”); przycisk tematu w
  wierszu etykiety (flex, zawija się czysto), przycisk kraju osobno nad opisem karty. Dni 23.09–01.10 przebudowane i opublikowane.

# Dymki pasków z wyboru nagłówków (także bez plakatu) — 2026-10-02

- Cofnięty warunek „dymek tylko z narysowanego plakatu”: dymek to nagłówek kraju z `plakat-TEMAT.json`, jak od początku
  (zapisywany też w kroku `paski`, więc dni bez plakatów, od 02.10, mają dymki). Przebudowa 23.09–01.10.

# Strona 2.0: nagłówki jako karty do rozwinięcia — 2026-10-02

- Wspólne `art_card`/`art_list` w `widok_obrazkowy.py` (strony tematów, „Czym żyje kraj”, osie krajów, oś czasu): etykieta
  „Artykuły (N)”, karta na nagłówek (ramka, tło, tytuł, pod nim logo i redakcja), bez kropek i wcięcia.
- `pasek.js`: strzałka w kółku (obrót w dół po rozwinięciu), streszczenie i „Przejdź do artykułu” w tej samej karcie z animacją
  wysokości; bez streszczenia ikona ↗ i zwykły link. Kolory przez zmienne `--art-*` (wariant `:root[data-theme=dark]`), znak ▸ usunięty.
- Dymek nad paskiem kraju tylko z chmurki narysowanego plakatu (`plakat-TEMAT.png`); sam `plakat-TEMAT.json` (np. 24.09
  `us_policy`) nie daje dymka. Przebudowane strony 23.09–01.10, osie krajów i oś czasu (bez obrazków). Test w `test_strona_tematu.py`.

# Strona 2.0: paski także dla dni 23–30.09 — 2026-10-02

- Dni 23–30.09 przerobione na nowy układ (okładka pasami, paski krajów na stronach tematów); `start.png` i plakaty zostają w katalogach.
- `paski.py run_all`: `PASKI_PROCESY` (domyślnie 8), starty domyślnie co 10 s (`PASKI_ODSTEP`); 429 także przy 4 procesach
  przerywa (kod 3). `strip_jobs` pomija obrazki, których paski już są (ponowne uruchomienie robi tylko brakujące).

# Wspólna pigułka kraju, wybór kraju na stronach tematów, kółko na rzędach krajów — 2026-10-02

- `widok_obrazkowy.country_pill(c, tag, attrs, big)`: jedna pigułka z flagą i nazwą (klasa `.kraj-pig`, `.duza` w nagłówkach).
  Używają jej: przyciski krajów, nagłówki sekcji krajów na „Czym żyje kraj”, nagłówki kart krajów na stronach tematów
  i kart (sprawy/różnice), oś kraju `kraje/KRAJ.html` (pigułka pod tytułem). Opisy w zwykłym tekście bez zmian.
- Strony tematów: klik w kraj nie przewija, tylko pokazuje samą wybraną kartę pod przyciskami (wariant „tylko ona”,
  jak „Czym żyje kraj”); pierwszy przycisk „Wszystkie kraje” (dodawany przez JS) przywraca całą listę. Domyślnie
  wszystkie karty; wybór w `#KRAJ` (działa też `#kraj-KRAJ`). Bez JS widać wszystko jak dotąd. Wspólny JS `COUNTRY_PICK_JS`
  (atrybut `data-wszystkie` na pudełku włącza „Wszystkie kraje”; bez niego jak dotąd domyślnie PL).
- `window.plxKolko(el)` w `pasek.js`: kółko nad rzędem przesuwa go w bok, na końcu rzędu albo gdy się mieści przewija stronę.
  Używają jej filtry osi czasu (dawny kod z 89a5f8e zastąpiony wywołaniem) i rzędy przycisków krajów.
- Przebudowane strony dni 23.09–01.10 i osie krajów (bez obrazków).

# „Czym żyje kraj”: baner i kafel pod okładką — 2026-10-02

- Wspólny baner dla wszystkich dni `data/widok/kraje/baner.webp` (ludziki-gazetki w szalikach krajów, Polska w środku,
  zarysy miast; bez tekstu): `widok_obrazkowy.py baner` generuje raz jeden obrazek Codex (2 pasy ok. 3:1, cięcie
  `paski.make`) do `kraje/_baner/wersja-1|2.webp`, `baner wybierz N` zapisuje wybraną; istniejącego nie nadpisuje.
  `plx site` kopiuje go razem z `widok/kraje/` do `v2/kraje/`.
- Pod okładką zamiast ramki z przyciskiem klikalny kafel w stylu pasów tematów (`.okl-pas`): baner, na półprzezroczystym
  pasie tytuł „Czym żyje kraj ›” i linijka „Sprawy, o których pisała prasa tylko jednego kraju”; link i `data-sekcja` bez zmian.
- `D/kraje.html`: baner na górze (zaokrąglone rogi), pod nim tytuł i podpis; przypis o AI pod przyciskami krajów.

# „Tylko tutaj” → „Czym żyje kraj”, jeden kraj naraz — 2026-10-02

- Strona dnia `D/kraje.html`: nagłówek „Czym żyje kraj · DD.MM”, nowy podpis; rząd przycisków krajów (flaga i nazwa,
  przewijany w poziomie), widać jeden kraj naraz (domyślnie Polska), wybór w `#KRAJ` (dawne `#kraj-XX` też działa); bez JS
  wszystkie kraje. Gotowych ludzików-gazetek osobno nie ma (są tylko wewnątrz plakatów i pasków), więc flagi.
- Oś kraju `kraje/KRAJ.html`: „Czym żyje Polska” / „Czym żyją Niemcy” (słownik `LIVES` w `widok_obrazkowy.py`).
- Link pod okładką i sekcja w panelu właściciela: „Czym żyje kraj” (klucz `kraje` bez zmian). Przebudowane dni 23.09–01.10 i osie.

# Strony tematów: wyróżnione podsumowanie i przyciski krajów — 2026-10-02

- `widok_obrazkowy.py theme_page`: opis zbiorczy w osobnym bloku z etykietą „Podsumowanie wszystkich krajów” (tło karty,
  zaokrąglone rogi, lewy pasek w kolorze akcentu, tekst nieco większy i półgruby); zdanie „N krajów pisało…” nad nim jako podpis.
- Pod blokiem pigułki krajów (flaga + nazwa) w kolejności kart, kotwice `#kraj-XX`, płynne przewijanie, zawijanie na telefonie.
  Kolory przez zmienne CSS (`--karta`, `--linia`, `--cegla`). Test `tests/test_strona_tematu.py`.
- 01.10 przebudowane (`strona`, bez obrazków) i opublikowane.

# Strona 2.0: okładka pasami, paski krajów na stronach tematów — 2026-10-02

- Nowy `scripts/v2/paski.py` (wspólny dla okładki, stron tematów i „Tylko tutaj”): jeden obrazek Codex 1024×1536 z N
  poziomymi pasami w ciemnych ramkach, bez żadnego tekstu; oryginał zapisany przed cięciem (`.png` + `.json` z listą
  wyników, `paski.py pokroj` tnie ponownie bez Codex); przy złej liczbie pasków jedno ponowienie, potem odrzucony.
  `run_all`: do 8 procesów co 15 s, po pierwszym 429 4 co 20 s i ponowienie; liczba na starcie, podsumowanie na końcu.
  Detekcja ramek przeniesiona z `kraje.py`, który korzysta teraz z `paski.make` (też 8/4 procesy).
- `widok_obrazkowy.py paski`: okładka dnia jako pasy tematów (najwyżej 3 na obrazek, pas ok. 2:1, `pas-TEMAT.webp`)
  i paski krajów na stronach tematów (jeden na kraj, przy > 6 krajach 2 obrazki; scena z opisu kraju, ludzik-gazetka
  w szaliku kraju w rogu; `pas-TEMAT-KRAJ.webp`). Oryginały w `data/widok/D/_paski/`.
- Okładka w HTML: nagłówek, na pasie tytuł, „N krajów” i flagi (uproszczone SVG), kolory przez zmienne CSS, link do
  strony tematu; `data-sekcja="tematy"`, powitanie i „Tylko tutaj” bez zmian. Strona tematu: pas tematu, tytuł, opis,
  karty krajów z paskiem i dymkiem HTML z nagłówkiem z `plakat-TEMAT.json` (kraj bez nagłówka: bez dymka, kraj bez
  paska: karta bez obrazka). Plakat znika z nowych stron; tryb plakatu i `start.png` zostają dla dni bez `_paski/`.
- Testy offline `tests/test_paski.py` (podział, prompt, cięcie, ponowienie i odrzucenie, 429).

# Kraje: cięcie pasków przy liniach w scenie, `pokroj`, dane wstecz — 2026-10-02

- `scripts/v2/kraje.py`: `detect_strips(png, n)`. Najpierw dotychczasowe cięcie po wszystkich ciemnych pasach
  (`runs_strips`); gdy liczba pasków różni się od N albo któryś ma < 40% średniej wysokości (linia sceny wzięta za ramkę),
  `chosen_strips`: ramka = pas 6 px…3% H, wiersze ≥ 95% ciemnych pikseli jednolitego tonu; spośród układów N−1 ramek
  z każdym paskiem ≥ 40% średniej wybór najgrubszych (remis: równiejsze paski). Okna ±15% wokół k·H/N odrzucone:
  Codex rysuje paski nierównej wysokości (np. 475/396/632 px). Test offline na sztucznym obrazku z linią w pasku.
- `kraje.py pokroj D KRAJ...`: ponowne cięcie zapisanego oryginału (`_gen-KRAJ/pasy.png` po odrzuceniu, inaczej
  `_KRAJ.png`) bez Codex. Sprawdzone na 80 oryginałach: wszystkie cięte, dotychczasowe cięcia bez zmian.
- Dane „Tylko tutaj” wstecz 23–30.09 (`kraje.py D`, `ciag D`), 79 obrazków pasków (78 od razu albo po 1 ponowieniu,
  IL 25.09 pokrojony po zmianie). Strony osi krajów i dni przebudowane, opublikowane.

# Streszczenia: 3–5 zdań, tryb `skroc` — 2026-10-02

- `scripts/v2/streszczenia.py`: nowe streszczenia 3–5 zdań (50–100 słów, walidacja 3–6), wcześniej 5–7.
- Tryb `skroc` (jednorazowy): Codex skraca istniejące streszczenia do ok. 60% bez pełnych tekstów (scala zdania);
  akceptacja 40–90% słów, 3–6 zdań, cytaty tylko dosłowne z dotychczasowego tekstu; skrócone mają `"k":1`.
- 02.10: 1180 z 1193 skróconych (2 przebiegi), 13 zostaje w starej wersji; kopia sprzed zmiany w
  `data/widok/streszczenia_kopia_0210/`. Opublikowane.

# Kraje: oś kraju w czasie — 2026-10-02

- `scripts/v2/kraje.py strona`: strona osi kraju `data/widok/kraje/KRAJ.html` ze wszystkich dni w `data/widok/kraje/*.json`,
  najnowszy u góry; sekcja na dzień z tematami (paski grafik, jeśli są i tytuły się zgadzają, opis, nagłówki z `data-a`)
  i linkiem do strony dnia. `plx site` kopiuje ją do `v2/kraje/` razem z logo i paskami dni; serwer liczy ją do sekcji „kraje”.
- `scripts/v2/kraje.py ciag D`: Codex porównuje tematy dnia z tematami tego kraju z 7 dni wstecz i oznacza ciąg dalszy
  (`ciag_od`: pierwszy dzień sprawy). Walidacja w kodzie: wskazany dzień i temat muszą istnieć. Na osi kraju etykieta
  „Ciąg dalszy · od DD.MM” z linkiem do tamtego dnia. Dla 01.10 brak wcześniejszych dni, więc bez oznaczeń.
- Strona dnia „Tylko tutaj”: przy nazwie kraju link „Cała oś kraju →”. `streszczenia.py shown_ids` skanuje też osie krajów.

# Kraje: paski scen nad tematami — 2026-10-02

- `scripts/v2/kraje.py obrazki D [KRAJ...]` (domyślnie PL): jeden pionowy obrazek Codex 1024×1536 na kraj, N poziomych
  pasków (N = liczba tematów) rozdzielonych grubą ciemną ramką, bez napisów, ludzie uproszczeni. Paski cięte po
  wykrytych ramkach (`detect_strips`; `detect_panels` z widok_obrazkowy zakłada siatkę 2 kolumn); inna liczba niż N =
  błąd, nic nie zapisane. Wynik `data/widok/kraje/D/KRAJ-n.webp` + tytuły tematów w `KRAJ.json`.
- Strona „Tylko tutaj”: pasek nad tytułem tematu na całą szerokość, zaokrąglone rogi; tylko gdy zapisane tytuły
  zgadzają się z bieżącymi. `copy_v2` kopiuje też pliki `.webp`.

# Kraje: dłuższe opisy tematów — 2026-10-02

- `scripts/v2/kraje.py`: opis tematu 2–3 zdania, 40–60 słów (co się dzieje, kto jest stroną, jak ujmują to redakcje;
  twierdzenia przypisane źródłom); walidacja 25–70 słów. Wyniki 01.10 policzone od nowa: opisy PL mają 28–34 słowa.

# Strona „Tylko tutaj” (Kraje) — 2026-10-02

- `widok_obrazkowy.py` buduje `data/widok/D/kraje.html` z `data/widok/kraje/D.json`: sekcja na kraj (Polska pierwsza, logo
  redakcji), tematy z opisem i nagłówkami jak w `article_list` (`data-a`, streszczenia po kliknięciu). Polecenia `strona` i `indeks`.
- Okładka: pasek „Tylko tutaj · Sprawy z prasy jednego kraju” pod obrazkiem okładki (okładka to jeden obraz z polami, więc link
  nie siedzi w samym obrazku). `data-sekcja="kraje"`, w panelu właściciela sekcja „Tylko tutaj” (`server.section_of`).
- 01.10: 94 nagłówki na stronie, 79 nowych streszczeń; opublikowane.

# Źródła: włączone wp i gazeta — 2026-10-02

- `wp` (Wirtualna Polska) i `gazeta` (Gazeta.pl) aktywne (decyzja właściciela); razem 34 aktywne źródła. Próba na pustej
  bazie: wp 15 artykułów / 15 pełnych tekstów, gazeta 30 / 30, bez błędów.

# Kraje: tematy „tylko w tym kraju” (dane) — 2026-10-02

- `scripts/v2/kraje.py D`: artykuły z okna dnia spoza wydarzeń wielokrajowych (Sprawy dnia i dalsze zdarzenia osi, łącznie
  z `pozostale`/`odrzucone`), per kraj Codex (model tekstowy) grupuje w 3–5 tematów krajowych (tytuł ≤ 6 słów, opis ≤ 25 słów,
  1–4 artykuły); bez poradników, lifestyle'u, sportu, pogody. Walidacja w kodzie, jedno ponowienie; tematy z ≥ 2 redakcji wyżej.
  Wynik `data/widok/kraje/D.json`. Próba 01.10: 531 artykułów z 14 krajów, 59 tematów (QA: żadnego tematu krajowego).

# Strona 2.0: znak „rozwiń” przy nagłówkach ze streszczeniem — 2026-10-02

- Linki `a[data-a]`, które mają streszczenie, dostają po wczytaniu shardów klasę `ma-str`, znak „▸” (otwarte „▾”, kolor
  przez zmienną `--str-znak`) i podpowiedź „Kliknij, aby rozwinąć streszczenie”. Linki bez streszczenia bez zmian.

# Oś czasu: przyciski dni i strzałki, kółko myszy — 2026-10-02

- Przyciski dni i strzałki nie przesuwały osi na szerokim ekranie: `scroll-padding-left` wracał jako tekst `max(...)`, więc
  przewijanie szło do 0; teraz liczone z `padding-left`. Pasek dni przewijany bez `scrollIntoView` (w Chromium przerywał płynne
  przewijanie osi). Zaznaczony dzień liczony z uwzględnieniem marginesu (wcześniej o dzień za wcześnie).
- Kółko myszy nad kartami przesuwa oś w bok o jedną kartę; na końcu osi kółko przewija stronę normalnie.
  Poza kartą (tło osi) kółko zawsze przewija stronę w dół, np. do rozwiniętych nagłówków.
- Kółko nad paskiem filtrów wątków przesuwa go w bok (na końcu paska przewija stronę).

# Koszty po przeglądzie, raport okładkowy przez Codex, oś tygodnia — 2026-10-01

Przegląd kosztów 24–30.09 (decyzja właściciela: zostawić to, czego używa wersja 2.0): ekstrakcja DeepSeek ok. 0,90 $ dziennie,
synteza Sonnet ok. 1,20 $, Sprawy dnia ok. 0,05 $, nagłówki po polsku ok. 0,06 $, telewizja ok. 0,22 $; razem ok. 2,5 $
dziennie. Codex (obrazki i teksty 2.0) z abonamentu. Pełne teksty: mediana 414 słów, limit 1500 słów ucina 3% artykułów,
więc limitu nie ruszamy.
- Daily w Actions bez syntezy (`run-daily --bez-raportu`): pobranie, ekstrakcja, metryki, status dnia. Zmiana trafia na `main`
  osobną gałęzią `daily-bez-syntezy` (Actions chodzi z `main`).
- Raport okładkowy lokalnie przez Codex (`report.form: okladka`, `codex:gpt-6.1-sol:medium`): tylko różnice i obraz kraju,
  czyli to, co bierze okładka 2.0. Test 8 modeli na 30.09 (tabela w CLAUDE.md): Codex Sol/Astra bez błędów walidacji za
  pierwszym razem i z różnicami o tych samych sprawach; Sonnet i DeepSeek bez myślenia porównywały różne sprawy. Pełny
  przebieg `plx report` przez Codex na kopii bazy: jedno wywołanie, bez ponowienia.
- Raport okładkowy, obraz kraju: każda strona z co najmniej dwóch redakcji, zewnętrzna najlepiej z dwóch krajów (Codex wybierał
  jedną redakcję po stronie). Dwa przebiegi na 30.09: oba bez błędów walidacji, oba IL z 2 + 2 redakcjami (TR i PS z zewnątrz).
  Potem lekka zachęta do dwóch obrazów kraju (dla różnych krajów, drugi tylko na tych samych warunkach): przebieg na 30.09
  dał CN i UA, oba 2 + 2 redakcje. Strona 2.0 pokazuje na razie tylko pierwszy.
- Pomiar czasu czytania od nowa (po przeglądzie Codexa): stary liczył każdy sygnał jako minutę do przodu, milkł dopiero po
  5 min bez ruchu, a ruch myszy go podtrzymywał, więc zostawiona karta dawała do ok. 6 min. Teraz pomiar trwa, gdy karta jest
  widoczna, okno ma fokus i od ostatniego kliknięcia, dotyku, przewinięcia albo klawisza minęło < 90 s. Sygnały niosą sekundy
  od poprzedniego (start, punkt kontrolny co minutę i przy zmianie miejsca, koniec z powodem: hidden, blur, idle, wyjscie)
  oraz identyfikator karty; panel liczy tylko zgłoszone sekundy, dwie karty naraz raz, krótkie wizyty w sekundach. W `/osoby`
  doszły czas według tematów (plakaty tematów 2.0) i diagnostyka (powody startu i końca, żądania od startu serwera).
  Sprawdzone w Chrome (Playwright, lokalny serwer, skrócone progi); stary format zdarzeń nie dolicza czasu.
- Telewizja wyłączona (`plx site --z-tv` przywraca). Po zmianach koszt ok. 1 $ dziennie.
- Oś wydarzeń (prototyp, `data/os_czasu.py` poza gitem): jedna ciągła oś przez wszystkie dni (najpierw był tydzień 24–30.09;
  właściciel wolał całość z przeskakiwaniem dni). Każdy dzień dopisuje Codex: 1–4 nowe zdarzenia, dalszy ciąg istniejących
  albo pominięcie, wątki do filtra; każde zdarzenie ma kadr bez napisów. Wybór dnia (lista i strzałki, przyklejona u góry),
  przesuwanie w bok, filtr wątku, nagłówki z linkami. Godzina na osi to pierwszy pokazany nagłówek w naszych źródłach, nie
  godzina zdarzenia. Na start 24 zdarzenia z 23–30.09; trzy kadry poprawione (prezydent Iranu narysowany jako duchowny,
  stereotypowo narysowani zatrzymani). Daty zdarzeń z treści artykułów i z GDELT: następny krok.
- Oś bez pomijania: limit 1–4 nowych zdarzeń dziennie wyrzucił 18 spraw (m.in. orbita Starshipa, rezygnacja Vučicia,
  strzelaniny w RPA), przez co 28.09 zniknął z osi. Teraz każda Sprawa dnia jest nowym zdarzeniem albo dalszym ciągiem
  istniejącego; pominięte dopisane (`os_czasu.py pominiete`, 42 zdarzenia). Wybór dni pokazuje każdy dzień kalendarza
  z zakresu, dzień bez zdarzeń jest wyszarzony.
- Karty osi mają 2–3 zdania opisu pod nagłówkiem (`os_czasu.py opisy`, Codex, z opisów i nagłówków wszystkich dni
  zdarzenia; ponownie, gdy zdarzenie dostanie nowy dzień). Bez dat dziennych (daty przy Sprawach to dni przeglądu, nie
  zdarzeń; pierwsza wersja je podawała), liczby ofiar przypisane źródłu.
- Strona dnia 2.0: kafelek „Dzień po dniu” pod okładką (wariant C z trzech, wybór właściciela): oś ostatnich 5 dni, po
  2 okrągłe kadry na zakładkę, link „Oś czasu ›”. Nazwa strony osi: „Oś czasu”. Kadry osi po 6 naraz.
- 01.10: Sprawy dnia prawie takie same jak 30.09 (flydubai, Pike, Irak). Sprawdzone, to nie błąd: pod sprawami 01.10 nie ma
  żadnego artykułu z 30.09, pokazane nagłówki są prawie wszystkie z 01.10, a sprawy się rozwinęły (Pike: 30.09 sąd wstrzymał
  egzekucję, 01.10 przeżyła dwie dawki).
- Ciąg dalszy (`os_czasu.py ciag D`, przed okładką): Codex sprawdza, czy Sprawa dnia 1–3 to ta sama sprawa co zdarzenie
  z wcześniejszych dni (to samo zdarzenie na osi albo wątek, ale nie sam szeroki temat), i pisze zdanie „co nowego”. Okładka
  dostaje etykietę „Ciąg dalszy · od DD.MM”, strona sprawy ramkę z tym zdaniem i linkiem na oś. 01.10: wszystkie trzy.
- Oś szerzej (decyzja właściciela): oprócz Spraw dnia dalsze zdarzenia z ≥ 2 krajów (te same dwa kroki co Sprawy dnia, ale
  Codex; `data/widok/os/dodatkowe/`), 4–8 nowych zdarzeń na dzień, mniej ważne dalsze pominięte. 01.10: 12 kandydatów,
  4 dodane (Fairford, Hegseth, naloty Pakistanu, irańska delegacja), razem 8.
- Obrazki Codex mają osobny dobowy limit (429 `usage_limit_reached`, okno 1440 min), którego `codex_limit.py` nie pokazuje:
  01.10 skończył się po ok. 25 obrazkach przy 30% okna 5 h. 8 procesów obrazków naraz działało bez problemu.
  Brakujące kadry: `os_czasu.py obrazki api` (OpenAI Images API, `gpt-image-2`, jakość medium, ok. 0,05 $ za kadr;
  01.10 cztery kadry, ok. 0,20 $, decyzja właściciela).
- Oś grupuje karty według dnia przeglądu, w którym sprawa weszła, nie według daty pierwszego nagłówka (decyzja właściciela):
  sprawy z wieczornymi nagłówkami D-1 lądowały na D-1, przez co 01.10 miał 4 karty, a 30.09 osiem. Godzina pierwszego
  nagłówka zostaje na karcie („1. nagłówek 30.09 18:49”). Teraz każdy dzień 23.09–01.10 ma 4–8 kart.
- Strona 2.0 (decyzje właściciela): kafelek „Dzień po dniu” na samej górze strony dnia, pod paskiem (był pod okładką i znikał
  poza pierwszym ekranem; próba wstawienia go między Wydarzenia dnia a resztę okładki odrzucona). Sprawy dnia nazywają się
  od 02.10 „Wydarzenia dnia” (nagłówek okładki, oś, panel); starsze okładki zostają.
- Menu osoby w pasku (litera imienia): kto jest zalogowany, powiadomienia, instalacja aplikacji, „Osoby” dla właściciela,
  „Wyloguj”. Imię i klucz powiadomień wstawia serwer (`window.plxJa`), więc strony dni się nie zmieniają.
- Instalacja jako aplikacja: na innym telefonie przeglądarka nie proponowała instalacji. Strona nie miała service workera
  (Chrome go wymaga do propozycji); teraz `/sw.js` (bez pamięci podręcznej, bez sieci krótki komunikat) i własna propozycja
  „Zainstaluj” (zdarzenie `beforeinstallprompt`), na iPhonie wskazówka „Udostępnij → Do ekranu początkowego”.
- Powiadomienia push o nowym wydaniu (Web Push, `hosting/powiadomienia.py`): włączane w menu, subskrypcje w repo aktywności
  (`powiadomienia.json`). Serwer wysyła raz na nowy dzień przy starcie po wdrożeniu (`v2/powiadomienie.json` z `plx site`:
  dzień i trzy Wydarzenia dnia); dzień zaznaczony przed wysyłką, więc restart nie powtarza; wygasłe subskrypcje (404/410)
  usuwane. Pierwsza zależność serwera spoza biblioteki standardowej: `pywebpush` (tylko do tego; bez niej i bez
  `VAPID_PRIVATE_KEY` w Renderze strona działa bez powiadomień). iPhone: tylko w zainstalowanej aplikacji (iOS 16.4+).
- Panel `/osoby`: na górze „Gdzie czytają” (wszyscy oprócz właściciela) dziś i 7 dni: części strony i strony czytane
  najdłużej; u osoby to samo zamiast 30 dni. Wizyty sumują czas według strony (np. „Oś czasu 6 min” zamiast osobnego wpisu
  dla każdego dnia osi).
- Streszczenia pod nagłówkami (02.10, decyzja właściciela: przez Codex, nie w ekstrakcji DeepSeek, bo tam +0,3–0,8 $ dziennie
  za streszczenia, których prawie nikt nie zobaczy): `scripts/v2/streszczenia.py D` streszcza tylko artykuły podlinkowane
  na stronach dnia i na osi (`data-a`; 01.10: 211 na stronach dnia, z osią ok. 530), z pełnego tekstu w lokalnej bazie
  5–7 zdań, przy samym leadzie (rp, Spiegel i inne bez pełnego tekstu) 1–2 zdania. Kontrola liczby zdań i długości cytatów,
  jedno ponowienie. Klik w nagłówek rozwija streszczenie i „Przejdź do artykułu →” (`pasek.js`, pliki `v2/streszczenia/`).
  Próba 10 artykułów: ok. 1% okna 5 h Codex, przypisania („według…”, „autor ocenia”) poprawne.

# Strona: nowe logo, pasek 2.0, czas według części strony — 2026-10-01

- Logo „Gazeta w kadrze” (E1 z trzeciej rundy propozycji z GPT, wybór właściciela): znak to gazeta wychodząca poza drugą ramę,
  czyli ta sama sprawa z dwóch miejsc; napis kapitalikami z większym P, podział kolorem PARA / LAKSA. SVG z literami jako
  krzywymi w `site/assets/logo/`, ikony aplikacji PNG wyrenderowane raz przez Chrome do `site/assets/icons/` (wcześniej
  rysowane w kodzie, bo znak był z dwóch kół). Logo w nagłówku starej wersji, favicon i ikony aplikacji.
- Wersja 2.0: wspólny pasek i stopka w jednym pliku (`site/assets/pasek.js` → `v2/pasek.js`); strony dni mają tylko
  `<div id="pasek">` i ten skrypt, więc zmiana paska nie wymaga już przebudowy stron. Pasek grubszy, logo po lewej, po prawej
  wybór dnia ze strzałkami (na stronach tematów i spraw powrót do strony dnia); „Stara wersja” w stopce. Na komputerze pasek
  wyrównany do kolumny treści. Strony 2.0 mają favicon i manifest. Przebudowa 25–30.09 tylko z pamięci podręcznej, bez Codex.
- Czas na stronie: pingi tylko wtedy, gdy ktoś w ostatnich 5 min ruszał stroną (przewijanie, dotyk, mysz, klawisz); potem
  jedno „h” i cisza, pierwszy ruch wznawia (`server.IDLE_S`). Karta zostawiona na ekranie pingowała bez końca: zawyżała czas
  czytania i nie dawała darmowemu Renderowi zasnąć. Sprawdzone w Chrome z przyspieszonym zegarem.
- Wersja 2.0 dla 23 i 24.09 (komplet od pierwszego dnia, decyzja właściciela). 24.09 ma okładkę z samymi sprawami dnia:
  raport tego dnia nie ma różnic ani autoobrazu (za mało źródeł). Plakat polityki USA z 24.09 dwa razy zablokowany przez
  moderację, strona tematu używa kafelka z siatki. Literówka na plakacie poprawiona ręcznie na pikselach (edycja przez Codex jej nie usunęła).
- Tytuł okładki dla nowych dni: „Przegląd prasy · DD.MM” zamiast „Świat w prasie” (decyzja właściciela); okładek 25–30.09
  nie poprawiamy.
- Panel `/osoby`: każda osoba to rozwijany wiersz na całą szerokość: czas w częściach strony (okładka, sprawy dnia, różnice,
  obraz kraju, tematy dnia, stara wersja w całości), oś czasu dni (wspólna skala ucięta do godzin czytania) i wizyty z listą
  stron. Na stronie dnia 2.0 okładka i siatka tematów liczą się osobno: sygnał podaje, która część (`data-sekcja`) jest na
  środku ekranu, także po przewinięciu.
- Poprawka liczenia: sygnał „h” poprzedniej strony dochodzi często po wejściu na następną i ucinał jej pierwszą minutę;
  teraz zatrzymuje tylko stronę, z której przyszedł.

# Strona: konta osób i czas na stronie — 2026-10-01

Decyzja właściciela: pokazać stronę kilku osobom i wiedzieć, kto ile na niej siedzi; wersja darmowa (bez płatnego dysku Rendera).
- Właściciel (SITE_USER/SITE_PASSWORD) dodaje osoby na `/osoby`; każda dostaje jednorazowy link `/zaproszenie/...` (7 dni)
  i sama ustawia hasło (min. 10 znaków, zapisany tylko skrót PBKDF2). Logowanie dalej przez okienko przeglądarki (Basic Auth),
  bez formularza i sesji. Przyciski: nowy link (też reset hasła), zablokuj/odblokuj.
- Czas: serwer dokleja do stron HTML sygnał co minutę, gdy karta jest widoczna (`/_ping`); wejście na stronę też się liczy.
  Sesja kończy się po 10 min ciszy. Zestawienie (kto, od–do, minuty, strony; 7 i 30 dni) jest na `/osoby`.
- Zapis: darmowy Render kasuje dysk przy uśpieniu i każdym wdrożeniu, więc osoby i aktywność trafiają do prywatnego repo
  `kraxtere/paralaksa-aktywnosc` przez API GitHuba (`hosting/konta.py`, bez `git` i `ssh`, których serwer nie potrzebuje).
  Aktywność co 3 min i przy SIGTERM (usypianie), zmiany osób od razu. Wymaga `ACTIVITY_TOKEN` w Renderze (token fine-grained
  tylko do tego repo, Contents: zapis); bez niego działa jak dotąd, tylko konto właściciela.
- Próba na prawdziwym repo (zaproszenie, hasło, logowanie, zapis i odczyt aktywności) przeszła; dane próby usunięte.

Poprawki tego samego dnia (uwagi właściciela):
- Logowanie formularzem (`/logowanie`) zamiast okienka Basic Auth: okienko nie działa w części przeglądarek wbudowanych
  (Messenger, WhatsApp) i zapomina hasło po zamknięciu przeglądarki. Podpisane ciasteczko na 90 dni, odnawiane przy wizytach,
  bez zapisu po stronie serwera (przeżywa uśpienie). Nowe hasło, blokada albo usunięcie kończą zalogowanie. Po ustawieniu hasła
  z zaproszenia urządzenie jest od razu zalogowane. Basic Auth zostaje dla skryptów. Limit 20 nieudanych prób na adres na kwadrans.
- Bez informacji o mierzeniu czasu na stronach dla osób (decyzja właściciela); opis zostaje tylko w panelu `/osoby`.
- Przycisk „Usuń”: kasuje konto (hasło, link), imię zostaje przy dawnych sesjach z dopiskiem „usunięta”, login nie wraca do obiegu.
- Co było czytane: sygnał niesie też zakładkę (`#raport`), wysyłany jest także po kliknięciu, gdy zakładka się zmieni,
  i „h” od razu po schowaniu karty albo aplikacji (koniec czasu bez czekania na minutę). W sesji lista stron z tytułami i czasem.
- Sprawdzone w Chrome (widok telefonu) na lokalnym serwerze: zaproszenie, logowanie, przekierowanie z powrotem, zakładki, „h”.
- Wersja 2.0 (obrazkowa) jest podstawowa (decyzja właściciela): `/` otwiera najnowszy dzień 2.0, stara wersja pod `/index.html`.

# Rosja w daily — 2026-09-30

Decyzja właściciela: rosyjskie źródła w codziennym przebiegu, sankcje UE nie są przeszkodą (dotąd Rosja była tylko w kartach
zdarzeń i w telewizji GDELT).
- Aktywne: `izvestia` (Izwiestia, prokremlowska, pod sankcjami UE) i `rg` (Rossijskaja Gazieta, dziennik rządowy), po rosyjsku,
  z pełnymi tekstami. Razem 32 aktywne źródła, 14 krajów.
- Nieaktywne z opisem: `tass` (robots.txt i artykuły zwracają 403 dla naszego UA), `rt_ru` (serwer zrywa połączenie z naszym UA).
  Z innym UA oba działają, ale UA nie zmieniamy (to byłoby obchodzenie blokady). RIA nie rozwiązuje się w DNS w PL, Kommersant
  bez odpowiedzi, RBC 401 na artykułach, Interfax pusty kanał.
- Próba ekstrakcji (DeepSeek V4-Pro) na 5 + 5 artykułach: 12 sygnałów, trafne tematy i stanowiska (np. Zacharowa o języku
  rosyjskim na Ukrainie jako krytyka), bez ponowień, 0,009 $. RG ma dużo spraw krajowych i poradników, które nie dają sygnałów.
- Niewiadoma: z GitHub Actions (IP poza Rosją) źródła mogą odmawiać; błąd jednego źródła to tylko ostrzeżenie informacyjne.

# Telewizja: historie dnia — 2026-09-27

Zamiast archiwum 17 raportów: do 3 zdarzeń dziennie, w których streszczenia stacji podają różne wersje. Kierunek z burzy mózgów
GPT (zlecenie `docs/TV_BURZA_BRIEF.md`, wynik lokalnie w `data/gdelt/burza/`): jeden ekran, konkretna różnica, dowody pod spodem.

- `gdelt/tv_stories.py`, `plx gdelt tv-historie [--dni N] [--do D]`, na stronie pierwsza zakładka Telewizji „Historie dnia”.
  Trzy kroki: (1) `deepseek-flash` wypisuje z każdego raportu do 25 tez o konkretnych zdarzeniach z numerami zdań; sekcje, w których
  Gemini przewiduje albo dopisuje hipotezy (HYPOTHESES, STRATEGIC FORESIGHT, RISK ASSESSMENT, BLIND SPOTS, CONTRARIAN/„red team”,
  INFORMATION WARFARE), są odcinane wcześniej, bez modelu; (2) `deepseek-v4-pro` łączy tezy stacji w zdarzenia i proponuje do 8 różnic
  (liczba, status, tożsamość, przebieg, przyczyna, rola, ocena) z wersjami; (3) `claude-haiku-4-5` sprawdza każdą na oryginalnych
  zdaniach (EN i PL) przez pytania kontrolne, a o odrzuceniu decyduje kod: zaokrąglenie, dokładniejsza wersja, pisownia, akcent,
  inna miara, to samo innymi słowami, stacja bez wersji wprost („nie wspomina”, „co sugeruje”). Dodatkowo reguły w kodzie: liczby
  jako przedziały z precyzji zapisu („ponad 108” zgodne ze 110, 59,8 i 59,2 nie), nazwy prawie tak samo zapisane to pisownia.
  Słowa różnicujące muszą być dosłownie w zdaniu (podświetlane na stronie).
- Karta: rodzaj różnicy, jedno zdanie, pasek 17 stacji według regionów (kolor wersji / wspomina / nie znaleziono w streszczeniu /
  brak raportu), wersje obok siebie ze zdaniem każdej stacji i linkiem do raportu, zastrzeżenie modelu. Etykieta: porównanie streszczeń
  GDELT, nie słów z anteny, do sprawdzenia w wydaniu.
- Wybór weryfikatora: ci sami kandydaci 19, 22, 25.09 sprawdzeni trzema modelami. DeepSeek Pro (0,01 $ dziennie) przepuszczał wnioski
  i różne zakresy; Haiku (0,04) i Sonnet 5 (0,11) odrzucały podobnie. Flash w roli sędziego uznawał „do stycznia” i „do 10 stycznia”
  za sprzeczność; weryfikator z myśleniem był 4× droższy, 4 min na dzień i nadal przepuszczał transliterację.
- Koszt ok. 0,07 $ dziennie (tezy 0,02, zdarzenia 0,01, weryfikacja 0,04), tylko przy `plx site`. Zapis na każdym kroku
  (`<KOD>.claims.json`, `historie-kandydaci.json`, `historie-weryfikacja.json` z surowymi odpowiedziami, `historie.json`), więc
  zmiana reguł w kodzie nie wymaga nowych wywołań. Haiku zamyka polski cudzysłów prostym i psuje JSON: naprawiane przed odczytem.
- Pilot 19–26.09: 1–4 historie dziennie. Dobre: Dobropole (okrążenie w stacjach rosyjskich, obrona w Current Time i Espreso),
  licencja na Patrioty (obietnica czy przyznana), Starlink (sabotaż państwowy w TVP Info, „fałszywa flaga” w M1), Fridman i Usmanow
  (Rada UE czy Sąd UE), frekwencja Dumy. Słabe, które przeszły: „naciskał” i „żądał” (21.09). Wynik zmienia się między przebiegami.

# Telewizja: raporty GDELT „Today's Media Trends” — 2026-09-26

- `plx gdelt tv [--dzien D] [--kanal KOD ...] [--fraza F ...]` (`gdelt/tv.py`): pobiera dzienne raporty PDF GDELT
  (streszczenia wydań z TV News Archive robione przez Gemini) dla 17 kanałów: TVP Info, Espreso, Rossija 1 i 24, Pierwyj, NTV,
  Belarus 24, Current Time, LRT, DR1, M1, BBC News, France 24, TRT World, Kan 11, Press TV, CCTV-13. Raport za dzień D wychodzi w D+1.
- Bez modelu i bez kosztów. Wypisuje nazwy, które danego dnia padają w co najmniej 3 stacjach, a dzień wcześniej były
  w najwyżej jednej (albo stacji przybyło co najmniej 3 i dwa razy więcej). Nazwa to słowo wielką literą zaraz po słowie małą literą
  („the Firepoint”), więc tytuły sekcji raportów odpadają. Nazwy padające w tych samych zdaniach łączą się w jedną grupę.
  Przy każdej grupie po jednym zdaniu z każdej stacji, obok siebie. Wynik w `data/gdelt/tv-<dzień>.md`, tekst i linki w `data/gdelt/tv/`.
- Sprawdzone na 24–25.09: same wyszły Starlink, powitanie Xi na Andrews, Netanjahu i Abbas, OpenAI w Australii, a 25.09
  Bucza („dossier” Ławrowa dla Guterresa), Superintelligence, ArcelorMittal, „SWO”.
- Ograniczenia: raport to interpretacja modelu, nie przekaz stacji (ręczne sprawdzenie 24.09: fakty się zgadzały, ale np. słowa
  gościa kryminologa stały się stanowiskiem „urzędników”). Link prowadzi do całego wydania, nie do minuty. Transkrypcje są tylko
  w Visual Explorer (podpisane ciasteczko na wydanie, oryginały w Internet Archive prywatne), więc ich nie pobieramy.
  Szczegół, który robi kartę (Nowa Poczta w Rossiji 24 i Espreso), był tylko w transkrypcjach.
- `plx gdelt tv-widoki [--dni 7] [--do D]` (`gdelt/tv_views.py`): robocze widoki tylko z telewizji w jednym pliku HTML
  (`data/gdelt/tv-widoki.html`, niepublikowany): tablica dnia (nowe nazwy × stacje w regionach), jeden temat (zdanie z każdej
  stacji i lista stacji, w których raporcie nie pada), dwie stacje obok siebie (streszczenia i wspólne rzadkie nazwy, np. Kyivstar
  i ArcelorMittal w Rossiji 24 i Espreso 25.09), kanał w czasie (tytuły i nowe nazwy dzień po dniu), szukanie frazy we wszystkich zdaniach.
- Te widoki są osobną zakładką „Telewizja” na stronie wewnętrznej (pod hasłem), w jej wyglądzie i trybie ciemnym. `plx site`
  dociąga raporty z ostatnich 7 dni (`--tv-dni`), `--bez-tv` buduje z zapisanych.
- Telewizja po polsku z przełącznikiem PL/EN (EN to oryginał raportu; wybór zapamiętany). `gdelt/tv_pl.py`: tytuł i każde
  zdanie raportu tłumaczone modelem `deepseek-flash` (tłumaczenie, nie analiza; ok. 0,007 $ za raport, ok. 0,12 $ dziennie za 17 stacji),
  porcje po 40 zdań, 6 raportów naraz, tylko przy `plx site`. Zapis obok raportu (`data/gdelt/tv/<dzień>/<KOD>.pl.json`), wyrównany
  ze zdaniami oryginału; brak tłumaczenia zdania pokazuje angielskie. Szukanie frazy działa w obu językach (Bucza i Bucha).
  `--bez-historii` używa tylko zapisanych tłumaczeń.

# Strona jako aplikacja — 2026-09-26

- Przeglądarka proponuje instalację strony jako aplikacji (Chrome, Edge, Android; na iOS „Do ekranu początkowego”).
  `site/icons.py`: manifest (`manifest.webmanifest`, okno bez paska adresu) i ikony PNG z logo, rysowane w czystym Pythonie.
  Chrome przez DevTools: manifest bez błędów, brak przeszkód w instalacji (serwer lokalny z hasłem).
- Serwer wydaje bez hasła tylko manifest i ikony, bo przeglądarka pobiera je bez logowania. Reszta nadal pod hasłem.

# Strona: kliknięcia w trybie ciemnym, nagłówki po polsku — 2026-09-26

- Błąd: w trybie ciemnym każde kliknięcie w dzienniku (odnośnik raportu, lista tematów, logo) przełączało na porównanie
  krajów. Tryb ciemny ustawia `data-theme` na `<html>`, a dziennik tym samym atrybutem oznaczał klikalne tematy, więc
  `closest("[data-theme]")` łapał całą stronę. Temat ma teraz `data-topic`; test pilnuje, żeby skrypty nie wracały do `[data-theme]`.
- Wszystkie nagłówki dnia po polsku (lista artykułów, porównanie krajów, panel artykułu, podpowiedzi odnośników), oryginał
  mniejszy pod spodem. `site/titles.py`: model ekstrakcji, porcje po 120 nagłówków, 4 równolegle, tylko przy `plx site`.
  Zapis w `data/tytuly/<dzień>.json` według id artykułu, kolejne budowy tłumaczą tylko nowe. Skopiowany oryginał nie liczy się
  jako tłumaczenie. Pierwsze trzy dni (1531 nagłówków): 0,15 $. `--bez-historii` używa tylko zapisanych.
- Strona budowana z gałęzi bez najnowszego `main` pokazywała 25.09 „bez raportu”; raporty dnia są w `main`.

# Strona wewnętrzna pod hasłem (Render) — 2026-09-26

- Strona z `plx site` jest dostępna w internecie tylko pod hasłem. `plx site --publikuj` wypycha zbudowaną stronę jednym commitem
  (force push, repo nie puchnie od starych wersji) do osobnego prywatnego repo `SITE_REPO` (`kraxtere/paralaksa-strona`).
  Przed pushem sprawdza przez `gh`, że repo jest prywatne; publiczne odrzuca.
- Render (darmowy Web Service) uruchamia `server.py` z `src/paralaksa/site/hosting/`: tylko biblioteka standardowa, HTTP Basic Auth,
  login i hasło wyłącznie w zmiennych Rendera (`SITE_USER`, `SITE_PASSWORD`), bez nich odpowiedź 503. Bez listingu katalogów,
  `X-Robots-Tag: noindex`. Darmowy plan usypia usługę po 15 min bez ruchu (pierwsze wejście ok. minuty).
- Osobne repo zamiast gałęzi w tym: `paralaksa-narracji` zostaje publiczne, więc minuty GitHub Actions są bez limitu
  (daily 35–55 min dziennie przekroczyłby z czasem 2000 min miesięcznie dla repo prywatnego).

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
  Przy pierwszej karcie zrobionej z pomocą narzędzia (2026-09-24-netanjahu-abbas-onz) dwie kolejne poprawki: części fraz jako
  rdzenie 1–2 słów (model podawał całe wyrażenia, np. „выход из зала”, a nagłówki piszą „покинули зал”) i kolejność trafień
  według liczby pasujących fraz (ogólna fraza „UN General Assembly” zapychała kolejkę zapowiedziami innych wystąpień).
  Wynik: 272 nagłówki w 18 językach zamiast 82 w 14; karta z 16 relacjami z 11 krajów w ok. 25 min.
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

# Ekstrakcja: 8 równoległych wywołań — 2026-09-25

- Pierwszy przebieg z 30 źródłami (25.09, 1094 nowe artykuły, 862 w oknie publikacji) doszedł do `max_runtime_s` 2400 s:
  840 przetworzonych, 22 (WAFA) odłożone na kolejny przebieg, kod 1. `extract.max_concurrency` 4 → 8, limit czasu bez zmian.
  Koszt na artykuł się nie zmienia; dzień kosztował 2,55 $ z limitu 3 $ (ekstrakcja 1,17 $, synteza 1,38 $).
- Z GitHub Actions nie działają Al-Quds (403 na kanał) i Indian Express (robots.txt blokuje; z domowego łącza przepuszcza).
  Obie blokady dotyczą adresów centrów danych; nie obchodzimy ich.

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
