---
id: 2026-09-23-smiglowiec-braniewo
tytul: Rosyjski Mi-8 przez 42 sekundy w polskiej przestrzeni powietrznej koło Braniewa
status: kandydat
powod_odrzucenia: null
droga: od_wiadomosci        # z naszej bazy: BBC 23.09; polskich relacji o śmigłowcu w bazie nie ma
dziedzina: [bezpieczenstwo]
forma: os_czasu             # tego samego dnia trzy różne zdarzenia na niebie nad Polską; łatwo je pomylić

fakt:
  czas: '2026-09-23T11:08+02:00'   # godzina naruszenia wg relacji z komunikatu DORSZ; komunikatu nie otwierano
  opis: >-
    23 września 2026 rosyjski śmigłowiec Mi-8 z obwodu królewieckiego wleciał na ok. 300 m w polską przestrzeń powietrzną
    na północ od Braniewa i przebywał w niej 42 sekundy. Poderwano myśliwce. Według DORSZ Rosja ponownie testuje gotowość
    obrony powietrznej. Rosyjska redakcja BFM 23.09 odnotowała brak komentarza władz Rosji w chwili publikacji.
  zrodlo_pierwotne: https://x.com/DowOperSZ/status/2102723364439679215   # oryginalny wpis DORSZ; X nie dał się otworzyć, treść za rp.pl

stan_wiedzy_zmienial_sie: true
os_czasu:
  - {czas: '2026-09-23T07:14+02:00', co_wiadomo: 'INNE ZDARZENIE: poranne poderwanie samolotów z powodu ataku Rosji na Ukrainę; DORSZ: przestrzeń nie została naruszona', zrodlo: r1}
  - {czas: '2026-09-23T11:08+02:00', co_wiadomo: 'naruszenie przez Mi-8 koło Braniewa (godzina wg DORSZ w relacjach)', zrodlo: fakt}
  - {czas: '2026-09-23T13:42+02:00', co_wiadomo: 'Rzeczpospolita publikuje wiadomość o Mi-8; obecny nagłówek po aktualizacji o 15:04', zrodlo: r6}
  - {czas: '2026-09-23T15:58+02:00', co_wiadomo: 'INNE ZDARZENIE: Onet (za Dziennikiem Bałtyckim) o poszukiwaniu niezidentyfikowanego obiektu pod Malborkiem', zrodlo: r2}
  - {czas: '2026-09-23T16:25+02:00', co_wiadomo: 'BFM w Rosji relacjonuje polski komunikat i pisze, że brak komentarza strony rosyjskiej', zrodlo: r9}
  - {czas: '2026-09-23T17:37+02:00', co_wiadomo: 'BBC: Polska oskarża rosyjski śmigłowiec o naruszenie przestrzeni', zrodlo: r3}

