# Wersja 2.0 strony: skrypty dnia

Skrypty obrazkowej wersji strony (do 2026-10-01 leżały w `data/`, poza gitem). Uruchamiane lokalnie z katalogu repo,
bo czytają i piszą `data/` (baza `data/prod.db` tylko do odczytu, wyniki w `data/widok/`). Obrazki i większość tekstów
robi Codex z limitu konta (`codex_limit.py` pokazuje zużycie). Nigdy w Actions.

## Nowy dzień D: jedno polecenie (od 05.10)

`python scripts/v2/dzien.py D [--publikuj] [--faza 1|2|3] [--sucho]` robi kroki poniżej w trzech fazach i wznawia od miejsca przerwania
(gotowe pomija; stan w `data/widok/D/_dzien.json`):
1. teksty po kolei: `plx site`, `plx report`, `dzien_prasy`, `os_czasu dzien/ciag/opisy`, `kraje.py D` i `kraje.py ciag D`;
2. wszystkie obrazki dnia w jednej kolejce `paski.run_all` (paski tematów i krajów w tematach, okładka, oś, kraje wszystkich krajów),
   jeden proces na obrazek (`PASKI_PROCESY=100` domyślnie), starty co 10 s, po 429 hamowanie jak w kroku 6;
   teksty potrzebne obrazkom (podsumowania, `plakat-*.json`) powstają przy budowie zleceń (z pamięci podręcznej);
3. strony dnia, osi i krajów, `streszczenia.py D`, strony ponownie (streszczenia), z `--publikuj` także `plx site --publikuj`.
Kod wyjścia: 1 = krok tekstowy lub strona nie wyszedł, 2 = obrazki odrzucone lub przerwane (ponowne uruchomienie robi tylko brakujące).
Ręczne kroki poniżej zostają do poprawek pojedynczych obrazków; `kraje.py obrazki` ręcznie nadal domyślnie tylko PL.

## Nowy dzień D: kroki ręczne

1. Baza z produkcji do `data/prod.db` (`docs/OPERATIONS.md`, odszyfrowanie snapshotu).
2. `plx site --db data/prod.db`: Sprawy dnia (`data/stories/D.json`) i nagłówki po polsku (`data/tytuly/`).
3. `plx report --date D --db data/prod.db`: raport okładkowy (różnice i obraz kraju) przez Codex.
4. `python scripts/v2/dzien_prasy.py D --bez-opisow`: dane krajów i tematów dnia (`data/dzien_prasy/D/opisy.json`),
   bez modelu (od 30.09; z opisami krajów przez DeepSeek ok. 0,04 $).
5. Oś wydarzeń, część tekstowa (przed okładką, bo okładka oznacza ciąg dalszy):
   - `python scripts/v2/os_czasu.py dzien D`: dalsze zdarzenia dnia (≥ 2 kraje, `data/widok/os/dodatkowe/D.json`),
     potem Sprawy dnia i dalsze zdarzenia → nowe zdarzenia albo dalszy ciąg, razem 4–8 nowych na dzień;
   - `python scripts/v2/os_czasu.py ciag D`: które Sprawy dnia 1–3 to ciąg dalszy wcześniejszych dni i co nowego
     (`data/widok/os/ciag/D.json`; okładka dostaje etykietę „Ciąg dalszy · od DD.MM”, strona sprawy ramkę z linkiem na oś).
