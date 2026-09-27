# Zlecenie: burza mózgów, jak z telewizji zrobić wnioski zamiast archiwum (dla GPT)

**Zakres pracy: wyłącznie myślenie i raport tekstowy.** Nie zmieniaj kodu, konfiguracji, testów ani żadnych plików.
Nie pobieraj niczego z sieci (w szczególności transkrypcji, patrz „Ograniczenia”). Wynik to Twoja końcowa odpowiedź
(Markdown, po polsku). Decyzje podejmuje właściciel.

## Problem właściciela (jego słowami, streszczone)

Zakładka Telewizja na stronie wewnętrznej pokazuje raporty 17 stacji dziennie. To wygląda jak archiwum tematów.
Normalny człowiek nie ma czasu czytać, co mówi 17 telewizji, a obok jest równie duży raport z prasy. Trzeba to
**syntezować**: wskazać różnice, konkretne historie i konkretne **sprzeczności**, może z grafiką. Trzeba wyłuskać,
co z tego wynika, a nie pokazać wszystko.

## Co mamy (zasób)

**Telewizja: raporty GDELT „Today's Media Trends”.** Dla każdej stacji i dnia PDF, w którym model Gemini (GDELT)
streszcza wszystkie wydania stacji z tego dnia (TV News Archive). Po angielsku, publikacja dzień później (D+1).
- 17 stacji: TVP Info (PL), Espreso (UA), Rossija 1, Rossija 24, Pierwyj kanał, NTV (RU), Belarus 24 (BY),
  Current Time (RFE/RL, po rosyjsku), LRT (LT), DR1 (DK), M1 (HU), BBC News (UK), France 24 (FR), TRT World (TR),
  Kan 11 (IL), Press TV (IR), CCTV-13 (CN).
- Skala: jeden dzień to ok. 3000 zdań i 80 tys. słów (25.09: 2966 zdań, 78,6 tys. słów). Raport stacji to 120–270 zdań.
- Struktura raportu: tytuł (teza dnia), „Day at a glance”, sekcje typu „MAJOR DEVELOPMENTS”, akapity z nagłówkami.
  Linki prowadzą do całego wydania w Visual Explorer (nie do minuty).
- **To interpretacja modelu, nie słowa stacji.** Styl jest napuszony („statecraft”, „architektura bezpieczeństwa”).
  Weryfikacja ręczna jednego raportu (TVP Info) wykazała, że sprawdzalne fakty się zgadzały, ale była jedna błędna atrybucja
  (słowa gościa-kryminologa podane jako „urzędnicy”).
- Po naszej stronie: tłumaczenie na polski (deepseek-flash, ok. 0,12 $ dziennie), bez innych modeli.
  Automat bez modelu wyłapuje nazwy własne nowe w ≥3 stacjach względem dnia poprzedniego i pokazuje zdanie z każdej stacji.
- Dane lokalnie (czytaj):
  - `data/gdelt/burza/probka-2026-09-25.md`: **zacznij tu**. Jeden dzień po polsku, tytuł i początek streszczenia każdej stacji
    wg bloków, 12 automatycznych „nowych nazw” ze zdaniem z każdej stacji.
  - `data/gdelt/tv/<dzień>/<KOD>.json` (pełny tekst raportu po angielsku, pole `text`) i `<KOD>.pl.json` (zdania po polsku),
    dni 2026-09-19..25.
  - `data/gdelt/tv-<dzień>.md`: wynik automatu „nowe nazwy” per dzień.
  - Obecne widoki (dla kontekstu): `src/paralaksa/gdelt/tv_views.py`, `src/paralaksa/site/assets/tv.js`. Zakładki:
    tablica (nowe nazwy × stacje), temat (jedna nazwa, stacje wg bloków, kto milczy), para stacji, dziennik stacji, szukaj.

**Prasa (dla porównania, już działa):** codzienny przebieg: 30 redakcji z 13 krajów, sygnały (temat, rama, stance) z modelu,
raport dnia (`reports/2026-09-26.md`, skrót `reports/2026-09-26.short.md`), „historie dnia” (wydarzenia z ≥3 krajów
z nagłówkiem z każdego kraju: `data/stories/2026-09-26.json`). Koncepcja formatu publicznego:
`docs/PARALAKSA_ZDARZEN.md` („Jedno zdarzenie. Dwie opowieści.”, jedno zdarzenie, nagłówki obok siebie, bez komentarza).
Uwaga: prasa i TV to różne dni (TV kończy się na 25.09, prasa ma 26.09); próbka TV i prasa z 25.09 są w `data/stories/2026-09-25.json`.

## Ograniczenia (twarde)

- Transkrypcji nie pobieramy automatycznie (podpisane ciasteczko w Visual Explorer, w Internet Archive prywatne). Nie proponuj obejścia.
  Ręczne sprawdzenie pojedynczego wydania przez człowieka jest możliwe.
- Opisujemy przekaz, nie fakty; każde twierdzenie z odnośnikiem; cytaty maks. 15 słów; bez prognoz jako faktów.
- Rozróżnienie „stacja powiedziała” vs „Gemini streszczając stację napisał” musi być widoczne dla odbiorcy.
- Strona jest wewnętrzna (pod hasłem), ale pomysły mogą celować też w format publiczny (krótka forma, pion).
- Budżet: grosze dziennie. Dodatkowy model po naszej stronie jest dopuszczalny, jeśli za to płacimy centy, a nie dolary, i jeśli
  wynik da się sprawdzić (odnośnik do zdania raportu).

## Pytania

1. **Co z tego zasobu realnie da się wyłuskać**, czego nie da prasa? Oceń uczciwie, także czego *nie* da się rzetelnie pokazać
   (np. przez warstwę Gemini).
2. **Sprzeczności**: jakie typy sprzeczności między stacjami są wykrywalne w tych streszczeniach (ten sam fakt, różne liczby; ta sama
   osoba, przeciwna rola; wydarzenie przemilczane; różna przyczyna)? Pokaż **co najmniej 5 konkretnych przykładów z próbki 25.09**
   (lub pełnych raportów), z cytatem ≤15 słów i stacją. Zaznacz, które wymagałyby sprawdzenia w transkrypcji.
3. **Synteza dnia**: zaproponuj 3–5 różnych form „jednego ekranu” zamiast archiwum (np. „3 historie dnia w TV”, „kto o czym milczy”,
   „jeden fakt, trzy wersje”, „TV kontra prasa tego samego kraju”). Dla każdej: co pokazuje, skąd dane, jak liczone (automat czy model,
   jaki prompt w 2 zdaniach), koszt, ryzyko błędu i jak je widać.
4. **Grafika**: jakie wizualizacje mają sens na tych danych (mapa bloków, macierz stacje × tematy, oś tygodnia, „oś przemilczenia”)?
   Które niosą wniosek, a które są ozdobą?
5. **Połączenie z prasą**: gdzie TV i prasa się wzmacniają (np. temat obecny w TV, nieobecny w prasie danego kraju)? Zaproponuj
   jeden widok łączony.
6. **Priorytet**: co zrobić jako pierwsze (jedna rzecz, najwięcej wartości na koszt), co jako drugie, czego nie robić.

Pisz zwięźle, konkretnie, bez ogólników o „potencjale danych”. Przykłady wyłącznie z plików, nic z pamięci.