relacje:
  - id: r1
    kraj: PL
    kto: Onet
    rola: redakcja
    gatunek: wiadomosc
    link: https://wiadomosci.onet.pl/kraj/rosja-atakuje-ukraine-polskie-wojsko-reaguje/7kqptkw
    publikacja: '2026-09-23T05:14+00:00'   # z RSS
    aktualizacja: null
    porownywana_wersja: 'tytuł i lead z RSS pobrane 2026-09-23'
    archiwum: {link: 'https://web.archive.org/web/20260924022437/https://wiadomosci.onet.pl/kraj/rosja-atakuje-ukraine-polskie-wojsko-reaguje/7kqptkw', wykonano: '2026-09-24T02:24Z'}   # własna kopia Save Page Now z 2026-09-24: strona z chwili kopii, nie z dnia publikacji
    naglowek: 'Rosja atakuje Ukrainę. Polska poderwała samoloty'
    tlumaczenie: null
    zostawia_z: 'Działania prewencyjne, przestrzeń nienaruszona. To NIE jest relacja o śmigłowcu (ten wleciał kilka godzin później).'
    sprawdzil: null
  - id: r2
    kraj: PL
    kto: Onet (za Dziennikiem Bałtyckim)
    rola: redakcja
    gatunek: wiadomosc
    link: https://wiadomosci.onet.pl/trojmiasto/akcja-sluzb-pod-malborkiem-poszukiwany-jest-niezidentyfikowany-obiekt/kj8l256
    publikacja: '2026-09-23T13:58+00:00'   # z RSS
    aktualizacja: null
    porownywana_wersja: 'tytuł i lead z RSS pobrane 2026-09-23'
    archiwum: {link: 'https://web.archive.org/web/20260924022510/https://wiadomosci.onet.pl/trojmiasto/akcja-sluzb-pod-malborkiem-poszukiwany-jest-niezidentyfikowany-obiekt/kj8l256', wykonano: '2026-09-24T02:25Z'}   # własna kopia Save Page Now z 2026-09-24: strona z chwili kopii, nie z dnia publikacji
    naglowek: 'Akcja służb pod Malborkiem. Poszukiwany jest niezidentyfikowany obiekt'
    tlumaczenie: null
    zostawia_z: 'Coś mogło spaść koło jednostki wojskowej. Związek ze śmigłowcem nieustalony, nie łączyć.'
    sprawdzil: null
  - id: r3
    kraj: UK
    kto: BBC
    rola: redakcja
    gatunek: wiadomosc
    link: https://www.bbc.co.uk/news/articles/c699d2dn9z0mo
    publikacja: '2026-09-23T15:37+00:00'   # z RSS
    aktualizacja: null
    porownywana_wersja: 'tytuł i lead z RSS pobrane 2026-09-23'
    archiwum: {link: 'https://web.archive.org/web/20260923160024/https://www.bbc.co.uk/news/articles/c699d2dn9z0mo', wykonano: '2026-09-23T16:00Z'}
    naglowek: 'Poland accuses Russian military helicopter of violating its airspace'
    tlumaczenie: 'Polska oskarża rosyjski śmigłowiec wojskowy o naruszenie jej przestrzeni powietrznej'
    zostawia_z: 'Naruszenie jako zarzut strony polskiej („accuses”); w leadzie 42 sekundy i poderwane myśliwce.'
    sprawdzil: null
  - id: r4
    kraj: US
    kto: Reuters (przedruk US News)
    rola: agencja
    gatunek: wiadomosc
    link: https://www.usnews.com/news/world/articles/2026-09-23/russian-military-helicopter-entered-polish-airspace-briefly-polish-army-says
    publikacja: null
    aktualizacja: null
    porownywana_wersja: null
    archiwum: {link: 'https://web.archive.org/web/20260924022601/https://www.usnews.com/news/world/articles/2026-09-23/russian-military-helicopter-entered-polish-airspace-briefly-polish-army-says', wykonano: '2026-09-24T02:26Z'}   # własna kopia Save Page Now z 2026-09-24: strona z chwili kopii, nie z dnia publikacji
    naglowek: 'Russian Military Helicopter Entered Polish Airspace Briefly, Polish Army Says'
    tlumaczenie: 'Rosyjski śmigłowiec wojskowy na krótko wleciał w polską przestrzeń, podaje polska armia'
    zostawia_z: '„Na krótko” w nagłówku; źródłem jest polska armia.'
    sprawdzil: null          # tytuł z wyników wyszukiwania
  - id: r5
    kraj: UA
    kto: Ukraińska Prawda (wersja angielska)
    rola: redakcja
    gatunek: wiadomosc
    link: https://www.pravda.com.ua/eng/news/2026/09/23/8054747/
    publikacja: null
    aktualizacja: null
    porownywana_wersja: null
    archiwum: {link: 'https://web.archive.org/web/20260924022637/https://www.pravda.com.ua/eng/news/2026/09/23/8054747/', wykonano: '2026-09-24T02:26Z'}   # własna kopia Save Page Now z 2026-09-24: strona z chwili kopii, nie z dnia publikacji
    naglowek: 'Russian Mi-8 helicopter violates Polish airspace near Braniewo'
    tlumaczenie: 'Rosyjski śmigłowiec Mi-8 narusza polską przestrzeń powietrzną koło Braniewa'
    zostawia_z: 'Naruszenie jako fakt, bez atrybucji w nagłówku.'
    sprawdzil: null          # tytuł z wyników wyszukiwania
  - id: r6
    kraj: PL
    kto: Rzeczpospolita
    rola: redakcja
    gatunek: wiadomosc
    link: https://www.rp.pl/wojsko/art45179981-rosyjski-smiglowiec-wojskowy-naruszyl-przestrzen-powietrzna-polski
    publikacja: '2026-09-23T13:42+02:00'   # godzina na stronie rp.pl
    aktualizacja: '2026-09-23T15:04+02:00'
    porownywana_wersja: 'bieżący H1 po aktualizacji; wcześniejszy nagłówek z dnia publikacji nieustalony'
    archiwum: {link: 'https://web.archive.org/web/20260924022724/https://www.rp.pl/wojsko/art45179981-rosyjski-smiglowiec-wojskowy-naruszyl-przestrzen-powietrzna-polski', wykonano: '2026-09-24T02:27Z'}   # własna kopia Save Page Now z 2026-09-24: strona z chwili kopii, nie z dnia publikacji
    naglowek: 'Rosyjski śmigłowiec wojskowy naruszył przestrzeń powietrzną Polski'
    tlumaczenie: null
    zostawia_z: 'Naruszenie podane wprost; ocena wojska „Rosja testuje” jest w podtytule i innym tytule strony.'
    sprawdzil: GPT 2026-09-24
  - id: r7
    kraj: US
    kto: Fox News
    rola: redakcja
    gatunek: wiadomosc
    link: https://www.foxnews.com/world/nato-ally-pushes-fort-trump-us-military-base-russian-helicopter-penetrates-airspace
    publikacja: null
    aktualizacja: null
    porownywana_wersja: null
    archiwum: {link: 'https://web.archive.org/web/20260924021435/https://www.foxnews.com/world/nato-ally-pushes-fort-trump-us-military-base-russian-helicopter-penetrates-airspace', wykonano: '2026-09-24T02:14Z'}   # kopia Wayback: pierwsza po publikacji (plx events archive)
    naglowek: "NATO ally pushes 'Fort Trump' US military base as Russian helicopter penetrates airspace"
    tlumaczenie: 'Sojusznik z NATO forsuje amerykańską bazę „Fort Trump”, gdy rosyjski śmigłowiec wdziera się w przestrzeń'
    zostawia_z: 'Śmigłowiec jako uzasadnienie bazy: dwa niezależne zdarzenia w jednym zdaniu (por. karta 2026-09-22-fort-trump).'
    sprawdzil: null          # tytuł z wyników wyszukiwania
  - id: r8
    kraj: PL
    kto: Dowództwo Operacyjne RSZ
    rola: strona_sprawy
    gatunek: komunikat
    link: https://x.com/DowOperSZ/status/2102723364439679215
    publikacja: null          # nie potwierdzono godziny w samym wpisie; 11:08 to czas zdarzenia
    aktualizacja: null
    porownywana_wersja: 'wpis X rozpoznany w wyszukiwarce, treść cytowana w r6; oryginał wymaga otwarcia'
    archiwum: {link: null, wykonano: null}
    naglowek: null           # wpis społecznościowy nie ma odrębnego nagłówka
    tlumaczenie: null
    zostawia_z: 'Źródło danych 11:08, do 300 m i 42 sekundy; nie jest niezależną redakcją.'
    sprawdzil: null
  - id: r9
    kraj: RU
    kto: Business FM / BFM.ru
    rola: redakcja
    gatunek: wiadomosc
    link: https://www.bfm.ru/news/618787
    publikacja: '2026-09-23T17:25+03:00'  # godzina moskiewska widoczna na stronie
    aktualizacja: null
    porownywana_wersja: 'strona otwarta 2026-09-24; kopii z dnia publikacji nie znaleziono'
    archiwum: {link: 'https://web.archive.org/web/20260924022853/https://www.bfm.ru/news/618787', wykonano: '2026-09-24T02:28Z'}   # własna kopia Save Page Now z 2026-09-24: strona z chwili kopii, nie z dnia publikacji
    naglowek: 'Польша обвинила Россию в нарушении воздушного пространства страны'
    tlumaczenie: 'Polska oskarżyła Rosję o naruszenie przestrzeni powietrznej kraju'
    zostawia_z: 'Opis polskiego zarzutu; tekst stwierdza, że komentarza ze strony rosyjskiej na razie brak.'
    sprawdzil: GPT 2026-09-24

