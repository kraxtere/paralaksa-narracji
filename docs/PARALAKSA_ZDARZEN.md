# Paralaksa zdarzeń — zwrot koncepcji (2026-09-23)

Po przeglądzie warunków źródeł (`LEGAL_REVIEW_2026-09-23.md`) właściciel zmienia kierunek:
zamiast analitycznego raportu trendów — **krótka forma**: jedno zdarzenie, nagłówki z wielu krajów obok siebie,
bez komentarza. Punkt wyjścia: „jeśli chcesz wiedzieć, co się dzieje, oglądaj wiadomości z różnych miejsc”.
Ludzie żyją nagłówkami, więc nagłówek jest materiałem, nie pełny tekst.

## Aktualizacja 2026-09-24: „Jedno zdarzenie. Dwie opowieści.”

Ta sekcja ma pierwszeństwo przed resztą dokumentu, która opisuje pierwszy prototyp.
- **Jednostką jest zdarzenie, nie redakcja ani kraj.** Najpierw wspólny, potwierdzony fakt, potem relacje, potem rozwidlenie:
  w którym momencie opis zaczyna budować spokój, lęk, oburzenie albo nadzieję. Kontrast może być też wewnątrz jednego kraju.
- **Dwie drogi:** od wiadomości do zdarzenia (bieżące publikacje podsuwają zdarzenie) i od zdarzenia do wiadomości
  (wybieramy zdarzenie, np. Mercosur, i szukamy relacji także poza stałą listą źródeł).
- **Formy:** dwie opowieści, kilka perspektyw albo oś czasu, gdy stan wiedzy zmieniał się w ciągu dnia.
  Nie zestawiamy wersji z różnym stanem wiedzy jako dwóch opowieści.
- **Katalog:** karty w `events/*.md` (szablon i zasady: `events/README.md`). Hipoteza odbioru jest jawna i pokazywana widzowi
  do oceny, bez przypisywania redakcjom intencji. Fakt, przekaz i nasza ilustracja są rozdzielone.
- **Pilot ręczny** na kilku zdarzeniach. Dopiero notatki z pilota („co było najbardziej żmudne”) zdecydują, co automatyzować.
  Nie rozwijamy KM4 według starego SPEC.

## Stan: prototyp (2026-09-23)

- `plx board events/<id>.yaml [-o data/boards] [--no-png]` → HTML + PNG 1080×1920 (pion: TikTok/Reels/Shorts).
  PNG przez Chrome/Edge/Chromium headless (`PLX_BROWSER` nadpisuje ścieżkę). Kod: `src/paralaksa/board/`.
- Zdarzenie opisuje ręcznie kuratorowany YAML (`events/`): neutralny tytuł, zakres dat, **jawna reguła doboru**,
  lista `article_id` z bazy i robocze tłumaczenia nagłówków obcojęzycznych.
- Dwa przykłady z bazy z 22–23.09 (wyniki w `data/boards/`, poza gitem):
  - `2026-09-22-sankcje-oligarchowie` — ta sama decyzja UE: Rzeczpospolita tytułuje „UE przedłuża sankcje”,
    niemieckie i brytyjskie redakcje „UE usuwa/skreśla oligarchów”, Ukraińska Prawda „handel sankcjami i zakładnikami”.
  - `2026-09-23-xi-w-usa` — wizyta Xi: CGTN o „współpracy mimo rywalizacji”, BBC o „czerwonym dywanie”,
    Al Jazeera o wojnie handlowej, Onet o Ukrainie i chińskich ośrodkach nuklearnych.
- Historia ze śmigłowcem nad Polską (BBC, 23.09) nie nadaje się: w bazie ma tylko jedną redakcję.

## Zasady formatu (wbudowane w kod)

1. **Bez komentarza.** Na planszy tylko nagłówki, redakcja, typ (prywatne/publiczne/państwowe/agencja), czas UTC, domena.
2. **Dobór regułą, nie gustem.** Wszystkie nagłówki z bazy spełniające regułę zapisaną w YAML i drukowaną w stopce;
   wybieranie „najlepszych” nagłówków byłoby już komentarzem.
3. **Kolejność neutralna:** kraje i nagłówki według czasu publikacji.
4. **Oryginał zawsze widoczny**, tłumaczenie oznaczone jako robocze; cytat maks. 15 słów (dłuższe ucinane „…”).
5. Opis zdarzenia w nagłówku planszy — tylko fakty z leadów, bez oceny.

## Stan prawny (uczciwie)

Nagłówek zacytowany z podaniem redakcji i linkiem to zwykły przegląd prasy. **Nie zmienia to** tego, że
automatyczne przetwarzanie kanałów BBC, Guardiana i Al Jazeery (także samych nagłówków przez model) jest objęte
ich zastrzeżeniami wobec analizy/TDM/AI. Właściciel zna przegląd i podejmuje decyzję; tu tylko zapis.
Mniejsza ekspozycja: bez pełnych tekstów, bez wysyłania treści na zewnątrz (patrz lokalne grupowanie niżej).

## KM4 w nowym kierunku (propozycja, nic z tego nie jest wdrożone)

1. **Tylko nagłówek + lead.** `fulltext: false` dla wszystkich źródeł (pełny tekst przestaje być potrzebny);
   pokrywa się z wariantem „bez archiwum” z `LEGAL_OPTIONS_2026-09-23.md`. Do decyzji właściciela, bo zmienia
   działający daily (płytsze sygnały w raporcie).
2. **Automatyczne grupowanie zdarzeń** zamiast ręcznego YAML: wielojęzyczne embeddingi nagłówków+leadów liczone
   **lokalnie** (mały model, CPU) → klastry „to samo zdarzenie, wiele krajów” → kandydaci na planszę z progiem
   ≥3 kraje. Nic nie wychodzi poza maszynę. To ta sama technika, którą SPEC planował dla tematów wyłaniających się.
3. **Tłumaczenia**: lokalny model tłumaczący albo ręcznie; kurator zatwierdza planszę przed publikacją.
4. **GDELT jako zwiadowca** („gdzie głośno, gdzie cicho”): API DOC odpowiadało 2026-09-23 kodem 429 (limit),
   surowe pliki 15-minutowe (`data.gdeltproject.org/gdeltv2/lastupdate.txt`: events ~90 KB, mentions ~170 KB,
   GKG ~7 MB) działają. Mentions dają listę domen, które pisały o zdarzeniu — sygnał do wyboru tematu,
   nagłówki bierzemy z naszego RSS.
5. **Formaty**: plansza pionowa (jest), karuzela (slajd na kraj + plansza zbiorcza), scenopis komiksu.
