# Wersja 2.0 strony: skrypty dnia

Skrypty obrazkowej wersji strony (do 2026-10-01 leżały w `data/`, poza gitem). Uruchamiane lokalnie z katalogu repo,
bo czytają i piszą `data/` (baza `data/prod.db` tylko do odczytu, wyniki w `data/widok/`). Obrazki i większość tekstów
robi Codex z limitu konta (`codex_limit.py` pokazuje zużycie). Nigdy w Actions.

## Nowy dzień D

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
6. Strona dnia (`DZIEN=D` w środowisku):
   - `python scripts/v2/widok_obrazkowy.py obraz`: siatka tematów `start.png`;
   - `python scripts/v2/widok_obrazkowy.py plakat TEMAT` dla każdego tematu z `tematy.json`;
   - `python scripts/v2/widok_powitanie.py`: okładka `powitanie.png`;
   - `python scripts/v2/widok_obrazkowy.py strona`: HTML okładki, spraw, różnic, obrazu kraju i tematów.
   Obrazki można puszczać równolegle (8 procesów Codex naraz działało 01.10).
7. Oś wydarzeń, reszta: `python scripts/v2/os_czasu.py opisy`, `obrazki`, `strona`.
8. `plx site --db data/prod.db --publikuj`.

Po każdym obrazku z ludźmi: obejrzeć (bez stereotypów, bez napisów na kadrach osi). Przy blokadzie moderacji plakatu:
`widok_warianty.py`.

## Pliki

- `widok_obrazkowy.py`: siatka tematów, plakaty, wszystkie strony dnia; `widok_tresci.py`: dane i pamięć podręczna tekstów stron.
- `widok_powitanie.py`: okładka dnia (sprawy, różnice, obraz kraju).
- `os_czasu.py`: ciągła oś wydarzeń (`data/widok/os/`).
- `dzien_prasy.py`: dane i opisy krajów dnia; `loga.py`: ikony redakcji (`data/logos/`).
- `komiks_codex.py`: wywołanie Codex (`codex_exe`) i dawny prototyp komiksu; `codex_limit.py`: stan limitu Codex.