kontrasty:
  - miedzy: [r3, r5]
    rodzaj: dobor_slow
    opis: 'BBC: Polska „oskarża” (zarzut jednej strony). UP: śmigłowiec „narusza” (fakt). Reuters: „na krótko… podaje armia”.'
    zastrzezenia: 'BFM również pisze „oskarżyła”, ale to relacja o polskim stanowisku, nie odpowiedź władz Rosji. Nie ustalono późniejszego oficjalnego stanowiska. Tytuły r4 i r5 tylko z wyszukiwarki.'
  - miedzy: [r3, r7]
    rodzaj: kolejnosc_informacji
    opis: 'Fox łączy naruszenie z kampanią Nawrockiego o „Fort Trump”; BBC opisuje samo naruszenie.'
    zastrzezenia: 'Związek wskazuje redakcja, nie strony. Wywiad Nawrockiego dla Bloomberga był dzień wcześniej (22.09).'

jak_szukano: ['nasza baza (RSS 23.09): Onet, rp, BBC', 'wyszukiwarka WWW en/pl: Reuters/US News, UP eng, Kyiv Post, TVP World, Euronews, Fox, rp, TVN24, Defence24, Interia', 'newscord.org (porównywarka redakcji) dla kontroli', 'wyszukiwarka WWW pl/ru/en 24.09: DORSZ X i Facebook, rp.pl, bfm.ru, mid.ru, mil.ru; otwarte rp.pl i bfm.ru']
---

