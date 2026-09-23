---
id: 2023-09-15-zboze-polska-ukraina
tytul: Polska utrzymuje ograniczenie importu produktów rolnych z Ukrainy po wygaśnięciu środka UE
status: kandydat
powod_odrzucenia: null
droga: od_zdarzenia
dziedzina: [rolnictwo, handel, gospodarka]
forma: dwie_opowiesci
fakt:
  czas: '2023-09-16T00:00+02:00'
  opis: 'Po wygaśnięciu środka unijnego Polska wprowadziła krajowy zakaz przywozu określonych produktów rolnych z Ukrainy; rozporządzenie weszło w życie 16 września, nie jest to zakaz wszelkiego tranzytu.'
  zrodlo_pierwotne: https://eli.gov.pl/eli/DU/2023/1898/ogl/pol
stan_wiedzy_zmienial_sie: true # zapowiedź premiera wieczorem i opublikowane rozporządzenie to różne etapy
os_czasu:
  - {czas: null, co_wiadomo: '15 września KE ogłasza wygaśnięcie swoich ograniczeń; komunikat nie podaje godziny', zrodlo: https://enlargement.ec.europa.eu/news/following-expiry-restrictive-measures-ukrainian-exports-grain-ukraine-agrees-introduce-measures-2023-09-15_en}
  - {czas: '2023-09-15T20:20+03:00', co_wiadomo: 'Ukraińska Prawda relacjonuje zapowiedź polskiego premiera; to jeszcze nie publikacja krajowego rozporządzenia', zrodlo: r2}
  - {czas: '2023-09-15T21:35+02:00', co_wiadomo: 'Rzeczpospolita relacjonuje podpisanie rozporządzenia; artykuł później aktualizowano', zrodlo: r1}
  - {czas: '2023-09-16T00:00+02:00', co_wiadomo: 'wejście w życie krajowego rozporządzenia', zrodlo: https://eli.gov.pl/eli/DU/2023/1898/ogl/pol}
relacje:
  - id: r1
    kraj: PL
    kto: Rzeczpospolita
    rola: redakcja
    link: https://www.rp.pl/rolnictwo/art39118781-polska-wprowadza-zakaz-importu-zboza-z-ukrainy-buda-podpisal-rozporzadzenie
    publikacja: '2023-09-15T21:35+02:00'
    aktualizacja: '2026-08-27T20:03+02:00'
    porownywana_wersja: 'aktualizacja 2026-08-27T20:03+02:00; bez kopii historycznej'
    archiwum: {link: null, wykonano: null}
    naglowek: 'Polska wprowadza zakaz importu zboża z Ukrainy. Buda podpisał rozporządzenie'
    tlumaczenie: 'Polska wprowadza zakaz importu zboża z Ukrainy. Buda podpisał rozporządzenie'
    zostawia_z: 'Pierwszy plan: krajowe rozporządzenie po decyzji KE; w artykule także głos premiera o interesie polskiego rolnika.'
    sprawdzil: 'GPT 2026-09-23'
  - id: r2
    kraj: UA
    kto: Ukraińska Prawda / Europejska Prawda
    rola: redakcja
    link: https://www.pravda.com.ua/news/2023/09/15/7420022/
    publikacja: '2023-09-15T20:20+03:00'
    aktualizacja: null
    porownywana_wersja: 'wersja dostępna 2026-09-23, pierwotny znacznik 20:20; brak kopii historycznej'
    archiwum: {link: null, wykonano: null}
    naglowek: 'Польща продовжить заборону на імпорт українського зерна, попри дозвіл ЄС – Моравецький'
    tlumaczenie: 'Polska utrzyma zakaz importu ukraińskiego zboża mimo zgody UE – Morawiecki'
    zostawia_z: 'Pierwszy plan: jednostronna decyzja Warszawy mimo wygaśnięcia ograniczenia UE.'
    sprawdzil: 'GPT 2026-09-23'
kontrasty:
  - miedzy: [r1, r2]
    rodzaj: dobor_slow
    opis: 'Polska redakcja otwiera podpisaniem krajowego aktu; ukraińska decyzją Polski „mimo zgody UE”.'
    zastrzezenia: 'Ukraińska relacja była wcześniej i dotyczyła zapowiedzi premiera, polska później podpisanego aktu. To dwie fazy jednej decyzji; bez kopii RP z września 2023 siła kontrastu pozostaje niepotwierdzona. Ukraiński tekst streszcza PAP i wypowiedź polskiego premiera, nie zawiera samodzielnego głosu ukraińskich rolników.'
jak_szukano: ['wyszukiwarka WWW pl/uk/en; przeczytano Rzeczpospolitą, Ukraińską Prawdę, komunikat KE i akt prawny ELI; porównano godziny Kijów/Warszawa']
---

## Fakt
Komisja zapowiedziała wygaśnięcie unijnych ograniczeń i ukraińskie działania kontrolne. Polska opublikowała własne rozporządzenie, obowiązujące od północy 16 września. Zakres produktów i wyjątki wynikają z aktu prawnego; sam nagłówek „zakaz zboża” je upraszcza.

## Przekaz
Dwie redakcje eksponują inny punkt odniesienia: krajową ochronę rynku i odmowę podążenia za decyzją UE. To użyteczny test „Polska oczami innych”, ale niemal ten sam materiał faktograficzny pochodzi z wypowiedzi polskiego premiera. Nie nazywamy tego jeszcze silną różnicą społeczną Polska–Ukraina.

## Hipoteza odbioru
Widz może ocenić, czy słowo „mimo” zmienia jego reakcję na działanie Polski, wiedząc, że ukraiński artykuł ukazał się przed podpisaniem aktu.

## Ilustracja
Ta sama bariera celna widziana z dwóch stron; osobna strzałka tranzytu, który nie oznacza automatycznie importu na polski rynek.

## Uczciwość odcinka
- [ ] Zdobyć wrześniową wersję polskiego tekstu i upewnić się, że nie dopisano elementów po 2023.
- [ ] Człowiek sprawdzi akt, teksty i zakres wyjątku tranzytowego.

## Notatki z pilota
- Czas pracy: nie mierzono osobno; wspólna kwerenda i edycja kart w sesji 2026-09-23 (ok. 15–20 min łącznie dla 8 kart).
- Co było najbardziej żmudne (kandydat do automatyzacji): rozróżnienie zapowiedzi od wejścia prawa w życie i sprawdzenie translacji „mimo” w oryginale.
- Czego zabrakło w karcie: pole „faza zdarzenia” dla relacji.
