---
id: 2024-08-02-zatrudnienie-usa
tytul: USA publikuje dane o zatrudnieniu i bezrobociu za lipiec 2024
status: odrzucony
powod_odrzucenia: 'Pozorny format A/B: artykuł Axios i telewizyjny wywiad Bloomberga z członkinią administracji to różne gatunki i różne role; Axios sam wymienia czynniki uspokajające. Nie znaleziono drugiego zweryfikowanego artykułu redakcyjnego z przeciwną tezą o tych samych liczbach i stanie wiedzy.'
droga: od_zdarzenia
dziedzina: [gospodarka, praca]
forma: dwie_opowiesci
fakt:
  czas: '2024-08-02T08:30-04:00' # koniec embarga BLS; nie czas zbierania danych
  opis: 'BLS podał przyrost zatrudnienia poza rolnictwem o 114 tys. w lipcu i stopę bezrobocia 4,3 proc. Są to wyniki dwóch różnych badań statystycznych; same w sobie nie stwierdzają recesji.'
  zrodlo_pierwotne: https://www.bls.gov/news.release/archives/empsit_08022024.htm
stan_wiedzy_zmienial_sie: false
os_czasu: []
relacje:
  - id: r1
    kraj: US
    kto: Axios
    rola: redakcja
    gatunek: wiadomosc
    link: https://www.axios.com/2024/08/02/jobs-economy-unemployment-fed-rate-recession
    publikacja: null # widoczna data aktualizacji 2.08, brak godziny
    aktualizacja: null
    porownywana_wersja: 'wersja dostępna 2026-09-23; brak godzin'
    archiwum: {link: null, wykonano: null}
    naglowek: 'New jobs numbers raise alarm bells on recession risk'
    tlumaczenie: 'Nowe dane o zatrudnieniu uruchamiają alarm dotyczący ryzyka recesji'
    zostawia_z: 'Ryzyko wzrostu bezrobocia, ale także wyraźne zastrzeżenia o nadal niskiej stopie i możliwych czynnikach łagodzących.'
    sprawdzil: 'GPT 2026-09-23'
  - id: r2
    kraj: US
    kto: Bloomberg (wywiad z p.o. sekretarz pracy Julie Su)
    rola: redakcja
    gatunek: wywiad
    link: https://www.bloomberg.com/news/videos/2024-08-02/acting-labor-secretary-says-she-s-not-worried-about-recession-risk
    publikacja: '2024-08-02T13:52+00:00'
    aktualizacja: null
    porownywana_wersja: 'opublikowany zapis wywiadu dostępny 2026-09-23; brak historii zmian'
    archiwum: {link: null, wykonano: null}
    naglowek: 'Acting Labor Secretary Says She’s Not Worried About Recession Risk'
    tlumaczenie: 'Pełniąca obowiązki sekretarz pracy nie obawia się ryzyka recesji'
    zostawia_z: 'To argument osoby z administracji rządowej w wywiadzie, nie własna ocena redakcji Bloomberga.'
    sprawdzil: 'GPT 2026-09-23'
kontrasty:
  - miedzy: [r1, r2]
    rodzaj: czyj_glos
    opis: 'Nagłówek redakcyjny o alarmie i głos przedstawicielki administracji o nadal silnym rynku.'
    zastrzezenia: 'ODRZUCONE jako dowód sprzecznych ram dwóch redakcji: różny gatunek, rola i brak godziny Axios; w tekście Axios występują też czynniki uspokajające. Bloomberg sygnalizuje wyraźnie, że to słowa rozmówczyni.'
jak_szukano: ['wyszukiwarka WWW en; otwarto archiwalny komunikat BLS, Axios i stronę wideo Bloomberga wraz z transkrypcją; szukano drugiej redakcji z przeciwną tezą, nie potwierdzono']
---

## Fakt
114 tys. to lipcowa zmiana liczby etatów poza rolnictwem w badaniu zakładów, a 4,3 proc. to stopa bezrobocia z badania gospodarstw. Nie dodawać tych wielkości ani nie pisać, że „114 tys. ludzi straciło pracę”.

## Przekaz
Axios otwiera ryzykiem, lecz opisuje również rosnącą aktywność zawodową i inne zastrzeżenia. Bloomberg prezentuje wypowiedź Julie Su. Zrównanie jej słów ze stanowiskiem całej redakcji tworzyłoby sztuczną sprzeczność.

## Hipoteza odbioru
Nie używać jako pary „media straszą, media uspokajają”. Osobny odcinek o tym, jak działa próg statystyczny, wymaga innej kwerendy.

## Ilustracja
Nie przygotowywać do formatu A/B.

## Uczciwość odcinka
- [x] Odrzucono zestawienie dwóch gatunków i dwóch ról jako kontrast redakcyjny.
- [x] Rozróżniono dwa badania w pierwotnych danych.

## Notatki z pilota
- Czas pracy: nie mierzono osobno; wspólna kwerenda i edycja kart w sesji 2026-09-23 (ok. 15–20 min łącznie dla 8 kart).
- Co było najbardziej żmudne (kandydat do automatyzacji): odróżnienie cytatu polityka od ramy redakcji i odszukanie godzin publikacji.
- Czego zabrakło w karcie: osobne pole dla gatunku relacji i roli rozmówcy (nie tylko wydawcy).