6. Strona dnia (`DZIEN=D` w środowisku), od 01.10 pasami:
   - `python scripts/v2/widok_obrazkowy.py paski`: kafelki tematów (panorama ok. 3:1 na temat ze scen dnia, gazetki „jak Wally”, 2 na obrazek poziomy, `pas-TEMAT.webp`) i paski
     krajów na stronach tematów (jeden na kraj, `pas-TEMAT-KRAJ.webp`; dymek = nagłówek z `plakat-TEMAT.json`).
     Okładka: obrazki po najwyżej 3 pasy (pas ok. 2:1); temat: jeden obrazek (przy > 6 krajach dwa), do 8 procesów co 10 s (`PASKI_PROCESY=12`, `PASKI_ODSTEP`), po 429 4 co 20 s;
     429 także przy 4: przerwanie (kod 3); ponowne uruchomienie robi tylko brakujące paski.
     Oryginały w `_paski/`; odrzucone po ponowieniu wypisane na końcu (karta bez paska). Ponowne cięcie bez Codex:
     `python scripts/v2/paski.py pokroj data/widok/D/_paski/NAZWA.png`;
   - okładka „Przegląd prasy” z pasów (od 02.10, zamiast `widok_powitanie.py` / `powitanie.png`; obrazki bez tekstu,
     wszystkie napisy w HTML): `python scripts/v2/okladka.py paski` (jeden pas na sprawę, różnicę i obraz kraju,
     3 pasy na obrazek; sceny i styl dawnego plakatu z gazetkami, bez tytułów i podpisów; tylko brakujące).
     Sprawdzić wzrokiem: zero liter, najwyżej 4 gazetki w pasie, bez fałszywych symboli państw; zły obrazek: przenieść jego
     `okl-*.webp` i oryginał z `_paski/` do `_stare/`, uruchomić `paski` ponownie (raz);
   - `python scripts/v2/widok_obrazkowy.py strona`: HTML okładki, spraw, różnic, obrazu kraju i tematów.
   Dni 23–30.09 przerobione na paski 02.10 (`paski`, potem `strona`); dawne `start.png` i plakaty zostają w katalogach.
7. Oś wydarzeń, reszta: `python scripts/v2/os_czasu.py opisy`, `obrazki`, `strona`.
8. `python scripts/v2/kraje.py D`: „Czym żyje kraj”, 3–5 tematów krajowych z artykułów spoza wydarzeń wielokrajowych
   (po krokach 5 i 7; `data/widok/kraje/D.json`, Codex, ok. 2 min). Potem `python scripts/v2/kraje.py obrazki D`
   (domyślnie tylko PL; 1 obrazek na kraj, `paski.py`): paski scen nad tematami (`data/widok/kraje/D/PL-n.webp`);
   przy innej liczbie pasków jedno ponowienie, potem kraj odrzucony (nic nie zapisane); `kraje.py pokroj D KRAJ`. Potem `python scripts/v2/kraje.py ciag D`
   (Codex: ciąg dalszy spraw z 7 dni wstecz, pole `ciag_od`) i `python scripts/v2/kraje.py strona` (osie krajów
   `data/widok/kraje/KRAJ.html`, wszystkie dni). Na koniec `DZIEN=D widok_obrazkowy.py strona`.
9. `python scripts/v2/streszczenia.py D`: streszczenia artykułów pod nagłówkami stron dnia i osi (tylko brakujące).
10. `plx site --db data/prod.db --publikuj`.

Po każdym obrazku z ludźmi: obejrzeć (bez stereotypów, bez napisów na kadrach osi). Przy blokadzie moderacji plakatu:
`widok_warianty.py`.

## Pliki

- `dzien.py`: procedura dnia w 3 fazach (teksty, wszystkie obrazki naraz, strony i publikacja); `image_jobs()` w `widok_obrazkowy.py`, `okladka.py`, `os_czasu.py`, `kraje.py` oddają zlecenia obrazków.
- `paski.py`: wspólne paski (obrazek Codex z N pasami, cięcie po ramkach, 8/4 procesy).
- `widok_obrazkowy.py`: okładka pasami (dawniej siatka tematów i plakaty), wszystkie strony dnia; `widok_tresci.py`: dane i pamięć podręczna tekstów stron.
- `widok_powitanie.py`: dane okładki (`poster_data`) i dawny plakat z napisami `powitanie.png` (do 01.10).
- `okladka.py`: okładka z pasów (sceny z plakatu bez napisów, `paski.prompt` + `STYLE`, HTML `cover_html`).
- `os_czasu.py`: ciągła oś wydarzeń (`data/widok/os/`).
- `kraje.py`: „Czym żyje kraj”, tematy tylko w prasie jednego kraju (`data/widok/kraje/`).
- `streszczenia.py`: streszczenia artykułów pod nagłówkami (`data/widok/streszczenia/`, klik w nagłówek na stronie); 3–5 zdań, `skroc` jednorazowo skraca starsze (5–7 zdań) do ok. 60%.
- `dzien_prasy.py`: dane i opisy krajów dnia; `loga.py`: ikony redakcji (`data/logos/`).
- `komiks_codex.py`: wywołanie Codex (`codex_exe`) i dawny prototyp komiksu; `codex_limit.py`: stan limitu Codex.
