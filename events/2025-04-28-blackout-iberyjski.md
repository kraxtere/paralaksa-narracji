---
id: 2025-04-28-blackout-iberyjski
tytul: Awaria sieci pozbawia prądu Hiszpanię i Portugalię
status: odrzucony
powod_odrzucenia: 'Pozorny kontrast narracyjny: hiszpański i portugalski reportaż opisują lokalne skutki tego samego blackoutu podobnym językiem dezorganizacji. Różni się miejsce scen, a tekst hiszpański aktualizowano do późnego wieczora. Nie ma tu udowodnionych przeciwstawnych ram redakcji ani równoczesnych wersji.'
droga: od_zdarzenia
dziedzina: [energetyka, bezpieczenstwo]
forma: dwie_opowiesci
fakt:
  czas: '2025-04-28T12:33+02:00'
  opis: 'Kontynentalne systemy elektroenergetyczne Hiszpanii i Portugalii doświadczyły masowego blackoutu; wskazanie dokładnej przyczyny wymaga późniejszego raportu, którego nie wolno wkładać w usta redakcjom z pierwszego dnia.'
  zrodlo_pierwotne: https://www.entsoe.eu/publications/blackout/28-april-2025-iberian-blackout/
stan_wiedzy_zmienial_sie: true
os_czasu:
  - {czas: '2025-04-28T12:33+02:00', co_wiadomo: 'początek utraty zasilania według późniejszego raportu operatorów', zrodlo: https://www.entsoe.eu/publications/blackout/28-april-2025-iberian-blackout/}
  - {czas: '2025-04-28T15:54+01:00', co_wiadomo: 'Observador przedstawia skutki w Portugalii; przyczyny na ten moment niepotwierdzone', zrodlo: r2}
  - {czas: '2025-04-28T22:34+02:00', co_wiadomo: 'El País nadal pisze o braku ostatecznego wyjaśnienia przyczyny, dodając wieczorne informacje o przywracaniu zasilania', zrodlo: r1}
relacje:
  - id: r1
    kraj: ES
    kto: El País
    rola: redakcja
    link: https://elpais.com/economia/2025-04-28/apagon-electrico-masivo-en-espana.html
    publikacja: '2025-04-28T12:54+02:00'
    aktualizacja: '2025-04-28T22:34+02:00'
    porownywana_wersja: 'aktualizacja 2025-04-28T22:34+02:00; bez kopii z 12:54'
    archiwum: {link: null, wykonano: null}
    naglowek: 'Un apagón eléctrico masivo en España y Portugal desata el caos'
    tlumaczenie: 'Masowy blackout w Hiszpanii i Portugalii wywołuje chaos'
    zostawia_z: 'Brak prądu dezorganizuje życie w Hiszpanii i Portugalii; przyczyna pozostaje przedmiotem dochodzenia.'
    sprawdzil: 'GPT 2026-09-23'
  - id: r2
    kraj: PT
    kto: Observador (tekst z materiałami Agência Lusa)
    rola: redakcja
    link: https://observador.pt/2025/04/28/avioes-e-comboios-parados-pessoas-retiradas-do-metro-de-lisboa-semaforos-desligados-e-escolas-fechadas-um-pais-as-escuras/
    publikacja: '2025-04-28T15:54+01:00'
    aktualizacja: null # na stronie bez godziny aktualizacji
    porownywana_wersja: 'wersja dostępna 2026-09-23; brak historii zmian'
    archiwum: {link: null, wykonano: null}
    naglowek: 'Aviões e comboios parados, pessoas retiradas do Metro de Lisboa…' # skrót nagłówka do 15 słów
    tlumaczenie: 'Samoloty i pociągi stoją, pasażerowie ewakuowani z metra w Lizbonie…'
    zostawia_z: 'Konkrety o transporcie, szpitalach i szkołach w Portugalii; rząd nie potwierdza przyczyny.'
    sprawdzil: 'GPT 2026-09-23'
kontrasty:
  - miedzy: [r1, r2]
    rodzaj: kolejnosc_informacji
    opis: 'Hiszpański tekst patrzy szeroko na chaos i przywracanie zasilania, portugalski lokalizuje skutki w usługach publicznych.'
    zastrzezenia: 'ODRZUCONE jako przeciwstawna opowieść: oba teksty alarmują o realnych skutkach; to różne lokalne sceny i różne momenty aktualizacji. Nie należy opowiadać o przypisaniu winy na podstawie niepotwierdzonych hipotez z dnia zdarzenia.'
jak_szukano: ['wyszukiwarka WWW es/pt/en; otwarto El País, Observador, stronę ENTSO-E; sprawdzono strefy CEST i WEST oraz godzinę aktualizacji']
---

## Fakt
Masowa awaria rozpoczęła się o 12:33 CEST, czyli 11:33 w kontynentalnej Portugalii. Przyczyna nie była wówczas ustalona; późniejsze wyniki dochodzeń to osobne zdarzenie informacyjne.

## Przekaz
Obie relacje przedstawiają zakłócenia jako poważne. Sceny w Lizbonie i Madrycie są różne, ale to różnica geograficznej perspektywy na realne skutki, bez wykazanego mechanizmu przeciwnych nastrojów.

## Hipoteza odbioru
Nie robić z tej pary odcinka „oni uspokajali, oni straszyli”. Może posłużyć jako negatywny przykład przy poszukiwaniu kontrastu transgranicznego.

## Ilustracja
Nie przygotowywać odcinka A/B. Jeśli użyty edukacyjnie, jedna mapa czasu i lokalne skutki oznaczone jako lokalne.

## Uczciwość odcinka
- [x] Różnica czasu hiszpańskiego i portugalskiego uwzględniona.
- [x] Nie nadano wstecz przyczyny awarii pierwszym relacjom.

## Notatki z pilota
- Czas pracy: nie mierzono osobno; wspólna kwerenda i edycja kart w sesji 2026-09-23 (ok. 15–20 min łącznie dla 8 kart).
- Co było najbardziej żmudne (kandydat do automatyzacji): normalizacja stref i identyfikacja aktualizowanego reportażu.
- Czego zabrakło w karcie: pole lokalizacji opisywanego skutku, osobne od kraju redakcji.
