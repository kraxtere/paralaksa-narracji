# Zadania: zakładka „Kraje” i ikonka rozwijania (plan 2026-10-02)

Każde zadanie uruchamiać w czystej sesji (`/clear`), wkleić tylko blok „Polecenie”. Kolejność: 1 (niezależne), 2 → 3, 4 i 5 opcjonalne.
Wspólne dla wszystkich: przestrzegaj sekcji „Oszczędzanie kontekstu” w CLAUDE.md; czytaj tylko potrzebne fragmenty plików;
test tylko tego, co zmieniasz, pełny `pytest -q` raz na końcu; bez zrzutów ekranu; wpis w CHANGELOG; commit + push na bieżącą gałąź.

## Koncepcja
Zakładka „Kraje” w wersji 2.0: dla każdego kraju dnia 3–5 tematów krajowych z artykułów, które nie weszły do żadnego
wydarzenia wielokrajowego („tylko tutaj”). Polska pierwsza i najbogatsza. Nagłówki jak wszędzie: po polsku, `data-a`, klik → streszczenie.
Bez poradników i lifestyle'u (filtruje Codex). Plansza TV i pas „TVP Info a prasa” później (zadanie 5).

## Zadanie 1: ikonka „rozwiń” przy nagłówkach ze streszczeniem — Sonnet, low
Polecenie:
> W `src/paralaksa/site/assets/pasek.js` jest blok streszczeń (klik w link `a[data-a]` rozwija `.streszcz`). Po wczytaniu shardów
> oznacz linki, które MAJĄ streszczenie, klasą `ma-str` i dodaj CSS: po linku mały znak „▸” (szary, przez zmienną CSS), przy otwartym
> „▾”; `title="Kliknij, aby rozwinąć streszczenie"`. Linki bez streszczenia bez zmian. Dopisz asercję w `tests/test_site.py`
> (zawartość pasek.js), puść tylko ten test, CHANGELOG, commit, push, potem `plx site --db data/prod.db --publikuj`.

## Zadanie 2: dane „tylko w tym kraju” — Sonnet, medium
Polecenie:
> Nowy skrypt `scripts/v2/kraje.py D` (wzoruj się na `scripts/v2/streszczenia.py`: Codex przez tę samą funkcję, model luna, porcje,
> jedna próba ponowienia, walidacja w kodzie). Dla dnia D weź artykuły z okna dnia (tak jak `data/stories/D.json` je liczy) bez
> przypisania do żadnej historii (pola `pozostale`/`odrzucone` w stories JSON oraz artykuły z `data/widok/os/dodatkowe/D.json`
> traktuj jako przypisane, jeśli tam są). Per kraj: Codex grupuje w 3–5 tematów krajowych (tytuł tematu po polsku ≤ 6 słów,
> 1 zdanie opisu bez ocen), każdy z 1–4 id artykułów; odrzuca poradniki, lifestyle, sport, pogodę. Temat z ≥ 2 redakcji wyżej.
> Polskie tytuły z `data/tytuly/`. Walidacja: id tylko z wejścia, bez duplikatów, opis ≤ 25 słów. Wynik `data/widok/kraje/D.json`.
> Zapisz rozmiar wejścia i zużycie limitu w jednej linii wyjścia. Uruchom na 2026-10-01, pokaż mi tylko JSON dla PL (krótko).
> Dopisz krok do `scripts/v2/README.md` (przed streszczeniami). Bez testów jednostkowych poza walidacją (1 test offline). Commit, push.

## Zadanie 3: strona „Kraje” — Sonnet, medium
Polecenie:
> Na podstawie `data/widok/kraje/D.json` (z `scripts/v2/kraje.py`) dodaj w `scripts/v2/widok_obrazkowy.py` stronę
> `data/widok/D/kraje.html`: sekcja na kraj (flaga/nazwa jak na stronach obrazu kraju, Polska pierwsza), tematy z opisem i listą
> nagłówków w tym samym HTML co `article_list` (z `data-a`, logo redakcji). Nagłówek strony: „Tylko tutaj · DD.MM”, podpis:
> „Sprawy obecne w prasie jednego kraju, nieobecne w Wydarzeniach dnia”. Link do strony w okładce dnia (obok Wydarzeń dnia,
> sprawdź, jak są linkowane sekcje) i `data-sekcja="kraje"` + obsługa w `server.section_of`. Sprawdź, że `streszczenia.py shown_ids`
> łapie nowe linki (uruchom `streszczenia.py 2026-10-01`). Przebuduj stronę 01.10 poleceniem `indeks`/`strona`, `plx site --publikuj`.
> CHANGELOG, krótka linia w CLAUDE.md (mapa kodu), commit, push.

## Zadanie 4 (decyzja właściciela): włączyć wp i gazeta — Sonnet, low
Polecenie:
> W `config/sources.yaml` ustaw `active: true` dla `wp` i `gazeta` (zweryfikowane wcześniej). Sprawdź `plx ingest -s wp -s gazeta --db data/test.db`
> na pustej bazie testowej (wypisz tylko liczbę artykułów i pełnych tekstów). Zaktualizuj liczbę źródeł w CLAUDE.md, CHANGELOG, commit, push.

## Zadanie 5 (później): Polska — telewizja obok prasy — Opus, medium
Do zaprojektowania po tygodniu działania zadań 2–3: pas „TVP Info” na stronie Kraje (tematy z raportu GDELT, D+1, podpis „streszczenie AI”),
oznaczenie, które tematy TV są też w prasie PL, opcjonalnie plansza dnia jak w `data/checks/tvp-info-*` (zużywa 1 obrazek z dobowego limitu).
