# Karty zdarzeń (pilot „Jedno zdarzenie. Dwie opowieści.”)

Jednostką jest **zdarzenie**, nie redakcja. Najpierw ustalamy wspólny fakt, potem dopinamy relacje z różnych miejsc
i opisujemy, w którym momencie opowieść zaczyna budować spokój, lęk, oburzenie albo nadzieję. Koncepcja: `docs/PARALAKSA_ZDARZEN.md`.

- Jeden plik `RRRR-MM-DD-nazwa.md` na zdarzenie, według `_szablon_zdarzenia.md`: nagłówek YAML (do filtrowania) + opis.
- Pliki `*.yaml` w tym katalogu to specyfikacje prototypu planszy (`plx board`), nie karty.
- Na etapie pilota wszystko ręcznie. Automatyzujemy dopiero to, co według notatek z pilota zjada najwięcej czasu.

## Zasady wypełniania (obowiązkowe)

1. **Linki jako surowe adresy** `https://…`, nigdy same nazwy redakcji. Relacja bez linku nie istnieje.
2. **Czas ze strefą** (ISO 8601, np. `2026-01-09T14:05+01:00`) dla publikacji i aktualizacji, jeśli redakcja ją podaje.
   Nie porównujemy wersji o różnym stanie wiedzy jak dwóch opowieści. Wtedy używamy formy `os_czasu`.
3. **Archiwum**: link do kopii (web.archive.org / archive.today) z godziną jej wykonania. Kopia późniejsza niż porównywana wersja niczego nie dowodzi.
4. **Nagłówek maks. 15 słów**, reszta własnymi słowami. **Nie kopiujemy pełnych tekstów ani długich fragmentów.**
5. **Rola źródła**: `redakcja`, `agencja` albo `strona_sprawy` (rząd, ministerstwo, firma, organizacja). Komunikat strony sprawy to jej stanowisko, a nie relacja medialna.
   **Gatunek**: `wiadomosc`, `relacja_na_zywo`, `wywiad`, `analiza`, `komentarz`, `przeglad` (przegląd kilku tematów) albo `komunikat`. Słowa rozmówcy w wywiadzie to nie rama redakcji.
6. **Liczby**: przy każdej liczbie zapisz, czego dotyczy (np. pracownicy bezpośredni vs łańcuch dostaw).
7. **`sprawdzil`**: kto otworzył link i przeczytał materiał, np. `GPT 2026-09-24` albo `człowiek 2026-09-24`.
   Do odcinka idą tylko relacje sprawdzone przez człowieka.
8. **Bez źródeł objętych sankcjami UE** (RT, Sputnik i inne z listy UE). Perspektywę rosyjską czy białoruską bierzemy z dozwolonych źródeł albo z oficjalnych komunikatów.
9. **Odrzucone przypadki zostają** (`status: odrzucony` + `powod_odrzucenia`). To wiedza o granicy między kontrastem rzeczywistym a pozornym.
10. **Nie przypisujemy redakcjom intencji.** Hipoteza odbioru jest hipotezą do oceny widza.
11. **`jak_szukano`**: narzędzia i języki. **Notatki z pilota**: czas pracy i to, co było najbardziej żmudne. Na tej podstawie zdecydujemy, co automatyzować.

Pomoc: `plx events check events/<karta>.md` (albo `events` dla wszystkich) zapisuje w `data/checks/` podpowiedzi:
kopie Wayback z dnia publikacji, nagłówek i metadane z każdej kopii, zmiany nagłówka i nagłówki pokazywane na przemian (test A/B).
Karty nie zmienia. Podpowiedź to nie weryfikacja: `sprawdzil` wpisuje ten, kto przeczytał materiał.

Karty edytujemy tylko w `events/`. Zmiany w kodzie (`src/`, `tests/`, `config/`, `.github/`) nie należą do pracy nad kartami.