## Fakt
Mi-8 z obwodu królewieckiego wleciał o 11:08 na ok. 300 m i był nad Polską 42 sekundy. Pilot sam zawrócił, a myśliwce poderwano.
Tego samego dnia są jeszcze dwa inne zdarzenia na niebie: poranne poderwanie samolotów bez naruszenia przestrzeni
i popołudniowe poszukiwania obiektu pod Malborkiem.

## Przekaz
Nagłówki różnią się czasownikiem: „oskarża”, „narusza”, „wleciał na krótko”, „wdziera się”. Polska Rzeczpospolita używa „naruszył”, a rosyjskie BFM „Polska oskarżyła”. To wybór słów redakcji, nie rosyjska odpowiedź. Fox wiąże zdarzenie z „Fort Trump”.
**Pułapka:** porównywarka newscord.org pokazuje jako „kluczową rozbieżność” jedną redakcję z „brief violation” i drugą z „no violation detected”.
To wygląda na pomylenie z porannym komunikatem o innym zdarzeniu (r1). Do sprawdzenia, ale dokładnie tę pomyłkę ma wyłapywać nasza oś czasu.

## Hipoteza odbioru
„Oskarża” może zostawić widza z myślą, że fakt jest sporny. „Wdziera się” i „Rosja testuje” zostawiają z alarmem.

## Ilustracja
Zegar z trzema znacznikami (7:14, 11:08, 15:58) i trzema różnymi kolorami. Linia granicy z kreską 300 m. Bez rekonstrukcji lotu.

## Uczciwość odcinka
- [ ] Otworzyć wpis DORSZ w X; potwierdzić godzinę publikacji na samej platformie i treść bez pośrednictwa redakcji.
- [ ] Nie łączyć poranka, śmigłowca i Malborka w jedną historię.
- [ ] Ponowić sprawdzenie oficjalnej odpowiedzi Rosji przed odcinkiem; BFM 23.09 o 17:25 MSK notowało jej brak, a przeszukanie stron MSZ i MON Rosji 24.09 nie ujawniło stanowiska. Brak znalezionego komunikatu nie dowodzi, że go nie było.
- [ ] Porównanie z kartą 2023-08-01-smiglowce-bialowieza: tu wojsko potwierdziło od razu, w 2023 nie.

## Notatki z pilota
- Czas pracy: ok. 15 min (Claude).
- Co było najbardziej żmudne: rozplątanie trzech zdarzeń jednego dnia; dodatkowe wyszukanie i lektura źródeł 24.09 ok. 20 min (GPT), trudność: niedostępny bezpośrednio post X i brak potwierdzenia rosyjskiej odpowiedzi.
- Czego zabrakło w karcie: pole „zdarzenia pokrewne tego dnia, nie mylić”. Na razie wpisy w os_czasu z dopiskiem INNE ZDARZENIE.
