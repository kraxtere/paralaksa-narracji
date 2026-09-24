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
    obrony powietrznej. Rosja (stan na 23.09) nie skomentowała.
  zrodlo_pierwotne: null     # komunikat Dowództwa Operacyjnego RSZ (X / gov.pl) do dopięcia

stan_wiedzy_zmienial_sie: true
os_czasu:
  - {czas: '2026-09-23T07:14+02:00', co_wiadomo: 'INNE ZDARZENIE: poranne poderwanie samolotów z powodu ataku Rosji na Ukrainę; DORSZ: przestrzeń nie została naruszona', zrodlo: r1}
  - {czas: '2026-09-23T11:08+02:00', co_wiadomo: 'naruszenie przez Mi-8 koło Braniewa (godzina wg DORSZ w relacjach)', zrodlo: fakt}
  - {czas: '2026-09-23T15:58+02:00', co_wiadomo: 'INNE ZDARZENIE: Onet (za Dziennikiem Bałtyckim) o poszukiwaniu niezidentyfikowanego obiektu pod Malborkiem', zrodlo: r2}
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
    archiwum: {link: null, wykonano: null}
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
    archiwum: {link: null, wykonano: null}
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
    archiwum: {link: null, wykonano: null}
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
    archiwum: {link: null, wykonano: null}
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
    publikacja: null
    aktualizacja: null
    porownywana_wersja: null
    archiwum: {link: null, wykonano: null}
    naglowek: 'Rosyjski śmigłowiec wleciał nad Polskę, poderwano myśliwce. „Rosja testuje”'
    tlumaczenie: null
    zostawia_z: 'Ocena wojska („Rosja testuje”) w nagłówku.'
    sprawdzil: null          # tytuł z wyników wyszukiwania; nie było go w naszym RSS rp
  - id: r7
    kraj: US
    kto: Fox News
    rola: redakcja
    gatunek: wiadomosc
    link: https://www.foxnews.com/world/nato-ally-pushes-fort-trump-us-military-base-russian-helicopter-penetrates-airspace
    publikacja: null
    aktualizacja: null
    porownywana_wersja: null
    archiwum: {link: null, wykonano: null}
    naglowek: "NATO ally pushes 'Fort Trump' US military base as Russian helicopter penetrates airspace"
    tlumaczenie: 'Sojusznik z NATO forsuje amerykańską bazę „Fort Trump”, gdy rosyjski śmigłowiec wdziera się w przestrzeń'
    zostawia_z: 'Śmigłowiec jako uzasadnienie bazy: dwa niezależne zdarzenia w jednym zdaniu (por. karta 2026-09-22-fort-trump).'
    sprawdzil: null          # tytuł z wyników wyszukiwania

kontrasty:
  - miedzy: [r3, r5]
    rodzaj: dobor_slow
    opis: 'BBC: Polska „oskarża” (zarzut jednej strony). UP: śmigłowiec „narusza” (fakt). Reuters: „na krótko… podaje armia”.'
    zastrzezenia: 'Rosja nie zaprzeczyła, więc „oskarża” nie oznacza sporu o fakty. Tytuły r4 i r5 tylko z wyszukiwarki.'
  - miedzy: [r3, r7]
    rodzaj: kolejnosc_informacji
    opis: 'Fox łączy naruszenie z kampanią Nawrockiego o „Fort Trump”; BBC opisuje samo naruszenie.'
    zastrzezenia: 'Związek wskazuje redakcja, nie strony. Wywiad Nawrockiego dla Bloomberga był dzień wcześniej (22.09).'

jak_szukano: ['nasza baza (RSS 23.09): Onet, rp, BBC', 'wyszukiwarka WWW en/pl: Reuters/US News, UP eng, Kyiv Post, TVP World, Euronews, Fox, rp, TVN24, Defence24, Interia', 'newscord.org (porównywarka redakcji) dla kontroli']
---

## Fakt
Mi-8 z obwodu królewieckiego wleciał o 11:08 na ok. 300 m i był nad Polską 42 sekundy. Pilot sam zawrócił, a myśliwce poderwano.
Tego samego dnia są jeszcze dwa inne zdarzenia na niebie: poranne poderwanie samolotów bez naruszenia przestrzeni
i popołudniowe poszukiwania obiektu pod Malborkiem.

## Przekaz
Nagłówki różnią się czasownikiem: „oskarża”, „narusza”, „wleciał na krótko”, „wdziera się”. Fox wiąże zdarzenie z „Fort Trump”.
**Pułapka:** porównywarka newscord.org pokazuje jako „kluczową rozbieżność” jedną redakcję z „brief violation” i drugą z „no violation detected”.
To wygląda na pomylenie z porannym komunikatem o innym zdarzeniu (r1). Do sprawdzenia, ale dokładnie tę pomyłkę ma wyłapywać nasza oś czasu.

## Hipoteza odbioru
„Oskarża” może zostawić widza z myślą, że fakt jest sporny. „Wdziera się” i „Rosja testuje” zostawiają z alarmem.

## Ilustracja
Zegar z trzema znacznikami (7:14, 11:08, 15:58) i trzema różnymi kolorami. Linia granicy z kreską 300 m. Bez rekonstrukcji lotu.

## Uczciwość odcinka
- [ ] Komunikat DORSZ (godzina publikacji) jako źródło pierwotne.
- [ ] Nie łączyć poranka, śmigłowca i Malborka w jedną historię.
- [ ] Sprawdzić, czy Rosja zareagowała później (w podobnych incydentach mówiła o awarii nawigacji).
- [ ] Porównanie z kartą 2023-08-01-smiglowce-bialowieza: tu wojsko potwierdziło od razu, w 2023 nie.

## Notatki z pilota
- Czas pracy: ok. 15 min (Claude).
- Co było najbardziej żmudne: rozplątanie trzech zdarzeń jednego dnia.
- Czego zabrakło w karcie: pole „zdarzenia pokrewne tego dnia, nie mylić”. Na razie wpisy w os_czasu z dopiskiem INNE ZDARZENIE.
